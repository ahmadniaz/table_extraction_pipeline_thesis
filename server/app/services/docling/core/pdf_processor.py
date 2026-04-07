"""PDF document processor."""

import asyncio
import time
from pathlib import Path
from typing import List, Tuple
import numpy as np
import pdfplumber
from pdf2image import convert_from_path

from ..utils.config import Config
from .document_types import DocumentFormat, ProcessedDocument, DocumentProcessingError
from .table_extractor import TableExtractor


class PDFProcessor:
    """Process PDF documents using Docling and other tools."""
    
    def __init__(self, config: Config, logger, docling_converter):
        """Initialize PDF processor."""
        self.config = config
        self.processing_config = config.processing
        self.logger = logger
        self.docling_converter = docling_converter
        self.table_extractor = TableExtractor(logger)
    
    async def process(self, pdf_path: Path) -> ProcessedDocument:
        """Process PDF document."""
        self.logger.logger.info("Processing PDF document with Docling")
        
        try:
            # Use Docling for primary processing
            start_time = time.time()
            conversion_result = await asyncio.to_thread(
                self.docling_converter.convert, str(pdf_path)
            )
            docling_time = time.time() - start_time
            
            # Access the assembled document from ConversionResult
            if hasattr(conversion_result, 'assembled') and conversion_result.assembled:
                document = conversion_result.assembled
                self.logger.log_model_performance(
                    "docling_converter",
                    docling_time,
                    {"pages_processed": len(document.elements) if hasattr(document, 'elements') and document.elements else 1}
                )
            else:
                raise DocumentProcessingError("ConversionResult does not contain assembled document")
            
            # Extract tables from the assembled document
            tables = []
            for element in document.elements:
                if hasattr(element, '__class__') and 'Table' in element.__class__.__name__:
                    tables.append(element)
            
            self.logger.logger.info(f"Found {len(tables)} tables in document")
            
            # Process extracted tables into structured data
            extracted_tables = []
            for i, table in enumerate(tables):
                table_data = self.table_extractor.extract_table_data(table, i, str(pdf_path))
                if table_data:
                    extracted_tables.append(table_data)
            
            # Extract pages and metadata with intelligent page detection
            pages = []
            
            # Try to detect page boundaries from the document structure
            page_boundaries = self._detect_page_boundaries(document.elements)
            
            if page_boundaries:
                # Create separate pages based on detected boundaries
                for page_num, (start_idx, end_idx) in enumerate(page_boundaries):
                    page_elements = document.elements[start_idx:end_idx]
                    
                    page_data = {
                        'page_number': page_num,
                        'width': 0,  # Will be set from PDF if needed
                        'height': 0,
                        'elements': [],
                        'text': '',
                        'tables': []
                    }
                    
                    # Process elements for this page
                    for element in page_elements:
                        element_data = {
                            'type': element.__class__.__name__,
                            'bbox': None,  # Docling v2 doesn't expose bbox directly
                            'text': getattr(element, 'text', ''),
                            'confidence': 1.0  # Default confidence
                        }
                        page_data['elements'].append(element_data)
                        
                        if hasattr(element, 'text') and element.text:
                            page_data['text'] += element.text + ' '
                        
                        # Check if this is a table
                        if hasattr(element, '__class__') and 'Table' in element.__class__.__name__:
                            table_data = {
                                'bbox': None,
                                'confidence': 1.0,
                                'rows': getattr(element, 'num_rows', 0),
                                'columns': getattr(element, 'num_cols', 0)
                            }
                            page_data['tables'].append(table_data)
                    
                    pages.append(page_data)
            else:
                # Fallback: Create a single page with all elements
                page_data = {
                    'page_number': 0,
                    'width': 0,  # Will be set from PDF if needed
                    'height': 0,
                    'elements': [],
                    'text': '',
                    'tables': []
                }
                
                # Extract all elements from the assembled document
                for element in document.elements:
                    element_data = {
                        'type': element.__class__.__name__,
                        'bbox': None,  # Docling v2 doesn't expose bbox directly
                        'text': getattr(element, 'text', ''),
                        'confidence': 1.0  # Default confidence
                    }
                    page_data['elements'].append(element_data)
                    
                    if hasattr(element, 'text') and element.text:
                        page_data['text'] += element.text + ' '
                    
                    # Check if this is a table
                    if hasattr(element, '__class__') and 'Table' in element.__class__.__name__:
                        table_data = {
                            'bbox': None,
                            'confidence': 1.0,
                            'rows': getattr(element, 'num_rows', 0),
                            'columns': getattr(element, 'num_cols', 0)
                        }
                        page_data['tables'].append(table_data)
                
                pages.append(page_data)
            
            # Get document metadata
            metadata = {
                'title': '',  # Docling v2 doesn't expose title directly
                'num_pages': len(pages),
                'processing_time': docling_time,
                'source': 'docling',
                'docling_version': '2.43.0',
                'extracted_tables_count': len(extracted_tables)
            }
            
            # Also extract text using pdfplumber for comparison
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() or ""
                        full_text += "\n"
            except Exception as e:
                self.logger.logger.warning(f"PDFPlumber extraction failed: {e}")
                full_text = ""
            
            return ProcessedDocument(
                document_path=str(pdf_path),
                format=DocumentFormat.PDF,
                pages=pages,
                metadata=metadata,
                docling_result=conversion_result,
                text_content=full_text,
                extracted_tables=extracted_tables
            )
            
        except Exception as e:
            self.logger.logger.error(f"PDF processing failed: {e}")
            raise
    
    async def extract_images(self, processed_doc: ProcessedDocument) -> List[np.ndarray]:
        """Extract images from processed document pages."""
        images = []
        
        try:
            self.logger.logger.info(f"Extracting images from PDF: {processed_doc.document_path}")
            
            # Convert PDF to images
            pdf_images = convert_from_path(
                processed_doc.document_path,
                dpi=200,  # Good quality for OCR
                fmt='RGB',
                thread_count=2  # Parallel processing
            )
            
            for page_num, pil_image in enumerate(pdf_images):
                try:
                    # Convert PIL image to numpy array
                    image_array = np.array(pil_image)
                    images.append(image_array)
                    
                    self.logger.logger.debug(f"Extracted image from page {page_num}: {image_array.shape}")
                    
                except Exception as e:
                    self.logger.logger.error(f"Failed to process image from page {page_num}: {e}")
                    # Add a blank image as placeholder
                    blank_image = np.zeros((800, 600, 3), dtype=np.uint8)
                    images.append(blank_image)
            
            self.logger.logger.info(f"Successfully extracted {len(images)} page images from PDF")
            
        except Exception as e:
            self.logger.logger.error(f"PDF image extraction failed: {e}")
            # Fallback: create blank images for each page
            for page_num in range(processed_doc.num_pages):
                blank_image = np.zeros((800, 600, 3), dtype=np.uint8)
                images.append(blank_image)
        
        return images
    
    def _detect_page_boundaries(self, elements: List) -> List[Tuple[int, int]]:
        """Intelligently detect page boundaries from document elements."""
        if not elements:
            return []
        
        page_boundaries = []
        current_page_start = 0
        
        # Look for page break indicators in the elements
        for i, element in enumerate(elements):
            element_text = getattr(element, 'text', '') or ''
            element_text = element_text.lower() if element_text else ''
            
            # Check for page break indicators
            page_break_indicators = [
                'continued', 'page', 'statement', 'commission statement',
                'deposit advice', 'check number', 'statement date'
            ]
            
            # If we find a strong page break indicator, consider it a new page
            if any(indicator in element_text for indicator in page_break_indicators):
                # Check if this looks like a header/title (likely start of new page)
                if len(element_text) < 100 and any(word in element_text for word in ['statement', 'commission', 'continued']):
                    # This might be a new page
                    if i > current_page_start:
                        page_boundaries.append((current_page_start, i))
                        current_page_start = i
        
        # Add the final page
        if current_page_start < len(elements):
            page_boundaries.append((current_page_start, len(elements)))
        
        # If we didn't find clear boundaries, return empty list to use fallback
        if len(page_boundaries) <= 1:
            return []
        
        self.logger.logger.info(f"Detected {len(page_boundaries)} page boundaries: {page_boundaries}")
        return page_boundaries
