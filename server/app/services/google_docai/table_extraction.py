"""
Table extraction methods for Google Document AI.
"""

from typing import Any, List, Dict, Tuple
from datetime import datetime
from .config import (
    HEADER_CONFIDENCE_THRESHOLD,
    CELL_CONFIDENCE_THRESHOLD,
    MIN_TABLE_WIDTH,
    MIN_TABLE_HEIGHT
)
from .post_processing import PatternAnalyzer


class TableExtractor:
    """Handles table extraction from Google Document AI documents."""
    
    def __init__(self):
        self.pattern_analyzer = PatternAnalyzer()
    
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
            # Extract tables from each page
            for page_num, page in enumerate(document.pages):
                page_tables = self.extract_tables_from_page(page, page_num, document)
                tables.extend(page_tables)
            
            return tables
            
        except Exception as e:
            print(f"Error extracting tables from document: {e}")
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
            # First, try to detect and process Form Parser format (tables structure)
            form_parser_tables = self.extract_form_parser_tables(page, page_num, document)
            if form_parser_tables:
                tables.extend(form_parser_tables)
                return tables
            
            # Fall back to traditional spatial clustering approach
            table_blocks = [block for block in page.blocks if block.layout.text_anchor.text_segments]
            
            for table_idx, table_block in enumerate(table_blocks):
                try:
                    # Extract table structure
                    table_data = self.extract_table_structure(table_block, page)
                    
                    if table_data and table_data.get("rows"):
                        # Add metadata
                        table_data.update({
                            "table_index": len(tables),
                            "page_number": page_num + 1,
                            "extractor": "google_docai",
                            "confidence": self.calculate_table_confidence(table_block),
                            "metadata": {
                                "page_number": page_num + 1,
                                "table_index": table_idx,
                                "extraction_method": "google_docai",
                                "timestamp": datetime.now().isoformat()
                            }
                        })
                        
                        tables.append(table_data)
                
                except Exception as e:
                    print(f"Error extracting table {table_idx} from page {page_num}: {e}")
                    continue
            
            return tables
            
        except Exception as e:
            print(f"Error extracting tables from page {page_num}: {e}")
            return []
    
    def extract_form_parser_tables(
        self, 
        page: Any, 
        page_num: int, 
        document: Any
    ) -> List[Dict[str, Any]]:
        """
        Extract tables using Document AI Form Parser format (tables structure).
        
        Args:
            page: Document AI page
            page_num: Page number
            document: Document AI document
            
        Returns:
            List of extracted tables in standard format
        """
        tables = []
        
        try:
            # Check if page has tables (Form Parser format)
            if hasattr(page, 'tables') and page.tables:
                for table_idx, table in enumerate(page.tables):
                    try:
                        # Convert Form Parser table to standard format
                        table_data = self.convert_form_parser_table_to_standard_format(
                            table, page_num, table_idx, document
                        )
                        
                        if table_data and table_data.get("rows"):
                            tables.append(table_data)
                            print(f"✅ Successfully converted Form Parser table: {len(table_data.get('headers', []))} headers, {len(table_data.get('rows', []))} rows")
                        else:
                            # Fallback: Try to extract table from raw text using spatial analysis
                            print(f"⚠️ Form Parser table {table_idx} has no rows, trying fallback extraction...")
                            fallback_table = self.extract_table_from_raw_text(page, page_num, table_idx, document)
                            if fallback_table and fallback_table.get("rows"):
                                tables.append(fallback_table)
                                print(f"✅ Fallback extraction successful: {len(fallback_table.get('headers', []))} headers, {len(fallback_table.get('rows', []))} rows")
                    
                    except Exception as e:
                        print(f"Error extracting Form Parser table {table_idx} from page {page_num}: {e}")
                        # Try fallback extraction
                        try:
                            fallback_table = self.extract_table_from_raw_text(page, page_num, table_idx, document)
                            if fallback_table and fallback_table.get("rows"):
                                tables.append(fallback_table)
                                print(f"✅ Fallback extraction successful after error: {len(fallback_table.get('headers', []))} headers, {len(fallback_table.get('rows', []))} rows")
                        except Exception as fallback_error:
                            print(f"Fallback extraction also failed: {fallback_error}")
                        continue
            
            return tables
            
        except Exception as e:
            print(f"Error extracting Form Parser tables from page {page_num}: {e}")
            return []

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
        except Exception as e:
            print(f"Error extracting text from text anchor: {e}")
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
                return {"header": [], "rows": [], "confidence": 0.0}
            
            # Sort text blocks by vertical position (top to bottom)
            text_blocks.sort(key=lambda x: x['bbox']['y'] if x['bbox'] else 0)
            
            # Group text blocks into rows based on vertical proximity
            rows = []
            current_row = []
            last_y = None
            
            for block in text_blocks:
                if block['bbox']:
                    current_y = block['bbox']['y']
                    if last_y is None or abs(current_y - last_y) < 20:  # 20px tolerance
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
            
            # Extract headers from first row
            headers = []
            if rows:
                header_blocks = rows[0]
                headers = [block['text'] for block in header_blocks]
                rows = rows[1:]  # Remove header row from data rows
            
            # Extract data rows
            data_rows = []
            for row_blocks in rows:
                row_data = [block['text'] for block in row_blocks]
                if any(cell.strip() for cell in row_data):  # Only add non-empty rows
                    data_rows.append(row_data)
            
            # Normalize row lengths
            if headers:
                max_cols = len(headers)
                normalized_rows = []
                for row in data_rows:
                    normalized_row = row[:max_cols] + [""] * (max_cols - len(row))
                    normalized_rows.append(normalized_row)
                data_rows = normalized_rows
            
            return {
                "header": headers,
                "rows": data_rows,
                "confidence": 0.5,  # Lower confidence for fallback method
                "bbox": {},
                "page_number": page_num + 1,
                "table_index": table_idx,
                "extractor": "google_docai_fallback",
                "metadata": {
                    "page_number": page_num + 1,
                    "table_index": table_idx,
                    "extraction_method": "google_docai_fallback",
                    "timestamp": datetime.now().isoformat(),
                    "source_format": "raw_text_analysis"
                }
            }
            
        except Exception as e:
            print(f"Error in fallback table extraction: {e}")
            return {"header": [], "rows": [], "confidence": 0.0}
    
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
            
        except Exception as e:
            print(f"Error extracting cell text with confidence: {e}")
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
        document: Any = None
    ) -> Dict[str, Any]:
        """
        Convert a Document AI Form Parser table to standard format with enhanced header detection.
        
        Args:
            table: Document AI Form Parser table object
            page_num: Page number where the table was found
            table_index: Index of the table on the page
            document: Document AI document object
            
        Returns:
            Standard table dictionary with headers, rows, and metadata
        """
        try:
            headers = []
            rows = []
            header_confidence_scores = []
            
            # Enhanced header extraction with confidence scoring
            if hasattr(table, 'header_rows') and table.header_rows:
                for header_row in table.header_rows:
                    row_cells = []
                    row_confidence = []
                    for cell in header_row.cells:
                        cell_text, confidence = self.extract_cell_text_with_confidence(cell, document)
                        row_cells.append(cell_text)
                        row_confidence.append(confidence)
                    if row_cells:
                        headers.extend(row_cells)
                        header_confidence_scores.extend(row_confidence)
                        print(f"🔍 Header row extracted: {row_cells} with confidence: {row_confidence}")
            
            # Extract body rows with confidence tracking
            if hasattr(table, 'body_rows') and table.body_rows:
                for body_row in table.body_rows:
                    row_cells = []
                    for cell in body_row.cells:
                        cell_text, confidence = self.extract_cell_text_with_confidence(cell, document)
                        # Only include cells with sufficient confidence
                        if confidence >= CELL_CONFIDENCE_THRESHOLD:
                            row_cells.append(cell_text)
                        else:
                            # Try alternative text extraction for low-confidence cells
                            alt_text = self.extract_alternative_text(cell, document)
                            row_cells.append(alt_text if alt_text else cell_text)
                    if row_cells:
                        rows.append(row_cells)
            
            # Enhanced header detection with fallback mechanisms
            if not headers and rows:
                print("⚠️ No headers detected, using first row as headers")
                headers = rows[0]
                rows = rows[1:]
                header_confidence_scores = [0.5] * len(headers)  # Default confidence for inferred headers
            
            # Filter low-confidence headers and generate alternatives
            if headers and header_confidence_scores:
                print(f"🔍 Processing {len(headers)} headers with confidence scores: {header_confidence_scores}")
                filtered_headers = []
                for i, (header, confidence) in enumerate(zip(headers, header_confidence_scores)):
                    if confidence >= HEADER_CONFIDENCE_THRESHOLD:
                        filtered_headers.append(header)
                        print(f"✅ Header '{header}' (confidence: {confidence:.2f}) accepted")
                    else:
                        # Generate alternative header for low-confidence cells
                        alt_header = self.pattern_analyzer.generate_header_from_data(rows, i) if rows else f"Column_{i+1}"
                        filtered_headers.append(header)  # Keep original header even if low confidence
                        print(f"🔄 Low confidence header '{header}' (confidence: {confidence:.2f}) kept as is")
                headers = filtered_headers
                print(f"📋 Final headers: {headers}")
            else:
                print(f"⚠️ No headers or confidence scores: headers={len(headers) if headers else 0}, confidence_scores={len(header_confidence_scores) if header_confidence_scores else 0}")
            
            # Ensure all rows have the same number of columns as headers
            if headers:
                max_cols = len(headers)
                normalized_rows = []
                for row in rows:
                    # Pad with empty strings if row has fewer columns
                    normalized_row = row[:max_cols] + [""] * (max_cols - len(row))
                    normalized_rows.append(normalized_row)
                rows = normalized_rows
            
            # Generate default headers if none were detected
            if not headers and rows:
                max_cols = max(len(row) for row in rows) if rows else 0
                headers = [f"Column_{i+1}" for i in range(max_cols)]
                print(f"📋 Generated default headers: {headers}")
            
            # Extract metadata
            confidence = getattr(table, 'confidence', 0.0)
            bbox = {}
            if hasattr(table, 'layout') and hasattr(table.layout, 'bounding_poly'):
                vertices = table.layout.bounding_poly.vertices
                if len(vertices) >= 4:
                    bbox = {
                        "x0": vertices[0].x,
                        "y0": vertices[0].y,
                        "x1": vertices[2].x,
                        "y1": vertices[2].y
                    }
            
            # Create standard table format
            print(f"📊 Creating table with {len(headers)} headers and {len(rows)} rows")
            print(f"📋 Headers: {headers}")
            table_dict = {
                "header": headers,
                "rows": rows,
                "confidence": confidence,
                "bbox": bbox,
                "page_number": page_num + 1,
                "table_index": table_index,
                "extractor": "google_docai_form_parser",
                "metadata": {
                    "page_number": page_num + 1,
                    "table_index": table_index,
                    "extraction_method": "google_docai_form_parser",
                    "timestamp": datetime.now().isoformat(),
                    "source_format": "form_parser_table"
                }
            }
            print(f"✅ Table created with header field: {table_dict.get('header', [])}")
            
            return table_dict
            
        except Exception as e:
            print(f"Error converting Form Parser table to standard format: {e}")
            return {
                "header": [],
                "rows": [],
                "confidence": 0.0,
                "bbox": {},
                "page_number": page_num + 1,
                "table_index": table_index,
                "extractor": "google_docai_form_parser",
                "metadata": {
                    "page_number": page_num + 1,
                    "table_index": table_index,
                    "extraction_method": "google_docai_form_parser",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
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
                "header": headers,
                "rows": table_rows,
                "confidence": layout.confidence,
                "bbox": {
                    "x0": bbox[0].x,
                    "y0": bbox[0].y,
                    "x1": bbox[2].x,
                    "y1": bbox[2].y
                }
            }
            
        except Exception as e:
            print(f"Error analyzing table structure: {e}")
            return {"header": [], "rows": [], "confidence": 0.0}
    
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
