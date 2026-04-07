"""Table extraction for document processing."""

import time
import re
from typing import Dict, Any, List, Optional, Tuple
from itertools import zip_longest

from .table_validator import TableValidator


class TableExtractor:
    """Extract and process tables from documents."""
    
    def __init__(self, logger):
        """Initialize table extractor."""
        self.logger = logger
        self.validator = TableValidator(logger)
    
    def extract_tables_from_document(self, document) -> List[Any]:
        """
        Extract table objects from Docling v2 document.
        
        Args:
            document: Docling v2 assembled document object
            
        Returns:
            List of table objects
        """
        tables = []
        
        try:
            # In Docling v2, tables are in the elements list
            if hasattr(document, 'elements'):
                for element in document.elements:
                    # Check if element is a table by class name
                    if hasattr(element, '__class__') and 'Table' in element.__class__.__name__:
                        if self.validator.is_valid_table_element(element):
                            tables.append(element)
                            self.logger.logger.info(f"Found valid table element: {element.__class__.__name__}")
                        else:
                            self.logger.logger.debug(f"Skipping invalid table element: {element.__class__.__name__}")
                
                self.logger.logger.info(f"Found {len(tables)} valid tables via document.elements")
            
            self.logger.logger.info(f"Total found {len(tables)} tables in document")
            
        except Exception as e:
            self.logger.logger.error(f"Error extracting tables from document: {e}")
        
        return tables
    
    def _debug_docling_table_structure(self, table, table_index: int):
        """CRITICAL: See what Docling actually extracts."""
        self.logger.logger.info(f"🔍 DEBUGGING Table {table_index}:")
        
        # Debug available attributes
        table_attrs = [attr for attr in dir(table) if not attr.startswith('_')]
        self.logger.logger.info(f"  Available attributes: {table_attrs}")
        
        # Debug table_cells
        if hasattr(table, 'table_cells') and table.table_cells:
            self.logger.logger.info(f"  table_cells count: {len(table.table_cells)}")
            for i, cell in enumerate(table.table_cells[:10]):
                self.logger.logger.info(f"    Cell {i}: '{cell.text}' at row {cell.start_row_offset_idx}")
        else:
            self.logger.logger.warning(f"  No table_cells attribute found")
        
        # **NEW: Debug other table attributes**
        for attr in ['text', 'content', 'data', 'rows', 'columns', 'cells']:
            if hasattr(table, attr):
                attr_value = getattr(table, attr)
                if attr_value:
                    if attr == 'text':
                        self.logger.logger.info(f"  {attr}: {len(str(attr_value))} chars - {str(attr_value)[:100]}...")
                    else:
                        self.logger.logger.info(f"  {attr}: {type(attr_value)} with {len(attr_value) if hasattr(attr_value, '__len__') else 'unknown'} items")
                else:
                    self.logger.logger.info(f"  {attr}: empty")
        
        # Debug dataframe export
        if hasattr(table, 'export_to_dataframe'):
            try:
                df = table.export_to_dataframe()
                if df is not None and not df.empty:
                    self.logger.logger.info(f"  DataFrame: {df.shape} - {df.columns.tolist()}")
                else:
                    self.logger.logger.warning(f"  DataFrame: empty or None")
            except Exception as e:
                self.logger.logger.error(f"  DataFrame failed: {e}")

    def extract_table_data(self, table, table_index: int, pdf_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract data from a single Docling table with robust structure handling.
        
        Args:
            table: Docling table object
            table_index: Index of the table
            pdf_path: Original PDF path for metadata
            
        Returns:
            Normalized table dictionary with consistent structure
        """
        try:
            # === ADD THIS FIRST ===
            self._debug_docling_table_structure(table, table_index)
            
            # Try multiple extraction methods
            extraction_results = []
            
            # Method 1: table_cells (your current approach)
            headers_1, rows_1 = self._extract_via_table_cells(table)
            if headers_1 and len(headers_1) > 0:
                extraction_results.append(("table_cells", headers_1, rows_1))
            
            # Method 2: dataframe export  
            headers_2, rows_2 = self._extract_via_dataframe(table)
            if headers_2 and len(headers_2) > 0:
                extraction_results.append(("dataframe", headers_2, rows_2))
            
            # Method 3: direct attributes
            headers_3, rows_3 = self._extract_via_attributes(table) 
            if headers_3 and len(headers_3) > 0:
                extraction_results.append(("attributes", headers_3, rows_3))
            
            # Use best result
            if extraction_results:
                method, headers, rows = max(extraction_results, 
                    key=lambda x: len(x[1]) + len(x[2]))
                self.logger.logger.info(f"✅ Using {method}: {len(headers)} headers, {len(rows)} rows")
                
                # **ENHANCED: Check if we got empty or generic content**
                has_real_content = any(
                    header and header.strip() and not header.startswith('Column_') 
                    for header in headers
                ) or any(
                    any(cell and cell.strip() and not cell.startswith('Data_') 
                        for cell in row) 
                    for row in rows
                )
                
                if not has_real_content:
                    self.logger.logger.warning("🔄 Got empty/generic content, trying complex extraction immediately...")
                    complex_headers, complex_rows = self._extract_complex_table_structure(table)
                    if complex_headers and len(complex_headers) > 1:  # Better than generic
                        headers, rows = complex_headers, complex_rows
                        self.logger.logger.info(f"✅ Complex extraction improved result: {len(headers)} headers, {len(rows)} rows")
                    
                    # **NEW: If still no real content, try Docling dataframe export as last resort**
                    if not any(header and header.strip() and not header.startswith('Column_') for header in headers):
                        self.logger.logger.warning("🔄 Still no real content, trying Docling dataframe export...")
                        try:
                            if hasattr(table, 'export_to_dataframe'):
                                df = table.export_to_dataframe()
                                if df is not None and not df.empty:
                                    headers = [str(col).strip() for col in df.columns]
                                    rows = []
                                    for _, row in df.iterrows():
                                        row_data = [str(cell).strip() if cell else "" for cell in row]
                                        rows.append(row_data)
                                    self.logger.logger.info(f"✅ DataFrame export succeeded: {len(headers)} headers, {len(rows)} rows")
                                    self.logger.logger.info(f"🔍 Sample headers: {headers[:5]}")
                                    if rows:
                                        self.logger.logger.info(f"🔍 Sample row: {rows[0][:5]}")
                        except Exception as e:
                            self.logger.logger.error(f"DataFrame export failed: {e}")
                            
                        # **FINAL FALLBACK: Try to extract from table text content**
                        if not any(header and header.strip() and not header.startswith('Column_') for header in headers):
                            self.logger.logger.warning("🔄 Final fallback: trying to extract from table text content...")
                            try:
                                if hasattr(table, 'text') and table.text:
                                    # Try to parse the raw text as a table
                                    text_headers, text_rows = self._parse_table_from_text(table.text)
                                    if text_headers and len(text_headers) > 1:
                                        headers, rows = text_headers, text_rows
                                        self.logger.logger.info(f"✅ Text parsing succeeded: {len(headers)} headers, {len(rows)} rows")
                                        self.logger.logger.info(f"🔍 Sample headers: {headers[:5]}")
                                        if rows:
                                            self.logger.logger.info(f"🔍 Sample row: {rows[0][:5]}")
                            except Exception as e:
                                self.logger.logger.error(f"Text parsing failed: {e}")
                        
                        # **CRITICAL FIX: If we still have empty rows, try to extract from document context**
                        if headers and not any(any(cell.strip() for cell in row) for row in rows):
                            self.logger.logger.warning("🚨 CRITICAL: All rows are empty! Trying document context extraction...")
                            try:
                                # Try to extract from the document's raw text using table structure
                                context_headers, context_rows = self._extract_from_document_context(table, headers)
                                if context_rows and any(any(cell.strip() for cell in row) for row in context_rows):
                                    rows = context_rows
                                    self.logger.logger.info(f"✅ Successfully extracted from document context: {len(rows)} rows with data")
                            except Exception as e:
                                self.logger.logger.error(f"Document context extraction failed: {e}")
            else:
                # Try complex table structure extraction as fallback
                self.logger.logger.info("🔄 Trying complex table structure extraction as fallback...")
                headers, rows = self._extract_complex_table_structure(table)
                if headers and rows:
                    self.logger.logger.info(f"✅ Complex extraction succeeded: {len(headers)} headers, {len(rows)} rows")
                else:
                    self.logger.logger.error("❌ ALL extraction methods failed!")
                    # Debug: log what we got from each method
                    self.logger.logger.error(f"🔍 DEBUG: table_cells result: {self._extract_via_table_cells(table)}")
                    self.logger.logger.error(f"🔍 DEBUG: dataframe result: {self._extract_via_dataframe(table)}")
                    self.logger.logger.error(f"🔍 DEBUG: attributes result: {self._extract_via_attributes(table)}")
                    return None
            
            # **NEW: Validate table quality and skip if it's likely metadata/header content**
            if not self.validator.is_valid_financial_table_lenient(headers, rows):
                self.logger.logger.warning(f"Table {table_index} appears to be metadata/header content, skipping")
                return None
            
            # Extract footers if available
            footers = self._extract_footers(table)
            
            # **CRITICAL: Handle row expansion for split headers**
            if len(headers) > 9:  # We expect more than the original 9 due to header splitting
                rows = self._expand_rows_for_split_headers(rows, headers)
            
            # Ensure all rows have the same length as headers
            rows = self._normalize_row_lengths(rows, len(headers))
            
            # Get table metadata
            metadata = self._extract_table_metadata(table, table_index, pdf_path)
            
            # Create cells structure for validation compatibility
            cells = self._create_cells_from_headers_and_rows(headers, rows)
            
            # Create columns structure
            columns = [{"name": header, "index": i} for i, header in enumerate(headers)]
            
            # Create consistent table structure
            table_data = {
                "headers": headers,
                "rows": rows,
                "cells": cells,  # Required by validation
                "columns": columns,  # Required by validation
                "footers": footers,
                "metadata": metadata,
                "row_count": len(rows),
                "column_count": len(headers),
                "table_index": table_index,
                "extractor": "TableExtractor"
            }
            
            return table_data
            
        except Exception as e:
            self.logger.logger.error(f"Error extracting table data: {e}")
            # Return minimal valid structure on error
            return {
                "headers": ["Column_1"],
                "rows": [],
                "footers": [],
                "metadata": {
                    "error": str(e),
                    "status": "error",
                    "table_index": table_index,
                    "extractor": "TableExtractor"
                },
                "row_count": 0,
                "column_count": 1,
                "table_index": table_index,
                "extractor": "TableExtractor"
            }
    
    def _extract_headers(self, table) -> List[str]:
        """Extract headers with robust multi-row header handling and complex document support."""
        try:
            headers = []
            
            # For Docling v2 table elements, extract from table_cells structure
            if hasattr(table, 'table_cells') and table.table_cells:
                cells_by_row = self._group_cells_by_row_v2(table.table_cells)
                
                self.logger.logger.info(f"🔍 DEBUG: Found {len(cells_by_row)} rows in table, {len(table.table_cells)} total cells")
                
                if cells_by_row:
                    best_header_row = None
                    best_score = -1
                    
                    for row_idx, header_cells in cells_by_row.items():
                        row_headers = []
                        for cell in header_cells:
                            # Try multiple ways to extract text from Docling cells
                            cell_text = ""
                            if hasattr(cell, 'text') and cell.text:
                                cell_text = str(cell.text)
                            elif hasattr(cell, 'content') and cell.content:
                                cell_text = str(cell.content)
                            elif hasattr(cell, 'value') and cell.value:
                                cell_text = str(cell.value)
                            elif hasattr(cell, 'data') and cell.data:
                                cell_text = str(cell.data)
                            else:
                                # Debug: print cell attributes to understand structure
                                self.logger.logger.warning(f"🔍 DEBUG: Header cell has no text content. Attributes: {dir(cell)}")
                                # Try to get any string representation
                                cell_text = str(cell) if cell else ""
                                if cell_text and cell_text != str(type(cell)):
                                    self.logger.logger.info(f"🔍 DEBUG: Using string representation: '{cell_text}'")
                                else:
                                    cell_text = ""
                            
                            row_headers.append(self._clean_text(cell_text))
                        
                        # ✅ FIXED: More flexible column requirements for complex documents
                        if len(row_headers) < 1:  # Changed from 3 to 1
                            continue
                        
                        # ✅ ENHANCED: Multi-tier scoring system
                        score = self._calculate_enhanced_header_score(row_headers, cells_by_row, row_idx)
                        
                        self.logger.logger.info(f"🔍 DEBUG: Row {row_idx} ({len(row_headers)} cols): {row_headers[:8]}... Score: {score:.2f}")
                        
                        if score > best_score:
                            best_score = score
                            best_header_row = row_headers
                    
                    if best_header_row:
                        # ✅ ENHANCED: Smart header processing for complex docs
                        headers = self._process_headers_for_complex_docs(best_header_row)
                        self.logger.logger.info(f"🔧 COMPLEX DOC: Processed headers: {headers}")
                        return headers
            
            # Try to export to dataframe first (most reliable)
            if hasattr(table, 'export_to_dataframe'):
                try:
                    df = table.export_to_dataframe()
                    if df is not None and not df.empty:
                        headers = [self._clean_text(str(col).strip()) for col in df.columns]
                        self.logger.logger.info(f"Extracted headers from dataframe: {headers}")
                        return headers
                except Exception as e:
                    self.logger.logger.warning(f"Error getting headers from dataframe: {e}")
            
            # Try different header extraction methods
            if hasattr(table, 'headers') and table.headers:
                headers = [self._clean_text(str(h).strip()) for h in table.headers if h]
            elif hasattr(table, 'header_rows') and table.header_rows:
                headers = self._process_multi_row_headers(table.header_rows)
            elif hasattr(table, 'columns') and table.columns:
                headers = [self._clean_text(str(col.get('header', f'Column_{i+1}')).strip()) 
                          for i, col in enumerate(table.columns)]
            
            # Final fallback: generate headers based on table width
            if not headers or all(not h.strip() for h in headers):
                max_columns = self._get_table_width(table)
                headers = [f"Column_{i+1}" for i in range(max_columns)]
            
            self.logger.logger.info(f"Extracted {len(headers)} headers: {headers}")
            return headers
            
        except Exception as e:
            self.logger.logger.error(f"Error extracting headers: {e}")
            return ["Column_1"]

    def _calculate_enhanced_header_score(self, headers: List[str], all_rows: Dict, row_idx: int) -> float:
        """Enhanced scoring system for complex documents."""
        if not headers:
            return 0.0
        
        score = 0.0
        
        # Base score from validator (existing logic)
        base_score = self.validator.score_potential_headers(headers)
        score += base_score * 0.4
        
        # ✅ NEW: Position-based scoring (earlier rows more likely to be headers)
        position_score = max(0, (10 - row_idx) / 10)  # Higher score for earlier rows
        score += position_score * 0.2
        
        # ✅ NEW: Content diversity scoring
        diversity_score = self._calculate_content_diversity(headers)
        score += diversity_score * 0.2
        
        # ✅ NEW: Complex document pattern recognition
        complex_doc_score = self._assess_complex_document_patterns(headers)
        score += complex_doc_score * 0.2
        
        return score

    def _calculate_content_diversity(self, headers: List[str]) -> float:
        """Calculate content diversity score."""
        if not headers:
            return 0.0
        
        # Check for diverse content types in headers
        has_text = any(re.search(r'[a-zA-Z]', str(h)) for h in headers)
        has_numbers = any(re.search(r'\d', str(h)) for h in headers)
        has_mixed = len(set(len(str(h).split()) for h in headers)) > 1
        
        diversity_indicators = sum([has_text, has_numbers, has_mixed])
        return diversity_indicators / 3.0

    def _assess_complex_document_patterns(self, headers: List[str]) -> float:
        """Assess patterns specific to complex documents."""
        if not headers:
            return 0.0
        
        complex_indicators = 0
        header_text = ' '.join(str(h).lower() for h in headers)
        
        # Look for section indicators
        section_terms = ['summary', 'detail', 'breakdown', 'analysis', 'report', 'statement']
        if any(term in header_text for term in section_terms):
            complex_indicators += 1
        
        # Look for multi-level structure indicators
        if any(len(str(h).split()) > 2 for h in headers):  # Multi-word headers
            complex_indicators += 1
        
        # Look for varied header lengths (indicates structured content)
        header_lengths = [len(str(h)) for h in headers]
        if len(set(header_lengths)) > 1:
            complex_indicators += 1
        
        return min(1.0, complex_indicators / 3.0)

    def _process_headers_for_complex_docs(self, headers: List[str]) -> List[str]:
        """Process headers specifically for complex documents."""
        processed = []
        
        for header in headers:
            header_str = str(header).strip()
            if not header_str:
                header_str = f"Column_{len(processed) + 1}"
            processed.append(header_str)
        
        # ✅ ENHANCED: Ensure minimum headers for complex docs
        while len(processed) < 2:  # Ensure at least 2 columns
            processed.append(f"Column_{len(processed) + 1}")
        
        return processed

    def _extract_via_table_cells(self, table) -> Tuple[List[str], List[List[str]]]:
        """Method 1: Extract via table_cells structure."""
        try:
            headers = []
            rows = []
            
            if hasattr(table, 'table_cells') and table.table_cells:
                self.logger.logger.info(f"🔍 DEBUG: Found table_cells: {len(table.table_cells)} cells")
                cells_by_row = self._group_cells_by_row_v2(table.table_cells)
                self.logger.logger.info(f"🔍 DEBUG: Grouped into {len(cells_by_row)} rows")
                
                if cells_by_row:
                    # Extract headers from first row
                    first_row_idx = min(cells_by_row.keys())
                    header_cells = cells_by_row[first_row_idx]
                    headers = []
                    for cell in header_cells:
                        # Try multiple ways to extract text from Docling cells
                        cell_text = ""
                        if hasattr(cell, 'text') and cell.text:
                            cell_text = str(cell.text)
                        elif hasattr(cell, 'content') and cell.content:
                            cell_text = str(cell.content)
                        elif hasattr(cell, 'value') and cell.value:
                            cell_text = str(cell.value)
                        elif hasattr(cell, 'data') and cell.data:
                            cell_text = str(cell.data)
                        else:
                            # Debug: print cell attributes to understand structure
                            self.logger.logger.warning(f"🔍 DEBUG: Header cell has no text content. Attributes: {dir(cell)}")
                            # Try to get any string representation
                            cell_text = str(cell) if cell else ""
                            if cell_text and cell_text != str(type(cell)):
                                self.logger.logger.info(f"🔍 DEBUG: Using string representation: '{cell_text}'")
                            else:
                                cell_text = ""
                        
                        headers.append(self._clean_text(cell_text))
                    self.logger.logger.info(f"🔍 DEBUG: Extracted headers: {headers}")
                    
                    # Extract data rows (skip first row)
                    sorted_row_indices = sorted(cells_by_row.keys())
                    for row_idx in sorted_row_indices[1:]:
                        row_cells = cells_by_row[row_idx]
                        row_data = []
                        for cell in row_cells:
                            # Try multiple ways to extract text from Docling cells
                            cell_text = ""
                            if hasattr(cell, 'text') and cell.text:
                                cell_text = str(cell.text)
                            elif hasattr(cell, 'content') and cell.content:
                                cell_text = str(cell.content)
                            elif hasattr(cell, 'value') and cell.value:
                                cell_text = str(cell.value)
                            elif hasattr(cell, 'data') and cell.data:
                                cell_text = str(cell.data)
                            else:
                                # Debug: print cell attributes to understand structure
                                self.logger.logger.warning(f"🔍 DEBUG: Data cell has no text content. Attributes: {dir(cell)}")
                                # Try to get any string representation
                                cell_text = str(cell) if cell else ""
                                if cell_text and cell_text != str(type(cell)):
                                    self.logger.logger.info(f"🔍 DEBUG: Using string representation: '{cell_text}'")
                                else:
                                    cell_text = ""
                            
                            row_data.append(self._clean_text(cell_text))
                        rows.append(row_data)
                    
                    self.logger.logger.info(f"🔍 DEBUG: Extracted {len(rows)} data rows")
                else:
                    self.logger.logger.warning("🔍 DEBUG: No cells_by_row found")
            else:
                self.logger.logger.warning("🔍 DEBUG: No table_cells attribute found")
            
            self.logger.logger.info(f"  Method 1 (table_cells): {len(headers)} headers, {len(rows)} rows")
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Method 1 failed: {e}")
            return [], []

    def _extract_via_dataframe(self, table) -> Tuple[List[str], List[List[str]]]:
        """Method 2: Extract via dataframe export."""
        try:
            headers = []
            rows = []
            
            if hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                if df is not None and not df.empty:
                    headers = [self._clean_text(str(col).strip()) for col in df.columns]
                    
                    for _, row in df.iterrows():
                        processed_row = [str(cell).strip() if cell else "" for cell in row]
                        rows.append(processed_row)
            
            self.logger.logger.info(f"  Method 2 (dataframe): {len(headers)} headers, {len(rows)} rows")
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Method 2 failed: {e}")
            return [], []

    def _extract_via_attributes(self, table) -> Tuple[List[str], List[List[str]]]:
        """Method 3: Extract via direct attributes."""
        try:
            headers = []
            rows = []
            
            # Try different header extraction methods
            if hasattr(table, 'headers') and table.headers:
                headers = [self._clean_text(str(h).strip()) for h in table.headers if h]
            elif hasattr(table, 'header_rows') and table.header_rows:
                headers = self._process_multi_row_headers(table.header_rows)
            elif hasattr(table, 'columns') and table.columns:
                headers = [self._clean_text(str(col.get('header', f'Column_{i+1}')).strip()) 
                          for i, col in enumerate(table.columns)]
            
            # Try different row extraction methods
            if hasattr(table, 'data') and table.data:
                if hasattr(table.data, 'rows') and table.data.rows:
                    for row in table.data.rows:
                        processed_row = self._flatten_row_data(row)
                        rows.append(processed_row)
                elif hasattr(table.data, '__iter__'):
                    for row in table.data:
                        processed_row = self._flatten_row_data(row)
                        rows.append(processed_row)
            
            # Fallback to rows attribute
            if not rows and hasattr(table, 'rows') and table.rows:
                for row in table.rows:
                    processed_row = self._flatten_row_data(row)
                    rows.append(processed_row)
            
            # Final fallback: generate headers based on table width
            if not headers or all(not h.strip() for h in headers):
                max_columns = self._get_table_width(table)
                headers = [f"Column_{i+1}" for i in range(max_columns)]
            
            self.logger.logger.info(f"  Method 3 (attributes): {len(headers)} headers, {len(rows)} rows")
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Method 3 failed: {e}")
            return [], []
    
    def _group_cells_by_row_v2(self, table_cells) -> Dict[int, List]:
        """Group Docling v2 table cells by row using the new structure."""
        cells_by_row = {}
        
        try:
            self.logger.logger.info(f"🔍 DEBUG: Grouping {len(table_cells)} cells by row")
            
            for cell in table_cells:
                # Use start_row_offset_idx for row grouping
                row_idx = cell.start_row_offset_idx
                if row_idx not in cells_by_row:
                    cells_by_row[row_idx] = []
                cells_by_row[row_idx].append(cell)
            
            self.logger.logger.info(f"🔍 DEBUG: Found {len(cells_by_row)} unique rows")
            
            # Sort cells within each row by column position
            for row_idx in cells_by_row:
                cells_by_row[row_idx].sort(key=lambda cell: cell.start_col_offset_idx)
                self.logger.logger.info(f"🔍 DEBUG: Row {row_idx}: {len(cells_by_row[row_idx])} cells")
            
            return cells_by_row
            
        except Exception as e:
            self.logger.logger.error(f"Error grouping cells by row: {e}")
            return {}
    
    def _extract_rows(self, table) -> List[List[str]]:
        """Extract rows with consistent data handling."""
        try:
            rows = []
            
            # For Docling v2 table elements, extract from table_cells structure
            if hasattr(table, 'table_cells') and table.table_cells:
                # Group cells by row using the new Docling v2 structure
                cells_by_row = self._group_cells_by_row_v2(table.table_cells)
                
                if cells_by_row:
                    # Skip the first row (headers) and extract data rows
                    sorted_row_indices = sorted(cells_by_row.keys())
                    for row_idx in sorted_row_indices[1:]:  # Skip first row (headers)
                        row_cells = cells_by_row[row_idx]
                        row_data = []
                        for cell in row_cells:
                            # Try multiple ways to extract text from Docling cells
                            cell_text = ""
                            if hasattr(cell, 'text') and cell.text:
                                cell_text = str(cell.text)
                            elif hasattr(cell, 'content') and cell.content:
                                cell_text = str(cell.content)
                            elif hasattr(cell, 'value') and cell.value:
                                cell_text = str(cell.value)
                            elif hasattr(cell, 'data') and cell.data:
                                cell_text = str(cell.data)
                            else:
                                # Debug: print cell attributes to understand structure
                                self.logger.logger.warning(f"🔍 DEBUG: Cell has no text content. Attributes: {dir(cell)}")
                                # Try to get any string representation
                                cell_text = str(cell) if cell else ""
                                if cell_text and cell_text != str(type(cell)):
                                    self.logger.logger.info(f"🔍 DEBUG: Using string representation: '{cell_text}'")
                                else:
                                    cell_text = ""
                            
                            row_data.append(self._clean_text(cell_text))
                        rows.append(row_data)
                    
                    self.logger.logger.info(f"Extracted {len(rows)} rows from cell structure")
                    return rows
            
            # Try to export to dataframe first (most reliable)
            if hasattr(table, 'export_to_dataframe'):
                try:
                    df = table.export_to_dataframe()
                    if df is not None and not df.empty:
                        self.logger.logger.info("Using dataframe export for table data")
                        for _, row in df.iterrows():
                            processed_row = [str(cell).strip() if cell else "" for cell in row]
                            rows.append(processed_row)
                        return rows
                except Exception as e:
                    self.logger.logger.warning(f"Error exporting to dataframe: {e}")
            
            # Try to access table data directly
            if hasattr(table, 'data') and table.data:
                try:
                    if hasattr(table.data, 'rows') and table.data.rows:
                        for row in table.data.rows:
                            processed_row = self._flatten_row_data(row)
                            rows.append(processed_row)
                    elif hasattr(table.data, '__iter__'):
                        for row in table.data:
                            processed_row = self._flatten_row_data(row)
                            rows.append(processed_row)
                except Exception as e:
                    self.logger.logger.warning(f"Error accessing table.data: {e}")
            
            # Fallback to rows attribute
            if not rows and hasattr(table, 'rows') and table.rows:
                try:
                    for row in table.rows:
                        processed_row = self._flatten_row_data(row)
                        rows.append(processed_row)
                except Exception as e:
                    self.logger.logger.warning(f"Error accessing table.rows: {e}")
            
            self.logger.logger.info(f"Extracted {len(rows)} rows from table")
            return rows
            
        except Exception as e:
            self.logger.logger.error(f"Error extracting rows: {e}")
            return []
    
    def _extract_footers(self, table) -> List[str]:
        """Extract footer information from table if available."""
        try:
            footers = []
            if hasattr(table, 'footers') and table.footers:
                footers = [self._clean_text(str(f).strip()) for f in table.footers if f]
            elif hasattr(table, 'footer_rows') and table.footer_rows:
                for row in table.footer_rows:
                    footer_text = " ".join([str(cell).strip() for cell in row if cell])
                    if footer_text:
                        footers.append(self._clean_text(footer_text))
            return footers
        except Exception as e:
            self.logger.logger.warning(f"Error extracting footers: {e}")
            return []
    
    def _extract_table_metadata(self, table, table_index: int, pdf_path: str) -> Dict[str, Any]:
        """Extract metadata about the table."""
        metadata = {
            "table_index": table_index,
            "source_file": pdf_path,
            "extraction_method": "docling",
            "timestamp": time.time()
        }
        
        try:
            if hasattr(table, 'bbox'):
                metadata['bbox'] = table.bbox
            if hasattr(table, 'page'):
                metadata['page_number'] = table.page
            if hasattr(table, 'confidence'):
                metadata['confidence'] = table.confidence
        except Exception as e:
            self.logger.logger.warning(f"Error extracting table metadata: {e}")
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Basic cleaning
        cleaned = " ".join(text.split()).strip()
        
        # Apply deduplication to remove repeated text patterns
        cleaned = self._deduplicate_text(cleaned)
        
        return cleaned
    
    def _parse_table_from_text(self, text: str) -> Tuple[List[str], List[List[str]]]:
        """Parse table structure from raw text content."""
        try:
            if not text or not text.strip():
                return [], []
            
            lines = text.strip().split('\n')
            if len(lines) < 2:
                return [], []
            
            # Try to identify headers and data rows
            headers = []
            rows = []
            
            # Look for lines that might be headers (shorter, more descriptive)
            potential_headers = []
            potential_data = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Split by common delimiters
                parts = []
                for delimiter in ['\t', '|', '  ', ' ']:
                    if delimiter in line:
                        parts = [part.strip() for part in line.split(delimiter) if part.strip()]
                        break
                
                if not parts:
                    parts = [line]
                
                # Heuristic: headers are usually shorter and more descriptive
                if len(parts) >= 2 and all(len(part) < 50 for part in parts):
                    potential_headers.append(parts)
                else:
                    potential_data.append(parts)
            
            # Use the first potential header row as headers
            if potential_headers:
                headers = potential_headers[0]
                # Use remaining potential headers and all data as rows
                rows = potential_headers[1:] + potential_data
            else:
                # No clear headers, use first row as headers
                if potential_data:
                    headers = potential_data[0]
                    rows = potential_data[1:]
            
            # Clean up the data
            headers = [self._clean_text(header) for header in headers]
            rows = [[self._clean_text(cell) for cell in row] for row in rows]
            
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Error parsing table from text: {e}")
            return [], []
    
    def _flatten_row_data(self, row) -> List[str]:
        """Flatten row data into a list of strings."""
        try:
            if isinstance(row, (list, tuple)):
                return [str(cell).strip() if cell else "" for cell in row]
            elif hasattr(row, '__iter__') and not isinstance(row, str):
                return [str(cell).strip() if cell else "" for cell in row]
            else:
                return [str(row).strip()]
        except Exception:
            return [str(row)]
    
    def _get_table_width(self, table) -> int:
        """Determine the width (number of columns) of a table."""
        try:
            if hasattr(table, 'export_to_dataframe'):
                try:
                    df = table.export_to_dataframe()
                    if df is not None:
                        return len(df.columns)
                except:
                    pass
            
            if hasattr(table, 'columns') and table.columns:
                return len(table.columns)
            
            if hasattr(table, 'headers') and table.headers:
                return len(table.headers)
            
            # Fallback: check first row
            if hasattr(table, 'rows') and table.rows and len(table.rows) > 0:
                return len(table.rows[0]) if hasattr(table.rows[0], '__len__') else 1
            
            return 1
        except:
            return 1
    
    def _normalize_row_lengths(self, rows: List[List[str]], target_length: int) -> List[List[str]]:
        """Ensure all rows have the same length by padding with empty strings."""
        normalized_rows = []
        for row in rows:
            if len(row) < target_length:
                padded_row = row + [""] * (target_length - len(row))
                normalized_rows.append(padded_row)
            elif len(row) > target_length:
                normalized_rows.append(row[:target_length])
            else:
                normalized_rows.append(row)
        return normalized_rows
    
    def _process_multi_row_headers(self, header_rows: List) -> List[str]:
        """Process multi-row headers into a single header row."""
        try:
            if not header_rows:
                return []
            
            # Process all header rows to lists of strings
            processed = [[str(cell).strip() for cell in row] for row in header_rows]
            
            # Use zip_longest to align columns across all header rows
            columns = list(zip_longest(*processed, fillvalue=""))
            
            # Join each column's header parts with space, filtering out empty elements
            headers = [" ".join(filter(None, col)).strip() for col in columns]
            return [self._clean_text(header) for header in headers]
            
        except Exception as e:
            self.logger.logger.error(f"Error processing multi-row headers: {e}")
            return []
    
    def _split_compound_headers(self, headers: List[str]) -> List[str]:
        """Split compound headers like 'Census Ct. Paid Amount' into separate columns."""
        split_headers = []
        
        for header in headers:
            header_text = str(header).strip()
            
            # Check for specific known compound patterns that should be split
            if 'Census Ct. Paid Amount' in header_text:
                # Split this into two separate headers
                split_headers.extend(['Census Ct.', 'Paid Amount'])
                self.logger.logger.info(f"🔧 SPLIT: '{header_text}' → ['Census Ct.', 'Paid Amount']")
            elif 'Census Ct.' in header_text and 'Paid' in header_text:
                # Handle variations of this pattern
                split_headers.extend(['Census Ct.', 'Paid Amount'])
                self.logger.logger.info(f"🔧 SPLIT: '{header_text}' → ['Census Ct.', 'Paid Amount']")
            # DO NOT split financial headers that should remain intact
            elif any(keyword in header_text.lower() for keyword in [
                'total premium', 'commissionable', 'non-commissionable', 
                'commission earned', 'commission due', 'previous comm',
                'billed period', 'group name', 'master group', 'group id',
                'prod type', 'cr%', 'spl%'
            ]):
                # Keep financial headers intact - don't split them
                split_headers.append(header_text)
                self.logger.logger.info(f"🔧 KEEP INTACT: '{header_text}' (financial header)")
            elif len(header_text) > 25 and ' ' in header_text:
                # For other long headers with spaces, try intelligent splitting
                parts = header_text.split()
                mid_point = len(parts) // 2
                if mid_point > 0:
                    left_part = ' '.join(parts[:mid_point])
                    right_part = ' '.join(parts[mid_point:])
                    split_headers.extend([left_part, right_part])
                    self.logger.logger.info(f"🔧 SPLIT: '{header_text}' → ['{left_part}', '{right_part}']")
                else:
                    split_headers.append(header_text)
            else:
                split_headers.append(header_text)
        
        return split_headers
    
    def _is_financial_table(self, headers: List[str]) -> bool:
        """Check if the table appears to be a financial/commission statement table."""
        if not headers:
            return False
        
        # Convert headers to lowercase for easier matching
        header_text = ' '.join(headers).lower()
        
        # Financial table indicators
        financial_indicators = [
            'premium', 'commission', 'billed', 'group', 'client', 'invoice',
            'total', 'amount', 'due', 'paid', 'rate', 'percentage', 'period',
            'earned', 'allocated', 'non-commissionable', 'commissionable'
        ]
        
        # Count how many financial indicators are present
        indicator_count = sum(1 for indicator in financial_indicators if indicator in header_text)
        
        # If more than 3 financial indicators are found, it's likely a financial table
        is_financial = indicator_count >= 3
        
        self.logger.logger.info(f"🔍 FINANCIAL DETECTION: {indicator_count}/{len(financial_indicators)} indicators found - Financial table: {is_financial}")
        
        return is_financial
    
    def _expand_rows_for_split_headers(self, rows: List[List[str]], headers: List[str]) -> List[List[str]]:
        """Expand data rows to match split headers, specifically handling Census Ct./Paid Amount split."""
        expanded_rows = []
        
        for row in rows:
            if len(row) == 9 and len(headers) == 10:  # Common case: 9 original → 10 with split
                # Find the last column value and split it if it contains multiple values
                expanded_row = row[:8]  # First 8 columns stay the same
                
                # The 9th column (index 8) might contain both Census Ct. and Paid Amount
                last_cell = str(row[8]).strip()
                
                # Try to intelligently split the last cell
                if ' ' in last_cell and len(last_cell) > 3:
                    # If it has spaces, split it
                    parts = last_cell.split()
                    if len(parts) >= 2:
                        expanded_row.extend([parts[0], ' '.join(parts[1:])])
                    else:
                        expanded_row.extend([last_cell, ''])
                elif last_cell and last_cell != '':
                    # Single value goes to first new column
                    expanded_row.extend([last_cell, ''])
                else:
                    # Empty value
                    expanded_row.extend(['', ''])
                
                expanded_rows.append(expanded_row)
            else:
                # No expansion needed or unusual case
                expanded_rows.append(row)
        
        return expanded_rows
    
    def _create_cells_from_headers_and_rows(self, headers: List[str], rows: List[List[str]]) -> List[Dict[str, Any]]:
        """Create cells structure from headers and rows for validation compatibility."""
        cells = []
        
        # Add header cells
        for col_idx, header in enumerate(headers):
            cells.append({
                "row": 0,
                "column": col_idx,
                "text": header,
                "is_header": True,
                "confidence": 1.0,
                "bbox": [0, 0, 0, 0]  # Placeholder bbox
            })
        
        # Add data cells
        for row_idx, row in enumerate(rows):
            for col_idx, cell_text in enumerate(row):
                if col_idx < len(headers):  # Ensure we don't exceed column count
                    cells.append({
                        "row": row_idx + 1,  # +1 because row 0 is headers
                        "column": col_idx,
                        "text": cell_text,
                        "is_header": False,
                        "confidence": 1.0,
                        "bbox": [0, 0, 0, 0]  # Placeholder bbox
                    })
        
        return cells
    
    def _deduplicate_text(self, text: str) -> str:
        """Remove duplicate words/phrases from text while preserving meaningful content."""
        if not text:
            return text
        
        # Split into words
        words = text.split()
        if len(words) <= 3:
            return text
        
        # Look for obvious repetitive patterns - be conservative to preserve content
        # Only remove clear duplicates like "LLC LLC LLC" or "Logistics Logistics"
        result_text = text
        
        # Simple pattern: remove exact word repetitions (2+ times)
        for word in set(words):
            if len(word) > 2:  # Only for meaningful words
                # Look for 3+ repetitions of the same word
                pattern = f' {word} {word} {word}'
                if pattern in result_text:
                    # Replace with single occurrence
                    result_text = result_text.replace(pattern, f' {word}')
                    self.logger.logger.info(f"🧹 DEDUPLICATED word: '{word}' (removed repetitions)")
        
        # Pattern: remove phrase duplications like "Development, LLC Development, LLC"
        import re
        # Look for patterns like "word, word word, word" or "and word word and word word"
        phrase_patterns = [
            r'(\b\w+,?\s+\w+)\s+\1',  # "Development, LLC Development, LLC"
            r'(\band\s+\w+\s+\w+)\s+\1',  # "and Transport LLC and Transport LLC"
            r'(\b\w+\s+\w+\s+\w+)\s+\1',  # "Delivery Logistics LLC Delivery Logistics LLC"
        ]
        
        for pattern in phrase_patterns:
            matches = re.findall(pattern, result_text)
            for match in matches:
                # Replace duplicate phrase with single occurrence
                duplicate_pattern = f'{match} {match}'
                if duplicate_pattern in result_text:
                    result_text = result_text.replace(duplicate_pattern, match)
                    self.logger.logger.info(f"🧹 DEDUPLICATED phrase: '{match}' (removed duplication)")
        
        # Log the deduplication if significant changes were made
        if len(result_text) < len(text) * 0.8:  # If we removed more than 20% of the text
            self.logger.logger.info(f"🧹 DEDUPLICATED: '{text[:50]}...' → '{result_text[:50]}...'")
        
        return result_text.strip()

    def _extract_complex_table_structure(self, table) -> Tuple[List[str], List[List[str]]]:
        """Advanced method for extracting complex table structures that other methods fail on."""
        try:
            headers = []
            rows = []
            
            self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Starting complex table structure analysis")
            
            # **NEW: Try OTSL sequence extraction first (Docling v2 internal format)**
            if hasattr(table, 'otsl_seq') and table.otsl_seq:
                self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Found OTSL sequence with {len(table.otsl_seq)} elements")
                otsl_headers, otsl_rows = self._extract_from_otsl_sequence_with_context(table.otsl_seq, table)
                if otsl_headers and len(otsl_headers) > 1:
                    self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: OTSL extraction succeeded: {len(otsl_headers)} headers, {len(otsl_rows)} rows")
                    return otsl_headers, otsl_rows
                else:
                    self.logger.logger.warning(f"🔍 COMPLEX EXTRACTION: OTSL extraction failed: {len(otsl_headers)} headers, {len(otsl_rows)} rows")
            
            # Try to get raw table structure
            if hasattr(table, 'table_cells') and table.table_cells:
                self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Found {len(table.table_cells)} table cells")
                
                # Analyze the raw cell structure
                raw_cells = []
                for i, cell in enumerate(table.table_cells):
                    # Extract all available attributes
                    cell_info = {
                        'text': getattr(cell, 'text', '').strip(),
                        'row': getattr(cell, 'start_row_offset_idx', 0),
                        'col': getattr(cell, 'start_col_offset_idx', 0),
                        'row_span': getattr(cell, 'row_span', 1),
                        'col_span': getattr(cell, 'col_span', 1),
                        'bbox': getattr(cell, 'bbox', None)
                    }
                    raw_cells.append(cell_info)
                    
                    # Debug first few cells
                    if i < 5:
                        self.logger.logger.info(f"🔍 Cell {i}: text='{cell_info['text']}', row={cell_info['row']}, col={cell_info['col']}")
                
                if raw_cells:
                    # Find the structure by analyzing cell positions
                    max_row = max(cell['row'] for cell in raw_cells)
                    max_col = max(cell['col'] + cell['col_span'] for cell in raw_cells)
                    
                    self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Grid dimensions: {max_row + 1} rows x {max_col} cols")
                    
                    # Create a grid representation
                    grid = [[None for _ in range(max_col)] for _ in range(max_row + 1)]
                    
                    # Place cells in the grid
                    for cell_info in raw_cells:
                        row, col = cell_info['row'], cell_info['col']
                        row_span, col_span = cell_info['row_span'], cell_info['col_span']
                        
                        # Place the main cell
                        if row < len(grid) and col < len(grid[row]):
                            grid[row][col] = cell_info['text']
                        
                        # Expand merged cells
                        for r in range(row, min(row + row_span, len(grid))):
                            for c in range(col, min(col + col_span, len(grid[r]))):
                                if r < len(grid) and c < len(grid[r]) and grid[r][c] is None:
                                    grid[r][c] = cell_info['text']
                    
                    # **IMPROVED: Intelligent header detection for commission statements**
                    # Look for the row that best matches header characteristics
                    best_header_row_idx = 0
                    best_header_score = 0
                    
                    for row_idx in range(len(grid)):
                        row = grid[row_idx]
                        non_empty_cells = [cell for cell in row if cell and str(cell).strip()]
                        
                        if len(non_empty_cells) >= 3:  # Commission tables typically have many columns
                            # Calculate header score based on content characteristics
                            header_score = 0
                            for cell in non_empty_cells:
                                cell_text = str(cell).strip().lower()
                                # Check for common header words
                                if any(word in cell_text for word in [
                                    'group', 'name', 'date', 'plan', 'rate', 'lives', 'premium', 
                                    'commission', 'paid', 'billed', 'received', 'due', 'effective'
                                ]):
                                    header_score += 1
                                # Headers are typically shorter and more descriptive
                                if len(cell_text) <= 20 and cell_text.isalpha():
                                    header_score += 0.5
                            
                            if header_score > best_header_score:
                                best_header_score = header_score
                                best_header_row_idx = row_idx
                    
                    # Extract headers from the best header row
                    if grid and len(grid) > best_header_row_idx:
                        headers = []
                        for i, cell in enumerate(grid[best_header_row_idx]):
                            if cell and str(cell).strip():
                                headers.append(str(cell).strip())
                            else:
                                headers.append(f"Column_{i+1}")
                        
                        self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Found headers at row {best_header_row_idx} (score: {best_header_score}): {headers}")
                    
                    # Extract data rows (skip header row)
                    for row_idx in range(best_header_row_idx + 1, len(grid)):
                        row_data = [str(cell) if cell is not None else "" 
                                   for cell in grid[row_idx]]
                        if any(cell.strip() for cell in row_data):  # Only add non-empty rows
                            rows.append(row_data)
                    
                    self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Final result: {len(headers)} headers, {len(rows)} rows")
                    
                    # **NEW: If still no good results, try alternative cell grouping**
                    if len(headers) <= 1 or len(rows) == 0:
                        self.logger.logger.warning("🔍 COMPLEX EXTRACTION: Standard grid failed, trying alternative grouping...")
                        alt_headers, alt_rows = self._extract_alternative_cell_grouping(raw_cells)
                        if len(alt_headers) > len(headers):
                            headers, rows = alt_headers, alt_rows
                            self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Alternative method improved: {len(headers)} headers, {len(rows)} rows")
                    
                    return headers, rows
            
            self.logger.logger.warning("🔍 COMPLEX EXTRACTION: No table_cells found")
            
            # **NEW: Final fallback - try to extract from table text**
            if hasattr(table, 'text') and table.text:
                self.logger.logger.info("🔍 COMPLEX EXTRACTION: Trying text-based extraction as final fallback...")
                self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Table text length: {len(table.text)}")
                self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Table text preview: {table.text[:200]}...")
                text_headers, text_rows = self._extract_from_table_text(table.text)
                if text_headers and len(text_headers) > 1:
                    self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Text extraction succeeded: {len(text_headers)} headers, {len(text_rows)} rows")
                    return text_headers, text_rows
                else:
                    self.logger.logger.warning(f"🔍 COMPLEX EXTRACTION: Text extraction failed: {len(text_headers)} headers, {len(text_rows)} rows")
            
            # **NEW: Try other text attributes if available**
            for text_attr in ['content', 'data', 'raw_text']:
                if hasattr(table, text_attr):
                    attr_value = getattr(table, text_attr)
                    if attr_value and str(attr_value).strip():
                        self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: Trying {text_attr} attribute...")
                        text_headers, text_rows = self._extract_from_table_text(str(attr_value))
                        if text_headers and len(text_headers) > 1:
                            self.logger.logger.info(f"🔍 COMPLEX EXTRACTION: {text_attr} extraction succeeded: {len(text_headers)} headers, {len(text_rows)} rows")
                            return text_headers, text_rows
            
            return [], []
            
        except Exception as e:
            self.logger.logger.error(f"Error extracting complex table structure: {e}")
            return [], []

    def _extract_alternative_cell_grouping(self, raw_cells: List[Dict]) -> Tuple[List[str], List[List[str]]]:
        """Alternative method for grouping cells when standard grid approach fails."""
        try:
            headers = []
            rows = []
            
            # Group cells by row
            cells_by_row = {}
            for cell in raw_cells:
                row = cell['row']
                if row not in cells_by_row:
                    cells_by_row[row] = []
                cells_by_row[row].append(cell)
            
            # Sort rows and find the best header row
            sorted_rows = sorted(cells_by_row.keys())
            header_row_idx = None
            
            for row_idx in sorted_rows:
                row_cells = cells_by_row[row_idx]
                # Look for a row with multiple meaningful cells
                meaningful_cells = [c for c in row_cells if c['text'] and len(c['text'].strip()) > 1]
                if len(meaningful_cells) >= 3:
                    header_row_idx = row_idx
                    break
            
            if header_row_idx is not None:
                # Extract headers from the identified row
                header_cells = sorted(cells_by_row[header_row_idx], key=lambda x: x['col'])
                headers = [cell['text'].strip() for cell in header_cells if cell['text'].strip()]
                
                # Extract data rows
                for row_idx in sorted_rows:
                    if row_idx > header_row_idx:  # Skip header row
                        row_cells = sorted(cells_by_row[row_idx], key=lambda x: x['col'])
                        row_data = [cell['text'].strip() for cell in row_cells]
                        if any(cell.strip() for cell in row_data):
                            rows.append(row_data)
            
            self.logger.logger.info(f"🔍 ALTERNATIVE GROUPING: {len(headers)} headers, {len(rows)} rows")
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Error in alternative cell grouping: {e}")
            return [], []

    def _extract_from_table_text(self, table_text: str) -> Tuple[List[str], List[List[str]]]:
        """Extract table structure from raw text as final fallback."""
        try:
            headers = []
            rows = []
            
            lines = table_text.strip().split('\n')
            if not lines:
                return [], []
            
            self.logger.logger.info(f"🔍 TEXT EXTRACTION: Processing {len(lines)} lines")
            
            # Look for lines that might be headers (contain common table headers)
            header_keywords = ['group', 'number', 'name', 'rate', 'date', 'product', 'premium', 'payment', 'commission', 'type', 'split', 'mo', 'days', 'count', 'comments', 'exch']
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in header_keywords):
                    self.logger.logger.info(f"🔍 TEXT EXTRACTION: Found potential header line {i}: {line[:100]}...")
                    
                    # This might be a header row
                    # Try to split by common delimiters
                    potential_headers = []
                    for delimiter in ['\t', '  ', '|', ' ']:
                        if delimiter in line:
                            potential_headers = [h.strip() for h in line.split(delimiter) if h.strip()]
                            if len(potential_headers) >= 3:  # Reasonable number of columns
                                break
                    
                    if len(potential_headers) >= 3:  # Reasonable number of columns
                        headers = potential_headers
                        self.logger.logger.info(f"🔍 TEXT EXTRACTION: Using headers: {headers}")
                        
                        # Try to extract data rows from subsequent lines
                        for j in range(i + 1, min(i + 50, len(lines))):  # Look at next 50 lines
                            data_line = lines[j].strip()
                            if data_line and len(data_line) > 10:  # Skip very short lines
                                # Try to split by same delimiter
                                for delimiter in ['\t', '  ', '|', ' ']:
                                    if delimiter in data_line:
                                        row_data = [cell.strip() for cell in data_line.split(delimiter) if cell.strip()]
                                        if len(row_data) >= len(headers) * 0.3:  # At least 30% of expected columns
                                            rows.append(row_data)
                                            self.logger.logger.info(f"🔍 TEXT EXTRACTION: Added row {len(rows)}: {row_data[:5]}...")
                                        break
                        
                        # If we found headers and some rows, we're done
                        if headers and rows:
                            break
            
            # **NEW: If no headers found, try to extract from structured text patterns**
            if not headers and not rows:
                self.logger.logger.info("🔍 TEXT EXTRACTION: No headers found, trying pattern-based extraction...")
                headers, rows = self._extract_from_structured_patterns(lines)
            
            self.logger.logger.info(f"🔍 TEXT EXTRACTION: Final result: {len(headers)} headers, {len(rows)} rows")
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Error in text-based extraction: {e}")
            return [], []

    def _extract_from_otsl_sequence_with_context(self, otsl_seq: List[str], table) -> Tuple[List[str], List[List[str]]]:
        """Extract table structure and content from Docling v2 OTSL sequence format with document context."""
        try:
            headers = []
            rows = []
            
            self.logger.logger.info(f"🔍 OTSL EXTRACTION: Processing {len(otsl_seq)} OTSL elements with context")
            
            # **NEW: Try to extract actual content from document context**
            # First, let's try to get the raw table data from the document
            document_context = self._extract_document_context_for_table(table)
            
            if document_context:
                self.logger.logger.info(f"🔍 OTSL EXTRACTION: Found document context with {len(document_context)} elements")
                # Use the document context to extract real content
                return self._extract_table_from_document_context(document_context, otsl_seq)
            
            # Fallback to structure-only extraction
            return self._extract_from_otsl_sequence(otsl_seq, table)
            
        except Exception as e:
            self.logger.logger.error(f"Error extracting from OTSL sequence with context: {e}")
            return [], []

    def _extract_document_context_for_table(self, table) -> List[str]:
        """Extract document context elements that might contain table content."""
        try:
            context_elements = []
            
            # Try to access the parent document or surrounding elements
            # This is a heuristic approach to find table content
            
            # Method 1: Try to get text from surrounding elements
            if hasattr(table, 'cluster') and table.cluster:
                # The cluster might contain related elements
                cluster_elements = table.cluster
                for element in cluster_elements:
                    if hasattr(element, 'text') and element.text:
                        context_elements.append(element.text)
            
            # Method 2: Try to access document-level text
            if hasattr(table, 'model_dump'):
                try:
                    raw_data = table.model_dump()
                    if 'cluster' in raw_data and raw_data['cluster']:
                        for element in raw_data['cluster']:
                            if isinstance(element, dict) and 'text' in element:
                                context_elements.append(element['text'])
                except Exception as e:
                    self.logger.logger.warning(f"Error accessing cluster data: {e}")
            
            # Method 3: Try to extract from the document's text content
            # This would require access to the parent document, which we don't have here
            # For now, we'll return what we can find
            
            self.logger.logger.info(f"🔍 CONTEXT EXTRACTION: Found {len(context_elements)} context elements")
            return context_elements
            
        except Exception as e:
            self.logger.logger.error(f"Error extracting document context: {e}")
            return []

    def _extract_table_from_document_context(self, context_elements: List[str], otsl_seq: List[str]) -> Tuple[List[str], List[List[str]]]:
        """Extract table content using document context and OTSL structure."""
        try:
            headers = []
            rows = []
            
            # Parse OTSL sequence to understand table structure
            current_row = []
            current_col = 0
            max_cols = 0
            in_header = False
            header_found = False
            context_index = 0
            
            # OTSL sequence patterns:
            # 'ched' = header cell, 'lcel' = left cell, 'fcel' = full cell, 'ecel' = end cell
            # 'nl' = new line, 'srow' = start row
            
            for i, token in enumerate(otsl_seq):
                if token == 'nl':
                    # New line - finish current row
                    if current_row:
                        if in_header and not header_found:
                            # This is the header row
                            headers = current_row.copy()
                            header_found = True
                            self.logger.logger.info(f"🔍 CONTEXT OTSL: Found headers: {headers}")
                        else:
                            # This is a data row
                            rows.append(current_row.copy())
                            self.logger.logger.info(f"🔍 CONTEXT OTSL: Added row {len(rows)}: {current_row[:5]}...")
                        
                        max_cols = max(max_cols, len(current_row))
                        current_row = []
                        current_col = 0
                        in_header = False
                
                elif token == 'srow':
                    # Start of new row
                    in_header = True
                    current_row = []
                    current_col = 0
                
                elif token in ['ched', 'lcel', 'fcel', 'ecel']:
                    # Cell tokens - try to extract actual content from context
                    cell_content = ""
                    
                    if context_index < len(context_elements):
                        # Use actual content from document context
                        cell_content = context_elements[context_index].strip()
                        context_index += 1
                    else:
                        # Fallback to placeholder
                        if token == 'ched':
                            cell_content = f"Header_{current_col + 1}"
                        else:
                            cell_content = f"Data_{current_col + 1}"
                    
                    current_row.append(cell_content)
                    current_col += 1
            
            # Handle the last row if it doesn't end with 'nl'
            if current_row:
                if in_header and not header_found:
                    headers = current_row.copy()
                    header_found = True
                    self.logger.logger.info(f"🔍 CONTEXT OTSL: Found headers (final): {headers}")
                else:
                    rows.append(current_row.copy())
                    self.logger.logger.info(f"🔍 CONTEXT OTSL: Added final row {len(rows)}: {current_row[:5]}...")
            
            # Generate headers if none found
            if not headers and max_cols > 0:
                headers = [f"Column_{i+1}" for i in range(max_cols)]
                self.logger.logger.info(f"🔍 CONTEXT OTSL: Generated headers: {headers}")
            
            # Normalize all rows to have the same number of columns
            if headers:
                normalized_rows = []
                for row in rows:
                    normalized_row = row[:len(headers)]  # Truncate if too long
                    while len(normalized_row) < len(headers):  # Pad if too short
                        normalized_row.append("")
                    normalized_rows.append(normalized_row)
                rows = normalized_rows
            
            self.logger.logger.info(f"🔍 CONTEXT OTSL: Final result: {len(headers)} headers, {len(rows)} rows")
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Error extracting table from document context: {e}")
            return [], []

    def _extract_from_otsl_sequence(self, otsl_seq: List[str], table=None) -> Tuple[List[str], List[List[str]]]:
        """Extract table structure from Docling v2 OTSL sequence format (structure only)."""
        try:
            headers = []
            rows = []
            
            self.logger.logger.info(f"🔍 OTSL EXTRACTION: Processing {len(otsl_seq)} OTSL elements")
            
            # Parse OTSL sequence to understand table structure
            current_row = []
            current_col = 0
            max_cols = 0
            in_header = False
            header_found = False
            
            # OTSL sequence patterns:
            # 'ched' = header cell, 'lcel' = left cell, 'fcel' = full cell, 'ecel' = end cell
            # 'nl' = new line, 'srow' = start row
            
            for i, token in enumerate(otsl_seq):
                if token == 'nl':
                    # New line - finish current row
                    if current_row:
                        if in_header and not header_found:
                            # This is the header row
                            headers = current_row.copy()
                            header_found = True
                            self.logger.logger.info(f"🔍 OTSL EXTRACTION: Found headers: {headers}")
                        else:
                            # This is a data row
                            rows.append(current_row.copy())
                            self.logger.logger.info(f"🔍 OTSL EXTRACTION: Added row {len(rows)}: {current_row[:5]}...")
                        
                        max_cols = max(max_cols, len(current_row))
                        current_row = []
                        current_col = 0
                        in_header = False
                
                elif token == 'srow':
                    # Start of new row
                    in_header = True
                    current_row = []
                    current_col = 0
                
                elif token in ['ched', 'lcel', 'fcel', 'ecel']:
                    # Cell tokens - we need to extract the actual content
                    # Since OTSL only gives structure, we'll try to extract real content
                    # from the document context or use intelligent placeholders
                    
                    if token == 'ched':
                        # Header cell - try to extract real header content
                        cell_content = self._extract_cell_content_from_context(table, current_col, in_header=True)
                        if not cell_content or cell_content.startswith('Header_'):
                            # Fallback to intelligent header naming
                            cell_content = self._generate_intelligent_header_name(current_col, headers, rows)
                        in_header = True
                    else:
                        # Data cell - try to extract real data content
                        cell_content = self._extract_cell_content_from_context(table, current_col, in_header=False)
                        if not cell_content or cell_content.startswith('Data_'):
                            # Fallback to intelligent data naming
                            cell_content = self._generate_intelligent_data_name(current_col, current_row, rows)
                    
                    current_row.append(cell_content)
                    current_col += 1
            
            # Handle the last row if it doesn't end with 'nl'
            if current_row:
                if in_header and not header_found:
                    headers = current_row.copy()
                    header_found = True
                    self.logger.logger.info(f"🔍 OTSL EXTRACTION: Found headers (final): {headers}")
                else:
                    rows.append(current_row.copy())
                    self.logger.logger.info(f"🔍 OTSL EXTRACTION: Added final row {len(rows)}: {current_row[:5]}...")
            
            # **CRITICAL: Since OTSL only gives structure, we need to extract actual content**
            # This is a limitation - we know the table structure but not the content
            # For now, we'll create a basic structure that can be enhanced later
            
            if not headers and max_cols > 0:
                # Generate headers based on column count
                headers = [f"Column_{i+1}" for i in range(max_cols)]
                self.logger.logger.info(f"🔍 OTSL EXTRACTION: Generated headers based on structure: {headers}")
            
            # Normalize all rows to have the same number of columns
            if headers:
                normalized_rows = []
                for row in rows:
                    normalized_row = row[:len(headers)]  # Truncate if too long
                    while len(normalized_row) < len(headers):  # Pad if too short
                        normalized_row.append("")
                    normalized_rows.append(normalized_row)
                rows = normalized_rows
            
            self.logger.logger.info(f"🔍 OTSL EXTRACTION: Final result: {len(headers)} headers, {len(rows)} rows")
            
            # **IMPORTANT: This method provides structure but not content**
            # The actual table content needs to be extracted from the document context
            # This is a known limitation of the OTSL approach
            
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Error extracting from OTSL sequence: {e}")
            return [], []

    def _extract_cell_content_from_context(self, table, col_index: int, in_header: bool = False) -> str:
        """Try to extract real cell content from document context."""
        try:
            # Try to get content from table text if available
            if hasattr(table, 'text') and table.text:
                # Parse the table text to extract cell content
                lines = table.text.strip().split('\n')
                if lines and len(lines) > 0:
                    # Simple heuristic: first line might be headers, rest are data
                    if in_header and len(lines) > 0:
                        # Try to extract header content
                        first_line = lines[0]
                        parts = self._split_table_line(first_line)
                        if col_index < len(parts):
                            return parts[col_index].strip()
                    elif not in_header and len(lines) > 1:
                        # Try to extract data content (use a sample row)
                        sample_line = lines[1] if len(lines) > 1 else lines[0]
                        parts = self._split_table_line(sample_line)
                        if col_index < len(parts):
                            return parts[col_index].strip()
            
            # Try to extract from table attributes
            if hasattr(table, 'num_cols') and hasattr(table, 'num_rows'):
                # This is a structured table, try to extract content
                # For now, return empty to trigger fallback
                return ""
            
            return ""
            
        except Exception as e:
            self.logger.logger.warning(f"Error extracting cell content from context: {e}")
            return ""
    
    def _split_table_line(self, line: str) -> List[str]:
        """Split a table line into columns using common delimiters."""
        # Try different delimiters in order of preference
        for delimiter in ['\t', '|', '  ', ' ']:
            if delimiter in line:
                parts = [part.strip() for part in line.split(delimiter) if part.strip()]
                if len(parts) > 1:  # Only use if we get multiple parts
                    return parts
        
        # If no delimiter works, return the whole line as one part
        return [line.strip()] if line.strip() else []
    
    def _generate_intelligent_header_name(self, col_index: int, existing_headers: List[str], existing_rows: List[List[str]]) -> str:
        """Generate intelligent header names based on context - NO HARDCODED PATTERNS."""
        # **CRITICAL FIX: Remove hardcoded headers to prevent incorrect extraction**
        # Instead, use generic naming that forces the system to extract real headers
        return f"Column_{col_index + 1}"
    
    def _generate_intelligent_data_name(self, col_index: int, current_row: List[str], existing_rows: List[List[str]]) -> str:
        """Generate intelligent data names based on context."""
        # For data cells, we'll use empty string as placeholder
        # The real data should come from document context
        return ""

    def _extract_from_document_context(self, table, expected_headers: List[str]) -> Tuple[List[str], List[List[str]]]:
        """Extract table data from document context when Docling cells are empty."""
        try:
            self.logger.logger.info(f"🔍 Extracting from document context - looking for actual table structure")
            
            # Try to get the document's raw text content
            document_text = ""
            if hasattr(table, 'text') and table.text:
                document_text = table.text
            elif hasattr(table, 'content') and table.content:
                document_text = table.content
            elif hasattr(table, 'raw_text') and table.raw_text:
                document_text = table.raw_text
            
            if not document_text:
                self.logger.logger.warning("No document text available for context extraction")
                return [], []
            
            # Parse the text to find table-like structures
            lines = document_text.strip().split('\n')
            
            # **IMPROVED: Look for actual table headers in the document**
            # Instead of looking for expected headers, find the actual headers
            actual_headers = []
            header_line_idx = -1
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Look for lines that contain multiple words separated by spaces/tabs
                # This is typical of table headers
                words = line.split()
                if len(words) >= 3:  # Commission tables typically have many columns
                    # Check if this looks like a header row (contains common header words)
                    header_indicators = 0
                    for word in words:
                        word_lower = word.lower()
                        if any(indicator in word_lower for indicator in [
                            'group', 'name', 'date', 'plan', 'rate', 'lives', 'premium', 
                            'commission', 'paid', 'billed', 'received', 'due', 'effective'
                        ]):
                            header_indicators += 1
                    
                    # If we found several header indicators, this is likely the header row
                    if header_indicators >= 2:
                        actual_headers = words
                        header_line_idx = i
                        self.logger.logger.info(f"🔍 Found potential header row at line {i}: {actual_headers}")
                        break
            
            if header_line_idx == -1 or not actual_headers:
                self.logger.logger.warning("Could not find actual header line in document context")
                return [], []
            
            # Extract data rows after the header line
            data_rows = []
            for i in range(header_line_idx + 1, len(lines)):
                line = lines[i].strip()
                if not line:
                    continue
                
                # Skip lines that look like headers or summaries
                if any(keyword in line.lower() for keyword in ['total', 'summary', 'continued', 'page']):
                    continue
                
                # Try to split the line into columns
                # Look for common delimiters
                columns = []
                if '\t' in line:
                    columns = line.split('\t')
                elif '  ' in line:  # Multiple spaces
                    columns = [col.strip() for col in line.split('  ') if col.strip()]
                else:
                    # Try to split by single spaces, but be more careful
                    parts = line.split(' ')
                    if len(parts) >= len(actual_headers) * 0.5:  # At least half the actual columns
                        columns = parts
                
                if len(columns) >= len(actual_headers) * 0.5:  # At least half the actual columns
                    # Pad or truncate to match actual header count
                    while len(columns) < len(actual_headers):
                        columns.append('')
                    columns = columns[:len(actual_headers)]
                    data_rows.append(columns)
            
            self.logger.logger.info(f"🔍 Extracted {len(data_rows)} rows from document context")
            if data_rows:
                self.logger.logger.info(f"🔍 Sample row: {data_rows[0][:5]}")
            
            return actual_headers, data_rows
            
        except Exception as e:
            self.logger.logger.error(f"Document context extraction failed: {e}")
            return expected_headers, []

    def _extract_from_structured_patterns(self, lines: List[str]) -> Tuple[List[str], List[List[str]]]:
        """Extract table data from structured text patterns."""
        try:
            headers = []
            rows = []
            
            # Look for patterns that suggest table structure
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line looks like it has multiple data elements
                # Commission statements often have patterns like: "Q38436 PRESTON PRODUCTIONS BASE 05/01/2025 MEDHMO"
                if len(line.split()) >= 5:  # At least 5 space-separated elements
                    # Try to split and see if it looks like table data
                    elements = line.split()
                    
                    # Look for patterns that suggest this is data (not headers)
                    if any(char.isdigit() for char in line) and any(char.isalpha() for char in line):
                        # This looks like data - try to parse it
                        if not headers:
                            # First data row - try to infer headers
                            headers = [f"Column_{j+1}" for j in range(len(elements))]
                            self.logger.logger.info(f"🔍 PATTERN EXTRACTION: Inferred headers: {headers}")
                        
                        rows.append(elements)
                        self.logger.logger.info(f"🔍 PATTERN EXTRACTION: Added row {len(rows)}: {elements[:5]}...")
            
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Error in pattern-based extraction: {e}")
            return [], []

    def _extract_from_table_text(self, text: str) -> Tuple[List[str], List[List[str]]]:
        """Extract table data directly from table text content."""
        try:
            self.logger.logger.info(f"🔍 TEXT EXTRACTION: Starting text-based extraction")
            
            lines = text.strip().split('\n')
            headers = []
            rows = []
            
            # Look for the header row first
            header_line_idx = -1
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line looks like headers
                words = line.split()
                if len(words) >= 3:
                    # Count header indicators
                    header_indicators = 0
                    for word in words:
                        word_lower = word.lower()
                        if any(indicator in word_lower for indicator in [
                            'group', 'name', 'date', 'plan', 'rate', 'lives', 'premium', 
                            'commission', 'paid', 'billed', 'received', 'due', 'effective'
                        ]):
                            header_indicators += 1
                    
                    if header_indicators >= 2:
                        headers = words
                        header_line_idx = i
                        self.logger.logger.info(f"🔍 TEXT EXTRACTION: Found headers at line {i}: {headers}")
                        break
            
            if header_line_idx == -1:
                self.logger.logger.warning("🔍 TEXT EXTRACTION: No header row found")
                return [], []
            
            # Extract data rows
            for i in range(header_line_idx + 1, len(lines)):
                line = lines[i].strip()
                if not line:
                    continue
                
                # Skip summary lines
                if any(keyword in line.lower() for keyword in ['total', 'summary', 'continued', 'page']):
                    continue
                
                # Try to split the line into columns
                words = line.split()
                if len(words) >= len(headers) * 0.5:  # At least half the expected columns
                    # Pad or truncate to match header count
                    while len(words) < len(headers):
                        words.append('')
                    words = words[:len(headers)]
                    rows.append(words)
            
            self.logger.logger.info(f"🔍 TEXT EXTRACTION: Extracted {len(rows)} rows")
            return headers, rows
            
        except Exception as e:
            self.logger.logger.error(f"Text extraction failed: {e}")
            return [], []
