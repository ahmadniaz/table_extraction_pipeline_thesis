"""
Date Extraction Service - Extracts statement dates from commission statements
This service provides robust date extraction from various commission statement formats
"""

import re
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import asyncio
from pathlib import Path
import tempfile
import os

# Import OCR and document processing capabilities
from app.new_extraction_services.models.advanced_ocr_engine import AdvancedOCREngine
from app.new_extraction_services.utils.config import get_config
from app.new_extraction_services.utils.logging_utils import setup_logging, get_logger
from app.new_extraction_services.core.document_processor import DocumentProcessor

# For PDF processing
import pdfplumber
from pdf2image import convert_from_path
import numpy as np
from PIL import Image

# For Excel processing
import pandas as pd


@dataclass
class ExtractedDate:
    """Container for extracted date information."""
    date_value: str
    label: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    page_number: int
    context: str  # Surrounding text for context
    date_type: str  # "statement_date", "payment_date", "billing_date", etc.


class DateExtractionService:
    """
    Service for extracting statement dates from commission statement documents.
    Handles various date formats and labels used by different carriers.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the date extraction service."""
        self.config = get_config(config_path)
        setup_logging(self.config)
        self.logger = get_logger(__name__, self.config)
        
        # Initialize OCR engine for text extraction
        self.ocr_engine = AdvancedOCREngine(self.config)
        
        # Initialize document processor
        self.document_processor = DocumentProcessor(self.config)
        
        # Circuit breaker for OCR failures
        self.ocr_failure_count = 0
        self.max_ocr_failures = 3
        self.ocr_circuit_breaker_reset_time = 300  # 5 minutes
        self.last_ocr_failure_time = None
        
        # Common date labels found in commission statements
        self.date_labels = {
            "statement_date": [
                "statement date", "statement", "date", "as of", "for period ending",
                "period ending", "ending", "statement period", "report date"
            ],
            "payment_date": [
                "payment date", "payment", "paid date", "settlement date", "eft settlement date",
                "payment week", "payment period", "transfer date"
            ],
            "billing_date": [
                "billing date", "billing period", "billing", "invoice date",
                "premium due date", "due date"
            ],
            "effective_date": [
                "effective date", "effective", "coverage date", "policy date",
                "start date", "beginning date", "group effective date", "group effective dat"
            ],
            "report_date": [
                "report date", "report", "generated", "created", "issued",
                "document date", "print date", "report run date"
            ],
            "archive_date": [
                "archive date", "archived", "filing date"
            ],
            "coverage_period": [
                "coverage period", "coverage", "period", "billing period"
            ]
        }
        
        # Enhanced date patterns for validation - smart and comprehensive
        self.date_patterns = [
            # MM/DD/YYYY or MM-DD-YYYY (most common US format)
            r'\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](19|20)\d{2}\b',
            # MM/DD/YY or MM-DD-YY (2-digit year)
            r'\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-]\d{2}\b',
            # YYYY-MM-DD (ISO format)
            r'\b(19|20)\d{2}-(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])\b',
            # Month DD, YYYY (full month name) - improved to handle optional comma
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(19|20)\d{2}\b',
            # Abbreviated month DD, YYYY
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+(19|20)\d{2}\b',
            # DD/MM/YYYY (European format)
            r'\b(0?[1-9]|[12]\d|3[01])[/-](0?[1-9]|1[0-2])[/-](19|20)\d{2}\b',
            # MM/DD/YYYY with optional spaces around separators
            r'\b(0?[1-9]|1[0-2])\s*[/-]\s*(0?[1-9]|[12]\d|3[01])\s*[/-]\s*(19|20)\d{2}\b',
            # Month DD YYYY (without comma)
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\s+(19|20)\d{2}\b',
            # Abbreviated month DD YYYY (without comma)
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}\s+(19|20)\d{2}\b',
            # DD Month YYYY (alternative format)
            r'\b(0?[1-9]|[12]\d|3[01])\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(19|20)\d{2}\b',
            # DD Abbreviated Month YYYY
            r'\b(0?[1-9]|[12]\d|3[01])\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(19|20)\d{2}\b',
            # **NEW: Patterns for concatenated text (no spaces) - common in PDF extraction**
            # MM/DD/YYYY without word boundaries (for concatenated text)
            r'(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](19|20)\d{2}',
            # Month DD, YYYY without spaces (concatenated)
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\d{1,2},?\d{4}',
            # Abbreviated month DD, YYYY without spaces (concatenated)
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\d{1,2},?\d{4}',
            # Statement date patterns (common in commission statements)
            r'StatementDate\d{1,2}/\d{1,2}/\d{4}',
            r'StatementDate\d{1,2}-\d{1,2}-\d{4}',
            # Payment date patterns
            r'PaymentDate\d{1,2}/\d{1,2}/\d{4}',
            r'PaymentDate\d{1,2}-\d{1,2}-\d{4}',
        ]
        
        self.logger.logger.info("Date Extraction Service initialized successfully")
    
    async def extract_dates_from_file(
        self, 
        file_path: str,
        max_pages: int = 2  # Process first 2 pages by default for better date detection
    ) -> Dict[str, Any]:
        """
        Extract dates from the first few pages of a document.
        
        Args:
            file_path: Path to the document file
            max_pages: Maximum number of pages to process (default: 2 for better date detection)
            
        Returns:
            Dictionary containing extracted dates and metadata
        """
        try:
            self.logger.logger.info(f"Starting date extraction for file: {file_path}")
            
            # Validate file exists
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": "File does not exist",
                    "dates": []
                }
            
            # Get file extension
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                return await self._extract_dates_from_pdf(file_path, max_pages)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif']:
                return await self._extract_dates_from_image(file_path)
            elif file_ext in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
                return await self._extract_dates_from_excel(file_path)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported file format: {file_ext}",
                    "dates": []
                }
                
        except Exception as e:
            self.logger.logger.error(f"Date extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dates": []
            }
    
    async def extract_dates_from_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        file_type: str = "pdf",
        max_pages: int = 2
    ) -> Dict[str, Any]:
        """
        Extract dates from file bytes using the date extraction pipeline.
        
        Args:
            file_bytes: File content as bytes
            file_name: Name of the file
            file_type: Type of file (pdf, image, etc.)
            max_pages: Maximum number of pages to process (default: 2 for better date detection)
            
        Returns:
            Dictionary containing extracted dates and metadata
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as temp_file:
                temp_file.write(file_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Extract dates from the temporary file
                result = await self.extract_dates_from_file(
                    temp_file_path,
                    max_pages
                )
                
                return result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            self.logger.logger.error(f"Date extraction from bytes failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dates": []
            }
    
    async def _extract_dates_from_pdf(self, file_path: str, max_pages: int) -> Dict[str, Any]:
        """Extract dates from PDF document with timeout and retry limits."""
        try:
            dates = []
            extraction_methods = []
            
            # Method 1: Use pdfplumber for text extraction (fast, no OCR)
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page_num in range(min(len(pdf.pages), max_pages)):
                        page = pdf.pages[page_num]
                        
                        # Extract text from page
                        text = page.extract_text() or ""
                        
                        # Extract dates from text
                        text_dates = self._extract_dates_from_text(text, page_num + 1)
                        dates.extend(text_dates)
                        
                        # Extract dates from words with bounding boxes
                        words = page.extract_words()
                        bbox_dates = self._extract_dates_from_words(words, page_num + 1)
                        dates.extend(bbox_dates)
                
                extraction_methods.append("text_extraction")
                self.logger.logger.info(f"Text extraction found {len(dates)} dates")
                
            except Exception as e:
                self.logger.logger.warning(f"Text extraction failed: {e}")
            
            # Method 2: Use OCR for scanned PDFs (only if text extraction found < 2 dates)
            # Add timeout and retry limits to prevent infinite loops
            if len(dates) < 2:  # Reduced threshold for OCR fallback
                # Check circuit breaker for OCR failures
                if self._is_ocr_circuit_breaker_open():
                    self.logger.logger.warning("OCR circuit breaker is open, skipping OCR extraction")
                    extraction_methods.append("ocr_circuit_breaker_open")
                else:
                    try:
                        # Set timeout for OCR processing (30 seconds max)
                        ocr_dates = await asyncio.wait_for(
                            self._extract_dates_with_ocr(file_path, max_pages),
                            timeout=30.0
                        )
                        dates.extend(ocr_dates)
                        extraction_methods.append("ocr")
                        self.logger.logger.info(f"OCR extraction found {len(ocr_dates)} additional dates")
                        
                        # Reset circuit breaker on success
                        self._reset_ocr_circuit_breaker()
                        
                    except asyncio.TimeoutError:
                        self.logger.logger.warning("OCR extraction timed out after 30 seconds")
                        extraction_methods.append("ocr_timeout")
                        self._increment_ocr_failure_count()
                    except Exception as e:
                        self.logger.logger.warning(f"OCR extraction failed: {e}")
                        extraction_methods.append("ocr_failed")
                        self._increment_ocr_failure_count()
            
            # Remove duplicates and sort by confidence
            unique_dates = self._deduplicate_dates(dates)
            
            # Early exit if no dates found after both methods
            if not unique_dates:
                return {
                    "success": False,
                    "error": "No dates found in document after text extraction and OCR",
                    "dates": [],
                    "extraction_methods": extraction_methods,
                    "total_dates_found": 0
                }
            
            return {
                "success": True,
                "dates": [self._date_to_dict(date) for date in unique_dates],
                "total_dates_found": len(unique_dates),
                "extraction_methods": extraction_methods
            }
            
        except Exception as e:
            self.logger.logger.error(f"PDF date extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dates": []
            }
    
    async def _extract_dates_from_image(self, file_path: str) -> Dict[str, Any]:
        """Extract dates from image file."""
        try:
            # Convert image to numpy array
            image = Image.open(file_path)
            image_array = np.array(image)
            
            # Use OCR to extract text
            dates = await self._extract_dates_with_ocr_from_image(image_array, 1)
            
            # Remove duplicates and sort by confidence
            unique_dates = self._deduplicate_dates(dates)
            
            return {
                "success": True,
                "dates": [self._date_to_dict(date) for date in unique_dates],
                "total_dates_found": len(unique_dates),
                "extraction_methods": ["ocr"]
            }
            
        except Exception as e:
            self.logger.logger.error(f"Image date extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dates": []
            }
    
    async def _extract_dates_with_ocr(self, file_path: str, max_pages: int) -> List[ExtractedDate]:
        """Extract dates using OCR from PDF pages with timeout and retry limits."""
        try:
            dates = []
            
            # Convert PDF pages to images with timeout
            try:
                # Set timeout for PDF to image conversion (10 seconds)
                images = await asyncio.wait_for(
                    asyncio.to_thread(convert_from_path, file_path, first_page=1, last_page=max_pages),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                self.logger.logger.warning("PDF to image conversion timed out")
                return []
            except Exception as e:
                self.logger.logger.warning(f"PDF to image conversion failed: {e}")
                return []
            
            # Process each page with individual timeouts
            for page_num, image in enumerate(images):
                try:
                    image_array = np.array(image)
                    
                    # Extract dates from the image with timeout (5 seconds per page)
                    page_dates = await asyncio.wait_for(
                        self._extract_dates_with_ocr_from_image(image_array, page_num + 1),
                        timeout=5.0
                    )
                    dates.extend(page_dates)
                    
                except asyncio.TimeoutError:
                    self.logger.logger.warning(f"OCR extraction timed out for page {page_num + 1}")
                    continue
                except Exception as e:
                    self.logger.logger.warning(f"OCR extraction failed for page {page_num + 1}: {e}")
                    continue
            
            return dates
            
        except Exception as e:
            self.logger.logger.error(f"OCR date extraction failed: {e}")
            return []
    
    async def _extract_dates_with_ocr_from_image(self, image: np.ndarray, page_number: int) -> List[ExtractedDate]:
        """Extract dates from image using OCR with timeout and retry limits."""
        try:
            dates = []
            
            # Divide image into regions for better OCR
            height, width = image.shape[:2]
            
            # Create regions: top, left, right, center
            regions = [
                (0, 0, width, height // 3),  # Top third
                (0, 0, width // 3, height),  # Left third
                (2 * width // 3, 0, width, height),  # Right third
                (width // 4, height // 4, 3 * width // 4, 3 * height // 4),  # Center
            ]
            
            # Process regions with timeout and early exit
            for i, region_bbox in enumerate(regions):
                try:
                    # Set timeout for each region (2 seconds max)
                    ocr_result = await asyncio.wait_for(
                        self.ocr_engine.extract_text_ensemble(image, region_bbox),
                        timeout=2.0
                    )
                    
                    if ocr_result.text and ocr_result.confidence > 0.3:
                        # Extract dates from OCR text
                        region_dates = self._extract_dates_from_text(
                            ocr_result.text, 
                            page_number, 
                            region_bbox
                        )
                        dates.extend(region_dates)
                        
                        # Early exit if we found enough dates (optimization)
                        if len(dates) >= 3:
                            self.logger.logger.info(f"Found sufficient dates ({len(dates)}), skipping remaining regions")
                            break
                        
                except asyncio.TimeoutError:
                    self.logger.logger.warning(f"OCR extraction timed out for region {i + 1}")
                    continue
                except Exception as e:
                    self.logger.logger.warning(f"OCR extraction failed for region {i + 1}: {e}")
                    continue
            
            return dates
            
        except Exception as e:
            self.logger.logger.error(f"OCR image date extraction failed: {e}")
            return []
    
    def _extract_dates_from_text(self, text: str, page_number: int, bbox: Optional[List[float]] = None) -> List[ExtractedDate]:
        """Enhanced date extraction from text with intelligent context analysis."""
        dates = []
        
        # Split text into lines and create context windows
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Create context window (current line + surrounding lines)
            context_window = self._create_context_window(lines, line_num, window_size=2)
            
            # Find all date patterns in the line
            for pattern in self.date_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                
                for match in matches:
                    date_value = match.group()
                    
                    # Enhanced date validation with context
                    if not self._is_valid_date_with_context(date_value, context_window):
                        continue
                    
                    # Intelligent label detection with context
                    label, confidence = self._find_date_label_with_context(line, date_value, context_window)
                    
                    # Skip if confidence is too low
                    if confidence < 0.3:
                        continue
                    
                    # Create bounding box if not provided
                    if bbox is None:
                        # Estimate bbox based on line position
                        estimated_bbox = [0, line_num * 20, 800, (line_num + 1) * 20]
                    else:
                        estimated_bbox = bbox
                    
                    # Create extracted date object
                    extracted_date = ExtractedDate(
                        date_value=date_value,
                        label=label,
                        confidence=confidence,
                        bbox=estimated_bbox,
                        page_number=page_number,
                        context=context_window,
                        date_type=self._classify_date_type(label)
                    )
                    
                    dates.append(extracted_date)
        
        # Remove duplicates and prioritize by confidence
        dates = self._deduplicate_and_prioritize_dates(dates)
        
        return dates
    
    def _extract_dates_from_words(self, words: List[Dict], page_number: int) -> List[ExtractedDate]:
        """Extract dates from words with bounding boxes."""
        dates = []
        
        # Group words into lines based on y-coordinate
        lines = self._group_words_into_lines(words)
        
        for line in lines:
            line_text = ' '.join([word['text'] for word in line])
            
            # Find dates in the line
            for pattern in self.date_patterns:
                matches = re.finditer(pattern, line_text, re.IGNORECASE)
                
                for match in matches:
                    date_value = match.group()
                    
                    # Validate the date
                    if not self._is_valid_date(date_value):
                        continue
                    
                    # Find the word containing this date
                    date_word = None
                    for word in line:
                        if date_value in word['text']:
                            date_word = word
                            break
                    
                    if date_word:
                        # Find the label for this date
                        label, confidence = self._find_date_label(line_text, date_value)
                        
                        # Create bounding box from word coordinates
                        bbox = [
                            date_word.get('x0', 0),
                            date_word.get('top', 0),
                            date_word.get('x1', 0),
                            date_word.get('bottom', 0)
                        ]
                        
                        # Create extracted date object
                        extracted_date = ExtractedDate(
                            date_value=date_value,
                            label=label,
                            confidence=confidence,
                            bbox=bbox,
                            page_number=page_number,
                            context=line_text,
                            date_type=self._classify_date_type(label)
                        )
                        
                        dates.append(extracted_date)
        
        return dates
    
    def _group_words_into_lines(self, words: List[Dict]) -> List[List[Dict]]:
        """Group words into lines based on y-coordinate proximity."""
        if not words:
            return []
        
        # Sort words by y-coordinate
        sorted_words = sorted(words, key=lambda w: w['top'])
        
        lines = []
        current_line = []
        last_y = None
        
        for word in sorted_words:
            if last_y is None or abs(word['top'] - last_y) < 10:  # 10px tolerance
                current_line.append(word)
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [word]
            
            last_y = word['top']
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _find_date_label(self, text: str, date_value: str) -> Tuple[str, float]:
        """Find the label for a date in the surrounding text."""
        # Remove the date from text to analyze context
        context = text.replace(date_value, '').strip()
        
        best_label = "Unknown"
        best_confidence = 0.0
        
        # Check for exact label matches
        for date_type, labels in self.date_labels.items():
            for label in labels:
                if label.lower() in context.lower():
                    # Calculate confidence based on proximity and exactness
                    confidence = self._calculate_label_confidence(context, label, date_value)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_label = label
        
        # If no exact match, try to infer from context
        if best_confidence < 0.3:
            inferred_label = self._infer_label_from_context(context)
            if inferred_label:
                best_label = inferred_label
                best_confidence = 0.2
        
        return best_label, best_confidence
    
    def _calculate_label_confidence(self, context: str, label: str, date_value: str) -> float:
        """Calculate confidence score for a label match."""
        context_lower = context.lower()
        label_lower = label.lower()
        
        # Exact match gets highest confidence
        if label_lower in context_lower:
            # Check proximity to date (closer = higher confidence)
            label_pos = context_lower.find(label_lower)
            date_pos = context_lower.find(date_value.lower())
            
            if date_pos != -1:
                distance = abs(label_pos - date_pos)
                # Closer proximity = higher confidence
                proximity_score = max(0, 1 - (distance / 100))
                return 0.8 + (0.2 * proximity_score)
            else:
                return 0.8
        
        # Partial match gets lower confidence
        elif any(word in context_lower for word in label_lower.split()):
            return 0.4
        
        return 0.0
    
    def _infer_label_from_context(self, context: str) -> Optional[str]:
        """Infer label from context when no exact match is found."""
        context_lower = context.lower()
        
        # Common patterns in commission statements
        if any(word in context_lower for word in ['statement', 'report', 'document']):
            return "Statement Date"
        elif any(word in context_lower for word in ['payment', 'paid', 'settlement']):
            return "Payment Date"
        elif any(word in context_lower for word in ['billing', 'invoice', 'premium']):
            return "Billing Date"
        elif any(word in context_lower for word in ['effective', 'coverage', 'policy']):
            return "Effective Date"
        
        return None
    
    def _classify_date_type(self, label: str) -> str:
        """Classify the type of date based on its label."""
        label_lower = label.lower()
        
        for date_type, labels in self.date_labels.items():
            if any(l.lower() in label_lower for l in labels):
                return date_type
        
        return "unknown"
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Validate if a date string represents a valid date."""
        try:
            # Try to parse the date
            if re.match(r'\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](19|20)\d{2}\b', date_str):
                # MM/DD/YYYY or MM-DD-YYYY
                if '/' in date_str:
                    month, day, year = date_str.split('/')
                else:
                    month, day, year = date_str.split('-')
                datetime(int(year), int(month), int(day))
                return True
            elif re.match(r'\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-]\d{2}\b', date_str):
                # MM/DD/YY or MM-DD-YY
                if '/' in date_str:
                    month, day, year = date_str.split('/')
                else:
                    month, day, year = date_str.split('-')
                year = int(year)
                if year < 50:  # Assume 20xx
                    year += 2000
                else:  # Assume 19xx
                    year += 1900
                datetime(year, int(month), int(day))
                return True
            elif re.match(r'\b(19|20)\d{2}-(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])\b', date_str):
                # YYYY-MM-DD
                year, month, day = date_str.split('-')
                datetime(int(year), int(month), int(day))
                return True
            elif re.match(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(19|20)\d{2}\b', date_str, re.IGNORECASE):
                # Month DD, YYYY
                parts = date_str.replace(',', '').split()
                month_name, day, year = parts[0], parts[1], parts[2]
                month_num = datetime.strptime(month_name, '%B').month
                datetime(int(year), month_num, int(day))
                return True
            elif re.match(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+(19|20)\d{2}\b', date_str, re.IGNORECASE):
                # Abbreviated month DD, YYYY
                parts = date_str.replace(',', '').split()
                month_name, day, year = parts[0], parts[1], parts[2]
                month_num = datetime.strptime(month_name, '%b').month
                datetime(int(year), month_num, int(day))
                return True
            elif re.match(r'\b(0?[1-9]|[12]\d|3[01])[/-](0?[1-9]|1[0-2])[/-](19|20)\d{2}\b', date_str):
                # DD/MM/YYYY (European format)
                if '/' in date_str:
                    day, month, year = date_str.split('/')
                else:
                    day, month, year = date_str.split('-')
                datetime(int(year), int(month), int(day))
                return True
            # **NEW: Handle concatenated date patterns (no spaces)**
            elif re.match(r'(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](19|20)\d{2}', date_str):
                # MM/DD/YYYY without word boundaries (concatenated text)
                if '/' in date_str:
                    month, day, year = date_str.split('/')
                else:
                    month, day, year = date_str.split('-')
                datetime(int(year), int(month), int(day))
                return True
            elif re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\d{1,2},?\d{4}', date_str, re.IGNORECASE):
                # Month DD, YYYY without spaces (concatenated)
                # Extract month name and remaining digits
                month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                              'July', 'August', 'September', 'October', 'November', 'December']
                for month_name in month_names:
                    if date_str.lower().startswith(month_name.lower()):
                        remaining = date_str[len(month_name):]
                        # Extract day and year
                        if ',' in remaining:
                            day_str, year_str = remaining.split(',')
                        else:
                            # Try to split at year boundary (4 digits)
                            match = re.match(r'(\d{1,2})(\d{4})', remaining)
                            if match:
                                day_str, year_str = match.groups()
                            else:
                                continue
                        month_num = datetime.strptime(month_name, '%B').month
                        datetime(int(year_str), month_num, int(day_str))
                        return True
            elif re.match(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\d{1,2},?\d{4}', date_str, re.IGNORECASE):
                # Abbreviated month DD, YYYY without spaces (concatenated)
                month_abbrevs = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                for month_abbrev in month_abbrevs:
                    if date_str.lower().startswith(month_abbrev.lower()):
                        remaining = date_str[len(month_abbrev):]
                        # Remove optional period
                        if remaining.startswith('.'):
                            remaining = remaining[1:]
                        # Extract day and year
                        if ',' in remaining:
                            day_str, year_str = remaining.split(',')
                        else:
                            # Try to split at year boundary (4 digits)
                            match = re.match(r'(\d{1,2})(\d{4})', remaining)
                            if match:
                                day_str, year_str = match.groups()
                            else:
                                continue
                        month_num = datetime.strptime(month_abbrev, '%b').month
                        datetime(int(year_str), month_num, int(day_str))
                        return True
            elif re.match(r'StatementDate\d{1,2}/\d{1,2}/\d{4}', date_str, re.IGNORECASE):
                # StatementDate MM/DD/YYYY
                date_part = date_str[12:]  # Remove "StatementDate"
                month, day, year = date_part.split('/')
                datetime(int(year), int(month), int(day))
                return True
            elif re.match(r'StatementDate\d{1,2}-\d{1,2}-\d{4}', date_str, re.IGNORECASE):
                # StatementDate MM-DD-YYYY
                date_part = date_str[12:]  # Remove "StatementDate"
                month, day, year = date_part.split('-')
                datetime(int(year), int(month), int(day))
                return True
            
            return False
            
        except (ValueError, TypeError):
            return False
    
    def _deduplicate_dates(self, dates: List[ExtractedDate]) -> List[ExtractedDate]:
        """Remove duplicate dates and sort by confidence."""
        # Group by date value and label
        date_groups = {}
        
        for date in dates:
            key = (date.date_value, date.label)
            if key not in date_groups:
                date_groups[key] = []
            date_groups[key].append(date)
        
        # Keep the highest confidence date from each group
        unique_dates = []
        for group in date_groups.values():
            best_date = max(group, key=lambda d: d.confidence)
            unique_dates.append(best_date)
        
        # Sort by confidence (highest first)
        unique_dates.sort(key=lambda d: d.confidence, reverse=True)
        
        return unique_dates
    
    def _normalize_date_for_commission(self, date_str: str) -> Dict[str, Any]:
        """
        Normalize date string to standard format for commission calculations and dashboard.
        Converts month names to standardized format and extracts month/year for dashboard associations.
        """
        try:
            # Import the parse_statement_date function from mapping.py
            from app.api.mapping import parse_statement_date
            
            # Parse the date using the existing function
            parsed_date = parse_statement_date(date_str)
            
            if not parsed_date:
                self.logger.logger.warning(f"Could not parse date for normalization: {date_str}")
                return {
                    "original_date": date_str,
                    "normalized_date": None,
                    "iso_format": None,
                    "month_number": None,
                    "year": None,
                    "month_name": None,
                    "dashboard_month": None
                }
            
            # Extract components for commission dashboard
            month_number = parsed_date.month
            year = parsed_date.year
            month_name = parsed_date.strftime('%B')  # Full month name
            
            # Create dashboard month format (e.g., "2025-02" for February 2025)
            dashboard_month = f"{year}-{month_number:02d}"
            
            # Create ISO format for database storage
            iso_format = parsed_date.isoformat()
            
            self.logger.logger.info(f"Date normalized: '{date_str}' -> {iso_format} (Month: {month_number}, Year: {year}, Dashboard: {dashboard_month})")
            
            return {
                "original_date": date_str,
                "normalized_date": iso_format,
                "iso_format": iso_format,
                "month_number": month_number,
                "year": year,
                "month_name": month_name,
                "dashboard_month": dashboard_month,
                "parsed_date": parsed_date
            }
            
        except Exception as e:
            self.logger.logger.error(f"Error normalizing date '{date_str}': {str(e)}")
            return {
                "original_date": date_str,
                "normalized_date": None,
                "iso_format": None,
                "month_number": None,
                "year": None,
                "month_name": None,
                "dashboard_month": None,
                "error": str(e)
            }
    
    def _date_to_dict(self, date: ExtractedDate) -> Dict[str, Any]:
        """Convert ExtractedDate to dictionary format."""
        # Normalize the date value for commission calculations
        normalized_date = self._normalize_date_for_commission(date.date_value)
        
        return {
            "date_value": date.date_value,
            "normalized_date": normalized_date,
            "label": date.label,
            "confidence": date.confidence,
            "bbox": date.bbox,
            "page_number": date.page_number,
            "context": date.context,
            "date_type": date.date_type
        }
    
    async def _extract_dates_from_excel(self, file_path: str) -> Dict[str, Any]:
        """Extract dates from Excel document."""
        try:
            import pandas as pd
            
            dates = []
            
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            
            # Process first few sheets (usually the most relevant ones)
            for sheet_name in excel_file.sheet_names[:3]:  # Limit to first 3 sheets
                try:
                    # Read sheet data
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                    
                    if df.empty:
                        continue
                    
                    # Convert all data to string and search for dates
                    for row_idx, row in df.iterrows():
                        for col_idx, cell_value in enumerate(row):
                            if pd.notna(cell_value):
                                cell_str = str(cell_value).strip()
                                
                                # First, check if the entire cell is a valid date (standalone dates)
                                if self._is_valid_date(cell_str):
                                    # Look for date labels in nearby cells
                                    label = self._find_date_label_in_excel(df, row_idx, col_idx)
                                    
                                    # Create extracted date
                                    extracted_date = ExtractedDate(
                                        date_value=cell_str,
                                        label=label,
                                        confidence=0.8,  # High confidence for Excel data
                                        bbox=[col_idx, row_idx, col_idx + 1, row_idx + 1],  # Excel cell coordinates
                                        page_number=1,  # Excel doesn't have pages, use 1
                                        context=f"Sheet: {sheet_name}, Cell: {chr(65 + col_idx)}{row_idx + 1}",
                                        date_type=self._classify_date_type(label)
                                    )
                                    dates.append(extracted_date)
                                
                                # Also check if the cell contains dates with labels (like "Archive Date: 1/23/2025")
                                else:
                                    # Use the text extraction method to find dates within the cell text
                                    cell_dates = self._extract_dates_from_text(cell_str, page_number=1)
                                    
                                    # Add Excel-specific context to the extracted dates
                                    for cell_date in cell_dates:
                                        # Update the context to include Excel cell information
                                        cell_date.context = f"Sheet: {sheet_name}, Cell: {chr(65 + col_idx)}{row_idx + 1} - {cell_date.context}"
                                        
                                        # Update bounding box to Excel cell coordinates
                                        cell_date.bbox = [col_idx, row_idx, col_idx + 1, row_idx + 1]
                                        
                                        # Adjust confidence for Excel data
                                        cell_date.confidence = min(0.9, cell_date.confidence + 0.1)
                                        
                                        dates.append(cell_date)
                    
                except Exception as e:
                    self.logger.logger.warning(f"Error processing Excel sheet {sheet_name}: {e}")
                    continue
            
            # Remove duplicates and sort by confidence
            unique_dates = self._deduplicate_dates(dates)
            
            return {
                "success": True,
                "dates": [self._date_to_dict(date) for date in unique_dates],
                "total_dates": len(unique_dates),
                "extraction_methods": ["excel_text_extraction"],
                "processing_time": 0.0,
                "warnings": [],
                "errors": []
            }
            
        except Exception as e:
            self.logger.logger.error(f"Excel date extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dates": []
            }
    
    def _find_date_label_in_excel(self, df: pd.DataFrame, row_idx: int, col_idx: int) -> str:
        """Find date label in nearby Excel cells."""
        # Check header row (row 0)
        if row_idx > 0 and col_idx < len(df.columns):
            header_value = str(df.iloc[0, col_idx]).strip().lower()
            for date_type, labels in self.date_labels.items():
                for label in labels:
                    if label in header_value:
                        return header_value
        
        # Check left column for labels
        if col_idx > 0 and row_idx < len(df):
            left_value = str(df.iloc[row_idx, col_idx - 1]).strip().lower()
            for date_type, labels in self.date_labels.items():
                for label in labels:
                    if label in left_value:
                        return left_value
        
        # Default label
        return "date"
    
    async def get_extraction_status(self) -> Dict[str, Any]:
        """
        Get the status of the date extraction service.
        
        Returns:
            Dictionary containing service status information
        """
        return {
            "service": "date_extraction_service",
            "status": "active",
            "version": "1.0.0",
            "models_loaded": {
                "ocr_engine": self.ocr_engine is not None,
                "document_processor": self.document_processor is not None
            },
            "config": {
                "date_patterns_count": len(self.date_patterns),
                "date_labels_count": sum(len(labels) for labels in self.date_labels.values()),
                "supported_formats": ["pdf", "png", "jpg", "jpeg", "tiff", "tif", "xlsx", "xls", "xlsm", "xlsb"]
            }
        }
    
    def _create_context_window(self, lines: List[str], line_num: int, window_size: int = 2) -> str:
        """Create a context window around a line for better date label detection."""
        start_idx = max(0, line_num - window_size)
        end_idx = min(len(lines), line_num + window_size + 1)
        context_lines = lines[start_idx:end_idx]
        return ' '.join(context_lines)
    
    def _is_valid_date_with_context(self, date_value: str, context: str) -> bool:
        """Enhanced date validation that considers context to avoid false positives."""
        # Basic date validation
        if not self._is_valid_date(date_value):
            return False
        
        # Context-based validation - avoid dates that are clearly not statement dates
        context_lower = context.lower()
        
        # **IMPROVED: Be more permissive for statement dates**
        # Check if this looks like a statement date context
        statement_indicators = ['statement', 'commission', 'report', 'date', 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
        if any(indicator in context_lower for indicator in statement_indicators):
            # If context contains statement-related keywords, be more permissive
            return True
        
        # Skip dates that appear to be in table data (like policy numbers, IDs)
        if any(indicator in context_lower for indicator in ['policy', 'id', 'number', 'code', 'reference']):
            # Only skip if the date is clearly part of an ID/number
            if re.search(r'\d{4,}', date_value):  # Long numeric sequences
                return False
        
        # Skip dates that appear to be in financial amounts
        if re.search(r'\$.*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', context):
            return False
        
        return True
    
    def _find_date_label_with_context(self, line: str, date_value: str, context: str) -> Tuple[str, float]:
        """Enhanced label detection using context window for better accuracy."""
        line_lower = line.lower()
        context_lower = context.lower()
        
        # Check for explicit date labels in the line
        for date_type, labels in self.date_labels.items():
            for label in labels:
                if label in line_lower:
                    # Calculate confidence based on proximity to date
                    date_pos = line_lower.find(date_value.lower())
                    label_pos = line_lower.find(label)
                    if label_pos != -1:
                        distance = abs(date_pos - label_pos)
                        confidence = max(0.8, 1.0 - (distance / 100.0))  # Higher confidence for closer labels
                        return label, confidence
        
        # Check context window for labels
        for date_type, labels in self.date_labels.items():
            for label in labels:
                if label in context_lower:
                    # Lower confidence for context-based detection
                    return label, 0.6
        
        # Check for common statement date indicators
        statement_indicators = ['statement', 'report', 'commission', 'payment', 'billing']
        for indicator in statement_indicators:
            if indicator in context_lower:
                return f"{indicator} date", 0.5
        
        # **IMPROVED: Better detection for "Statement Date" specifically**
        if 'statement date' in context_lower:
            return "Statement Date", 0.9
        elif 'statement' in context_lower and 'date' in context_lower:
            return "Statement Date", 0.7
        
        # Default fallback
        return "date", 0.3
    
    def _deduplicate_and_prioritize_dates(self, dates: List[ExtractedDate]) -> List[ExtractedDate]:
        """Remove duplicate dates and prioritize by confidence and relevance."""
        if not dates:
            return dates
        
        # Group by date value
        date_groups = {}
        for date in dates:
            date_key = date.date_value.lower().strip()
            if date_key not in date_groups:
                date_groups[date_key] = []
            date_groups[date_key].append(date)
        
        # Select best date from each group
        unique_dates = []
        for date_group in date_groups.values():
            # Sort by confidence, then by date type priority
            type_priority = {
                'statement_date': 1,
                'payment_date': 2,
                'billing_date': 3,
                'effective_date': 4,
                'report_date': 5
            }
            
            best_date = max(date_group, key=lambda d: (
                d.confidence,
                -type_priority.get(d.date_type, 99)
            ))
            unique_dates.append(best_date)
        
        # Sort final results by confidence
        unique_dates.sort(key=lambda d: d.confidence, reverse=True)
        
        return unique_dates
    
    def _is_ocr_circuit_breaker_open(self) -> bool:
        """Check if OCR circuit breaker is open due to repeated failures."""
        if self.ocr_failure_count < self.max_ocr_failures:
            return False
        
        # Check if enough time has passed to reset the circuit breaker
        if self.last_ocr_failure_time is None:
            return True
        
        current_time = time.time()
        if current_time - self.last_ocr_failure_time > self.ocr_circuit_breaker_reset_time:
            self._reset_ocr_circuit_breaker()
            return False
        
        return True
    
    def _increment_ocr_failure_count(self):
        """Increment OCR failure count and update last failure time."""
        self.ocr_failure_count += 1
        self.last_ocr_failure_time = time.time()
        self.logger.logger.warning(f"OCR failure count: {self.ocr_failure_count}/{self.max_ocr_failures}")
    
    def _reset_ocr_circuit_breaker(self):
        """Reset OCR circuit breaker after successful operation."""
        self.ocr_failure_count = 0
        self.last_ocr_failure_time = None
        self.logger.logger.info("OCR circuit breaker reset")


# Create a global instance for easy access
_date_extraction_service = None

def get_date_extraction_service(config_path: Optional[str] = None) -> DateExtractionService:
    """
    Get or create a global instance of the date extraction service.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        DateExtractionService instance
    """
    global _date_extraction_service
    
    if _date_extraction_service is None:
        _date_extraction_service = DateExtractionService(config_path)
    
    return _date_extraction_service
