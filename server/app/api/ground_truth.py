import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Any, Optional
from sqlalchemy import select, delete as sa_delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, GroundTruthTable

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ground-truth", tags=["ground_truth"])


class GroundTruthIn(BaseModel):
    table_index: int
    headers: List[str]
    rows: List[List[Any]]
    notes: Optional[str] = None


class GroundTruthUpdate(BaseModel):
    headers: Optional[List[str]] = None
    rows: Optional[List[List[Any]]] = None
    notes: Optional[str] = None


class CorrectionEntry(BaseModel):
    row: int
    col: int
    original: str
    corrected: str


class ConfirmTableIn(BaseModel):
    table_index: int
    headers: List[str]
    rows: List[List[Any]]
    correction_log: List[CorrectionEntry] = Field(default_factory=list)
    notes: Optional[str] = None


class ConfirmGroundTruthBody(BaseModel):
    tables: List[ConfirmTableIn]


@router.post("/{doc_id}")
async def save_ground_truth(
    doc_id: uuid.UUID,
    body: GroundTruthIn,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Document not found")

    existing = await db.execute(
        select(GroundTruthTable).where(
            and_(
                GroundTruthTable.document_id == doc_id,
                GroundTruthTable.table_index == body.table_index,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            409, f"Ground truth for table_index {body.table_index} already exists. Use PUT to update."
        )

    gt = GroundTruthTable(
        document_id=doc_id,
        table_index=body.table_index,
        headers=body.headers,
        rows=body.rows,
        notes=body.notes,
    )
    db.add(gt)
    await db.commit()
    await db.refresh(gt)

    return {
        "id": str(gt.id),
        "document_id": str(gt.document_id),
        "table_index": gt.table_index,
        "headers": gt.headers,
        "rows": gt.rows,
        "notes": gt.notes,
        "annotated_at": gt.annotated_at.isoformat(),
        "confirmed": getattr(gt, "confirmed", False),
        "source": getattr(gt, "source", "manual"),
        "correction_log": getattr(gt, "correction_log", []) or [],
        "correction_count": getattr(gt, "correction_count", 0),
    }


@router.post("/{doc_id}/confirm")
async def confirm_ground_truth(
    doc_id: uuid.UUID,
    body: ConfirmGroundTruthBody,
    db: AsyncSession = Depends(get_db),
):
    """Replace all ground truth for a document with researcher-confirmed tables."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Document not found")

    await db.execute(sa_delete(GroundTruthTable).where(GroundTruthTable.document_id == doc_id))
    await db.commit()

    n = 0
    for t in body.tables:
        log = [e.model_dump() for e in t.correction_log]
        gt = GroundTruthTable(
            document_id=doc_id,
            table_index=t.table_index,
            headers=t.headers,
            rows=t.rows,
            notes=t.notes,
            confirmed=True,
            source="manual",
            correction_log=log,
            correction_count=len(log),
        )
        db.add(gt)
        await db.commit()
        await db.refresh(gt)
        n += 1

    return {"confirmed": True, "tables_saved": n}


@router.get("/{doc_id}")
async def get_ground_truths(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Document not found")

    result = await db.execute(
        select(GroundTruthTable)
        .where(GroundTruthTable.document_id == doc_id)
        .order_by(GroundTruthTable.table_index)
    )
    tables = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "document_id": str(t.document_id),
            "table_index": t.table_index,
            "headers": t.headers,
            "rows": t.rows,
            "notes": t.notes,
            "annotated_at": t.annotated_at.isoformat(),
            "confirmed": getattr(t, "confirmed", False),
            "source": getattr(t, "source", "manual"),
            "correction_log": getattr(t, "correction_log", []) or [],
            "correction_count": getattr(t, "correction_count", 0),
        }
        for t in tables
    ]


@router.put("/{doc_id}/{table_index}")
async def update_ground_truth(
    doc_id: uuid.UUID,
    table_index: int,
    body: GroundTruthUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GroundTruthTable).where(
            and_(
                GroundTruthTable.document_id == doc_id,
                GroundTruthTable.table_index == table_index,
            )
        )
    )
    gt = result.scalar_one_or_none()
    if not gt:
        raise HTTPException(404, f"Ground truth for table_index {table_index} not found")

    if body.headers is not None:
        gt.headers = body.headers
    if body.rows is not None:
        gt.rows = body.rows
    if body.notes is not None:
        gt.notes = body.notes

    await db.commit()
    await db.refresh(gt)

    return {
        "id": str(gt.id),
        "document_id": str(gt.document_id),
        "table_index": gt.table_index,
        "headers": gt.headers,
        "rows": gt.rows,
        "notes": gt.notes,
        "annotated_at": gt.annotated_at.isoformat(),
        "confirmed": getattr(gt, "confirmed", False),
        "source": getattr(gt, "source", "manual"),
        "correction_log": getattr(gt, "correction_log", []) or [],
        "correction_count": getattr(gt, "correction_count", 0),
    }


@router.delete("/{doc_id}/{table_index}")
async def delete_ground_truth(
    doc_id: uuid.UUID,
    table_index: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GroundTruthTable).where(
            and_(
                GroundTruthTable.document_id == doc_id,
                GroundTruthTable.table_index == table_index,
            )
        )
    )
    gt = result.scalar_one_or_none()
    if not gt:
        raise HTTPException(404, f"Ground truth for table_index {table_index} not found")

    await db.execute(
        sa_delete(GroundTruthTable).where(
            and_(
                GroundTruthTable.document_id == doc_id,
                GroundTruthTable.table_index == table_index,
            )
        )
    )
    await db.commit()
    return {"deleted_table_index": table_index, "document_id": str(doc_id)}
