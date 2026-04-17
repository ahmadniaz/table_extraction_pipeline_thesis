"""
Evaluation runner — routes extraction requests to the correct service,
records timing and cost, and normalises results into ExtractionResult rows.
"""

import asyncio
import concurrent.futures
import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExtractionResult, Document
from .cost_calculator import calculate_cost
from .table_merging import merge_similar_tables_global

logger = logging.getLogger(__name__)


def _json_safe(raw: Any) -> Any:
    """Best-effort JSON-serialisable snapshot for raw_output."""
    if raw is None:
        return None
    if isinstance(raw, (str, int, float, bool)):
        return raw
    if isinstance(raw, dict):
        return {str(k): _json_safe(v) for k, v in raw.items()}
    if isinstance(raw, (list, tuple)):
        return [_json_safe(x) for x in raw]
    if hasattr(raw, "model_dump"):
        try:
            return raw.model_dump()
        except Exception:
            pass
    if hasattr(raw, "__dict__"):
        try:
            return json.loads(json.dumps(raw, default=str))
        except Exception:
            return str(raw)
    return str(raw)


def _classify_exception(exc: BaseException) -> Tuple[str, bool, str]:
    """
    Map exception to (failure_reason, is_transient_failure, error_message).
    """
    msg = str(exc)

    try:
        import openai

        if isinstance(exc, openai.RateLimitError):
            return "rate_limit", True, msg
        if isinstance(exc, openai.APIConnectionError):
            return "server_down", True, msg
    except ImportError:
        pass

    try:
        import anthropic

        if isinstance(exc, anthropic.RateLimitError):
            return "rate_limit", True, msg
        if isinstance(exc, anthropic.APIConnectionError):
            return "server_down", True, msg
        if isinstance(exc, anthropic.APIStatusError):
            code = getattr(exc, "status_code", None)
            if code in (429, 529, 503):
                return "rate_limit", True, msg
    except ImportError:
        pass

    try:
        import mistralai

        rl = getattr(mistralai, "RateLimitError", None)
        if rl is not None and isinstance(exc, rl):
            return "rate_limit", True, msg
    except ImportError:
        pass

    try:
        import requests

        if isinstance(exc, requests.exceptions.ConnectionError):
            return "server_down", True, msg
    except ImportError:
        pass

    try:
        from botocore.exceptions import ClientError, BotoCoreError, EndpointConnectionError

        if isinstance(exc, EndpointConnectionError):
            return "server_down", True, msg
        if isinstance(exc, ClientError):
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("ThrottlingException", "ProvisionedThroughputExceededException"):
                return "rate_limit", True, msg
            if "Throttling" in code or "RateExceeded" in msg:
                return "rate_limit", True, msg
            return "api_error", False, msg
        if isinstance(exc, BotoCoreError):
            return "server_down", True, msg
    except ImportError:
        pass

    if any(kw in msg for kw in ("ThrottlingException", "Rate exceeded", "Too Many Requests")):
        return "rate_limit", True, msg

    if isinstance(exc, (asyncio.TimeoutError, concurrent.futures.TimeoutError)):
        return "timeout", True, msg

    return "api_error", False, msg


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
            # Preserve optional metadata if present (PyMuPDF-specific)
            entry = {"headers": headers, "rows": rows}
            for meta_key in (
                "page_number",
                "table_index",
                "strategy_used",
                "bbox",
                "row_count",
                "col_count",
                "textract_confidence",
                "cell_matching_used",
                "backend_used",
                "metadata",
                "extractor",
            ):
                if meta_key in t:
                    entry[meta_key] = t[meta_key]
            tables.append(entry)
    return tables


