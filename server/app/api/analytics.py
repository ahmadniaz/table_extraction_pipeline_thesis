"""
Analytics dataset: complete extraction + score + document metadata for the Results
Analytics UI. Joins are outer on scores so missing rows surface for reliability charts.

Field mapping for the React client: see `client/src/lib/analytics/ResultsDataAdapter.ts` and
`docs/results_analytics.md`. Tool list order follows `app.api.evaluation.ALL_TOOLS` and must
match `client/src/lib/evaluationTools.ts` (ALL_EVAL_TOOLS).
"""
from __future__ import annotations

import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, EvaluationScore, ExtractionResult, GroundTruthTable
from app.api.evaluation import ALL_TOOLS

router = APIRouter(tags=["analytics"])


def _num(n: Any) -> Optional[float]:
    if n is None:
        return None
    return float(n)


@router.get("/api/analytics/dataset")
async def get_analytics_dataset(db: AsyncSession = Depends(get_db)) -> dict:
    """Single payload for the analytics page: all documents, GT counts, every extraction row with optional score."""
    doc_result = await db.execute(select(Document).order_by(Document.uploaded_at))
    docs = list(doc_result.scalars().all())
    if not docs:
        return {
            "documents": [],
            "extraction_table_rows": [],
        }

    doc_ids: List[uuid.UUID] = [d.id for d in docs]
    gt_count_result = await db.execute(
        select(GroundTruthTable.document_id, func.count(GroundTruthTable.id).label("n"))
        .where(GroundTruthTable.document_id.in_(doc_ids))
        .group_by(GroundTruthTable.document_id)
    )
    gt_by_doc: dict = {r[0]: int(r[1]) for r in gt_count_result.all()}

    q = (
        select(ExtractionResult, Document, EvaluationScore)
        .join(Document, ExtractionResult.document_id == Document.id)
        .outerjoin(
            EvaluationScore, EvaluationScore.extraction_result_id == ExtractionResult.id
        )
        .order_by(Document.filename, ExtractionResult.tool_name, ExtractionResult.table_index)
    )
    result = await db.execute(q)
    rows = result.all()

    out_docs = []
    for d in docs:
        out_docs.append(
            {
                "id": str(d.id),
                "filename": d.filename,
                "complexity_tier": d.complexity_tier,
                "page_count": d.page_count,
                "is_digital": d.is_digital,
                "ground_truth_count": gt_by_doc.get(d.id, 0),
            }
        )

    out_ext: List[dict] = []
    for er, doc, sc in rows:
        rec: dict = {
            "extraction_result_id": str(er.id),
            "document_id": str(doc.id),
            "filename": doc.filename,
            "complexity_tier": doc.complexity_tier,
            "page_count": doc.page_count,
            "is_digital": doc.is_digital,
            "tool_name": er.tool_name,
            "table_index": er.table_index,
            "processing_time_ms": er.processing_time_ms,
            "cost_usd": _num(er.cost_usd),
            "error_message": er.error_message,
            "failure_reason": er.failure_reason,
            "is_transient_failure": bool(er.is_transient_failure),
            "is_draft": bool(getattr(er, "is_draft", False)),
        }
        if sc is not None:
            # Use explicit is-not-None so 0.0 is preserved
            rec["score"] = {
                "precision": _num(sc.precision),
                "recall": _num(sc.recall),
                "f1_score": _num(sc.f1_score),
                "teds_score": _num(sc.teds_score),
                "grits_top": _num(sc.grits_top),
                "grits_con": _num(sc.grits_con),
                "grits_loc": _num(sc.grits_loc),
            }
        else:
            rec["score"] = None
        out_ext.append(rec)

    return {
        "documents": out_docs,
        "extraction_table_rows": out_ext,
        "all_tool_ids": list(ALL_TOOLS),
    }
