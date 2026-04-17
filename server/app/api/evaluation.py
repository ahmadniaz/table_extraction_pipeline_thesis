import uuid
import csv
import io
import logging
from typing import List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, GroundTruthTable, ExtractionResult, EvaluationScore
from app.services.evaluation.runner import EvaluationRunner
from app.services.evaluation.metrics import compute_cell_f1, compute_teds, compute_grits

logger = logging.getLogger(__name__)
router = APIRouter(tags=["evaluation"])

ALL_TOOLS = ["pymupdf", "docling", "aws_textract", "google_docai", "gpt5", "claude_sonnet", "mistral"]

_SCORE_ZERO_NOTE = "Scored as 0 — tool produced no output"

# Extraction outcomes we treat as idempotent: re-calling POST /api/extract returns already_exists.
# Any other failure_reason (e.g. api_error) must allow delete + re-run so Retry works.
_FAILURE_REASONS_IDEMPOTENT_OK = frozenset({"tool_limitation", "empty_output"})


async def _mark_extractions_draft(
    db: AsyncSession, doc_id: uuid.UUID, tool_name: str
) -> None:
    """Mark all extraction rows for this tool as draft until the user saves from the editor."""
    await db.execute(
        update(ExtractionResult)
        .where(
            and_(
                ExtractionResult.document_id == doc_id,
                ExtractionResult.tool_name == tool_name,
            )
        )
        .values(is_draft=True)
    )
    await db.commit()


def _should_replace_existing_extraction(existing: List[ExtractionResult]) -> bool:
    """True if existing rows should be deleted and extraction re-run."""
    if not existing:
        return False
    if any(bool(getattr(r, "is_transient_failure", False)) for r in existing):
        return True
    for r in existing:
        fr = getattr(r, "failure_reason", None)
        if fr and fr not in _FAILURE_REASONS_IDEMPOTENT_OK:
            return True
    return False


def _summarise_extraction_rows(results: List[ExtractionResult]) -> dict:
    """Build per-tool extraction response payload from one or more ExtractionResult rows."""
    ordered = sorted(results, key=lambda r: r.table_index)
    first = ordered[0]
    if first.extracted_rows and isinstance(first.extracted_rows, list) and len(first.extracted_rows) > 0:
        tables_extracted = len(ordered)
    else:
        tables_extracted = 0
    processing_time_ms = max((r.processing_time_ms or 0) for r in ordered)
    cost_usd = sum(float(r.cost_usd or 0) for r in ordered)
    return {
        "extraction_result_id": str(first.id),
        "tool_name": first.tool_name,
        "tables_extracted": tables_extracted,
        "processing_time_ms": processing_time_ms,
        "cost_usd": cost_usd,
        "failure_reason": first.failure_reason,
        "is_transient_failure": bool(first.is_transient_failure),
    }


class EvaluateRequest(BaseModel):
    tools: List[str] = ["all"]


class BatchEvaluateRequest(BaseModel):
    tools: List[str] = ["all"]
    tier: str = "all"


class ExtractionTableUpdate(BaseModel):
    """One table in manual extraction edit (order in array = table_index after save)."""

    headers: List[str]
    rows: List[List[Any]]


class PutExtractionsBody(BaseModel):
    tables: List[ExtractionTableUpdate]


def _resolve_tools(tools: List[str]) -> List[str]:
    if "all" in tools:
        return ALL_TOOLS
    invalid = [t for t in tools if t not in ALL_TOOLS]
    if invalid:
        raise HTTPException(400, f"Unknown tools: {invalid}. Valid: {ALL_TOOLS}")
    return tools


