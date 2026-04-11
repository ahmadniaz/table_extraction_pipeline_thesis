"""
Main Google Document AI extractor for PDF documents.

Uses the Form Parser processor (FORM_PARSER_PROCESSOR) and its native
table API (page.tables → header_rows / body_rows) as the primary source
of truth.  Domain-specific post-processing (company name detection,
multi-page table stitching) is disabled so that this tool is
scientifically comparable to Textract, Docling, and PyMuPDF.
"""

import logging
import os
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Google Document AI imports
try:
    from google.cloud import documentai_v1 as documentai
    from google.auth import default
    GOOGLE_DOCAI_AVAILABLE = True
except ImportError:
    GOOGLE_DOCAI_AVAILABLE = False
    logger.warning(
        "Google Document AI SDK not available. "
        "Install with: pip install google-cloud-documentai google-auth"
    )

# Local imports
from .config import (
    DEFAULT_PROJECT_ID,
    DEFAULT_PROCESSOR_ID,
    DEFAULT_LOCATION,
    CREDENTIALS_PATHS,
    REGULAR_MODE_MAX_PAGES,
    IMAGELESS_MODE_MAX_PAGES,
)
from .processing import DocumentProcessor
from .table_extraction import TableExtractor
from .post_processing import TextCleaner

# Set False to keep results comparable across tools for the thesis.
ENABLE_MULTIPAGE_STITCHING = False


