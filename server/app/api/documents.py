import os
import uuid
import shutil
import logging
import asyncio
from pathlib import Path
from typing import List, Any, Dict

import fitz  # PyMuPDF
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import select, delete as sa_delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, GroundTruthTable, ExtractionResult, EvaluationScore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

PDF_STORAGE_DIR = Path("data/pdfs")
PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Default tool for corpus upload → ground-truth auto-seed (POST .../seed-ground-truth)
#
# Switched from Claude to PyMuPDF for cheap local full-flow testing (Apr 2026).
# Flip back anytime:
#   export DEFAULT_EXTRACTION_TOOL=claude_sonnet
# Only pymupdf and claude_sonnet are implemented for seeding; any other value
# logs a warning and falls back to pymupdf.
# ---------------------------------------------------------------------------
_DEFAULT_SEED_TOOL_RAW = os.getenv("DEFAULT_EXTRACTION_TOOL", "pymupdf").strip()

_VALID_SEED_TOOLS = frozenset(
    {
        "pymupdf",
        "claude_sonnet",
        "docling",
        "aws_textract",
        "google_docai",
        "gpt5",
        "mistral",
    }
)
_AUTO_SEED_SOURCES = frozenset(f"{t}_seed" for t in _VALID_SEED_TOOLS)


def _resolved_seed_tool() -> str:
    t = _DEFAULT_SEED_TOOL_RAW
    if t not in _VALID_SEED_TOOLS:
        logger.warning("Invalid DEFAULT_EXTRACTION_TOOL=%r — using pymupdf", t)
        return "pymupdf"
    if t not in ("pymupdf", "claude_sonnet"):
        logger.warning(
            "DEFAULT_EXTRACTION_TOOL=%r is not supported for seed yet — using pymupdf",
            t,
        )
        return "pymupdf"
    return t


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


@router.get("/{doc_id}/pdf")
async def get_document_pdf(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Serve the uploaded PDF bytes for in-browser preview (pdf.js)."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    path = doc.file_path
    if not path or not Path(path).is_file():
        raise HTTPException(404, "PDF file not found on disk")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=doc.filename or "document.pdf",
    )


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


def _claude_transient_from_payload(error_text: str) -> bool:
    em = (error_text or "").lower()
    return (
        "rate limit" in em
        or "429" in em
        or "529" in em
        or "overloaded" in em
        or "status 529" in em
    )


@router.post("/{doc_id}/seed-ground-truth")
async def seed_ground_truth_from_claude(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Pre-fill ground truth tables from an automated extraction (unconfirmed seed).

    Tool is chosen by DEFAULT_EXTRACTION_TOOL (default: pymupdf). Claude remains
    available via DEFAULT_EXTRACTION_TOOL=claude_sonnet.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    gt_all = await db.execute(select(GroundTruthTable).where(GroundTruthTable.document_id == doc_id))
    existing = gt_all.scalars().all()
    if any(getattr(g, "confirmed", False) for g in existing):
        raise HTTPException(409, "Ground truth already confirmed for this document.")

    await db.execute(
        sa_delete(GroundTruthTable).where(
            and_(
                GroundTruthTable.document_id == doc_id,
                GroundTruthTable.source.in_(_AUTO_SEED_SOURCES),
            )
        )
    )
    await db.commit()

    tool = _resolved_seed_tool()
    seed_source = f"{tool}_seed"
    tables: List[Dict[str, Any]] = []

    if tool == "claude_sonnet":
        # Imported here to avoid loading the Claude stack at app import time.
        from app.services.claude.service import ClaudeDocumentAIService

        config: dict = {}
        try:
            result_payload = await ClaudeDocumentAIService(config).extract_commission_data(doc.file_path)
        except Exception as e:
            try:
                import anthropic as _anthropic

                if isinstance(e, _anthropic.RateLimitError):
                    return JSONResponse(
                        status_code=503,
                        content={"error": "claude_unavailable", "retry": True},
                    )
                if isinstance(e, _anthropic.APIStatusError) and getattr(e, "status_code", None) == 529:
                    return JSONResponse(
                        status_code=503,
                        content={"error": "claude_unavailable", "retry": True},
                    )
            except ImportError:
                pass
            return JSONResponse(
                status_code=500,
                content={"error": str(e), "retry": False},
            )

        if isinstance(result_payload, dict) and result_payload.get("success") is False:
            err = result_payload.get("error") or ""
            if _claude_transient_from_payload(str(err)):
                return JSONResponse(
                    status_code=503,
                    content={"error": "claude_unavailable", "retry": True},
                )
            return JSONResponse(
                status_code=500,
                content={"error": str(err), "retry": False},
            )

        tables = (result_payload or {}).get("tables") if isinstance(result_payload, dict) else []
    else:
        # pymupdf — local, synchronous; keep event loop responsive.
        from app.services.pymupdf.service import PyMuPDFService

        try:
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(
                None,
                PyMuPDFService().extract_tables,
                doc.file_path,
            )
            tables = raw.get("tables") or []
        except Exception as e:
            logger.exception("PyMuPDF seed extraction failed")
            return JSONResponse(
                status_code=500,
                content={"error": str(e), "retry": False},
            )

    if not tables:
        return {
            "doc_id": str(doc_id),
            "tables_seeded": 0,
            "message": f"No tables found ({tool}) for this document.",
            "seed_tool": tool,
        }

    seeded = 0
    for table in tables:
        if not isinstance(table, dict):
            continue
        gt = GroundTruthTable(
            document_id=doc_id,
            table_index=seeded,
            headers=table.get("headers") or [],
            rows=table.get("rows") or [],
            confirmed=False,
            source=seed_source,
            correction_log=[],
            correction_count=0,
        )
        db.add(gt)
        await db.commit()
        await db.refresh(gt)
        seeded += 1

    return {
        "doc_id": str(doc_id),
        "tables_seeded": seeded,
        "message": f"Extraction ({tool}) complete. Please review and confirm.",
        "seed_tool": tool,
    }