@router.post("/api/extract/{doc_id}/{tool_name}")
async def extract_single_tool(
    doc_id: uuid.UUID,
    tool_name: str,
    force: bool = Query(
        False,
        description="Delete existing extraction rows and run again (evaluation UI Re-run / Retry).",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Run a single extraction tool on one document (idempotent unless prior run was transient)."""
    if tool_name not in ALL_TOOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tool_name '{tool_name}'. Valid: {ALL_TOOLS}",
        )

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    existing_res = await db.execute(
        select(ExtractionResult)
        .where(
            and_(
                ExtractionResult.document_id == doc_id,
                ExtractionResult.tool_name == tool_name,
            )
        )
        .order_by(ExtractionResult.table_index)
    )
    existing = list(existing_res.scalars().all())

    if existing:
        if not force and not _should_replace_existing_extraction(existing):
            out = _summarise_extraction_rows(existing)
            out["already_exists"] = True
            out["extraction_executed"] = False
            return out
        er_ids = [r.id for r in existing]
        await db.execute(delete(EvaluationScore).where(EvaluationScore.extraction_result_id.in_(er_ids)))
        await db.execute(
            delete(ExtractionResult).where(
                and_(
                    ExtractionResult.document_id == doc_id,
                    ExtractionResult.tool_name == tool_name,
                )
            )
        )
        await db.commit()

    runner = EvaluationRunner()
    rows = await runner.run_tool(tool_name, doc.file_path, doc.id, db)
    await _mark_extractions_draft(db, doc_id, tool_name)
    out = _summarise_extraction_rows(rows)
    out["already_exists"] = False
    out["extraction_executed"] = True
    return out


@router.post("/api/evaluate-tool/{doc_id}/{tool_name}")
async def evaluate_tool_for_document(
    doc_id: uuid.UUID,
    tool_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Score existing extraction results for one tool against confirmed ground truth."""
    if tool_name not in ALL_TOOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tool_name '{tool_name}'. Valid: {ALL_TOOLS}",
        )

    doc_res = await db.execute(select(Document).where(Document.id == doc_id))
    if not doc_res.scalar_one_or_none():
        raise HTTPException(404, "Document not found")

    er_res = await db.execute(
        select(ExtractionResult)
        .where(
            and_(
                ExtractionResult.document_id == doc_id,
                ExtractionResult.tool_name == tool_name,
            )
        )
        .order_by(ExtractionResult.table_index)
    )
    extractions = list(er_res.scalars().all())
    if not extractions:
        raise HTTPException(404, "No extraction results for this document and tool.")

    for er in extractions:
        if er.is_transient_failure or er.failure_reason in ("rate_limit", "server_down", "timeout"):
            return JSONResponse(
                status_code=503,
                content={
                    "error": "transient_failure",
                    "message": (
                        "Extraction failed due to API issue, not tool limitation. "
                        "Please retry extraction before evaluating."
                    ),
                },
            )

    if any(bool(getattr(er, "is_draft", False)) for er in extractions):
        return JSONResponse(
            status_code=422,
            content={
                "error": "draft_extraction",
                "message": "Open the extraction editor, review tables, and click Save extraction before scoring.",
            },
        )

    gt_res = await db.execute(
        select(GroundTruthTable)
        .where(
            and_(
                GroundTruthTable.document_id == doc_id,
                GroundTruthTable.confirmed.is_(True),
            )
        )
        .order_by(GroundTruthTable.table_index)
    )
    ground_truths = list(gt_res.scalars().all())
    if not ground_truths:
        return JSONResponse(
            status_code=422,
            content={"error": "No confirmed ground truth for this document."},
        )

    scores_out: List[dict] = []
    by_index = {e.table_index: e for e in extractions}

    for gt in ground_truths:
        er = by_index.get(gt.table_index)
        if er is None:
            continue

        await db.execute(delete(EvaluationScore).where(EvaluationScore.extraction_result_id == er.id))

        if er.failure_reason in ("tool_limitation", "empty_output"):
            note = _SCORE_ZERO_NOTE
            if er.error_message:
                if note not in er.error_message:
                    er.error_message = f"{er.error_message} | {note}"
            else:
                er.error_message = note
            score = EvaluationScore(
                extraction_result_id=er.id,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                teds_score=0.0,
                grits_top=0.0,
                grits_con=0.0,
                grits_loc=0.0,
            )
            db.add(score)
            await db.commit()
            scores_out.append({
                "table_index": gt.table_index,
                "f1": 0.0,
                "teds": 0.0,
                "grits_top": 0.0,
                "grits_con": 0.0,
                "grits_loc": 0.0,
            })
            continue

        gt_table = {"headers": gt.headers, "rows": gt.rows}
        ext_table = {"headers": er.extracted_headers, "rows": er.extracted_rows}

        f1_metrics = compute_cell_f1(er.extracted_rows or [], gt.rows or [])
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
        await db.commit()

        scores_out.append({
            "table_index": gt.table_index,
            "f1": f1_metrics["f1"],
            "teds": teds,
            "grits_top": grits["top"],
            "grits_con": grits["con"],
            "grits_loc": grits["loc"],
        })

    return scores_out


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
        if body.tier not in ("low", "medium", "high", "unconfirmed"):
            raise HTTPException(
                400,
                "tier must be 'all', 'low', 'medium', 'high', or 'unconfirmed'",
            )
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
            "failure_reason": er.failure_reason,
            "is_transient_failure": bool(er.is_transient_failure),
        })
    return output


