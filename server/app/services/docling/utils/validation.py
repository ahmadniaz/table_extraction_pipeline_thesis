"""Data validation utilities for table extraction pipeline."""

from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
from PIL import Image
# import magic  # Optional dependency
import re
from enum import Enum
from dataclasses import dataclass
from loguru import logger


class FileType(Enum):
    """Supported file types."""
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"
    TIFF = "tiff"
    DOCX = "docx"
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class DocumentValidator:
    """Validator for input documents."""
    
    def __init__(self, max_file_size: int = 50 * 1024 * 1024):  # 50MB default
        self.max_file_size = max_file_size
        self.allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.docx'}
        self.mime_types = {
            'application/pdf': FileType.PDF,
            'image/png': FileType.PNG,
            'image/jpeg': FileType.JPEG,
            'image/tiff': FileType.TIFF,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileType.DOCX
        }
    
    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate a document file."""
        file_path = Path(file_path)
        errors = []
        warnings = []
        metadata = {}
        
        # Check if file exists
        if not file_path.exists():
            errors.append(f"File does not exist: {file_path}")
            return ValidationResult(False, errors, warnings, metadata)
        
        # Check file size
        file_size = file_path.stat().st_size
        metadata['file_size'] = file_size
        
        if file_size > self.max_file_size:
            errors.append(f"File size ({file_size} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)")
        
        if file_size == 0:
            errors.append("File is empty")
        
        # Check file extension
        file_extension = file_path.suffix.lower()
        metadata['extension'] = file_extension
        
        if file_extension not in self.allowed_extensions:
            errors.append(f"Unsupported file extension: {file_extension}")
        
        # Check MIME type (simplified without libmagic)
        try:
            # Basic file type detection based on extension
            if file_extension in {'.pdf'}:
                metadata['file_type'] = FileType.PDF.value
            elif file_extension in {'.png'}:
                metadata['file_type'] = FileType.PNG.value
            elif file_extension in {'.jpg', '.jpeg'}:
                metadata['file_type'] = FileType.JPEG.value
            elif file_extension in {'.tiff', '.tif'}:
                metadata['file_type'] = FileType.TIFF.value
            elif file_extension in {'.docx'}:
                metadata['file_type'] = FileType.DOCX.value
            else:
                metadata['file_type'] = FileType.UNKNOWN.value
        except Exception as e:
            warnings.append(f"Could not determine file type: {e}")
        
        # Additional validation for image files
        if file_extension in {'.png', '.jpg', '.jpeg', '.tiff', '.tif'}:
            try:
                with Image.open(file_path) as img:
                    metadata['image_size'] = img.size
                    metadata['image_mode'] = img.mode
                    metadata['image_format'] = img.format
                    
                    # Check minimum dimensions
                    if img.size[0] < 100 or img.size[1] < 100:
                        warnings.append(f"Image dimensions ({img.size}) may be too small for reliable extraction")
                    
                    # Check maximum dimensions
                    if img.size[0] > 10000 or img.size[1] > 10000:
                        warnings.append(f"Image dimensions ({img.size}) are very large, processing may be slow")
                        
            except Exception as e:
                errors.append(f"Invalid image file: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )


class TableDataValidator:
    """Validator for extracted table data."""
    
    def __init__(self):
        self.financial_patterns = {
            'currency': re.compile(r'[$£€¥]\s*[\d,]+\.?\d*'),
            'percentage': re.compile(r'\d+\.?\d*\s*%'),
            'date': re.compile(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}'),
            'number': re.compile(r'^[\d,]+\.?\d*$')
        }
    
    def validate_table_structure(self, table_data: Dict[str, Any]) -> ValidationResult:
        """Validate table structure and content."""
        errors = []
        warnings = []
        metadata = {}
        
        # Check required fields
        required_fields = ['cells', 'rows', 'columns']
        for field in required_fields:
            if field not in table_data:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return ValidationResult(False, errors, warnings, metadata)
        
        # Validate table dimensions
        # Handle both old and new table formats
        rows_data = table_data.get('rows', [])
        columns_data = table_data.get('columns', [])
        cells = table_data.get('cells', [])
        
        # Extract numeric values
        if isinstance(rows_data, list):
            num_rows = table_data.get('row_count', len(rows_data))
        else:
            num_rows = int(rows_data) if rows_data else 0
        
        if isinstance(columns_data, list):
            num_cols = table_data.get('column_count', len(columns_data))
        else:
            num_cols = int(columns_data) if columns_data else 0
        
        metadata['num_rows'] = num_rows
        metadata['num_columns'] = num_cols
        metadata['num_cells'] = len(cells)
        
        if num_rows <= 0:
            errors.append("Table must have at least one row")
        
        if num_cols <= 0:
            errors.append("Table must have at least one column")
        
        if not cells:
            errors.append("Table must have at least one cell")
        
        # Validate cell structure
        valid_cells = 0
        for i, cell in enumerate(cells):
            if not isinstance(cell, dict):
                errors.append(f"Cell {i} is not a dictionary")
                continue
            
            # Check required cell fields
            cell_fields = ['row', 'column', 'text']
            missing_fields = [f for f in cell_fields if f not in cell]
            if missing_fields:
                warnings.append(f"Cell {i} missing fields: {missing_fields}")
            
            # Validate coordinates
            if 'row' in cell and 'column' in cell:
                row, col = cell['row'], cell['column']
                # Account for headers (row 0) + data rows
                max_rows = num_rows + 1  # +1 for header row
                if not (0 <= row < max_rows and 0 <= col < num_cols):
                    errors.append(f"Cell {i} coordinates ({row}, {col}) out of bounds (max: {max_rows-1}, {num_cols-1})")
                else:
                    valid_cells += 1
        
        metadata['valid_cells'] = valid_cells
        metadata['cell_coverage'] = valid_cells / (num_rows * num_cols) if num_rows * num_cols > 0 else 0
        
        # Data quality checks
        self._validate_data_quality(cells, warnings, metadata)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def _validate_data_quality(self, cells: List[Dict], warnings: List[str], metadata: Dict[str, Any]):
        """Validate data quality of extracted cells."""
        empty_cells = 0
        pattern_matches = {pattern: 0 for pattern in self.financial_patterns}
        text_lengths = []
        
        for cell in cells:
            text = cell.get('text', '').strip()
            
            if not text:
                empty_cells += 1
                continue
            
            text_lengths.append(len(text))
            
            # Check for financial patterns
            for pattern_name, pattern in self.financial_patterns.items():
                if pattern.search(text):
                    pattern_matches[pattern_name] += 1
        
        # Update metadata
        metadata['empty_cells'] = empty_cells
        metadata['empty_cell_ratio'] = empty_cells / len(cells) if cells else 0
        metadata['pattern_matches'] = pattern_matches
        metadata['avg_text_length'] = np.mean(text_lengths) if text_lengths else 0
        metadata['text_length_std'] = np.std(text_lengths) if text_lengths else 0
        
        # Generate warnings
        if metadata['empty_cell_ratio'] > 0.5:
            warnings.append(f"High ratio of empty cells: {metadata['empty_cell_ratio']:.1%}")
        
        if metadata['avg_text_length'] < 3:
            warnings.append(f"Average text length is very short: {metadata['avg_text_length']:.1f} characters")
        
        if sum(pattern_matches.values()) == 0:
            warnings.append("No financial patterns detected in table data")


class ExtractionResultValidator:
    """Validator for complete extraction results."""
    
    def __init__(self):
        self.table_validator = TableDataValidator()
    
    def validate_extraction_result(self, result: Dict[str, Any]) -> ValidationResult:
        """Validate complete extraction result."""
        errors = []
        warnings = []
        metadata = {}
        
        # Check required fields
        required_fields = ['tables', 'metadata', 'processing_time']
        for field in required_fields:
            if field not in result:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return ValidationResult(False, errors, warnings, metadata)
        
        # Validate tables
        tables = result.get('tables', [])
        metadata['num_tables'] = len(tables)
        
        if not tables:
            warnings.append("No tables extracted from document")
        
        table_validations = []
        for i, table in enumerate(tables):
            table_result = self.table_validator.validate_table_structure(table)
            table_validations.append(table_result)
            
            if not table_result.is_valid:
                errors.extend([f"Table {i}: {error}" for error in table_result.errors])
            
            warnings.extend([f"Table {i}: {warning}" for warning in table_result.warnings])
        
        metadata['table_validations'] = table_validations
        
        # Validate processing metadata
        processing_time = result.get('processing_time', 0)
        metadata['processing_time'] = processing_time
        
        if processing_time <= 0:
            warnings.append("Processing time not recorded or invalid")
        elif processing_time > 300:  # 5 minutes
            warnings.append(f"Processing time is very long: {processing_time:.1f} seconds")
        
        # Validate confidence scores
        confidence_scores = result.get('confidence_scores', {})
        if confidence_scores:
            avg_confidence = np.mean(list(confidence_scores.values()))
            metadata['avg_confidence'] = avg_confidence
            
            if avg_confidence < 0.7:
                warnings.append(f"Low average confidence score: {avg_confidence:.2f}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )


def validate_coordinates(bbox: List[float]) -> bool:
    """Validate bounding box coordinates."""
    if len(bbox) != 4:
        return False
    
    x1, y1, x2, y2 = bbox
    
    # Check if coordinates are valid numbers
    if not all(isinstance(coord, (int, float)) and not np.isnan(coord) for coord in bbox):
        return False
    
    # Check if bounding box has positive area
    if x2 <= x1 or y2 <= y1:
        return False
    
    # Check if coordinates are reasonable (not too large)
    if any(abs(coord) > 100000 for coord in bbox):
        return False
    
    return True


def validate_confidence_score(confidence: float) -> bool:
    """Validate confidence score."""
    return isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0


def sanitize_text(text: str) -> str:
    """Sanitize extracted text."""
    if not isinstance(text, str):
        return str(text)
    
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text.strip()
