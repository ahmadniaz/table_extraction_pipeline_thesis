import uuid
import csv
import io
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, GroundTruthTable, ExtractionResult, EvaluationScore
from app.services.evaluation.runner import EvaluationRunner
from app.services.evaluation.metrics import compute_cell_f1, compute_teds, compute_grits

logger = logging.getLogger(__name__)
router = APIRouter(tags=["evaluation"])

ALL_TOOLS = ["pymupdf", "docling", "google_docai", "gpt5", "claude_sonnet", "mistral"]


class EvaluateRequest(BaseModel):
    tools: List[str] = ["all"]


class BatchEvaluateRequest(BaseModel):
    tools: List[str] = ["all"]
    tier: str = "all"


def _resolve_tools(tools: List[str]) -> List[str]:
    if "all" in tools:
        return ALL_TOOLS
    invalid = [t for t in tools if t not in ALL_TOOLS]
    if invalid:
        raise HTTPException(400, f"Unknown tools: {invalid}. Valid: {ALL_TOOLS}")
    return tools


@router.post("/api/evaluate/{doc_id}")
async def evaluate_document(
    doc_id: uuid.UUID,
    body: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    gt_result = await db.execute(
        select(GroundTruthTable)
        .where(GroundTruthTable.document_id == doc_id)
        .order_by(GroundTruthTable.table_index)
    )
    ground_truths = gt_result.scalars().all()
    if not ground_truths:
        raise HTTPException(
            422, "No ground truth tables for this document. Upload ground truth first."
        )

    tools = _resolve_tools(body.tools)
    runner = EvaluationRunner()
    all_results = []

    for tool_name in tools:
        extraction_results = await runner.run_tool(tool_name, doc.file_path, doc.id, db)
        for er in extraction_results:
            gt_match = next((g for g in ground_truths if g.table_index == er.table_index), None)
            if gt_match and not er.error_message:
                gt_table = {"headers": gt_match.headers, "rows": gt_match.rows}
                ext_table = {"headers": er.extracted_headers, "rows": er.extracted_rows}

                f1_metrics = compute_cell_f1(er.extracted_rows or [], gt_match.rows or [])
                teds = compute_teds(ext_table, gt_table)
                grits = compute_grits(ext_table, gt_table)

                score = EvaluationScore(
                    extraction_result_id=er.id,
                    precision=f1_metrics["precision"],
                    recall=f1_metrics["recall"],
                    f1_score=f1_metrics["f1"],
                    teds_score=teds,
                    grits_top=grits["top"],
                    grits_con=grits["con"],
                    grits_loc=grits["loc"],
                )
                db.add(score)

            all_results.append({
                "tool": tool_name,
                "table_index": er.table_index,
                "processing_time_ms": er.processing_time_ms,
                "cost_usd": float(er.cost_usd) if er.cost_usd else None,
                "error": er.error_message,
                "has_ground_truth": gt_match is not None,
            })

    await db.commit()
    return {"document_id": str(doc_id), "results": all_results}


@router.post("/api/evaluate/batch")
async def evaluate_batch(
    body: BatchEvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    query = select(Document)
    if body.tier != "all":
        if body.tier not in ("low", "medium", "high"):
            raise HTTPException(400, "tier must be 'all', 'low', 'medium', or 'high'")
        query = query.where(Document.complexity_tier == body.tier)

    result = await db.execute(query.order_by(Document.uploaded_at))
    docs = result.scalars().all()
    if not docs:
        raise HTTPException(404, "No documents found matching criteria")

    tools = _resolve_tools(body.tools)
    runner = EvaluationRunner()
    summary = []

    for doc in docs:
        gt_result = await db.execute(
            select(GroundTruthTable)
            .where(GroundTruthTable.document_id == doc.id)
            .order_by(GroundTruthTable.table_index)
        )
        ground_truths = gt_result.scalars().all()
        if not ground_truths:
            summary.append({
                "document_id": str(doc.id),
                "filename": doc.filename,
                "status": "skipped",
                "reason": "no ground truth",
            })
            continue

        doc_results = []
        for tool_name in tools:
            extraction_results = await runner.run_tool(tool_name, doc.file_path, doc.id, db)
            for er in extraction_results:
                gt_match = next((g for g in ground_truths if g.table_index == er.table_index), None)
                if gt_match and not er.error_message:
                    gt_table = {"headers": gt_match.headers, "rows": gt_match.rows}
                    ext_table = {"headers": er.extracted_headers, "rows": er.extracted_rows}

                    f1_metrics = compute_cell_f1(er.extracted_rows or [], gt_match.rows or [])
                    teds = compute_teds(ext_table, gt_table)
                    grits = compute_grits(ext_table, gt_table)

                    score = EvaluationScore(
                        extraction_result_id=er.id,
                        precision=f1_metrics["precision"],
                        recall=f1_metrics["recall"],
                        f1_score=f1_metrics["f1"],
                        teds_score=teds,
                        grits_top=grits["top"],
                        grits_con=grits["con"],
                        grits_loc=grits["loc"],
                    )
                    db.add(score)
                doc_results.append(tool_name)

        await db.commit()
        summary.append({
            "document_id": str(doc.id),
            "filename": doc.filename,
            "status": "evaluated",
            "tools_run": doc_results,
        })

    return {"batch_size": len(docs), "results": summary}


@router.get("/api/results/")
async def get_all_results(db: AsyncSession = Depends(get_db)):
    query = (
        select(EvaluationScore, ExtractionResult, Document)
        .join(ExtractionResult, EvaluationScore.extraction_result_id == ExtractionResult.id)
        .join(Document, ExtractionResult.document_id == Document.id)
        .order_by(Document.complexity_tier, ExtractionResult.tool_name, ExtractionResult.table_index)
    )
    result = await db.execute(query)
    rows = result.all()

    output = []
    for score, er, doc in rows:
        output.append({
            "document_id": str(doc.id),
            "filename": doc.filename,
            "complexity_tier": doc.complexity_tier,
            "tool_name": er.tool_name,
            "table_index": er.table_index,
            "processing_time_ms": er.processing_time_ms,
            "cost_usd": float(er.cost_usd) if er.cost_usd else None,
            "precision": float(score.precision) if score.precision else None,
            "recall": float(score.recall) if score.recall else None,
            "f1_score": float(score.f1_score) if score.f1_score else None,
            "teds_score": float(score.teds_score) if score.teds_score else None,
            "grits_top": float(score.grits_top) if score.grits_top else None,
            "grits_con": float(score.grits_con) if score.grits_con else None,
            "grits_loc": float(score.grits_loc) if score.grits_loc else None,
        })
    return output


@router.get("/api/results/{doc_id}")
async def get_document_results(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Document not found")

    query = (
        select(EvaluationScore, ExtractionResult)
        .join(ExtractionResult, EvaluationScore.extraction_result_id == ExtractionResult.id)
        .where(ExtractionResult.document_id == doc_id)
        .order_by(ExtractionResult.tool_name, ExtractionResult.table_index)
    )
    result = await db.execute(query)
    rows = result.all()

    output = []
    for score, er in rows:
        output.append({
            "tool_name": er.tool_name,
            "table_index": er.table_index,
            "processing_time_ms": er.processing_time_ms,
            "cost_usd": float(er.cost_usd) if er.cost_usd else None,
            "error": er.error_message,
            "precision": float(score.precision) if score.precision else None,
            "recall": float(score.recall) if score.recall else None,
            "f1_score": float(score.f1_score) if score.f1_score else None,
            "teds_score": float(score.teds_score) if score.teds_score else None,
            "grits_top": float(score.grits_top) if score.grits_top else None,
            "grits_con": float(score.grits_con) if score.grits_con else None,
            "grits_loc": float(score.grits_loc) if score.grits_loc else None,
        })
    return output


@router.get("/api/results/export/csv")
async def export_results_csv(db: AsyncSession = Depends(get_db)):
    query = (
        select(EvaluationScore, ExtractionResult, Document)
        .join(ExtractionResult, EvaluationScore.extraction_result_id == ExtractionResult.id)
        .join(Document, ExtractionResult.document_id == Document.id)
        .order_by(Document.complexity_tier, ExtractionResult.tool_name)
    )
    result = await db.execute(query)
    rows = result.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "document_id", "filename", "complexity_tier", "tool_name", "table_index",
        "processing_time_ms", "cost_usd",
        "precision", "recall", "f1_score",
        "teds_score", "grits_top", "grits_con", "grits_loc",
    ])
    for score, er, doc in rows:
        writer.writerow([
            str(doc.id), doc.filename, doc.complexity_tier,
            er.tool_name, er.table_index,
            er.processing_time_ms,
            float(er.cost_usd) if er.cost_usd else "",
            float(score.precision) if score.precision else "",
            float(score.recall) if score.recall else "",
            float(score.f1_score) if score.f1_score else "",
            float(score.teds_score) if score.teds_score else "",
            float(score.grits_top) if score.grits_top else "",
            float(score.grits_con) if score.grits_con else "",
            float(score.grits_loc) if score.grits_loc else "",
        ])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=evaluation_results.csv"},
    )
