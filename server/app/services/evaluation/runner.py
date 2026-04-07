"""
Evaluation runner — routes extraction requests to the correct service,
records timing and cost, and normalises results into ExtractionResult rows.
"""

import asyncio
import logging
import time
import uuid
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExtractionResult, Document
from .cost_calculator import calculate_cost

logger = logging.getLogger(__name__)


def _normalise_tables(raw: Any) -> List[Dict[str, Any]]:
    """Convert varied service outputs into a list of {headers, rows} dicts."""
    tables: List[Dict[str, Any]] = []

    if isinstance(raw, dict):
        raw_tables = raw.get("tables") or []
    elif isinstance(raw, list):
        raw_tables = raw
    elif hasattr(raw, "tables"):
        raw_tables = raw.tables or []
    else:
        return tables

    for t in raw_tables:
        if isinstance(t, dict):
            headers = t.get("headers") or t.get("header") or []
            rows = t.get("rows") or t.get("data") or []
            tables.append({"headers": headers, "rows": rows})
    return tables


class EvaluationRunner:
    """Runs extraction tools against a document and persists ExtractionResult rows."""

    def __init__(self):
        self._services: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lazy service initialisation (heavy imports deferred)
    # ------------------------------------------------------------------

    def _get_claude(self):
        if "claude_sonnet" not in self._services:
            from app.services.claude.service import ClaudeDocumentAIService
            self._services["claude_sonnet"] = ClaudeDocumentAIService()
        return self._services["claude_sonnet"]

    def _get_mistral(self):
        if "mistral" not in self._services:
            from app.services.mistral.service import MistralDocumentAIService
            self._services["mistral"] = MistralDocumentAIService()
        return self._services["mistral"]

    def _get_gpt(self):
        if "gpt5" not in self._services:
            from app.services.ai.gpt4o_vision_service import GPT4oVisionService
            self._services["gpt5"] = GPT4oVisionService()
        return self._services["gpt5"]

    def _get_google_docai(self):
        if "google_docai" not in self._services:
            from app.services.google_docai.extractor import GoogleDocAIExtractor
            self._services["google_docai"] = GoogleDocAIExtractor()
        return self._services["google_docai"]

    def _get_docling(self):
        if "docling" not in self._services:
            from app.services.docling.pipeline import ExtractionPipeline
            from app.services.docling.utils.config import Config
            self._services["docling"] = ExtractionPipeline(Config())
        return self._services["docling"]

    # ------------------------------------------------------------------
    # Per-tool extraction
    # ------------------------------------------------------------------

    async def _extract_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """Rule-based extraction using pdfplumber (no AI)."""
        import pdfplumber

        tables = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                for raw_table in (page.extract_tables() or []):
                    if not raw_table:
                        continue
                    headers = [str(c) if c else "" for c in raw_table[0]]
                    rows = [
                        [str(c) if c else "" for c in row]
                        for row in raw_table[1:]
                    ]
                    tables.append({"headers": headers, "rows": rows})
        return {"tables": tables}

    async def _extract_docling(self, file_path: str) -> Any:
        pipeline = self._get_docling()
        return await pipeline.extract_tables(file_path)

    async def _extract_google_docai(self, file_path: str) -> Dict[str, Any]:
        extractor = self._get_google_docai()
        return await extractor.extract_tables_async(file_path)

    async def _extract_gpt5(self, file_path: str) -> Dict[str, Any]:
        service = self._get_gpt()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, service.extract_commission_data, file_path)

    async def _extract_claude(self, file_path: str) -> Dict[str, Any]:
        service = self._get_claude()
        return await service.extract_commission_data(file_path)

    async def _extract_mistral(self, file_path: str) -> Dict[str, Any]:
        service = self._get_mistral()
        return await service.extract_commission_data_via_ocr(file_path)

    _DISPATCH = {
        "pymupdf": "_extract_pymupdf",
        "docling": "_extract_docling",
        "google_docai": "_extract_google_docai",
        "gpt5": "_extract_gpt5",
        "claude_sonnet": "_extract_claude",
        "mistral": "_extract_mistral",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_tool(
        self,
        tool_name: str,
        file_path: str,
        document_id: uuid.UUID,
        db: AsyncSession,
    ) -> List[ExtractionResult]:
        """Run a single tool and persist ExtractionResult rows."""
        method_name = self._DISPATCH.get(tool_name)
        if not method_name:
            er = ExtractionResult(
                document_id=document_id,
                tool_name=tool_name,
                table_index=0,
                error_message=f"Unknown tool: {tool_name}",
                processing_time_ms=0,
                cost_usd=0,
            )
            db.add(er)
            await db.flush()
            return [er]

        start = time.perf_counter()
        error_msg: Optional[str] = None
        tables: List[Dict[str, Any]] = []

        try:
            raw = await getattr(self, method_name)(file_path)
            if isinstance(raw, dict) and raw.get("success") is False:
                error_msg = raw.get("error", "extraction returned success=False")
            else:
                tables = _normalise_tables(raw)
        except Exception as exc:
            logger.exception(f"{tool_name} failed on {file_path}")
            error_msg = str(exc)

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        doc_result = await db.execute(
            __import__("sqlalchemy").select(Document).where(Document.id == document_id)
        )
        doc = doc_result.scalar_one_or_none()
        page_count = doc.page_count or 1 if doc else 1
        cost = calculate_cost(tool_name, page_count)

        results: List[ExtractionResult] = []

        if error_msg or not tables:
            er = ExtractionResult(
                document_id=document_id,
                tool_name=tool_name,
                table_index=0,
                extracted_headers=None,
                extracted_rows=None,
                processing_time_ms=elapsed_ms,
                cost_usd=cost,
                error_message=error_msg or "No tables extracted",
            )
            db.add(er)
            await db.flush()
            results.append(er)
        else:
            for idx, tbl in enumerate(tables):
                er = ExtractionResult(
                    document_id=document_id,
                    tool_name=tool_name,
                    table_index=idx,
                    extracted_headers=tbl.get("headers"),
                    extracted_rows=tbl.get("rows"),
                    processing_time_ms=elapsed_ms if idx == 0 else 0,
                    cost_usd=cost if idx == 0 else 0,
                )
                db.add(er)
                await db.flush()
                results.append(er)

        return results

    async def run_all_tools(
        self,
        document_id: uuid.UUID,
        file_path: str,
        db: AsyncSession,
    ) -> List[ExtractionResult]:
        """Run every registered tool sequentially and return all results."""
        all_results: List[ExtractionResult] = []
        for tool_name in self._DISPATCH:
            results = await self.run_tool(tool_name, file_path, document_id, db)
            all_results.extend(results)
        return all_results