def _empty_extracted_rows(tables: List[Dict[str, Any]]) -> bool:
    if not tables:
        return True
    for t in tables:
        rows = t.get("rows")
        if isinstance(rows, list) and len(rows) > 0:
            return False
    return True


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
            from app.services.docling.docling_service import DoclingService

            self._services["docling"] = DoclingService()
        return self._services["docling"]

    def _get_pymupdf(self):
        if "pymupdf" not in self._services:
            from app.services.pymupdf.service import PyMuPDFService

            self._services["pymupdf"] = PyMuPDFService()
        return self._services["pymupdf"]

    def _get_aws_textract(self):
        if "aws_textract" not in self._services:
            from app.services.textract.service import TextractService

            self._services["aws_textract"] = TextractService()
        return self._services["aws_textract"]

    # ------------------------------------------------------------------
    # Per-tool extraction
    # ------------------------------------------------------------------

    async def _extract_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """Rule-based extraction using PyMuPDF native find_tables() API."""
        service = self._get_pymupdf()
        loop = asyncio.get_event_loop()
        # PyMuPDF is synchronous (C-extension); run in thread executor
        # to avoid blocking the FastAPI async event loop.
        return await loop.run_in_executor(
            None, service.extract_tables, file_path
        )

    async def _extract_aws_textract(self, file_path: str) -> Dict[str, Any]:
        """Cloud-based table extraction using AWS Textract AnalyzeDocument (TABLES)."""
        service = self._get_aws_textract()
        loop = asyncio.get_event_loop()
        # Textract client is synchronous; offload to executor to keep FastAPI async.
        return await loop.run_in_executor(
            None,
            service.analyze_document_tables,
            file_path,
        )

    async def _extract_docling(
        self, file_path: str, is_digital: bool = True
    ) -> Dict[str, Any]:
        """Table extraction using Docling v2 official API with TableFormerMode.ACCURATE."""
        service = self._get_docling()
        # Docling's converter is synchronous (C++ backend via Python bindings).
        # Run in thread executor to avoid blocking the FastAPI event loop.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, service.extract_tables, file_path, is_digital
        )

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
        "aws_textract": "_extract_aws_textract",
        "google_docai": "_extract_google_docai",
        "gpt5": "_extract_gpt5",
        "claude_sonnet": "_extract_claude",
        "mistral": "_extract_mistral",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def _persist_and_commit(self, db: AsyncSession, er: ExtractionResult) -> None:
        db.add(er)
        await db.flush()
        await db.commit()

    async def run_tool(
        self,
        tool_name: str,
        file_path: str,
        document_id: uuid.UUID,
        db: AsyncSession,
    ) -> List[ExtractionResult]:
        """Run a single tool and persist ExtractionResult rows (commit after each row)."""
        method_name = self._DISPATCH.get(tool_name)
        if not method_name:
            er = ExtractionResult(
                document_id=document_id,
                tool_name=tool_name,
                table_index=0,
                error_message=f"Unknown tool: {tool_name}",
                processing_time_ms=0,
                cost_usd=0,
                failure_reason="api_error",
                is_transient_failure=False,
                raw_output=None,
                is_draft=False,
            )
            await self._persist_and_commit(db, er)
            return [er]

        doc_result = await db.execute(select(Document).where(Document.id == document_id))
        doc = doc_result.scalar_one_or_none()
        page_count = doc.page_count or 1 if doc else 1
        is_digital = bool(doc.is_digital) if doc and doc.is_digital is not None else True

        start = time.perf_counter()
        error_msg: Optional[str] = None
        failure_reason: Optional[str] = None
        is_transient = False
        tables: List[Dict[str, Any]] = []
        raw: Any = None
        raw_safe: Any = None

        try:
            if tool_name == "docling":
                raw = await self._extract_docling(file_path, is_digital=is_digital)
            else:
                raw = await getattr(self, method_name)(file_path)
            raw_safe = _json_safe(raw)
            if isinstance(raw, dict) and raw.get("success") is False:
                error_msg = raw.get("error", "extraction returned success=False")
                em = (error_msg or "").lower()
                if "rate limit" in em or "429" in em or "529" in em or "overloaded" in em:
                    failure_reason = "rate_limit"
                    is_transient = True
                elif "timeout" in em:
                    failure_reason = "timeout"
                    is_transient = True
                elif "connection" in em or "connect" in em:
                    failure_reason = "server_down"
                    is_transient = True
                else:
                    failure_reason = "api_error"
                    is_transient = False
            else:
                tables = _normalise_tables(raw)
                tables = merge_similar_tables_global(tables)
        except BaseException as exc:
            logger.exception("%s failed on %s", tool_name, file_path)
            failure_reason, is_transient, error_msg = _classify_exception(exc)
            raw_safe = _json_safe(raw) if raw is not None else None

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # Use real token counts from LLM services when available (gpt5, claude, mistral)
        usage = raw.get("usage", {}) if isinstance(raw, dict) else {}
        input_tokens = usage.get("input_tokens") if usage else None
        output_tokens = usage.get("output_tokens") if usage else None
        cost = calculate_cost(tool_name, page_count, input_tokens, output_tokens)

        results: List[ExtractionResult] = []

        if error_msg is not None:
            er = ExtractionResult(
                document_id=document_id,
                tool_name=tool_name,
                table_index=0,
                extracted_headers=None,
                extracted_rows=None,
                processing_time_ms=elapsed_ms,
                cost_usd=cost,
                error_message=error_msg,
                failure_reason=failure_reason,
                is_transient_failure=is_transient,
                raw_output=raw_safe,
                is_draft=False,
            )
            await self._persist_and_commit(db, er)
            results.append(er)
            return results

        if _empty_extracted_rows(tables):
            if tool_name in ("pymupdf", "docling") and not is_digital:
                fr = "tool_limitation"
                transient = False
            else:
                fr = "empty_output"
                transient = False
            er = ExtractionResult(
                document_id=document_id,
                tool_name=tool_name,
                table_index=0,
                extracted_headers=None,
                extracted_rows=None,
                processing_time_ms=elapsed_ms,
                cost_usd=cost,
                error_message="No tables extracted",
                failure_reason=fr,
                is_transient_failure=transient,
                raw_output=raw_safe,
                is_draft=False,
            )
            await self._persist_and_commit(db, er)
            results.append(er)
            return results

        for idx, tbl in enumerate(tables):
            er = ExtractionResult(
                document_id=document_id,
                tool_name=tool_name,
                table_index=idx,
                extracted_headers=tbl.get("headers"),
                extracted_rows=tbl.get("rows"),
                processing_time_ms=elapsed_ms if idx == 0 else 0,
                cost_usd=cost if idx == 0 else 0,
                error_message=None,
                failure_reason=None,
                is_transient_failure=False,
                raw_output=raw_safe if idx == 0 else None,
                is_draft=False,
            )
            await self._persist_and_commit(db, er)
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