@router.get("/api/extractions/{doc_id}/{tool_name}")
async def get_extractions_for_tool(
    doc_id: uuid.UUID,
    tool_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Raw extraction rows for a document and tool (for preview before/without evaluation scores)."""
    if tool_name not in ALL_TOOLS:
        raise HTTPException(400, f"Unknown tool_name. Valid: {ALL_TOOLS}")
    doc_res = await db.execute(select(Document).where(Document.id == doc_id))
    if not doc_res.scalar_one_or_none():
        raise HTTPException(404, "Document not found")
    er_result = await db.execute(
        select(ExtractionResult)
        .where(
            and_(
                ExtractionResult.document_id == doc_id,
                ExtractionResult.tool_name == tool_name,
            )
        )
        .order_by(ExtractionResult.table_index)
    )
    ers = list(er_result.scalars().all())
    return [
        {
            "extraction_result_id": str(er.id),
            "table_index": er.table_index,
            "extracted_headers": er.extracted_headers,
            "extracted_rows": er.extracted_rows,
            "processing_time_ms": er.processing_time_ms,
            "cost_usd": float(er.cost_usd) if er.cost_usd else None,
            "error_message": er.error_message,
            "failure_reason": er.failure_reason,
            "is_transient_failure": bool(er.is_transient_failure),
            "is_draft": bool(getattr(er, "is_draft", False)),
        }
        for er in ers
    ]


@router.put("/api/extractions/{doc_id}/{tool_name}")
async def put_extractions_for_tool(
    doc_id: uuid.UUID,
    tool_name: str,
    body: PutExtractionsBody,
    db: AsyncSession = Depends(get_db),
):
    """
    Replace all ExtractionResult rows for a document + tool with manually edited tables.
    Preserves processing_time_ms, cost_usd, and raw_output on table_index 0 from the prior run.
    Deletes dependent EvaluationScore rows for superseded extraction results.
    """
    if tool_name not in ALL_TOOLS:
        raise HTTPException(400, f"Unknown tool_name. Valid: {ALL_TOOLS}")

    doc_res = await db.execute(select(Document).where(Document.id == doc_id))
    if not doc_res.scalar_one_or_none():
        raise HTTPException(404, "Document not found")

    if not body.tables:
        raise HTTPException(400, "At least one table is required")

    er_result = await db.execute(
        select(ExtractionResult)
        .where(
            and_(
                ExtractionResult.document_id == doc_id,
                ExtractionResult.tool_name == tool_name,
            )
        )
        .order_by(ExtractionResult.table_index)
    )
    existing = list(er_result.scalars().all())

    proc_ms = 0
    cost_val = None
    raw_out = None
    if existing:
        ordered = sorted(existing, key=lambda r: r.table_index)
        tpl = ordered[0]
        proc_ms = int(tpl.processing_time_ms or 0)
        cost_val = tpl.cost_usd
        raw_out = tpl.raw_output
        for r in ordered:
            pm = int(r.processing_time_ms or 0)
            if pm > proc_ms:
                proc_ms = pm
        er_ids = [r.id for r in existing]
        await db.execute(delete(EvaluationScore).where(EvaluationScore.extraction_result_id.in_(er_ids)))
        await db.execute(
            delete(ExtractionResult).where(
                and_(
                    ExtractionResult.document_id == doc_id,
                    ExtractionResult.tool_name == tool_name,
                )
            )
        )
        await db.commit()

    for idx, tbl in enumerate(body.tables):
        er = ExtractionResult(
            document_id=doc_id,
            tool_name=tool_name,
            table_index=idx,
            extracted_headers=tbl.headers,
            extracted_rows=tbl.rows,
            processing_time_ms=proc_ms if idx == 0 else 0,
            cost_usd=cost_val if idx == 0 else 0,
            raw_output=raw_out if idx == 0 else None,
            error_message=None,
            failure_reason=None,
            is_transient_failure=False,
            is_draft=False,
        )
        db.add(er)

    await db.commit()

    out_res = await db.execute(
        select(ExtractionResult)
        .where(
            and_(
                ExtractionResult.document_id == doc_id,
                ExtractionResult.tool_name == tool_name,
            )
        )
        .order_by(ExtractionResult.table_index)
    )
    saved = list(out_res.scalars().all())
    return [
        {
            "extraction_result_id": str(er.id),
            "table_index": er.table_index,
            "extracted_headers": er.extracted_headers,
            "extracted_rows": er.extracted_rows,
            "processing_time_ms": er.processing_time_ms,
            "cost_usd": float(er.cost_usd) if er.cost_usd else None,
            "is_draft": bool(getattr(er, "is_draft", False)),
        }
        for er in saved
    ]


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
            "extraction_result_id": str(er.id),
            "tool_name": er.tool_name,
            "table_index": er.table_index,
            "extracted_headers": er.extracted_headers,
            "extracted_rows": er.extracted_rows,
            "processing_time_ms": er.processing_time_ms,
            "cost_usd": float(er.cost_usd) if er.cost_usd else None,
            "error": er.error_message,
            "failure_reason": er.failure_reason,
            "is_transient_failure": bool(er.is_transient_failure),
            "precision": float(score.precision) if score.precision else None,
            "recall": float(score.recall) if score.recall else None,
            "f1_score": float(score.f1_score) if score.f1_score else None,
            "teds_score": float(score.teds_score) if score.teds_score else None,
            "grits_top": float(score.grits_top) if score.grits_top else None,
            "grits_con": float(score.grits_con) if score.grits_con else None,
            "grits_loc": float(score.grits_loc) if score.grits_loc else None,
        })
    return output


def _safe_csv_filename(name: str, fallback: str) -> str:
    n = (name or "").rsplit("/", 1)[-1]
    stem = n.rsplit(".", 1)[0] if "." in n else n
    safe = "".join(c for c in stem if c.isalnum() or c in "._- ")[:120]
    if not safe:
        safe = (fallback or "document").replace(".csv", "").replace(" ", "_") or "document"
    return f"{safe}_results.csv"


@router.get("/api/results/export/csv")
async def export_results_csv(
    doc_id: Optional[uuid.UUID] = Query(None, description="When set, export only this document"),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(EvaluationScore, ExtractionResult, Document)
        .join(ExtractionResult, EvaluationScore.extraction_result_id == ExtractionResult.id)
        .join(Document, ExtractionResult.document_id == Document.id)
        .order_by(Document.complexity_tier, ExtractionResult.tool_name)
    )
    if doc_id is not None:
        query = query.where(Document.id == doc_id)
    result = await db.execute(query)
    rows = result.all()

    out_name = "evaluation_results.csv"
    if doc_id is not None and rows:
        out_name = _safe_csv_filename(rows[0][2].filename, "document_results.csv")
    elif doc_id is not None:
        dres = await db.execute(select(Document).where(Document.id == doc_id))
        doc = dres.scalar_one_or_none()
        if doc:
            out_name = _safe_csv_filename(doc.filename, "document_results.csv")

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
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )


def _avg_nums(vals: List[Optional[float]]) -> str:
    xs = [v for v in vals if v is not None]
    if not xs:
        return ""
    return str(round(sum(xs) / len(xs), 6))


@router.get("/api/results/export/per-document-csv")
async def export_per_document_summary_csv(db: AsyncSession = Depends(get_db)):
    """One row per (document × tool); transient failures leave accuracy columns blank."""
    docs_result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    docs = list(docs_result.scalars().all())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "filename", "complexity_tier", "is_digital", "page_count",
        "tool_name", "f1_score", "precision", "recall", "teds_score",
        "grits_top", "grits_con", "grits_loc", "processing_time_ms",
        "cost_usd", "failure_reason", "is_transient_failure",
    ])

    for doc in docs:
        for tool_name in ALL_TOOLS:
            er_result = await db.execute(
                select(ExtractionResult)
                .where(
                    and_(
                        ExtractionResult.document_id == doc.id,
                        ExtractionResult.tool_name == tool_name,
                    )
                )
                .order_by(ExtractionResult.table_index)
            )
            ers = list(er_result.scalars().all())
            if not ers:
                writer.writerow([
                    doc.filename,
                    doc.complexity_tier,
                    doc.is_digital if doc.is_digital is not None else "",
                    doc.page_count if doc.page_count is not None else "",
                    tool_name,
                    "", "", "", "", "", "", "",
                    "", "", "", "",
                ])
                continue

            transient = any(bool(getattr(e, "is_transient_failure", False)) for e in ers)
            failure_reason = ers[0].failure_reason or ""
            proc_ms = max((e.processing_time_ms or 0) for e in ers)
            cost = sum(float(e.cost_usd or 0) for e in ers)

            if transient:
                writer.writerow([
                    doc.filename,
                    doc.complexity_tier,
                    doc.is_digital if doc.is_digital is not None else "",
                    doc.page_count if doc.page_count is not None else "",
                    tool_name,
                    "", "", "", "", "", "", "",
                    proc_ms,
                    cost,
                    failure_reason,
                    "true",
                ])
                continue

            f1s: List[Optional[float]] = []
            precs: List[Optional[float]] = []
            recs: List[Optional[float]] = []
            teds: List[Optional[float]] = []
            gtops: List[Optional[float]] = []
            gcons: List[Optional[float]] = []
            glocs: List[Optional[float]] = []

            for er in ers:
                sc_r = await db.execute(
                    select(EvaluationScore).where(EvaluationScore.extraction_result_id == er.id)
                )
                sc = sc_r.scalar_one_or_none()
                if sc:
                    f1s.append(float(sc.f1_score) if sc.f1_score is not None else None)
                    precs.append(float(sc.precision) if sc.precision is not None else None)
                    recs.append(float(sc.recall) if sc.recall is not None else None)
                    teds.append(float(sc.teds_score) if sc.teds_score is not None else None)
                    gtops.append(float(sc.grits_top) if sc.grits_top is not None else None)
                    gcons.append(float(sc.grits_con) if sc.grits_con is not None else None)
                    glocs.append(float(sc.grits_loc) if sc.grits_loc is not None else None)

            writer.writerow([
                doc.filename,
                doc.complexity_tier,
                doc.is_digital if doc.is_digital is not None else "",
                doc.page_count if doc.page_count is not None else "",
                tool_name,
                _avg_nums(f1s),
                _avg_nums(precs),
                _avg_nums(recs),
                _avg_nums(teds),
                _avg_nums(gtops),
                _avg_nums(gcons),
                _avg_nums(glocs),
                proc_ms,
                cost,
                failure_reason,
                "false",
            ])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="per_document_evaluation.csv"'},
    )