class GoogleDocAIExtractor:
    """
    Google Document AI extractor for PDF documents.
    
    Features:
    - Direct PDF processing without image conversion
    - Form Parser with table detection and form field extraction
    - Table detection and extraction from forms and documents
    - Whitespace analysis and spatial clustering (fallback)
    - Multiple output formats (JSON, HTML, CSV)
    - Confidence scoring and annotation
    - Automatic format detection and adaptation
    - JSON response logging for debugging
    """
    
    def __init__(self):
        self.name = "google_docai"
        self.description = "Google Document AI Form Parser with native table API"
        self.client = None
        self.project_id = None
        self.location = DEFAULT_LOCATION
        self.processor_id = None
        self.table_extractor = TableExtractor()
        self.text_cleaner = TextCleaner()
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Document AI client."""
        if not GOOGLE_DOCAI_AVAILABLE:
            logger.warning("Google Document AI SDK not available")
            return

        try:
            # Locate credentials file if GOOGLE_APPLICATION_CREDENTIALS is not set
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                possible_paths = CREDENTIALS_PATHS + [
                    os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "pdf-tables-extractor-465009-d9172fd0045d.json",
                    ),
                    os.path.join(os.getcwd(), "pdf-tables-extractor-465009-d9172fd0045d.json"),
                ]
                creds_file = next((p for p in possible_paths if os.path.exists(p)), None)
                if creds_file:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_file
                    logger.info("DocAI: using credentials file %s", creds_file)
                else:
                    logger.error("DocAI: credentials file not found (tried %s)", possible_paths)
                    return

            # Propagate defaults for project / processor IDs
            if not os.getenv("GOOGLE_CLOUD_PROJECT_ID"):
                os.environ["GOOGLE_CLOUD_PROJECT_ID"] = DEFAULT_PROJECT_ID
            if not os.getenv("GOOGLE_DOCAI_PROCESSOR_ID"):
                os.environ["GOOGLE_DOCAI_PROCESSOR_ID"] = DEFAULT_PROCESSOR_ID

            credentials, self.project_id = default()
            if not self.project_id:
                self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
            if not self.project_id:
                logger.error("DocAI: GOOGLE_CLOUD_PROJECT_ID is not set")
                return

            # Use regional endpoint (matches Google samples)
            api_endpoint = f"{self.location}-documentai.googleapis.com"
            self.client = documentai.DocumentProcessorServiceClient(
                credentials=credentials,
                client_options={"api_endpoint": api_endpoint},
            )

            self.processor_id = os.getenv("GOOGLE_DOCAI_PROCESSOR_ID", DEFAULT_PROCESSOR_ID)
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            self.document_processor = DocumentProcessor(self.client, self.processor_name)

            logger.info(
                "DocAI: initialised — project=%s processor=%s endpoint=%s",
                self.project_id, self.processor_id, api_endpoint,
            )

        except Exception as exc:
            logger.error("DocAI: failed to initialise client: %s", exc)
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Google Document AI is available and properly configured."""
        return (
            GOOGLE_DOCAI_AVAILABLE and 
            self.client is not None and 
            self.project_id is not None
        )
    
    def extract_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract tables from PDF using Google Document AI with smart page handling.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of extracted tables with metadata
        """
        if not self.is_available():
            raise RuntimeError("Google Document AI not available or not properly configured")

        try:
            with open(pdf_path, "rb") as fh:
                pdf_content = fh.read()

            page_count = self.document_processor.get_pdf_page_count(pdf_content)
            logger.info("DocAI: processing %s (%d pages)", pdf_path, page_count)

            tables: List[Dict[str, Any]] = []
            processing_mode = "unknown"

            if page_count <= REGULAR_MODE_MAX_PAGES:
                processing_mode = "regular"
                document = self.document_processor.process_document_regular_mode(pdf_content)
                tables = self.table_extractor.extract_tables_from_document(document)

            elif page_count <= IMAGELESS_MODE_MAX_PAGES:
                processing_mode = "imageless"
                try:
                    document = self.document_processor.process_document_imageless_mode(pdf_content)
                    tables = self.table_extractor.extract_tables_from_document(document)
                except Exception as exc:
                    if "PAGE_LIMIT_EXCEEDED" in str(exc) or "page limit" in str(exc).lower():
                        processing_mode = "chunked"
                        logger.info("DocAI: imageless mode page limit hit — falling back to chunked")
                        tables = self.document_processor.process_document_in_chunks(
                            pdf_content,
                            page_count,
                            self.table_extractor.extract_tables_from_document,
                        )
                    else:
                        raise

            else:
                processing_mode = "chunked"
                tables = self.document_processor.process_document_in_chunks(
                    pdf_content,
                    page_count,
                    self.table_extractor.extract_tables_from_document,
                )

            logger.info(
                "DocAI: mode=%s pages=%d tables=%d",
                processing_mode, page_count, len(tables),
            )

            # Multi-page stitching is DISABLED for thesis fairness.
            # Other tools (Textract, Docling, PyMuPDF) do not stitch tables across
            # pages, so enabling it here would give Google DocAI an unfair advantage.
            # To re-enable, set ENABLE_MULTIPAGE_STITCHING = True above.
            if ENABLE_MULTIPAGE_STITCHING and len(tables) > 1:
                try:
                    from app.services.extraction.extraction_utils import stitch_multipage_tables
                    tables = stitch_multipage_tables(tables)
                    logger.info("DocAI: after stitching: %d tables", len(tables))
                except Exception as exc:
                    logger.warning("DocAI: table stitching failed: %s — using unstitched tables", exc)

            return self._post_process_tables(tables)

        except Exception as exc:
            logger.error("DocAI: extraction failed for %s: %s", pdf_path, exc)
            raise

    async def extract_tables_async(self, pdf_path: str) -> Dict[str, Any]:
        """
        Async wrapper for extract_tables method.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extraction results
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.extract_tables, pdf_path)

        if isinstance(result, list):
            return {
                "success": True,
                "tables": result,
                "extraction_metadata": {
                    "method": "google_docai",
                    "timestamp": datetime.now().isoformat(),
                },
            }
        return result

    def _post_process_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Lightweight post-processing: trim whitespace and remove fully empty rows/columns.

        Deliberately minimal — no domain enrichment, no company name detection,
        no semantic header regeneration.  Keys are normalised to "headers" (not
        "header") to match Textract and Docling service outputs.
        """
        processed: List[Dict[str, Any]] = []

        for table in tables:
            try:
                # Support both legacy "header" key and new "headers" key
                raw_headers: List[str] = table.get("headers") or table.get("header") or []
                raw_rows: List[List[str]] = table.get("rows") or []

                # Trim whitespace
                cleaned_headers = [self.text_cleaner.clean_text(h) for h in raw_headers]
                cleaned_rows = [
                    [self.text_cleaner.clean_text(cell) for cell in row]
                    for row in raw_rows
                ]

                # Remove fully empty rows
                cleaned_rows = [r for r in cleaned_rows if any(c.strip() for c in r)]

                # Remove trailing all-empty columns
                try:
                    cleaned_headers, cleaned_rows = self.text_cleaner.remove_empty_cells(
                        cleaned_headers, cleaned_rows
                    )
                except Exception:
                    pass

                out: Dict[str, Any] = {
                    "headers": cleaned_headers,
                    "rows": cleaned_rows,
                    "docai_confidence": table.get("docai_confidence", table.get("confidence", 0.0)),
                    "bbox": table.get("bbox", {}),
                    "page_number": table.get("page_number", 0),
                    "table_index": table.get("table_index", 0),
                    "row_count": len(cleaned_rows),
                    "col_count": len(cleaned_headers),
                    "extractor": table.get("extractor", self.name),
                    "metadata": table.get("metadata", {}),
                }
                processed.append(out)

            except Exception as exc:
                logger.warning("DocAI: post-processing error: %s — keeping raw table", exc)
                processed.append(table)

        return processed
    
    def get_extraction_info(self) -> Dict[str, Any]:
        """Get information about this extractor."""
        return {
            "name": self.name,
            "description": self.description,
            "available": self.is_available(),
            "features": [
                "OCR with 600 DPI resolution",
                "Auto-rotate and deskew",
                "Form Parser with table detection",
                "Table extraction from forms and documents",
                "Whitespace analysis and spatial clustering (fallback)",
                "Contrast enhancement and denoising",
                "Multiple output formats",
                "Confidence scoring",
                "Automatic format detection and adaptation",
                "JSON response logging for debugging"
            ],
            "configuration": {
                "project_id": self.project_id,
                "location": self.location,
                "processor_id": self.processor_id
            }
        }

