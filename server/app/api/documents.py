import copy
import os
import uuid
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Any, Dict

import fitz  # PyMuPDF
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import select, delete as sa_delete, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, AsyncSessionLocal
from app.db.models import Document, GroundTruthTable, ExtractionResult, EvaluationScore
from app.services.evaluation.runner import EvaluationRunner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

PDF_STORAGE_DIR = Path("data/pdfs")
PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Default tool after upload (POST /upload) and for POST .../seed-ground-truth retry.
# Runs EvaluationRunner once → ExtractionResult rows + GroundTruthTable seed rows.
#
# Default: Claude Sonnet. For cheap local testing without API calls:
#   export DEFAULT_EXTRACTION_TOOL=pymupdf
# Only pymupdf and claude_sonnet are implemented; any other value logs a warning
# and falls back to pymupdf.
# ---------------------------------------------------------------------------
_DEFAULT_SEED_TOOL_RAW = os.getenv("DEFAULT_EXTRACTION_TOOL", "claude_sonnet").strip()

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


async def _delete_extractions_for_document_tool(
    db: AsyncSession, document_id: uuid.UUID, tool_name: str
) -> None:
    """Remove ExtractionResult rows (and dependent EvaluationScores) for one tool."""
    er_res = await db.execute(
        select(ExtractionResult.id).where(
            and_(
                ExtractionResult.document_id == document_id,
                ExtractionResult.tool_name == tool_name,
            )
        )
    )
    er_ids = [r[0] for r in er_res.fetchall()]
    if not er_ids:
        return
    await db.execute(
        sa_delete(EvaluationScore).where(EvaluationScore.extraction_result_id.in_(er_ids))
    )
    await db.execute(sa_delete(ExtractionResult).where(ExtractionResult.id.in_(er_ids)))
    await db.commit()


async def _delete_auto_seed_ground_truth(db: AsyncSession, document_id: uuid.UUID) -> None:
    await db.execute(
        sa_delete(GroundTruthTable).where(
            and_(
                GroundTruthTable.document_id == document_id,
                GroundTruthTable.source.in_(_AUTO_SEED_SOURCES),
            )
        )
    )
    await db.commit()


async def _insert_gt_from_extraction_results(
    db: AsyncSession,
    document_id: uuid.UUID,
    tool_name: str,
    results: List[Any],
) -> int:
    """
    Create unconfirmed GroundTruthTable rows from successful ExtractionResult rows.
    table_index matches ExtractionResult.table_index so evaluation pairing stays aligned.
    """
    seed_source = f"{tool_name}_seed"
    n = 0
    for er in sorted(results, key=lambda r: r.table_index):
        rows = er.extracted_rows
        if rows is None or not isinstance(rows, list) or len(rows) == 0:
            continue
        gt = GroundTruthTable(
            document_id=document_id,
            table_index=er.table_index,
            headers=er.extracted_headers or [],
            rows=rows,
            confirmed=False,
            source=seed_source,
            correction_log=[],
            correction_count=0,
        )
        db.add(gt)
        n += 1
    if n:
        await db.commit()
    return n


