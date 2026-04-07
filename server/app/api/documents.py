import os
import uuid
import shutil
import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, GroundTruthTable, ExtractionResult, EvaluationScore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

PDF_STORAGE_DIR = Path("data/pdfs")
PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _analyse_pdf(file_path: str) -> dict:
    """Extract page count and digital/scanned classification from a PDF."""
    doc = fitz.open(file_path)
    page_count = len(doc)

    text_pages = 0
    for page in doc:
        text = page.get_text().strip()
        if len(text) > 50:
            text_pages += 1

    is_digital = text_pages > (page_count * 0.5)
    doc.close()
    return {"page_count": page_count, "is_digital": is_digital}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    complexity_tier: str = Form("medium"),
    db: AsyncSession = Depends(get_db),
):
    if complexity_tier not in ("low", "medium", "high"):
        raise HTTPException(400, "complexity_tier must be 'low', 'medium', or 'high'")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    doc_id = uuid.uuid4()
    dest = PDF_STORAGE_DIR / f"{doc_id}.pdf"

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        info = _analyse_pdf(str(dest))
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, f"Failed to read PDF: {e}")

    document = Document(
        id=doc_id,
        filename=file.filename,
        complexity_tier=complexity_tier,
        page_count=info["page_count"],
        is_digital=info["is_digital"],
        file_path=str(dest),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    return {
        "id": str(document.id),
        "filename": document.filename,
        "complexity_tier": document.complexity_tier,
        "page_count": document.page_count,
        "is_digital": document.is_digital,
        "file_path": document.file_path,
        "uploaded_at": document.uploaded_at.isoformat(),
    }


@router.get("/")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "complexity_tier": d.complexity_tier,
            "page_count": d.page_count,
            "is_digital": d.is_digital,
            "uploaded_at": d.uploaded_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/{doc_id}")
async def get_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "complexity_tier": doc.complexity_tier,
        "page_count": doc.page_count,
        "is_digital": doc.is_digital,
        "file_path": doc.file_path,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }


@router.delete("/{doc_id}")
async def delete_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Cascade: evaluation_scores → extraction_results → ground_truth_tables → document
    er_ids = await db.execute(
        select(ExtractionResult.id).where(ExtractionResult.document_id == doc_id)
    )
    er_id_list = [r for (r,) in er_ids.fetchall()]
    if er_id_list:
        await db.execute(
            sa_delete(EvaluationScore).where(EvaluationScore.extraction_result_id.in_(er_id_list))
        )
    await db.execute(sa_delete(ExtractionResult).where(ExtractionResult.document_id == doc_id))
    await db.execute(sa_delete(GroundTruthTable).where(GroundTruthTable.document_id == doc_id))

    file_path = doc.file_path
    await db.execute(sa_delete(Document).where(Document.id == doc_id))
    await db.commit()

    if file_path:
        Path(file_path).unlink(missing_ok=True)

    return {"deleted": str(doc_id)}


@router.patch("/{doc_id}/tier")
async def update_complexity_tier(
    doc_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    tier = body.get("complexity_tier")
    if tier not in ("low", "medium", "high"):
        raise HTTPException(400, "complexity_tier must be 'low', 'medium', or 'high'")

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    doc.complexity_tier = tier
    await db.commit()
    return {"id": str(doc.id), "complexity_tier": doc.complexity_tier}
