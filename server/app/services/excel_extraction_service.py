"""
Excel Extraction Service - Robust Excel file processing with multi-sheet support
This service can handle Excel files with multiple sheets and dynamically find tables
across all sheets, returning results in the same format as other extraction pipelines.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
import json
from datetime import datetime
import uuid
import re
from dataclasses import dataclass, field
import warnings

# Suppress pandas warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pandas')

logger = logging.getLogger(__name__)

@dataclass
class ExcelTableInfo:
    """Information about a table found in Excel."""
    sheet_name: str
    start_row: int
    end_row: int
    start_col: int
    end_col: int
    headers: List[str]
    data: List[List[Any]]
    confidence: float
    table_type: str  # 'structured', 'unstructured', 'mixed'
    quality_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExcelExtractionResult:
    """Result of Excel extraction."""
    tables: List[ExcelTableInfo]
    total_sheets: int
    sheets_with_tables: int
    processing_time: float
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ExcelExtractionService:
    """
    Advanced Excel extraction service that can handle multiple sheets
    and dynamically find tables across all sheets.
    """
    
    def __init__(self, company_id: str = None):
        """Initialize the Excel extraction service."""
        self.logger = logging.getLogger(__name__)
        self.company_id = company_id
        
        # Table detection parameters
        self.min_table_size = (2, 2)  # Minimum rows, columns
        self.max_table_size = (1000, 50)  # Maximum rows, columns
        self.min_data_density = 0.3  # Minimum percentage of non-empty cells
        self.header_confidence_threshold = 0.7
        self.table_confidence_threshold = 0.5
        
        # Common table indicators
        self.table_indicators = [
            'total', 'subtotal', 'sum', 'amount', 'commission', 'earnings',
            'revenue', 'sales', 'profit', 'loss', 'income', 'expense',
            'premium', 'policy', 'claim', 'benefit', 'coverage'
        ]
        
        # Financial column patterns
        self.financial_patterns = [
            r'\$[\d,]+\.?\d*',  # Currency
            r'[\d,]+\.?\d*%',   # Percentages
            r'[\d,]+\.?\d*',    # Numbers
        ]
    
    def extract_tables_from_excel(
        self, 
        file_path: str,
        sheet_names: Optional[List[str]] = None,
        max_tables_per_sheet: int = 10,
        enable_quality_checks: bool = True
    ) -> ExcelExtractionResult:
        """
        Extract tables from Excel file with multi-sheet support.
        
        Args:
            file_path: Path to the Excel file
            sheet_names: Specific sheet names to process (None for all)
            max_tables_per_sheet: Maximum tables to extract per sheet
            enable_quality_checks: Whether to perform quality assessment
            
        Returns:
            ExcelExtractionResult with all found tables
        """
        start_time = datetime.now()
        self.logger.info(f"Starting Excel extraction from: {file_path}")
        
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            all_sheets = excel_file.sheet_names
            
            if sheet_names:
                sheets_to_process = [s for s in sheet_names if s in all_sheets]
                if not sheets_to_process:
                    raise ValueError(f"None of the specified sheets found: {sheet_names}")
            else:
                sheets_to_process = all_sheets
            
            self.logger.info(f"Processing {len(sheets_to_process)} sheets: {sheets_to_process}")
            
            all_tables = []
            sheets_with_tables = 0
            warnings = []
            errors = []
            
            for sheet_name in sheets_to_process:
                try:
                    self.logger.info(f"Processing sheet: {sheet_name}")
                    sheet_tables = self._extract_tables_from_sheet(
                        excel_file, 
                        sheet_name, 
                        max_tables_per_sheet,
                        enable_quality_checks
                    )
                    
                    if sheet_tables:
                        all_tables.extend(sheet_tables)
                        sheets_with_tables += 1
                        self.logger.info(f"Found {len(sheet_tables)} tables in sheet: {sheet_name}")
                    else:
                        self.logger.info(f"No tables found in sheet: {sheet_name}")
                        
                except Exception as e:
                    error_msg = f"Error processing sheet {sheet_name}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
                    warnings.append(f"Skipped sheet {sheet_name} due to error")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create metadata
            metadata = {
                "file_path": file_path,
                "total_sheets": len(all_sheets),
                "processed_sheets": len(sheets_to_process),
                "extraction_timestamp": datetime.now().isoformat(),
                "service_version": "1.0.0"
            }
            
            result = ExcelExtractionResult(
                tables=all_tables,
                total_sheets=len(all_sheets),
                sheets_with_tables=sheets_with_tables,
                processing_time=processing_time,
                warnings=warnings,
                errors=errors,
                metadata=metadata
            )
            
            self.logger.info(f"Excel extraction completed. Found {len(all_tables)} tables across {sheets_with_tables} sheets.")
            return result
            
        except Exception as e:
            error_msg = f"Excel extraction failed: {str(e)}"
            self.logger.error(error_msg)
            return ExcelExtractionResult(
                tables=[],
                total_sheets=0,
                sheets_with_tables=0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                errors=[error_msg]
            )
    
    def _extract_tables_from_sheet(
        self, 
        excel_file: pd.ExcelFile, 
        sheet_name: str,
        max_tables_per_sheet: int,
        enable_quality_checks: bool
    ) -> List[ExcelTableInfo]:
        """
        Extract tables from a specific sheet.
        
        Args:
            excel_file: Pandas ExcelFile object
            sheet_name: Name of the sheet to process
            max_tables_per_sheet: Maximum tables to extract
            enable_quality_checks: Whether to perform quality assessment
            
        Returns:
            List of ExcelTableInfo objects
        """
        try:
            # Read the sheet
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
            
            if df.empty:
                return []
            
            # Find potential table regions
            table_regions = self._find_table_regions(df)
            
            tables = []
            for region in table_regions[:max_tables_per_sheet]:
                table_info = self._extract_table_from_region(
                    df, region, sheet_name, enable_quality_checks
                )
                if table_info and table_info.confidence >= self.table_confidence_threshold:
                    tables.append(table_info)
            
            # Sort tables by confidence and quality
            tables.sort(key=lambda x: (x.confidence, x.quality_score), reverse=True)
            
            return tables
            
        except Exception as e:
            self.logger.error(f"Error extracting tables from sheet {sheet_name}: {str(e)}")
            return []
    
    def _find_table_regions(self, df: pd.DataFrame) -> List[Tuple[int, int, int, int]]:
        """
        Find potential table regions in the dataframe.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            List of (start_row, end_row, start_col, end_col) tuples
        """
        regions = []
        rows, cols = df.shape
        
        # Strategy 1: Look for structured tables with headers
        structured_regions = self._find_structured_tables(df)
        regions.extend(structured_regions)
        
        # Strategy 2: Look for data clusters
        data_regions = self._find_data_clusters(df)
        regions.extend(data_regions)
        
        # Strategy 3: Look for financial data patterns
        financial_regions = self._find_financial_data_regions(df)
        regions.extend(financial_regions)
        
        # Remove overlapping regions and keep the best ones
        regions = self._filter_overlapping_regions(regions)
        
        return regions
    
    def _find_structured_tables(self, df: pd.DataFrame) -> List[Tuple[int, int, int, int]]:
        """Find structured tables with clear headers and data."""
        regions = []
        rows, cols = df.shape
        
        # Look for rows that could be headers
        for start_row in range(rows - 1):
            header_confidence = self._assess_header_confidence(df.iloc[start_row])
            
            if header_confidence > self.header_confidence_threshold:
                # Find the end of this table
                end_row = self._find_table_end(df, start_row)
                
                if end_row > start_row + 1:  # At least 2 rows including header
                    # Find column boundaries
                    start_col, end_col = self._find_column_boundaries(df, start_row, end_row)
                    
                    if end_col > start_col:
                        regions.append((start_row, end_row, start_col, end_col))
        
        return regions
    
    def _find_data_clusters(self, df: pd.DataFrame) -> List[Tuple[int, int, int, int]]:
        """Find regions with high data density."""
        regions = []
        rows, cols = df.shape
        
        # Use sliding window approach
        window_size = 5
        
        for start_row in range(0, rows - window_size + 1):
            for start_col in range(0, cols - 2):
                # Check data density in this region
                region_data = df.iloc[start_row:start_row + window_size, start_col:start_col + 3]
                density = self._calculate_data_density(region_data)
                
                if density > self.min_data_density:
                    # Expand the region
                    end_row, end_col = self._expand_data_region(df, start_row, start_col)
                    
                    if end_row > start_row and end_col > start_col:
                        regions.append((start_row, end_row, start_col, end_col))
        
        return regions
    
    def _find_financial_data_regions(self, df: pd.DataFrame) -> List[Tuple[int, int, int, int]]:
        """Find regions containing financial data patterns."""
        regions = []
        rows, cols = df.shape
        
        # Look for rows with financial patterns
        financial_rows = []
        for row_idx in range(rows):
            row_data = df.iloc[row_idx].astype(str)
            financial_count = 0
            
            for cell in row_data:
                for pattern in self.financial_patterns:
                    if re.search(pattern, str(cell), re.IGNORECASE):
                        financial_count += 1
                        break
            
            if financial_count >= 2:  # At least 2 financial values
                financial_rows.append(row_idx)
        
        # Group consecutive financial rows
        if financial_rows:
            start_row = financial_rows[0]
            end_row = financial_rows[-1]
            
            # Find column boundaries
            start_col, end_col = self._find_financial_column_boundaries(df, start_row, end_row)
            
            if end_col > start_col:
                regions.append((start_row, end_row, start_col, end_col))
        
        return regions
    
    def _assess_header_confidence(self, header_row: pd.Series) -> float:
        """Assess how likely a row is to be a header."""
        confidence = 0.0
        
        # Check for non-numeric values
        non_numeric_count = 0
        for cell in header_row:
            if pd.notna(cell) and not self._is_numeric(cell):
                non_numeric_count += 1
        
        if len(header_row) > 0:
            confidence += (non_numeric_count / len(header_row)) * 0.4
        
        # Check for table indicators
        header_text = ' '.join(str(cell) for cell in header_row if pd.notna(cell)).lower()
        indicator_count = sum(1 for indicator in self.table_indicators if indicator in header_text)
        confidence += min(indicator_count * 0.2, 0.4)
        
        # Check for consistent formatting
        if len(header_row) >= 2:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _find_best_headers(self, table_df: pd.DataFrame, company_id: str = None) -> Tuple[List[str], int, str]:
        """
        Find the best header row by examining multiple rows and looking for patterns.
        If no good headers are found, check for learned headers as fallback.
        Returns (headers, data_start_row, table_type)
        """
        rows, cols = table_df.shape
        best_headers = None
        best_confidence = 0.0
        best_row_idx = 0
        
        # Look at the first few rows to find the best header
        max_header_search_rows = min(5, rows)  # Don't search more than 5 rows
        
        for row_idx in range(max_header_search_rows):
            row = table_df.iloc[row_idx]
            confidence = self._assess_header_confidence(row)
            
            # Additional checks for financial table headers
            if confidence > 0.3:  # Lower threshold for initial screening
                # Check if this row looks like financial table headers
                row_text = ' '.join(str(cell) for cell in row if pd.notna(cell)).lower()
                financial_indicators = [
                    'prem', 'group', 'agent', 'plan', 'tier', 'lives', 'rate', 'total',
                    'commission', 'invoice', 'billed', 'amount', 'client', 'company'
                ]
                
                financial_score = sum(1 for indicator in financial_indicators if indicator in row_text)
                if financial_score >= 3:  # At least 3 financial indicators
                    confidence += 0.3
                
                # Check for proper header structure (not all empty, not all same value)
                non_empty_cells = [str(cell).strip() for cell in row if pd.notna(cell) and str(cell).strip()]
                if len(non_empty_cells) >= 3 and len(set(non_empty_cells)) > 1:
                    confidence += 0.2
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_row_idx = row_idx
                
                # Create headers from this row
                headers = []
                for i, cell in enumerate(row):
                    if pd.notna(cell) and str(cell).strip():
                        headers.append(str(cell).strip())
                    else:
                        headers.append(f"Column_{i+1}")
                best_headers = headers
        
        # If we found good headers, use them
        if best_headers and best_confidence > 0.4:  # Good headers found in current file
            return best_headers, best_row_idx + 1, "structured"
        else:
            # No good headers found in current file - check for learned headers
            if company_id:
                learned_headers = self._get_learned_headers(table_df, company_id)
                if learned_headers:
                    self.logger.info(f"🎯 Excel: No good headers found in current file, using learned headers: {learned_headers}")
                    return learned_headers, 0, "learned"
            
            # Fallback to generic headers
            headers = [f"Column_{i+1}" for i in range(cols)]
            return headers, 0, "unstructured"
    
    def _get_learned_headers(self, table_df: pd.DataFrame, company_id: str) -> Optional[List[str]]:
        """
        Get learned headers for this table structure if available.
        Returns None if no learned headers are found or if they don't match.
        """
        try:
            # Analyze the current table structure
            rows, cols = table_df.shape
            table_structure = {
                "column_count": cols,
                "row_count": rows,
                "has_header_row": False  # We're looking for learned headers because current file has poor headers
            }
            
            # Get the first few rows to analyze the data pattern
            sample_headers = []
            for i in range(min(3, rows)):
                row = table_df.iloc[i]
                row_headers = [str(cell).strip() if pd.notna(cell) and str(cell).strip() else f"Column_{j+1}" 
                              for j, cell in enumerate(row)]
                sample_headers.append(row_headers)
            
            # Use the most common pattern as the "current" headers for comparison
            current_headers = sample_headers[0] if sample_headers else [f"Column_{i+1}" for i in range(cols)]
            
            # Import here to avoid circular imports
            from app.services.format_learning_service import FormatLearningService
            format_learning_service = FormatLearningService()
            
            # Find matching format
            learned_format, match_score = format_learning_service.find_matching_format_sync(
                company_id=company_id,
                headers=current_headers,
                table_structure=table_structure
            )
            
            if learned_format and match_score > 0.5:
                learned_headers = learned_format.get('headers', [])
                if learned_headers and len(learned_headers) == cols:
                    self.logger.info(f"🎯 Excel: Found learned headers with {match_score:.2f} match score: {learned_headers}")
                    return learned_headers
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting learned headers: {str(e)}")
            return None
    
    def _find_table_end(self, df: pd.DataFrame, start_row: int) -> int:
        """Find the end row of a table starting from start_row."""
        rows, cols = df.shape
        
        for row_idx in range(start_row + 1, rows):
            # Check if this row has significant data
            row_data = df.iloc[row_idx]
            non_empty_count = sum(1 for cell in row_data if pd.notna(cell) and str(cell).strip())
            
            if non_empty_count == 0:
                return row_idx
            
            # Check if this looks like a new table header
            if self._assess_header_confidence(row_data) > self.header_confidence_threshold:
                return row_idx
        
        return rows
    
    def _find_column_boundaries(self, df: pd.DataFrame, start_row: int, end_row: int) -> Tuple[int, int]:
        """Find the column boundaries for a table region."""
        cols = df.shape[1]
        
        # Find first column with data
        start_col = 0
        for col_idx in range(cols):
            col_data = df.iloc[start_row:end_row, col_idx]
            if any(pd.notna(cell) and str(cell).strip() for cell in col_data):
                start_col = col_idx
                break
        
        # Find last column with data
        end_col = start_col
        for col_idx in range(cols - 1, start_col - 1, -1):
            col_data = df.iloc[start_row:end_row, col_idx]
            if any(pd.notna(cell) and str(cell).strip() for cell in col_data):
                end_col = col_idx + 1
                break
        
        return start_col, end_col
    
    def _calculate_data_density(self, region: pd.DataFrame) -> float:
        """Calculate the density of non-empty cells in a region."""
        if region.empty:
            return 0.0
        
        total_cells = region.size
        non_empty_cells = sum(1 for cell in region.values.flatten() 
                            if pd.notna(cell) and str(cell).strip())
        
        return non_empty_cells / total_cells if total_cells > 0 else 0.0
    
    def _expand_data_region(self, df: pd.DataFrame, start_row: int, start_col: int) -> Tuple[int, int]:
        """Expand a data region to include all connected data."""
        rows, cols = df.shape
        
        # Expand down
        end_row = start_row
        for row_idx in range(start_row, rows):
            row_data = df.iloc[row_idx, start_col:start_col + 3]
            if self._calculate_data_density(row_data) > 0.1:
                end_row = row_idx + 1
            else:
                break
        
        # Expand right
        end_col = start_col
        for col_idx in range(start_col, cols):
            col_data = df.iloc[start_row:end_row, col_idx]
            if self._calculate_data_density(col_data) > 0.1:
                end_col = col_idx + 1
            else:
                break
        
        return end_row, end_col
    
    def _find_financial_column_boundaries(self, df: pd.DataFrame, start_row: int, end_row: int) -> Tuple[int, int]:
        """Find column boundaries for financial data."""
        cols = df.shape[1]
        
        # Find columns with financial data
        financial_cols = []
        for col_idx in range(cols):
            col_data = df.iloc[start_row:end_row, col_idx].astype(str)
            financial_count = 0
            
            for cell in col_data:
                for pattern in self.financial_patterns:
                    if re.search(pattern, str(cell), re.IGNORECASE):
                        financial_count += 1
                        break
            
            if financial_count > 0:
                financial_cols.append(col_idx)
        
        if financial_cols:
            return min(financial_cols), max(financial_cols) + 1
        else:
            return 0, cols
    
    def _filter_overlapping_regions(self, regions: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Filter out overlapping regions, keeping the best ones."""
        if not regions:
            return []
        
        # Sort by size (larger regions first)
        regions.sort(key=lambda x: (x[1] - x[0]) * (x[3] - x[2]), reverse=True)
        
        filtered_regions = []
        for region in regions:
            is_overlapping = False
            for existing_region in filtered_regions:
                if self._regions_overlap(region, existing_region):
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                filtered_regions.append(region)
        
        return filtered_regions
    
    def _regions_overlap(self, region1: Tuple[int, int, int, int], region2: Tuple[int, int, int, int]) -> bool:
        """Check if two regions overlap significantly."""
        start_row1, end_row1, start_col1, end_col1 = region1
        start_row2, end_row2, start_col2, end_col2 = region2
        
        # Check for overlap
        row_overlap = max(0, min(end_row1, end_row2) - max(start_row1, start_row2))
        col_overlap = max(0, min(end_col1, end_col2) - max(start_col1, start_col2))
        
        if row_overlap <= 0 or col_overlap <= 0:
            return False
        
        # Calculate overlap percentage
        area1 = (end_row1 - start_row1) * (end_col1 - start_col1)
        area2 = (end_row2 - start_row2) * (end_col2 - start_col2)
        overlap_area = row_overlap * col_overlap
        
        overlap_percentage = overlap_area / min(area1, area2)
        return overlap_percentage > 0.5  # More than 50% overlap
    
    def _extract_table_from_region(
        self, 
        df: pd.DataFrame, 
        region: Tuple[int, int, int, int],
        sheet_name: str,
        enable_quality_checks: bool
    ) -> Optional[ExcelTableInfo]:
        """Extract table information from a specific region."""
        start_row, end_row, start_col, end_col = region
        
        try:
            # Extract the table data
            table_df = df.iloc[start_row:end_row, start_col:end_col].copy()
            
            # Smart header detection - look for headers in multiple rows
            headers, data_start_row, table_type = self._find_best_headers(table_df, company_id=self.company_id)
            
            # Extract data rows starting from the detected header row
            data_rows = table_df.iloc[data_start_row:].values.tolist()
            
            # Clean data
            cleaned_data = []
            for row in data_rows:
                cleaned_row = []
                for cell in row:
                    if pd.isna(cell):
                        cleaned_row.append("")
                    else:
                        cleaned_row.append(str(cell).strip())
                cleaned_data.append(cleaned_row)
            
            # Calculate confidence and quality scores
            confidence = self._calculate_table_confidence(table_df, headers, cleaned_data)
            quality_score = self._calculate_quality_score(table_df, headers, cleaned_data) if enable_quality_checks else 1.0
            
            # Create metadata
            metadata = {
                "table_type": table_type,
                "has_headers": table_type == "structured",
                "data_density": self._calculate_data_density(table_df),
                "financial_data_present": self._has_financial_data(cleaned_data),
                "row_count": len(cleaned_data),
                "column_count": len(headers)
            }
            
            return ExcelTableInfo(
                sheet_name=sheet_name,
                start_row=start_row,
                end_row=end_row,
                start_col=start_col,
                end_col=end_col,
                headers=headers,
                data=cleaned_data,
                confidence=confidence,
                table_type=table_type,
                quality_score=quality_score,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting table from region {region}: {str(e)}")
            return None
    
    def _calculate_table_confidence(self, df: pd.DataFrame, headers: List[str], data: List[List[str]]) -> float:
        """Calculate confidence score for the extracted table."""
        confidence = 0.0
        
        # Data density
        density = self._calculate_data_density(df)
        confidence += density * 0.3
        
        # Header quality
        if headers and any(h.strip() for h in headers):
            confidence += 0.2
        
        # Data consistency
        if data:
            row_lengths = [len(row) for row in data]
            if len(set(row_lengths)) <= 1:  # Consistent row lengths
                confidence += 0.2
        
        # Financial data presence
        if self._has_financial_data(data):
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _calculate_quality_score(self, df: pd.DataFrame, headers: List[str], data: List[List[str]]) -> float:
        """Calculate quality score for the extracted table."""
        quality = 0.0
        
        # Data completeness
        if data:
            total_cells = len(data) * len(headers)
            non_empty_cells = sum(1 for row in data for cell in row if cell.strip())
            completeness = non_empty_cells / total_cells if total_cells > 0 else 0
            quality += completeness * 0.4
        
        # Structure quality
        if headers and data:
            consistent_rows = sum(1 for row in data if len(row) == len(headers))
            structure_quality = consistent_rows / len(data) if data else 0
            quality += structure_quality * 0.3
        
        # Data quality indicators
        if self._has_financial_data(data):
            quality += 0.3
        
        return min(quality, 1.0)
    
    def _has_financial_data(self, data: List[List[str]]) -> bool:
        """Check if the data contains financial information."""
        for row in data:
            for cell in row:
                for pattern in self.financial_patterns:
                    if re.search(pattern, str(cell), re.IGNORECASE):
                        return True
        return False
    
    def _is_numeric(self, value: Any) -> bool:
        """Check if a value is numeric."""
        try:
            float(str(value))
            return True
        except (ValueError, TypeError):
            return False
    
    def convert_to_client_format(self, result: ExcelExtractionResult, filename: str) -> Dict[str, Any]:
        """
        Convert Excel extraction result to the client-expected format.
        
        Args:
            result: ExcelExtractionResult object
            filename: Original filename
            
        Returns:
            Dictionary in the format expected by the client
        """
        try:
            # Transform tables to frontend format
            frontend_tables = []
            all_headers = []
            all_table_data = []
            total_cells = 0
            total_rows = 0
            
            for i, table_info in enumerate(result.tables):
                # Create frontend table format
                frontend_table = {
                    "header": table_info.headers,
                    "rows": table_info.data,
                    "name": f"Table {i+1} - {table_info.sheet_name}",
                    "id": str(uuid.uuid4()),
                    "extractor": "excel_extraction",
                    "metadata": {
                        "extraction_method": "excel",
                        "confidence": table_info.confidence,
                        "quality_score": table_info.quality_score,
                        "sheet_name": table_info.sheet_name,
                        "table_type": table_info.table_type,
                        "row_count": len(table_info.data),
                        "column_count": len(table_info.headers),
                        "quality_metrics": {
                            "overall_score": table_info.quality_score,
                            "completeness": table_info.metadata.get("data_density", 0.0),
                            "consistency": 1.0 if table_info.data else 0.0,
                            "accuracy": table_info.confidence,
                            "structure_quality": 1.0 if table_info.table_type == "structured" else 0.7,
                            "data_quality": table_info.quality_score,
                            "confidence_level": "high" if table_info.confidence > 0.8 else "medium",
                            "is_valid": table_info.confidence > self.table_confidence_threshold
                        },
                        "validation_warnings": [],
                        "financial_metadata": {
                            "has_financial_data": table_info.metadata.get("financial_data_present", False)
                        }
                    }
                }
                
                frontend_tables.append(frontend_table)
                all_headers.extend(table_info.headers)
                all_table_data.extend(table_info.data)
                total_cells += len(table_info.headers) * len(table_info.data)
                total_rows += len(table_info.data)
            
            # Calculate overall confidence
            overall_confidence = np.mean([t.confidence for t in result.tables]) if result.tables else 0.0
            
            # Create response in the same format as other extraction pipelines
            response = {
                "status": "success",
                "success": True,
                "message": f"Successfully extracted {len(result.tables)} tables from Excel file",
                "job_id": str(uuid.uuid4()),
                "file_name": filename,
                "tables": frontend_tables,
                "table_headers": all_headers,
                "table_data": all_table_data,
                "processing_time_seconds": result.processing_time,
                "extraction_time_seconds": result.processing_time,
                "extraction_metrics": {
                    "total_text_elements": total_cells,
                    "extraction_time": result.processing_time,
                    "table_confidence": overall_confidence,
                    "model_used": "excel_extraction"
                },
                "document_info": {
                    "file_type": "excel",
                    "total_tables": len(result.tables),
                    "total_sheets": result.total_sheets,
                    "sheets_with_tables": result.sheets_with_tables
                },
                "quality_summary": {
                    "total_tables": len(result.tables),
                    "valid_tables": len([t for t in result.tables if t.confidence > self.table_confidence_threshold]),
                    "average_quality_score": np.mean([t.quality_score for t in result.tables]) if result.tables else 0.0,
                    "overall_confidence": "HIGH" if overall_confidence > 0.8 else "MEDIUM" if overall_confidence > 0.5 else "LOW",
                    "issues_found": result.warnings,
                    "recommendations": [
                        f"Extracted {len(result.tables)} tables from {result.sheets_with_tables} sheets",
                        "Excel extraction completed successfully"
                    ]
                },
                "quality_metrics": {
                    "table_confidence": overall_confidence,
                    "text_elements_extracted": total_cells,
                    "table_rows_extracted": total_rows,
                    "extraction_completeness": "complete" if total_rows > 0 else "none",
                    "data_quality": "good" if overall_confidence > 0.7 else "medium"
                },
                "warnings": result.warnings,
                "errors": result.errors,
                "metadata": result.metadata,
                "timestamp": datetime.now().isoformat()
            }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error converting to client format: {str(e)}")
            return {
                "status": "error",
                "success": False,
                "error": f"Failed to convert Excel extraction result: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

# Global instance
excel_extraction_service = ExcelExtractionService()

def get_excel_extraction_service() -> ExcelExtractionService:
    """Get the global Excel extraction service instance."""
    return excel_extraction_service