async def _apply_default_tool_extraction_and_gt(db: AsyncSession, doc: Document) -> Dict[str, Any]:
    """
    Run DEFAULT_EXTRACTION_TOOL via EvaluationRunner (persists ExtractionResult rows),
    then seed GroundTruthTable rows from those extractions (single pass — no duplicate API calls).
    """
    tool = _resolved_seed_tool()
    await _delete_auto_seed_ground_truth(db, doc.id)
    await _delete_extractions_for_document_tool(db, doc.id, tool)

    runner = EvaluationRunner()
    try:
        results = await runner.run_tool(tool, doc.file_path, doc.id, AsyncSessionLocal)
    except Exception as e:
        logger.exception("Default tool extraction failed for document %s", doc.id)
        return {
            "seed_tool": tool,
            "tables_seeded": 0,
            "success": False,
            "error": str(e),
        }

    # Fresh session: caller's ``db`` may have been idle for a long extraction (e.g. Mistral).
    async with AsyncSessionLocal() as db_after:
        n = await _insert_gt_from_extraction_results(db_after, doc.id, tool, results)
        if tool == "claude_sonnet" and results:
            await db_after.execute(
                update(ExtractionResult)
                .where(
                    and_(
                        ExtractionResult.document_id == doc.id,
                        ExtractionResult.tool_name == tool,
                    )
                )
                .values(is_draft=True)
            )
            await db_after.commit()
    out: Dict[str, Any] = {
        "seed_tool": tool,
        "tables_seeded": n,
        "success": True,
    }
    if results and getattr(results[0], "is_transient_failure", False):
        out["transient_failure"] = True
        out["failure_reason"] = getattr(results[0], "failure_reason", None)
    return out


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
    complexity_tier: str = Form("unconfirmed"),
    db: AsyncSession = Depends(get_db),
):
    if complexity_tier not in ("low", "medium", "high", "unconfirmed"):
        raise HTTPException(
            400,
            "complexity_tier must be 'low', 'medium', 'high', or 'unconfirmed'",
        )

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

    seed_info = await _apply_default_tool_extraction_and_gt(db, document)

    return {
        "id": str(document.id),
        "filename": document.filename,
        "complexity_tier": document.complexity_tier,
        "page_count": document.page_count,
        "is_digital": document.is_digital,
        "file_path": document.file_path,
        "uploaded_at": document.uploaded_at.isoformat(),
        "seed": seed_info,
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
async def update_document_tier_and_pdf_type(
    doc_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Update complexity tier and/or digital vs scanned flag.
    Tier may be set to 'unconfirmed' only when correcting back from a mistaken choice; normal workflow picks low/medium/high in the UI.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    tier = body.get("complexity_tier")
    if tier is not None:
        if tier not in ("low", "medium", "high", "unconfirmed"):
            raise HTTPException(
                400,
                "complexity_tier must be 'low', 'medium', 'high', or 'unconfirmed'",
            )
        doc.complexity_tier = tier

    if "is_digital" in body:
        raw = body.get("is_digital")
        doc.is_digital = None if raw is None else bool(raw)

    await db.commit()
    await db.refresh(doc)
    return {
        "id": str(doc.id),
        "complexity_tier": doc.complexity_tier,
        "is_digital": doc.is_digital,
    }


class GroundTruthMergeIn(BaseModel):
    primary_table_id: uuid.UUID
    secondary_table_id: uuid.UUID


class GroundTruthUndoMergeIn(BaseModel):
    """Undo the last merge recorded on this survivor row's correction_log."""

    survivor_table_id: uuid.UUID


def _gt_row_to_width(row: List[Any], width: int) -> List[str]:
    cells = [str(c) if c is not None else "" for c in (row or [])]
    if len(cells) < width:
        return cells + [""] * (width - len(cells))
    return cells[:width]


def _ground_truth_to_json(gt: GroundTruthTable) -> Dict[str, Any]:
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


def _pop_last_merge_undo(log: List[Any]) -> tuple[List[Any], Dict[str, Any] | None]:
    """Remove and return the last merge_undo entry from correction_log (if any)."""
    if not log:
        return log, None
    for i in range(len(log) - 1, -1, -1):
        e = log[i]
        if isinstance(e, dict) and e.get("type") == "merge_undo":
            undo = e
            rest = log[:i] + log[i + 1 :]
            return rest, undo
    return log, None


def _correction_log_has_merge_undo(log: Any) -> bool:
    if not isinstance(log, list):
        return False
    return any(isinstance(e, dict) and e.get("type") == "merge_undo" for e in log)


@router.post("/{doc_id}/ground-truth/merge")
async def merge_ground_truth_tables(
    doc_id: uuid.UUID,
    body: GroundTruthMergeIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Merge secondary into primary (IDs from the client). Rows from secondary are appended
    after primary's rows; headers always stay exactly those of the primary (merge target) table.
    """
    if body.primary_table_id == body.secondary_table_id:
        raise HTTPException(400, "primary_table_id and secondary_table_id must differ")

    doc_row = await db.execute(select(Document).where(Document.id == doc_id))
    if not doc_row.scalar_one_or_none():
        raise HTTPException(404, "Document not found")

    r1 = await db.execute(
        select(GroundTruthTable).where(
            and_(
                GroundTruthTable.id == body.primary_table_id,
                GroundTruthTable.document_id == doc_id,
            )
        )
    )
    r2 = await db.execute(
        select(GroundTruthTable).where(
            and_(
                GroundTruthTable.id == body.secondary_table_id,
                GroundTruthTable.document_id == doc_id,
            )
        )
    )
    primary = r1.scalar_one_or_none()
    secondary = r2.scalar_one_or_none()
    if not primary or not secondary:
        raise HTTPException(404, "One or both ground-truth tables not found for this document")

    headers = list(primary.headers or [])
    width = len(headers)
    if width == 0:
        raise HTTPException(400, "Primary table has no headers")

    old_row_count = len(primary.rows or [])
    sec_rows = secondary.rows or []
    merged_rows = [_gt_row_to_width(r, width) for r in (primary.rows or [])]
    for row in sec_rows:
        merged_rows.append(_gt_row_to_width(row, width))

    log = list(getattr(primary, "correction_log", None) or [])
    ts = datetime.now(timezone.utc).isoformat()
    removed_table_index = int(secondary.table_index)
    log.append(
        {
            "type": "merge_undo",
            "field": "rows",
            "old_value": f"{old_row_count} rows",
            "new_value": (
                f"merged table_index={removed_table_index} into primary id={primary.id} "
                f"({len(sec_rows)} rows added); headers unchanged on merge target"
            ),
            "corrected_at": ts,
            "primary_rows_before": copy.deepcopy(primary.rows or []),
            "removed_table_index": removed_table_index,
            "removed_table": {
                "headers": copy.deepcopy(secondary.headers or []),
                "rows": copy.deepcopy(secondary.rows or []),
                "notes": secondary.notes,
                "source": getattr(secondary, "source", "manual") or "manual",
                "confirmed": bool(getattr(secondary, "confirmed", False)),
                "correction_log": copy.deepcopy(getattr(secondary, "correction_log", None) or []),
                "correction_count": int(getattr(secondary, "correction_count", 0) or 0),
            },
        }
    )

    primary.headers = headers
    primary.rows = merged_rows
    primary.correction_log = log
    primary.correction_count = int(getattr(primary, "correction_count", 0) or 0) + 1

    await db.execute(
        sa_delete(GroundTruthTable).where(GroundTruthTable.id == secondary.id)
    )
    await db.flush()

    rest = await db.execute(
        select(GroundTruthTable)
        .where(GroundTruthTable.document_id == doc_id)
        .order_by(GroundTruthTable.table_index)
    )
    all_gt = list(rest.scalars().all())
    for new_idx, gt in enumerate(all_gt):
        if gt.table_index != new_idx:
            gt.table_index = new_idx

    await db.commit()
    await db.refresh(primary)

    return _ground_truth_to_json(primary)


@router.post("/{doc_id}/ground-truth/merge/undo")
async def undo_merge_ground_truth_tables(
    doc_id: uuid.UUID,
    body: GroundTruthUndoMergeIn,
    db: AsyncSession = Depends(get_db),
):
    """Restore the last merge for the given survivor table (LIFO per survivor)."""
    doc_row = await db.execute(select(Document).where(Document.id == doc_id))
    if not doc_row.scalar_one_or_none():
        raise HTTPException(404, "Document not found")

    pr = await db.execute(
        select(GroundTruthTable).where(
            and_(
                GroundTruthTable.id == body.survivor_table_id,
                GroundTruthTable.document_id == doc_id,
            )
        )
    )
    primary = pr.scalar_one_or_none()
    if not primary:
        raise HTTPException(404, "Survivor ground-truth table not found")

    log = list(getattr(primary, "correction_log", None) or [])
    new_log, undo = _pop_last_merge_undo(log)
    if not undo or not isinstance(undo.get("removed_table"), dict):
        raise HTTPException(404, "No merge to undo for this table")

    removed = undo["removed_table"]
    s_idx = int(undo.get("removed_table_index", 0))
    primary_rows_before = undo.get("primary_rows_before")
    if not isinstance(primary_rows_before, list):
        raise HTTPException(500, "Invalid undo payload")

    primary.rows = copy.deepcopy(primary_rows_before)
    primary.correction_log = new_log
    primary.correction_count = max(0, int(getattr(primary, "correction_count", 0) or 0) - 1)

    rest = await db.execute(
        select(GroundTruthTable)
        .where(GroundTruthTable.document_id == doc_id)
        .order_by(GroundTruthTable.table_index)
    )
    ordered = list(rest.scalars().all())
    insert_at = max(0, min(s_idx, len(ordered)))

    new_gt = GroundTruthTable(
        document_id=doc_id,
        table_index=insert_at,
        headers=removed.get("headers") or [],
        rows=removed.get("rows") or [],
        notes=removed.get("notes"),
        source=str(removed.get("source") or "manual"),
        confirmed=bool(removed.get("confirmed", False)),
        correction_log=list(removed.get("correction_log") or []),
        correction_count=int(removed.get("correction_count", 0) or 0),
    )
    ordered.insert(insert_at, new_gt)
    for i, gt in enumerate(ordered):
        gt.table_index = i

    db.add(new_gt)
    await db.commit()
    await db.refresh(primary)
    await db.refresh(new_gt)

    return {
        "success": True,
        "survivor_table_id": str(primary.id),
        "restored_table_id": str(new_gt.id),
        "can_undo_more": _correction_log_has_merge_undo(primary.correction_log),
    }


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
    Re-run default-tool extraction + ground-truth seed (same path as upload).

    Tool is chosen by DEFAULT_EXTRACTION_TOOL (default: claude_sonnet). Use
    DEFAULT_EXTRACTION_TOOL=pymupdf for local rule-based seeding without Claude.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    gt_all = await db.execute(select(GroundTruthTable).where(GroundTruthTable.document_id == doc_id))
    existing = gt_all.scalars().all()
    if any(getattr(g, "confirmed", False) for g in existing):
        raise HTTPException(409, "Ground truth already confirmed for this document.")

    seed_info = await _apply_default_tool_extraction_and_gt(db, doc)

    if seed_info.get("transient_failure"):
        return JSONResponse(
            status_code=503,
            content={"error": "claude_unavailable", "retry": True},
        )

    if not seed_info.get("success"):
        err = seed_info.get("error") or "extraction failed"
        if _claude_transient_from_payload(str(err)):
            return JSONResponse(
                status_code=503,
                content={"error": "claude_unavailable", "retry": True},
            )
        return JSONResponse(
            status_code=500,
            content={"error": err, "retry": False},
        )

    tool = str(seed_info.get("seed_tool", "unknown"))
    seeded = int(seed_info.get("tables_seeded") or 0)
    if seeded == 0:
        return {
            "doc_id": str(doc_id),
            "tables_seeded": 0,
            "message": f"No tables found ({tool}) for this document.",
            "seed_tool": tool,
        }

    return {
        "doc_id": str(doc_id),
        "tables_seeded": seeded,
        "message": f"Extraction ({tool}) complete. Please review and confirm.",
        "seed_tool": tool,
    }
