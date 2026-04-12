"""
GPT-5 Vision service for PDF table extraction — thesis-grade implementation.

Uses the OpenAI Responses API (client.responses.create) with all GPT-5
document-analysis levers:
  - detail="original"          — preserves fine labels/grid lines on scans
  - reasoning={"effort":"high"} — multi-region table reasoning
  - text={"verbosity":"high"}   — faithful transcription, not summaries
  - Structured Outputs           — schema-guaranteed JSON, no fence stripping

Domain-specific enrichment (company name injection, header validation API
calls, document context analysis) is disabled by ENABLE_ENRICHMENT = False
so that GPT-5 is scientifically comparable to Textract, Docling, etc.
"""

import os
import json
import base64
import logging
import fitz  # PyMuPDF
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from PIL import Image, ImageEnhance
from openai import OpenAI
from app.services.ai.shared_prompts import SYSTEM_PROMPT, USER_PROMPT, EXTRACTION_SCHEMA

logger = logging.getLogger(__name__)

# ── Feature flags ─────────────────────────────────────────────────────────────
# Flip ENABLE_RESPONSES_API to False to fall back to Chat Completions (legacy).
ENABLE_RESPONSES_API: bool = True

# Set True only for non-thesis/production use that needs company enrichment.
ENABLE_ENRICHMENT: bool = False

# ── Structured output schema ──────────────────────────────────────────────────
# Alias the shared schema under the legacy name so any code that references
# TABLE_EXTRACTION_SCHEMA directly still works without modification.
TABLE_EXTRACTION_SCHEMA: Dict[str, Any] = EXTRACTION_SCHEMA


