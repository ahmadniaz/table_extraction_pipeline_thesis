"""
Table extraction methods for Google Document AI.

Uses the Form Parser table API exclusively as primary source of truth.
header_rows / body_rows → extract_cell_text_with_confidence → document.text.
All domain-specific heuristics (pattern analysis, confidence filtering for
individual cells, company name enrichment) have been removed so that this
tool is comparable to Textract, Docling, and PyMuPDF on equal footing.
"""

import logging
from typing import Any, List, Dict, Tuple
from datetime import datetime
from .config import MIN_TABLE_WIDTH, MIN_TABLE_HEIGHT

logger = logging.getLogger(__name__)


class TableExtractor:
    """Handles table extraction from Google Document AI documents."""

    def __init__(self):
        pass
    
    def extract_tables_from_document(self, document: Any) -> List[Dict[str, Any]]:
        """
        Extract tables from processed Google Document AI document.
        
        Args:
            document: Processed Document AI document
            
        Returns:
            List of extracted tables
        """
        tables = []
        
        try:
            for page_num, page in enumerate(document.pages):
                page_tables = self.extract_tables_from_page(page, page_num, document)
                tables.extend(page_tables)
            return tables
        except Exception as exc:
            logger.error("DocAI: error extracting tables from document: %s", exc)
            return []
    
    def extract_tables_from_page(
        self, 
        page: Any, 
        page_num: int, 
        document: Any
    ) -> List[Dict[str, Any]]:
        """
        Extract tables from a single page.
        
        Args:
            page: Document AI page
            page_num: Page number
            document: Document AI document
            
        Returns:
            List of tables from this page
        """
        tables = []
        
        try:
            # Form Parser tables are the primary source of truth.
            form_parser_tables = self.extract_form_parser_tables(page, page_num, document)
            if form_parser_tables:
                tables.extend(form_parser_tables)
                return tables

            # True fallback: page.tables was empty — attempt spatial clustering
            # against raw page blocks (last resort only).
            try:
                table_blocks = [
                    b for b in page.blocks
                    if b.layout.text_anchor.text_segments
                ]
            except Exception:
                table_blocks = []

            for table_idx, table_block in enumerate(table_blocks):
                try:
                    table_data = self.extract_table_structure(table_block, page)
                    if table_data and table_data.get("rows"):
                        table_data.update({
                            "table_index": len(tables),
                            "page_number": page_num,   # 0-based
                            "extractor": "google_docai_spatial",
                            "docai_confidence": self.calculate_table_confidence(table_block),
                            "metadata": {
                                "page_number": page_num,
                                "table_index": table_idx,
                                "extraction_method": "google_docai_spatial",
                                "timestamp": datetime.now().isoformat(),
                            },
                        })
                        tables.append(table_data)
                except Exception as exc:
                    logger.debug(
                        "DocAI: spatial fallback table %d page %d: %s",
                        table_idx, page_num, exc,
                    )

            return tables

        except Exception as exc:
            logger.error("DocAI: error extracting tables from page %d: %s", page_num, exc)
            return []
    
    def extract_form_parser_tables(
        self,
        page: Any,
        page_num: int,
        document: Any,
    ) -> List[Dict[str, Any]]:
        """
        Extract tables from a page using the Document AI Form Parser table API.

        Form Parser output is treated as ground truth.  A spatial-clustering
        fallback is attempted ONLY when a specific table has no rows at all
        (Form Parser detected a table region but could not parse its cells).
        """
        tables: List[Dict[str, Any]] = []

        if not (hasattr(page, "tables") and page.tables):
            return tables

        for table_idx, table in enumerate(page.tables):
            try:
                table_data = self.convert_form_parser_table_to_standard_format(
                    table, page_num, table_idx, document
                )

                if table_data.get("rows"):
                    tables.append(table_data)
                else:
                    # Form Parser returned a table block but no parseable rows —
                    # attempt a raw-text spatial fallback for this region only.
                    logger.debug(
                        "DocAI: Form Parser table %d on page %d has no rows — "
                        "attempting spatial fallback",
                        table_idx, page_num,
                    )
                    fallback = self.extract_table_from_raw_text(
                        page, page_num, table_idx, document
                    )
                    if fallback and fallback.get("rows"):
                        tables.append(fallback)

            except Exception as exc:
                logger.warning(
                    "DocAI: error on Form Parser table %d page %d: %s",
                    table_idx, page_num, exc,
                )
                try:
                    fallback = self.extract_table_from_raw_text(
                        page, page_num, table_idx, document
                    )
                    if fallback and fallback.get("rows"):
                        tables.append(fallback)
                except Exception:
                    pass

        return tables

    def extract_text_from_text_anchor(self, text_anchor: Any, document: Any) -> str:
        """
        Extract text from a Document AI text anchor using the document's text.
        
        Args:
            text_anchor: Document AI text anchor object
            document: Document AI document object
            
        Returns:
            Extracted text string
        """
        try:
            if not text_anchor or not text_anchor.text_segments:
                return ""
            
            text_parts = []
            for segment in text_anchor.text_segments:
                if hasattr(segment, 'start_index') and hasattr(segment, 'end_index'):
                    start_idx = segment.start_index
                    end_idx = segment.end_index
                    if start_idx < len(document.text) and end_idx <= len(document.text):
                        text_parts.append(document.text[start_idx:end_idx])
            
            return " ".join(text_parts).strip()
        except Exception as exc:
            logger.debug("DocAI: error extracting text from text anchor: %s", exc)
            return ""

    def extract_table_from_raw_text(
        self, 
        page: Any, 
        page_num: int, 
        table_idx: int, 
        document: Any
    ) -> Dict[str, Any]:
        """
        Fallback method to extract table from raw text when Document AI table structure is incomplete.
        
        Args:
            page: Document AI page
            page_num: Page number
            table_idx: Table index
            document: Document AI document
            
        Returns:
            Table dictionary in standard format
        """
        try:
            # Get all text blocks from the page
            text_blocks = []
            if hasattr(page, 'blocks'):
                for block in page.blocks:
                    if hasattr(block, 'layout') and hasattr(block.layout, 'text_anchor'):
                        text = self.extract_text_from_text_anchor(block.layout.text_anchor, document)
                        if text.strip():
                            # Get bounding box for spatial analysis
                            bbox = None
                            if hasattr(block.layout, 'bounding_poly') and block.layout.bounding_poly.vertices:
                                vertices = block.layout.bounding_poly.vertices
                                if len(vertices) >= 4:
                                    bbox = {
                                        'x': vertices[0].x,
                                        'y': vertices[0].y,
                                        'width': vertices[2].x - vertices[0].x,
                                        'height': vertices[2].y - vertices[0].y
                                    }
                            
                            text_blocks.append({
                                'text': text.strip(),
                                'bbox': bbox,
                                'confidence': getattr(block.layout, 'confidence', 0.0)
                            })
            
            if not text_blocks:
                return {"headers": [], "rows": [], "docai_confidence": 0.0}

            # Sort text blocks by vertical position (top to bottom)
            text_blocks.sort(key=lambda x: x["bbox"]["y"] if x["bbox"] else 0)

            # Group text blocks into rows based on vertical proximity
            rows = []
            current_row: List[Dict] = []
            last_y = None

            for block in text_blocks:
                if block["bbox"]:
                    current_y = block["bbox"]["y"]
                    if last_y is None or abs(current_y - last_y) < 20:
                        current_row.append(block)
                    else:
                        if current_row:
                            rows.append(current_row)
                        current_row = [block]
                    last_y = current_y
                else:
                    current_row.append(block)

            if current_row:
                rows.append(current_row)

            # First row → headers; remainder → data
            headers: List[str] = []
            if rows:
                headers = [block["text"] for block in rows[0]]
                rows = rows[1:]

            data_rows: List[List[str]] = []
            for row_blocks in rows:
                row_data = [block["text"] for block in row_blocks]
                if any(cell.strip() for cell in row_data):
                    data_rows.append(row_data)

            # Normalise row lengths
            if headers:
                max_cols = len(headers)
                data_rows = [
                    row[:max_cols] + [""] * (max_cols - len(row))
                    for row in data_rows
                ]

            return {
                "headers": headers,
                "rows": data_rows,
                "docai_confidence": 0.5,   # lower confidence for spatial fallback
                "bbox": {},
                "page_number": page_num,   # 0-based
                "table_index": table_idx,
                "row_count": len(data_rows),
                "col_count": len(headers),
                "extractor": "google_docai_fallback",
                "metadata": {
                    "page_number": page_num,
                    "table_index": table_idx,
                    "extraction_method": "google_docai_fallback",
                    "timestamp": datetime.now().isoformat(),
                    "source_format": "raw_text_analysis",
                },
            }

        except Exception as exc:
            logger.warning("DocAI: fallback extraction failed on page %d: %s", page_num, exc)
            return {"headers": [], "rows": [], "docai_confidence": 0.0}
    
    def extract_cell_text_with_confidence(
        self, 
        cell: Any, 
        document: Any
    ) -> Tuple[str, float]:
        """
        Extract text from a Document AI cell object with confidence scoring.
        
        Args:
            cell: Document AI cell object
            document: Document AI document object
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            if not hasattr(cell, 'layout') or not cell.layout:
                return "", 0.0
            
            text_anchor = cell.layout.text_anchor
            if not text_anchor:
                return "", 0.0
            
            text = self.extract_text_from_text_anchor(text_anchor, document)
            confidence = getattr(cell.layout, 'confidence', 0.0)
            
            return text, confidence
            
        except Exception as exc:
            logger.debug("DocAI: error extracting cell text: %s", exc)
            return "", 0.0

    def extract_cell_text(self, cell: Any, document: Any) -> str:
        """
        Extract text from a Document AI table cell (legacy method).
        
        Args:
            cell: Document AI table cell object
            document: Document AI document object
            
        Returns:
            Extracted cell text
        """
        text, _ = self.extract_cell_text_with_confidence(cell, document)
        return text

    def extract_alternative_text(self, cell: Any, document: Any) -> str:
        """
        Extract alternative text for low-confidence cells using multiple strategies.
        
        Args:
            cell: Document AI cell object
            document: Document AI document object
            
        Returns:
            Alternative text string
        """
        try:
            # Strategy 1: Try to get text from bounding box
            if hasattr(cell, 'layout') and hasattr(cell.layout, 'bounding_poly'):
                bbox = cell.layout.bounding_poly
                # Extract text from the bounding box area
                return self.extract_text_from_bbox(bbox, document)
            
            # Strategy 2: Try to get text from text segments
            if hasattr(cell, 'layout') and hasattr(cell.layout, 'text_anchor'):
                text_anchor = cell.layout.text_anchor
                if text_anchor and hasattr(text_anchor, 'text_segments'):
                    # Try to extract from all text segments
                    text_parts = []
                    for segment in text_anchor.text_segments:
                        if hasattr(segment, 'start_index') and hasattr(segment, 'end_index'):
                            try:
                                text_part = document.text[segment.start_index:segment.end_index]
                                text_parts.append(text_part)
                            except (IndexError, AttributeError):
                                continue
                    if text_parts:
                        return " ".join(text_parts)
            
            return ""
            
        except Exception as e:
            print(f"Error extracting alternative text: {e}")
            return ""

    def extract_text_from_bbox(self, bbox: Any, document: Any) -> str:
        """
        Extract text from a bounding box area.
        
        Args:
            bbox: Bounding box object
            document: Document AI document object
            
        Returns:
            Extracted text string
        """
        try:
            # This is a simplified implementation
            # In a full implementation, you would extract text from the specific area
            return ""
        except Exception as e:
            print(f"Error extracting text from bbox: {e}")
            return ""

    def convert_form_parser_table_to_standard_format(
        self,
        table: Any,
        page_num: int,
        table_index: int,
        document: Any = None,
    ) -> Dict[str, Any]:
        """
        Convert a Document AI Form Parser table to the standard {headers, rows} format.

        Header strategy (per Google Form Parser samples):
          - If table.header_rows is non-empty: use the LAST header row as column names.
          - If table.header_rows is empty but body_rows exist: synthesise Column_1…N names.

        No confidence thresholds are applied to individual cells — cell text is used
        as-is. This keeps the tool output directly comparable to Textract and Docling.

        Args:
            table:       Document AI Form Parser table object (Page.Table).
            page_num:    0-based page index.
            table_index: Position of this table on the page.
            document:    Document AI document object (for text_anchor resolution).

        Returns:
            {
                "headers": list[str],
                "rows":    list[list[str]],
                "docai_confidence": float,
                "bbox":    dict,
                "page_number":  int,   # 0-based
                "table_index":  int,
                "row_count":    int,
                "col_count":    int,
                "extractor":    str,
                "metadata":     dict,
            }
        """
        try:
            # ── Extract header rows ──────────────────────────────────────────
            headers: List[str] = []
            if hasattr(table, "header_rows") and table.header_rows:
                header_rows_text: List[List[str]] = []
                for header_row in table.header_rows:
                    row_cells = []
                    for cell in header_row.cells:
                        text, _ = self.extract_cell_text_with_confidence(cell, document)
                        row_cells.append(text.strip())
                    if row_cells:
                        header_rows_text.append(row_cells)
                # Use the LAST header row as column names (Google samples pattern)
                if header_rows_text:
                    headers = header_rows_text[-1]

            # ── Extract body rows ────────────────────────────────────────────
            rows: List[List[str]] = []
            if hasattr(table, "body_rows") and table.body_rows:
                # Synthesise Column_N headers from first body row when no header_rows exist
                if not headers:
                    first_body = table.body_rows[0]
                    headers = [f"Column_{i + 1}" for i in range(len(first_body.cells))]

                for body_row in table.body_rows:
                    row_cells = []
                    for cell in body_row.cells:
                        text, _ = self.extract_cell_text_with_confidence(cell, document)
                        row_cells.append(text.strip())
                    if any(c for c in row_cells):
                        rows.append(row_cells)

            # ── Normalise row lengths to header count ────────────────────────
            if headers:
                max_cols = len(headers)
                rows = [
                    row[:max_cols] + [""] * (max_cols - len(row))
                    for row in rows
                ]

            logger.debug(
                "DocAI: page=%d table=%d headers=%d rows=%d",
                page_num, table_index, len(headers), len(rows),
            )

            # ── Confidence ───────────────────────────────────────────────────
            confidence = float(getattr(table, "confidence", 0.0))

            # ── Bounding box ─────────────────────────────────────────────────
            bbox: Dict[str, Any] = {}
            try:
                if hasattr(table, "layout") and table.layout.bounding_poly.vertices:
                    v = table.layout.bounding_poly.vertices
                    if len(v) >= 4:
                        bbox = {"x0": v[0].x, "y0": v[0].y, "x1": v[2].x, "y1": v[2].y}
            except Exception:
                pass

            return {
                "headers": headers,
                "rows": rows,
                "docai_confidence": confidence,
                "bbox": bbox,
                "page_number": page_num,   # 0-based
                "table_index": table_index,
                "row_count": len(rows),
                "col_count": len(headers),
                "extractor": "google_docai_form_parser",
                "metadata": {
                    "page_number": page_num,
                    "table_index": table_index,
                    "extraction_method": "google_docai_form_parser",
                    "timestamp": datetime.now().isoformat(),
                    "source_format": "form_parser_table",
                },
            }

        except Exception as exc:
            logger.warning(
                "DocAI: failed to convert Form Parser table %d on page %d: %s",
                table_index, page_num, exc,
            )
            return {
                "headers": [],
                "rows": [],
                "docai_confidence": 0.0,
                "bbox": {},
                "page_number": page_num,
                "table_index": table_index,
                "row_count": 0,
                "col_count": 0,
                "extractor": "google_docai_form_parser",
                "metadata": {
                    "page_number": page_num,
                    "table_index": table_index,
                    "extraction_method": "google_docai_form_parser",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(exc),
                },
            }

    def extract_table_structure(self, table_block: Any, page: Any) -> Dict[str, Any]:
        """
        Extract table structure from a table block.
        
        Args:
            table_block: Table block from Document AI
            page: Page containing the table
            
        Returns:
            Table structure dictionary
        """
        try:
            # Get table layout
            table_layout = table_block.layout
            
            # Extract text segments
            text_segments = []
            for segment in table_layout.text_anchor.text_segments:
                text_segments.append({
                    "text": segment.text,
                    "start_index": segment.start_index,
                    "end_index": segment.end_index
                })
            
            # Analyze table structure using whitespace and spatial clustering
            table_structure = self.analyze_table_structure(text_segments, table_layout, page)
            
            return table_structure
            
        except Exception as e:
            print(f"Error extracting table structure: {e}")
            return {}
    
    def analyze_table_structure(
        self, 
        text_segments: List[Dict], 
        layout: Any, 
        page: Any
    ) -> Dict[str, Any]:
        """
        Analyze table structure using whitespace analysis and spatial clustering.
        
        Args:
            text_segments: Text segments from the table
            layout: Table layout
            page: Page containing the table
            
        Returns:
            Analyzed table structure
        """
        try:
            # Get bounding box
            bbox = layout.bounding_poly.vertices
            
            # Extract all text elements within the table area
            table_texts = []
            for token in page.tokens:
                token_bbox = token.layout.bounding_poly.vertices
                if self.is_inside_bbox(token_bbox, bbox):
                    table_texts.append({
                        "text": token.layout.text_anchor.text_segments[0].text if token.layout.text_anchor.text_segments else "",
                        "bbox": token_bbox,
                        "confidence": token.layout.confidence
                    })
            
            # Cluster text elements into rows and columns
            rows, columns = self.cluster_table_elements(table_texts, bbox)
            
            # Build table structure
            headers = []
            table_rows = []
            
            # Extract headers (first row or column)
            if rows:
                headers = [cell.get("text", "") for cell in rows[0]]
            
            # Extract data rows
            for row in rows[1:] if len(rows) > 1 else []:
                table_rows.append([cell.get("text", "") for cell in row])
            
            return {
                "headers": headers,
                "rows": table_rows,
                "docai_confidence": float(getattr(layout, "confidence", 0.0)),
                "bbox": {
                    "x0": bbox[0].x,
                    "y0": bbox[0].y,
                    "x1": bbox[2].x,
                    "y1": bbox[2].y,
                },
            }

        except Exception as exc:
            logger.debug("DocAI: analyze_table_structure error: %s", exc)
            return {"headers": [], "rows": [], "docai_confidence": 0.0}
    
    def cluster_table_elements(
        self, 
        table_texts: List[Dict], 
        table_bbox: List
    ) -> Tuple[List[List[Dict]], List[List[Dict]]]:
        """
        Cluster table text elements into rows and columns using spatial analysis.
        
        Args:
            table_texts: List of text elements in the table
            table_bbox: Table bounding box
            
        Returns:
            Tuple of (rows, columns) where each is a list of lists of text elements
        """
        try:
            if not table_texts:
                return [], []
            
            # Sort by Y coordinate (rows)
            sorted_by_y = sorted(table_texts, key=lambda x: x["bbox"][0].y)
            
            # Group into rows based on Y proximity
            rows = []
            current_row = []
            row_threshold = 20  # pixels
            
            for i, text in enumerate(sorted_by_y):
                if not current_row:
                    current_row = [text]
                else:
                    # Check if this text is in the same row
                    avg_y = sum(t["bbox"][0].y for t in current_row) / len(current_row)
                    if abs(text["bbox"][0].y - avg_y) <= row_threshold:
                        current_row.append(text)
                    else:
                        # Sort current row by X coordinate
                        current_row.sort(key=lambda x: x["bbox"][0].x)
                        rows.append(current_row)
                        current_row = [text]
            
            # Add last row
            if current_row:
                current_row.sort(key=lambda x: x["bbox"][0].x)
                rows.append(current_row)
            
            # Create columns (transpose rows)
            columns = []
            if rows:
                max_cols = max(len(row) for row in rows)
                for col_idx in range(max_cols):
                    column = []
                    for row in rows:
                        if col_idx < len(row):
                            column.append(row[col_idx])
                    columns.append(column)
            
            return rows, columns
            
        except Exception as e:
            print(f"Error clustering table elements: {e}")
            return [], []
    
    def is_inside_bbox(self, inner_bbox: List, outer_bbox: List) -> bool:
        """Check if inner bounding box is inside outer bounding box."""
        try:
            inner_center_x = (inner_bbox[0].x + inner_bbox[2].x) / 2
            inner_center_y = (inner_bbox[0].y + inner_bbox[2].y) / 2
            
            return (
                outer_bbox[0].x <= inner_center_x <= outer_bbox[2].x and
                outer_bbox[0].y <= inner_center_y <= outer_bbox[2].y
            )
        except:
            return False
    
    def calculate_table_confidence(self, table_block: Any) -> float:
        """Calculate confidence score for table extraction."""
        try:
            # Use layout confidence as base
            base_confidence = table_block.layout.confidence
            
            # Additional confidence factors
            confidence_factors = []
            
            # Check for table-like structure indicators
            if hasattr(table_block.layout, 'text_anchor') and table_block.layout.text_anchor.text_segments:
                confidence_factors.append(0.1)  # Has text content
            
            # Check bounding box quality
            if hasattr(table_block.layout, 'bounding_poly') and table_block.layout.bounding_poly.vertices:
                bbox = table_block.layout.bounding_poly.vertices
                if len(bbox) >= 4:
                    # Check if bounding box is reasonable size
                    width = bbox[2].x - bbox[0].x
                    height = bbox[2].y - bbox[0].y
                    if width > MIN_TABLE_WIDTH and height > MIN_TABLE_HEIGHT:
                        confidence_factors.append(0.1)
            
            # Calculate final confidence
            final_confidence = base_confidence + sum(confidence_factors)
            return min(final_confidence, 1.0)
            
        except Exception as e:
            print(f"Error calculating confidence: {e}")
            return 0.5
