"""
Docling table extraction service — thesis-grade implementation.

Uses Docling's official v2 API with:
  - PdfPipelineOptions(do_table_structure=True, do_ocr=True)
  - TableFormerMode.ACCURATE for maximum table structure quality
  - do_cell_matching=True (maps TableFormer structure back to PDF cells
    for digital PDFs, improving column separation accuracy)
  - EasyOcrOptions for scanned PDFs (already installed: easyocr ^1.7)
  - conv_res.document.tables iterator → export_to_dataframe()

Scientific note on do_cell_matching:
  True  (default) = structure prediction mapped back to PDF text cells.
                    Best for digital PDFs. Headers/rows align to the
                    actual text in the PDF coordinate system.
  False           = text cells from structure model predictions used.
                    Better when columns are erroneously merged.
  Strategy: attempt True first; if any table has mismatched column
  counts across rows, retry that document with False.

Note: docling_core TableItem.export_to_dataframe() takes no arguments
in v2.x; column headers and body rows are derived from the table grid.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DoclingService:
    """
    Extracts tables from PDF documents using Docling's official v2 API.

    Key design decisions:
    - DocumentConverter is initialised ONCE (expensive: loads TableFormer
      ACCURATE model ~500MB) and reused across all documents.
    - Two converters are maintained: one with do_cell_matching=True
      (digital PDFs) and one with do_cell_matching=False (fallback for
      misaligned column splits). This matches Docling's documented
      recommendation for handling column merge issues.
    - All Docling I/O is synchronous (C++ backend); run in thread
      executor to avoid blocking the FastAPI async event loop.
    - For scanned PDFs (detected via is_digital=False passed as hint),
      do_ocr=True ensures EasyOCR is applied. For digital PDFs, OCR
      is still enabled as a fallback — Docling applies it only to
      image-based content even in mixed PDFs.
    """

    def __init__(self):
        self._converter_cell_match: Optional[Any] = None
        self._converter_no_cell_match: Optional[Any] = None
        self._converter_pdfium: Optional[Any] = None
        self._initialised = False

    def _ensure_initialised(self) -> None:
        """Lazy initialisation — load Docling models on first use."""
        if self._initialised:
            return

        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            TableFormerMode,
            EasyOcrOptions,
        )

        logger.info(
            "Initialising Docling DocumentConverter with TableFormerMode.ACCURATE. "
            "This loads ~500MB of models and may take 30–60 seconds on first run."
        )

        # OCR options: EasyOCR English, no GPU (CPU-safe for thesis environment)
        ocr_options = EasyOcrOptions(lang=["en"], use_gpu=False)

        # ── Converter A: cell matching ON (default, best for digital PDFs) ──
        opts_a = PdfPipelineOptions(do_table_structure=True, do_ocr=True)
        opts_a.table_structure_options.mode = TableFormerMode.ACCURATE
        opts_a.table_structure_options.do_cell_matching = True
        opts_a.ocr_options = ocr_options

        self._converter_cell_match = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=opts_a)
            }
        )

        # ── Converter A2: same pipeline as A but PyPdfium backend (page-dimensions fix) ──
        opts_pdfium = PdfPipelineOptions(do_table_structure=True, do_ocr=True)
        opts_pdfium.table_structure_options.mode = TableFormerMode.ACCURATE
        opts_pdfium.table_structure_options.do_cell_matching = True
        opts_pdfium.ocr_options = ocr_options

        self._converter_pdfium = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=opts_pdfium,
                    backend=PyPdfiumDocumentBackend,
                )
            }
        )

        # ── Converter B: cell matching OFF (fallback for merged-column PDFs) ──
        opts_b = PdfPipelineOptions(do_table_structure=True, do_ocr=True)
        opts_b.table_structure_options.mode = TableFormerMode.ACCURATE
        opts_b.table_structure_options.do_cell_matching = False
        opts_b.ocr_options = ocr_options

        self._converter_no_cell_match = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=opts_b)
            }
        )

        self._initialised = True
        logger.info("Docling converters initialised successfully.")

    def extract_tables(
        self, file_path: str, is_digital: bool = True
    ) -> Dict[str, Any]:
        """
        Extract all tables from a PDF using Docling v2 official API.

        Args:
            file_path: Absolute or relative path to the PDF file.
            is_digital: Hint from Document.is_digital. Used for logging
                        only — Docling applies OCR regardless based on
                        its own page analysis.

        Returns:
            {
                "tables": [
                    {
                        "headers": list[str],
                        "rows": list[list[str]],
                        "page_number": int,   # 0-based
                        "table_index": int,
                        "row_count": int,
                        "col_count": int,
                        "cell_matching_used": bool,
                        "backend_used": str,
                    },
                    ...
                ],
                "total_pages": int,
                "tool": "docling",
                "model": "TableFormerMode.ACCURATE",
                "backend_used": str,
            }

        Raises:
            FileNotFoundError: if file_path does not exist.
            RuntimeError: if Docling conversion fails.
        """
        self._ensure_initialised()

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        # ── Primary conversion: cell matching ON ──
        logger.info("Docling: converting %s (is_digital=%s)", path.name, is_digital)
        backend_used = "docling_parse_v4"
        try:
            conv_res = self._converter_cell_match.convert(str(path))
        except RuntimeError as exc:
            msg = str(exc).lower()
            if "page-dimensions" in msg or "page-dimension" in msg:
                logger.warning(
                    "Docling: docling_parse_v4 failed with page-dimensions error on %s — "
                    "retrying with PyPdfiumDocumentBackend",
                    path.name,
                )
                try:
                    conv_res = self._converter_pdfium.convert(str(path))
                    backend_used = "pypdfium2"
                except Exception as exc2:
                    raise RuntimeError(
                        f"Docling conversion failed for {file_path} "
                        f"(both backends attempted): {exc2}"
                    ) from exc2
            else:
                raise RuntimeError(
                    f"Docling conversion failed for {file_path}: {exc}"
                ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Docling conversion failed for {file_path}: {exc}"
            ) from exc

        tables_primary = self._extract_tables_from_result(
            conv_res, cell_matching_used=True, backend_used=backend_used
        )

        conv_for_meta: Any = conv_res
        backend_used_out = backend_used

        # ── Detect column-merge issue ──
        # If any table has inconsistent column counts across rows,
        # retry that document with cell matching OFF.
        has_column_merge_issue = self._detect_column_merge_issue(tables_primary)

        if has_column_merge_issue:
            logger.info(
                "Docling: column merge issue detected in %s — "
                "retrying with do_cell_matching=False",
                path.name,
            )
            try:
                conv_res_b = self._converter_no_cell_match.convert(str(path))
                # No custom backend: default parse backend (docling_parse_v4).
                backend_fallback = "docling_parse_v4"
                tables_fallback = self._extract_tables_from_result(
                    conv_res_b,
                    cell_matching_used=False,
                    backend_used=backend_fallback,
                )
                # Use fallback only if it produces more consistent results
                if len(tables_fallback) >= len(tables_primary):
                    tables_primary = tables_fallback
                    conv_for_meta = conv_res_b
                    backend_used_out = backend_fallback
                    logger.info(
                        "Docling: using fallback (no cell matching) result "
                        "— %d tables",
                        len(tables_primary),
                    )
            except Exception as exc:
                logger.warning(
                    "Docling fallback conversion failed: %s — keeping primary result",
                    exc,
                )

        # Total pages from ConversionResult (same PDF either way)
        try:
            total_pages = len(conv_for_meta.document.pages)
        except Exception:
            try:
                import fitz

                d = fitz.open(str(path))
                try:
                    total_pages = d.page_count
                finally:
                    d.close()
            except Exception:
                total_pages = 0

        logger.info(
            "Docling: %d tables extracted from %s (%d pages)",
            len(tables_primary),
            path.name,
            total_pages,
        )

        return {
            "tables": tables_primary,
            "total_pages": total_pages,
            "tool": "docling",
            "model": "TableFormerMode.ACCURATE",
            "backend_used": backend_used_out,
        }

    def _extract_tables_from_result(
        self,
        conv_res: Any,
        cell_matching_used: bool,
        backend_used: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract table data from a Docling ConversionResult using the
        official v2 API: conv_res.document.tables → export_to_dataframe().
        """
        import pandas as pd

        results: List[Dict[str, Any]] = []

        try:
            tables = conv_res.document.tables
        except AttributeError as exc:
            logger.error(
                "Docling: conv_res.document.tables not accessible — "
                "possible Docling version mismatch: %s",
                exc,
            )
            return results

        for table_idx, table in enumerate(tables):
            try:
                df: pd.DataFrame = table.export_to_dataframe()

                if df.empty:
                    logger.debug(
                        "Docling: table %d is empty — skipping", table_idx
                    )
                    continue

                # ── Build headers and rows ──
                # export_to_dataframe() puts column names as df.columns
                # and data rows in df.values.
                headers: List[str] = [
                    str(col).strip() if col is not None else ""
                    for col in df.columns.tolist()
                ]

                rows: List[List[str]] = [
                    [
                        str(cell).strip() if cell is not None else ""
                        for cell in row
                    ]
                    for row in df.values.tolist()
                ]

                # Skip completely empty tables
                if all(h == "" for h in headers) and all(
                    all(c == "" for c in row) for row in rows
                ):
                    continue

                # ── Extract page number ──
                # TableItem.prov contains provenance with page_no (1-based in Docling)
                page_number = 0
                try:
                    if table.prov:
                        page_number = int(table.prov[0].page_no) - 1
                except Exception:
                    pass

                results.append(
                    {
                        "headers": headers,
                        "rows": rows,
                        "page_number": page_number,
                        "table_index": table_idx,
                        "row_count": len(rows),
                        "col_count": len(headers),
                        "cell_matching_used": cell_matching_used,
                        "backend_used": backend_used,
                    }
                )

            except Exception as exc:
                logger.warning(
                    "Docling: failed to extract table %d: %s",
                    table_idx,
                    exc,
                )
                continue

        return results

    def _detect_column_merge_issue(
        self, tables: List[Dict[str, Any]]
    ) -> bool:
        """
        Detect if any table has inconsistent column counts across rows,
        which indicates the cell-matching mode merged columns incorrectly.
        """
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            if not headers or not rows:
                continue
            expected_cols = len(headers)
            for row in rows:
                if len(row) != expected_cols:
                    return True
        return False