class GPT4oVisionService:
    """
    GPT-5 table extraction service.

    Supports two document paths:
      • Digital PDFs — text extracted via PyMuPDF, sent as text input.
        Uses reasoning=medium and verbosity=high for faithful transcription.
      • Scanned PDFs — pages rendered to PNG and sent as input_image blocks.
        Uses detail="original" and reasoning=high for dense scan analysis.

    Both paths use Structured Outputs to guarantee schema-valid JSON output.
    Token usage from each API response is recorded in self._last_usage for
    accurate cost estimation by the EvaluationRunner.
    """

    def __init__(self) -> None:
        self.client: Optional[OpenAI] = None
        self._last_usage: Dict[str, Optional[int]] = {
            "input_tokens": None,
            "output_tokens": None,
        }
        self._initialize_client()

    def _initialize_client(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set — GPT-5 service unavailable")
            return
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("GPT-5 service initialised (Responses API=%s)", ENABLE_RESPONSES_API)
        except Exception as exc:
            logger.error("Failed to initialise OpenAI client: %s", exc)

    def is_available(self) -> bool:
        return self.client is not None

    # ── PDF type detection ────────────────────────────────────────────────────

    def is_digital_pdf(self, pdf_path: str) -> bool:
        """Return True if the PDF contains selectable text (digital), False if scanned."""
        try:
            doc = fitz.open(pdf_path)
            text = "".join(
                doc.load_page(p).get_text()
                for p in range(min(3, len(doc)))
            )
            doc.close()
            text_length = len(text.strip())
            has_structured = any(
                kw in text.upper()
                for kw in ("COMMISSION", "PREMIUM", "COVERAGE", "POLICY", "CUSTOMER")
            )
            is_digital = text_length > 100 and has_structured
            logger.info(
                "PDF type: %d chars, structured=%s → digital=%s",
                text_length, has_structured, is_digital,
            )
            return is_digital
        except Exception as exc:
            logger.error("PDF type detection failed: %s", exc)
            return False

    # ── Page selection helpers ────────────────────────────────────────────────

    def _select_representative_pages(
        self, total_pages: int, max_pages: int, pdf_path: Optional[str] = None
    ) -> List[int]:
        if total_pages <= max_pages:
            return list(range(total_pages))
        if pdf_path:
            return self._select_pages_by_content_analysis(pdf_path, total_pages, max_pages)
        first = list(range(min(3, total_pages // 4)))
        last = list(range(max(0, total_pages - 3), total_pages))
        remaining = max_pages - len(first) - len(last)
        if remaining > 0:
            mid_start, mid_end = len(first), total_pages - len(last)
            step = max(1, (mid_end - mid_start) // remaining)
            middle = list(range(mid_start, mid_end, step))[:remaining]
        else:
            middle = []
        selected = sorted(set(first + middle + last))
        logger.info("Page sampling: %d/%d pages selected", len(selected), total_pages)
        return selected

    def _select_pages_by_content_analysis(
        self, pdf_path: str, total_pages: int, max_pages: int
    ) -> List[int]:
        try:
            doc = fitz.open(pdf_path)
            scores = [
                (p, self._calculate_page_content_score(
                    doc.load_page(p).get_text().upper(), p, total_pages
                ))
                for p in range(total_pages)
            ]
            doc.close()
            scores.sort(key=lambda x: x[1], reverse=True)
            selected: List[int] = []
            if scores and (scores[0][0] == 0 or scores[0][1] > 0):
                selected.append(0)
            for page_num, score in scores:
                if page_num not in selected and len(selected) < max_pages:
                    if score > 0 or (score > -20 and len(selected) < max_pages // 2):
                        selected.append(page_num)
            selected.sort()
            logger.info("Content-based selection: %d pages", len(selected))
            return selected
        except Exception as exc:
            logger.error("Content-based page selection failed: %s", exc)
            return list(range(min(max_pages, total_pages)))

    def _calculate_page_content_score(
        self, text: str, page_num: int, total_pages: int
    ) -> float:
        import re
        score = max(0.0, (total_pages - page_num) / total_pages * 10)
        for kw in ("COMMISSION AMOUNT", "TOTAL COMMISSION", "PREMIUM", "COVERAGE PERIOD",
                   "GROUP", "COMPANY", "SMALL GROUP", "MEDICAL", "DENTAL", "VISION",
                   "RATE", "PERCENTAGE", "AMOUNT", "PAID", "DUE"):
            if kw in text:
                score += 5.0
        for kw in ("$", "PAYMENT", "BILLING", "STATEMENT", "SUMMARY", "TOTAL"):
            if kw in text:
                score += 2.0
        for kw in ("NO COMMISSION ACTIVITY", "NO ACTIVITY", "INACTIVE",
                   "TERMINATED", "CANCELLED", "VOID"):
            if kw in text:
                score -= 50.0
        for kw in ("FOR THIS STATEMENT", "NO COMMISSION", "NO PREMIUM"):
            if kw in text:
                score -= 30.0
        score += min(len(text.strip()) / 1000.0, 10.0)
        if any(re.search(p, text) for p in (
            r"\d{1,2}/\d{1,2}/\d{4}", r"\d{4}-\d{2}-\d{2}",
            r"JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER",
        )):
            score += 3.0
        return score

    # ── Image conversion helpers ──────────────────────────────────────────────

    def _calculate_adaptive_dpi(self, page: fitz.Page) -> int:
        """
        Higher DPI for content-dense pages — more data needs more detail.

        With detail='original' the Responses API can handle up to 10 000 patches
        (6000px max dimension), so high-DPI images are fully utilised.
        """
        text_length = len(page.get_text())
        if text_length > 1000:
            return 600   # Dense table page — maximum fidelity
        elif text_length > 300:
            return 500   # Medium density
        else:
            return 400   # Sparse / mostly whitespace

    def _convert_page_to_optimized_image(
        self, doc: fitz.Document, page_num: int
    ) -> Optional[str]:
        try:
            page = doc.load_page(page_num)
            dpi = self._calculate_adaptive_dpi(page)
            matrix = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img = self._enhance_image(img, dpi)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode()
            logger.debug("Page %d: %d DPI, %d bytes, size=%s", page_num + 1, dpi, len(b64), img.size)
            return b64
        except Exception as exc:
            logger.error("Page %d conversion failed: %s", page_num, exc)
            return None

    def _enhance_image(self, img: Image.Image, dpi: int) -> Image.Image:
        try:
            if img.mode != "RGB":
                img = img.convert("RGB")
            factor_c = 1.3 if dpi >= 500 else 1.2
            factor_s = 1.2 if dpi >= 500 else 1.1
            img = ImageEnhance.Contrast(img).enhance(factor_c)
            img = ImageEnhance.Sharpness(img).enhance(factor_s)
            return img
        except Exception as exc:
            logger.warning("Image enhancement failed: %s", exc)
            return img

    # ── Prompt ────────────────────────────────────────────────────────────────

    def _create_system_prompt(self) -> str:
        """
        Single shared system prompt for both scanned and digital paths.

        Deliberately does NOT instruct the model to add a 'Company Name' column
        or any other synthetic column. Doing so would fabricate data that is not
        in the ground truth and would degrade TEDS/GriTS scores.
        """
        return """You are a precise data extraction specialist for insurance commission statements.

EXTRACTION RULES:
1. Extract EVERY table visible in the document.
2. Copy column headers EXACTLY as written — do not normalise or interpret.
3. Copy cell values EXACTLY as written — do not reformat or calculate.
4. Extract columns in EXACT visual order from LEFT to RIGHT.
5. If a cell is empty, leave it as an empty string.
6. Do NOT invent, infer, guess, or add columns not present in the source.
7. Do NOT reorder columns based on semantic meaning.
8. Pay careful attention to the leftmost and rightmost columns — they are
   frequently missed.
9. For multi-line headers, join with a single space.
10. Preserve all rows, including subtotals and summary rows.

Return only the JSON object matching the required schema."""

    # ── Responses API call helpers ────────────────────────────────────────────

    def _responses_call(
        self,
        content_blocks: List[Dict[str, Any]],
        reasoning_effort: str,
        verbosity: Optional[str] = None,
    ) -> str:
        """
        Single wrapper for all Responses API calls.

        Args:
            content_blocks: list of input_text / input_image dicts.
            reasoning_effort: "high" (vision/multi-region) or "medium" (digital text).
            verbosity: "high" for faithful transcription path; None for vision path.

        Returns:
            response.output_text (schema-valid JSON string).
        """
        text_cfg: Dict[str, Any] = {
            "format": {
                "type": "json_schema",
                "name": "table_extraction",
                "schema": TABLE_EXTRACTION_SCHEMA,
                "strict": True,
            }
        }
        if verbosity:
            text_cfg["verbosity"] = verbosity

        response = self.client.responses.create(  # type: ignore[union-attr]
            model="gpt-5",
            input=[{"role": "user", "content": content_blocks}],
            instructions=SYSTEM_PROMPT,
            reasoning={"effort": reasoning_effort},
            text=text_cfg,
            max_output_tokens=32000,
        )

        # Record real token usage for the cost calculator
        usage = getattr(response, "usage", None)
        self._last_usage = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        }
        logger.info(
            "GPT-5 usage — input=%s output=%s",
            self._last_usage["input_tokens"],
            self._last_usage["output_tokens"],
        )

        return response.output_text  # type: ignore[return-value]

    def _chat_completions_fallback(
        self,
        messages: List[Dict[str, Any]],
    ) -> str:
        """
        Legacy Chat Completions path (ENABLE_RESPONSES_API=False).

        Returns raw content string; caller must strip JSON fences manually.
        """
        response = self.client.chat.completions.create(  # type: ignore[union-attr]
            model="gpt-5",
            messages=messages,
            max_completion_tokens=32000,
        )
        if not response.choices:
            raise RuntimeError("Chat Completions returned no choices")
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Chat Completions returned empty content")
        # Record usage
        usage = getattr(response, "usage", None)
        self._last_usage = {
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "output_tokens": getattr(usage, "completion_tokens", None),
        }
        return content

    # ── Scanned PDF path ──────────────────────────────────────────────────────

    def extract_from_scanned_pdf(
        self, pdf_path: str, max_pages: int = 30
    ) -> Dict[str, Any]:
        """Convert PDF pages to PNG images and extract tables via vision."""
        if not self.is_available():
            return {"success": False, "error": "GPT-5 service not available"}
        try:
            doc = fitz.open(pdf_path)
            try:
                total_pages = len(doc)
                if total_pages > max_pages:
                    selected = self._select_representative_pages(
                        total_pages, max_pages, pdf_path
                    )
                    logger.warning(
                        "GPT-5: document %s has %d pages; only %d selected for analysis. "
                        "Tables on unselected pages will not be extracted.",
                        pdf_path,
                        total_pages,
                        len(selected),
                    )
                else:
                    selected = list(range(total_pages))
                images = [
                    img
                    for p in selected
                    if (
                        img := self._convert_page_to_optimized_image(doc, p)
                    )
                    is not None
                ]
            finally:
                doc.close()
            if not images:
                return {"success": False, "error": "Failed to render any pages to images"}
            return self._extract_tables_with_vision(images, selected)
        except Exception as exc:
            logger.error("Scanned PDF extraction failed: %s", exc)
            return {"success": False, "error": f"Scanned extraction failed: {exc}"}

    def _extract_tables_with_vision(
        self, enhanced_images: List[str], page_numbers: List[int]
    ) -> Dict[str, Any]:
        """
        Send page images to GPT-5 Responses API with detail='original'.

        detail='original' is the critical setting for dense commission
        statement scans — it preserves fine numeric values and grid lines
        that degrade with downsampling.  reasoning=high handles multi-region
        table analysis across the batch of page images.
        """
        try:
            logger.info("Vision call: %d images, pages=%s", len(enhanced_images), page_numbers)

            if ENABLE_RESPONSES_API:
                content_blocks: List[Dict[str, Any]] = [
                    {"type": "input_text", "text": USER_PROMPT}
                ]
                for b64 in enhanced_images:
                    content_blocks.append({
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{b64}",
                        "detail": "original",   # dense scan / small labels / low contrast
                    })
                raw = self._responses_call(
                    content_blocks,
                    reasoning_effort="high",   # multi-region table reasoning
                )
            else:
                # ── Chat Completions fallback ──────────────────────────────
                messages: List[Dict[str, Any]] = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": USER_PROMPT}],
                    },
                ]
                for b64 in enhanced_images:
                    messages[1]["content"].append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    })
                raw = self._chat_completions_fallback(messages)

            return self._parse_extraction_response(raw, "vision_analysis")

        except Exception as exc:
            logger.error("Vision extraction failed: %s", exc)
            return {"success": False, "error": f"Vision analysis failed: {exc}"}

    # ── Digital PDF path ──────────────────────────────────────────────────────

    def _extract_pdf_text(self, pdf_path: str) -> str:
        try:
            doc = fitz.open(pdf_path)
            parts = []
            for p in range(len(doc)):
                text = doc.load_page(p).get_text()
                if text.strip():
                    parts.append(f"\n--- PAGE {p + 1} ---\n{text}\n")
            doc.close()
            return "".join(parts)
        except Exception as exc:
            logger.error("PDF text extraction failed: %s", exc)
            return ""

    def extract_from_digital_pdf_intelligent(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract tables from a digital (text-based) PDF using the Responses API.

        text.verbosity='high' is OpenAI's lever for faithful layout-preserving
        transcription rather than compressed summaries.  reasoning=medium is
        sufficient because the text is already machine-readable.
        """
        if not self.is_available():
            return {"success": False, "error": "GPT-5 service not available"}
        try:
            doc_content = self._extract_pdf_text(pdf_path)
            if not doc_content.strip():
                return {"success": False, "error": "PDF contains no extractable text"}

            logger.info("Digital PDF call: %d chars of text", len(doc_content))
            prompt_text = USER_PROMPT + "\n\n--- DOCUMENT TEXT ---\n\n" + doc_content[:100_000]

            if ENABLE_RESPONSES_API:
                raw = self._responses_call(
                    [{"type": "input_text", "text": prompt_text}],
                    reasoning_effort="medium",   # text is already readable
                    verbosity="high",            # faithful transcription, not summary
                )
            else:
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_text},
                ]
                raw = self._chat_completions_fallback(messages)

            return self._parse_extraction_response(raw, "digital_pdf")

        except Exception as exc:
            logger.error("Digital PDF extraction failed: %s", exc)
            return {"success": False, "error": f"Digital extraction failed: {exc}"}

    # Keep legacy name as alias so any direct callers are unaffected
    extract_from_digital_pdf = extract_from_digital_pdf_intelligent

    # ── Response parsing ──────────────────────────────────────────────────────

    def _parse_extraction_response(
        self, content: str, method: str
    ) -> Dict[str, Any]:
        """
        Parse the model's JSON output.

        With ENABLE_RESPONSES_API=True and Structured Outputs, the content is
        always schema-valid JSON — no fence stripping or retries needed.

        With the Chat Completions fallback, a lightweight fence strip is applied
        before parsing.
        """
        try:
            if not content or not content.strip():
                return {"success": False, "error": "Model returned empty response"}

            # Fence stripping: only needed for Chat Completions fallback.
            # Structured Outputs never wrap the JSON in markdown fences.
            text = content.strip()
            if text.startswith("```"):
                # Strip opening fence (```json or ```)
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            parsed_json = json.loads(text)
            tables_raw = parsed_json.get("tables", [])

            if not tables_raw:
                return {"success": False, "error": "No tables found in model response"}

            processed: List[Dict[str, Any]] = []
            for i, table in enumerate(tables_raw):
                headers: List[str] = table.get("headers", [])
                rows: List[List[str]] = table.get("rows", [])

                # Normalise row lengths to header count; drop fully empty rows
                n = len(headers)
                rows = [(r + [""] * n)[:n] for r in rows]
                rows = [r for r in rows if any(c.strip() for c in r)]

                if not rows and not headers:
                    continue

                processed.append({
                    "headers": headers,
                    "rows": rows,
                    "extractor": f"gpt5_{method}",
                    "metadata": {
                        "extraction_method": method,
                        "timestamp": datetime.now().isoformat(),
                        "table_index": i,
                        "confidence_score": table.get("confidence_score", 0.9),
                        "page_number": table.get("page_number"),
                    },
                })

            if not processed:
                return {"success": False, "error": "All tables were empty after normalisation"}

            out: Dict[str, Any] = {
                "success": True,
                "tables": processed,
                "extraction_metadata": {
                    "method": method,
                    "timestamp": datetime.now().isoformat(),
                },
            }

            doc_meta = parsed_json.get("document_metadata")
            if doc_meta:
                out["document_metadata"] = doc_meta

            return out

        except json.JSONDecodeError as exc:
            logger.error("JSON decode failed (%s): %s — preview: %.200s", method, exc, content)
            return {"success": False, "error": f"JSON decode failed: {exc}"}
        except Exception as exc:
            logger.error("Response parsing failed (%s): %s", method, exc)
            return {"success": False, "error": f"Parsing failed: {exc}"}

    # ── Main entry point ──────────────────────────────────────────────────────

    def extract_commission_data(
        self, pdf_path: str, max_pages: int = 30
    ) -> Dict[str, Any]:
        """
        Route extraction based on PDF type.  Returns:
        {
            "success": bool,
            "tables": [{"headers": [...], "rows": [[...]], ...}, ...],
            "usage": {"input_tokens": int | None, "output_tokens": int | None},
            ...
        }
        """
        if not self.is_available():
            return {"success": False, "error": "GPT-5 service not available"}

        try:
            logger.info("GPT-5: extracting from %s", pdf_path)
            is_digital = self.is_digital_pdf(pdf_path)

            if is_digital:
                logger.info("Digital PDF — using text + Responses API")
                result = self.extract_from_digital_pdf_intelligent(pdf_path)
            else:
                logger.info("Scanned PDF — using vision + Responses API")
                result = self.extract_from_scanned_pdf(pdf_path, max_pages)

            # Attach real token usage so the runner can pass it to calculate_cost
            result["usage"] = dict(self._last_usage)

            # Company enrichment: disabled for thesis benchmark fairness
            if ENABLE_ENRICHMENT and result.get("success") and result.get("tables"):
                from app.services.data_processing.company_name_service import (
                    CompanyNameDetectionService,
                )
                detector = CompanyNameDetectionService()
                result["tables"] = [
                    detector.detect_company_names_in_extracted_data(t, "gpt5")
                    for t in result["tables"]
                ]
                result["company_detection_applied"] = True

            return result

        except Exception as exc:
            logger.error("GPT-5 extraction failed: %s", exc)
            return {"success": False, "error": f"Extraction failed: {exc}"}

    # ── Table merging utilities (kept for external callers) ───────────────────

    def merge_similar_tables(
        self, tables: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Delegate to the shared evaluation merge policy (same as EvaluationRunner)."""
        from app.services.evaluation.table_merging import merge_similar_tables_global

        return merge_similar_tables_global(tables)
