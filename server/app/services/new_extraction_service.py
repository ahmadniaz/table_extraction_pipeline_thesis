"""
New Extraction Service - Integration of the new working solution
This service provides a unified interface to the new extraction pipeline
while maintaining compatibility with the existing server structure.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import tempfile
import os
from datetime import datetime
from app.new_extraction_services.utils.compatibility import apply_compatibility_fixes

# Apply compatibility fixes
apply_compatibility_fixes()


# Import the new extraction solution
from app.new_extraction_services.utils.config import get_config
from app.new_extraction_services.utils.logging_utils import setup_logging, get_logger
from app.new_extraction_services.pipeline.extraction_pipeline import ExtractionPipeline, ExtractionOptions
from app.new_extraction_services.core.document_processor import DocumentProcessor
from app.new_extraction_services.models.advanced_tableformer import ProductionTableFormer
from app.new_extraction_services.models.advanced_ocr_engine import AdvancedOCREngine
from app.services.company_name_service import CompanyNameDetectionService


class NewExtractionService:
    """
    New extraction service that uses the advanced extraction pipeline.
    This service replaces the Docling-based extraction while maintaining
    the same interface for the existing server.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the new extraction service."""
        self.config = get_config(config_path)
        setup_logging(self.config)
        self.logger = get_logger(__name__, self.config)
        
        # Initialize the extraction pipeline
        self.pipeline = ExtractionPipeline(self.config)
        
        # Initialize document processor
        self.document_processor = DocumentProcessor(self.config)
        
        # Initialize models
        self.table_detector = ProductionTableFormer(self.config)
        self.ocr_engine = AdvancedOCREngine(self.config)
        
        # Initialize company name detection service for cleaning
        self.company_detector = CompanyNameDetectionService()
        
        self.logger.logger.info("New Extraction Service initialized successfully")
    
    async def extract_tables_from_file(
        self, 
        file_path: str, 
        file_type: str = "pdf",
        confidence_threshold: float = 0.5,
        enable_ocr: bool = True,
        enable_multipage: bool = True,
        max_tables_per_page: int = 10,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Extract tables from a file using the new extraction pipeline.
        
        Args:
            file_path: Path to the file to process
            file_type: Type of file (pdf, image, etc.)
            confidence_threshold: Minimum confidence for table detection
            enable_ocr: Whether to enable OCR processing
            enable_multipage: Whether to process all pages
            max_tables_per_page: Maximum number of tables per page
            output_format: Output format (json, csv, xlsx)
            
        Returns:
            Dictionary containing extraction results
        """
        try:
            self.logger.logger.info(f"Starting extraction for file: {file_path}")
            
            # Create extraction options
            extraction_options = ExtractionOptions(
                enable_ocr=enable_ocr,
                enable_multipage=enable_multipage,
                confidence_threshold=confidence_threshold,
                max_tables_per_page=max_tables_per_page,
                output_format=output_format,
                enable_quality_checks=True
            )
            
            # Extract tables using the new pipeline
            result = await self.pipeline.extract_tables(file_path, extraction_options)
            
            # Convert result to the expected format
            extraction_result = self._convert_result_to_dict(result)
            
            # **NEW: Apply systematic OCR correction to all extracted data**
            extraction_result = self._apply_ocr_corrections(extraction_result)
            
            self.logger.logger.info(f"Extraction completed successfully. Found {len(result.tables)} tables.")
            
            return extraction_result
            
        except Exception as e:
            self.logger.logger.error(f"Extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tables": [],
                "processing_time": 0,
                "confidence_scores": {"overall": 0.0}
            }
    
    def _apply_ocr_corrections(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply systematic OCR corrections to all extracted data.
        Fixes common OCR errors like O/0 substitution throughout the pipeline.
        
        Args:
            extraction_result: The extraction result dictionary
            
        Returns:
            Extraction result with OCR corrections applied
        """
        try:
            if not extraction_result or not extraction_result.get("tables"):
                return extraction_result
            
            corrected_tables = []
            total_corrections = 0
            
            for table in extraction_result["tables"]:
                corrected_table = self._correct_table_ocr_errors(table)
                corrected_tables.append(corrected_table)
                
                # Count corrections made
                corrections = self._count_ocr_corrections(table, corrected_table)
                total_corrections += corrections
            
            # Update the result with corrected tables
            extraction_result["tables"] = corrected_tables
            
            # Add OCR correction metadata
            extraction_result["ocr_corrections"] = {
                "total_corrections_applied": total_corrections,
                "correction_timestamp": datetime.now().isoformat(),
                "correction_method": "systematic_pipeline_correction"
            }
            
            if total_corrections > 0:
                self.logger.logger.info(f"🔧 Applied {total_corrections} OCR corrections to extracted data")
            
            return extraction_result
            
        except Exception as e:
            self.logger.logger.error(f"Error applying OCR corrections: {e}")
            return extraction_result
    
    def _correct_table_ocr_errors(self, table: Dict[str, Any]) -> Dict[str, Any]:
        """Correct OCR errors in a single table."""
        try:
            corrected_table = table.copy()
            
            # Correct headers
            if "header" in corrected_table and corrected_table["header"]:
                corrected_table["header"] = [self._fix_ocr_errors(header) for header in corrected_table["header"]]
            
            # Correct rows
            if "rows" in corrected_table and corrected_table["rows"]:
                corrected_rows = []
                for row in corrected_table["rows"]:
                    corrected_row = [self._fix_ocr_errors(cell) for cell in row]
                    corrected_rows.append(corrected_row)
                corrected_table["rows"] = corrected_rows
            
            # Correct table_data if present
            if "table_data" in corrected_table and corrected_table["table_data"]:
                table_data = corrected_table["table_data"]
                if isinstance(table_data, list):
                    corrected_table_data = []
                    for item in table_data:
                        if isinstance(item, dict):
                            corrected_item = {}
                            for key, value in item.items():
                                if isinstance(value, str):
                                    corrected_item[key] = self._fix_ocr_errors(value)
                                else:
                                    corrected_item[key] = value
                            corrected_table_data.append(corrected_item)
                        else:
                            corrected_table_data.append(item)
                    corrected_table["table_data"] = corrected_table_data
            
            return corrected_table
            
        except Exception as e:
            self.logger.logger.error(f"Error correcting table OCR errors: {e}")
            return table
    
    def _fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors in text."""
        if not text or not isinstance(text, str):
            return text
        
        import re
        original_text = text
        
        # Fix O to 0 in numeric contexts
        # Pattern 1: O between digits (e.g., 2O25 -> 2025)
        text = re.sub(r'(\d)O(\d)', r'\g<1>0\g<2>', text)
        
        # Pattern 2: O after currency symbol (e.g., $O -> $0)
        text = re.sub(r'(\$)O(\d)', r'\g<1>0\g<2>', text)
        
        # Pattern 3: Years like 2O25 -> 2025
        text = re.sub(r'2O2[0-9]', lambda m: m.group().replace('O', '0'), text)
        
        # Pattern 4: O in decimal contexts (e.g., 1O9.O1 -> 109.01)
        text = re.sub(r'(\d)O(\d)\.O(\d)', r'\g<1>0\g<2>.0\g<3>', text)
        
        # Pattern 5: O in percentage contexts (e.g., 2O.O% -> 20.0%)
        text = re.sub(r'(\d)O\.O%', r'\g<1>0.0%', text)
        
        # Pattern 6: O in state codes (e.g., MNOO867 -> MN00867)
        text = re.sub(r'([A-Z]{2})O+(\d+)', r'\g<1>00\g<2>', text)
        
        # Pattern 7: O in standalone numeric contexts
        text = re.sub(r' O(\d) ', r' 0\g<1> ', text)
        
        return text
    
    def _count_ocr_corrections(self, original_table: Dict[str, Any], corrected_table: Dict[str, Any]) -> int:
        """Count the number of OCR corrections made."""
        corrections = 0
        
        # Count header corrections
        if "header" in original_table and "header" in corrected_table:
            for orig, corr in zip(original_table["header"], corrected_table["header"]):
                if orig != corr:
                    corrections += 1
        
        # Count row corrections
        if "rows" in original_table and "rows" in corrected_table:
            for orig_row, corr_row in zip(original_table["rows"], corrected_table["rows"]):
                for orig_cell, corr_cell in zip(orig_row, corr_row):
                    if orig_cell != corr_cell:
                        corrections += 1
        
        return corrections
    
    async def extract_tables_from_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        file_type: str = "pdf",
        confidence_threshold: float = 0.5,
        enable_ocr: bool = True,
        enable_multipage: bool = True,
        max_tables_per_page: int = 10,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Extract tables from file bytes using the new extraction pipeline.
        
        Args:
            file_bytes: File content as bytes
            file_name: Name of the file
            file_type: Type of file (pdf, image, etc.)
            confidence_threshold: Minimum confidence for table detection
            enable_ocr: Whether to enable OCR processing
            enable_multipage: Whether to process all pages
            max_tables_per_page: Maximum number of tables per page
            output_format: Output format (json, csv, xlsx)
            
        Returns:
            Dictionary containing extraction results
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as temp_file:
                temp_file.write(file_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Extract tables from the temporary file
                result = await self.extract_tables_from_file(
                    temp_file_path,
                    file_type,
                    confidence_threshold,
                    enable_ocr,
                    enable_multipage,
                    max_tables_per_page,
                    output_format
                )
                
                return result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            self.logger.logger.error(f"Extraction from bytes failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tables": [],
                "processing_time": 0,
                "confidence_scores": {"overall": 0.0}
            }
    
    def _convert_result_to_dict(self, result) -> Dict[str, Any]:
        """
        Convert the extraction result to a dictionary format compatible
        with the existing server structure.
        
        Args:
            result: Extraction result from the new pipeline
            
        Returns:
            Dictionary representation of the result
        """
        tables = []
        
        for table in result.tables:
            # Debug: Print the actual table structure
            print(f"🔍 DEBUG: Converting table {len(tables)}")
            print(f"  - Table type: {type(table)}")
            print(f"  - Table keys: {list(table.keys()) if isinstance(table, dict) else 'Not a dict'}")
            
            if isinstance(table, dict):
                # Table is already a dictionary
                table_dict = {
                    "id": table.get("id", str(len(tables))),
                    "page_number": table.get("page_number", 1),
                    "bbox": table.get("bbox", [0, 0, 0, 0]),
                    "confidence": table.get("confidence", 0.0),
                    "data": table.get("data", []),
                    "headers": table.get("headers", []),
                    "rows": table.get("rows", []),
                    "table_type": table.get("table_type", "unknown"),
                    "name": table.get("name", f"Table_{len(tables)+1}")
                }
            else:
                # Table is an object, try to access attributes
                table_dict = {
                    "id": getattr(table, 'id', str(len(tables))),
                    "page_number": getattr(table, 'page_number', 1),
                    "bbox": getattr(table, 'bbox', [0, 0, 0, 0]),
                    "confidence": getattr(table, 'confidence', 0.0),
                    "data": getattr(table, 'data', []),
                    "headers": getattr(table, 'headers', []),
                    "rows": getattr(table, 'rows', []),
                    "table_type": getattr(table, 'table_type', "unknown"),
                    "name": getattr(table, 'name', f"Table_{len(tables)+1}")
                }
            
            # Apply company name cleaning to the table data
            cleaned_table = self._apply_company_name_cleaning(table_dict)
            
            # Debug: Print the extracted data
            print(f"  - Headers: {cleaned_table['headers']}")
            print(f"  - Rows count: {len(cleaned_table['rows'])}")
            if cleaned_table['rows']:
                print(f"  - First row: {cleaned_table['rows'][0]}")
            
            tables.append(cleaned_table)
        
        return {
            "success": True,
            "tables": tables,
            "processing_time": getattr(result, 'processing_time', 0),
            "confidence_scores": getattr(result, 'confidence_scores', {"overall": 0.0}),
            "warnings": getattr(result, 'warnings', []),
            "errors": getattr(result, 'errors', []),
            "total_tables": len(tables),
            "extraction_method": "new_advanced_pipeline"
        }
    
    def _apply_company_name_cleaning(self, table_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply company name cleaning to table data.
        
        Args:
            table_dict: Table dictionary with headers and rows
            
        Returns:
            Table dictionary with cleaned company names
        """
        try:
            # Handle both 'header' and 'headers' keys for compatibility
            headers = table_dict.get('headers', []) or table_dict.get('header', [])
            rows = table_dict.get('rows', [])
            
            self.logger.logger.info(f"🧹 Company cleaning: Found {len(headers)} headers: {headers}")
            
            # Find company name columns - be more intelligent about detection
            company_columns = []
            
            # Strategy 1: Look for explicit company-related headers
            for i, header in enumerate(headers):
                header_lower = str(header).lower()
                if any(keyword in header_lower for keyword in ['company', 'client', 'group', 'name']):
                    company_columns.append(i)
                    self.logger.logger.info(f"🧹 Found explicit company column at index {i}: '{header}'")
            
            # Strategy 2: If no explicit company columns found, analyze the first column
            if not company_columns and rows:
                # Check if the first column contains company names with state codes
                first_col_has_state_codes = False
                sample_size = min(5, len(rows))  # Check first 5 rows
                
                for i in range(sample_size):
                    if i < len(rows) and len(rows[i]) > 0:
                        first_cell = str(rows[i][0]).strip()
                        # Check if this looks like a company name with state code
                        if self._looks_like_company_with_state_code(first_cell):
                            first_col_has_state_codes = True
                            break
                
                if first_col_has_state_codes:
                    company_columns.append(0)
                    self.logger.logger.info(f"🧹 Detected company column at index 0 based on content analysis")
            
            if not company_columns:
                # No company columns found, return as is
                self.logger.logger.info("🧹 No company columns found, skipping cleaning")
                return table_dict
            
            # Clean company names in the identified columns
            cleaned_rows = []
            for row in rows:
                cleaned_row = row.copy() if isinstance(row, list) else row
                
                for col_idx in company_columns:
                    if col_idx < len(cleaned_row):
                        original_name = str(cleaned_row[col_idx]).strip()
                        if original_name:
                            # Clean the company name
                            cleaned_name = self.company_detector.clean_company_name(original_name)
                            if cleaned_name != original_name:
                                self.logger.logger.info(f"🧹 Cleaned company name: '{original_name}' → '{cleaned_name}'")
                            cleaned_row[col_idx] = cleaned_name
                
                cleaned_rows.append(cleaned_row)
            
            # Return updated table dictionary
            return {
                **table_dict,
                'rows': cleaned_rows
            }
            
        except Exception as e:
            self.logger.logger.error(f"Error applying company name cleaning: {e}")
            # Return original table if cleaning fails
            return table_dict
    
    def _looks_like_company_with_state_code(self, text: str) -> bool:
        """
        Check if text looks like a company name with state code pattern.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text looks like a company name with state code
        """
        if not text or not isinstance(text, str):
            return False
        
        import re
        
        # Check for state code patterns (2 letters followed by digits)
        state_code_patterns = [
            r'[A-Z]{2}\d{5}',  # VA00598, FL00719, etc.
            r'[A-Z]{2}\d{4}',  # VA0598, FL0719, etc.
            r'[A-Z]{2}\d{3}',  # VA598, FL719, etc.
            r'[A-Z]{2}\d{2}',  # VA98, FL19, etc.
            r'[A-Z]{2}\d{1}',  # VA8, FL9, etc.
            r'[A-Z]{2}O+\d+',  # OCR corrupted: VAO0598, FLOO719, etc.
        ]
        
        # Check if any state code pattern is found
        for pattern in state_code_patterns:
            if re.search(pattern, text):
                # Additional check: make sure there's some company-like text before the state code
                # This helps avoid false positives on pure state codes
                parts = re.split(pattern, text)
                if parts and len(parts[0].strip()) > 2:  # At least 3 characters before state code
                    return True
        
        return False
    
    async def get_extraction_status(self) -> Dict[str, Any]:
        """
        Get the status of the extraction service.
        
        Returns:
            Dictionary containing service status information
        """
        return {
            "service": "new_extraction_service",
            "status": "active",
            "version": "1.0.0",
            "models_loaded": {
                "table_detector": self.table_detector is not None,
                "ocr_engine": self.ocr_engine is not None
            },
            "config": {
                "confidence_threshold": getattr(self.config.processing, 'confidence_threshold', 0.5),
                "enable_ocr": getattr(self.config.processing, 'enable_ocr', True),
                "enable_multipage": getattr(self.config.processing, 'enable_multipage', True)
            }
        }
    
    async def validate_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate if a file can be processed by the extraction service.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Dictionary containing validation results
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    "valid": False,
                    "error": "File does not exist",
                    "supported_formats": ["pdf", "png", "jpg", "jpeg", "tiff", "tif", "docx"]
                }
            
            # Check file extension
            file_ext = Path(file_path).suffix.lower()
            supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.docx'}
            
            if file_ext not in supported_extensions:
                return {
                    "valid": False,
                    "error": f"Unsupported file format: {file_ext}",
                    "supported_formats": list(supported_extensions)
                }
            
            # Check file size (max 50MB)
            file_size = os.path.getsize(file_path)
            max_size = 50 * 1024 * 1024  # 50MB
            
            if file_size > max_size:
                return {
                    "valid": False,
                    "error": f"File too large: {file_size} bytes (max: {max_size} bytes)",
                    "file_size": file_size,
                    "max_size": max_size
                }
            
            return {
                "valid": True,
                "file_size": file_size,
                "file_type": file_ext,
                "supported_formats": list(supported_extensions)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }


# Create a global instance for easy access
_new_extraction_service = None

def get_new_extraction_service(config_path: Optional[str] = None) -> NewExtractionService:
    """
    Get or create a global instance of the new extraction service.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        NewExtractionService instance
    """
    global _new_extraction_service
    
    if _new_extraction_service is None:
        _new_extraction_service = NewExtractionService(config_path)
    
    return _new_extraction_service