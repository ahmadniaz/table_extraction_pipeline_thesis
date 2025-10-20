"""DOCX document processor."""

import asyncio
import time
from pathlib import Path

from ..utils.config import Config
from .document_types import DocumentFormat, ProcessedDocument


class DOCXProcessor:
    """Process DOCX documents using Docling."""
    
    def __init__(self, config: Config, logger, docling_converter):
        """Initialize DOCX processor."""
        self.config = config
        self.processing_config = config.processing
        self.logger = logger
        self.docling_converter = docling_converter
    
    async def process(self, docx_path: Path) -> ProcessedDocument:
        """Process DOCX document."""
        self.logger.logger.info("Processing DOCX document with Docling")
        
        try:
            # Use Docling for DOCX processing
            start_time = time.time()
            conversion_result = await asyncio.to_thread(
                self.docling_converter.convert, str(docx_path)
            )
            docling_time = time.time() - start_time
            
            # Extract content similar to PDF processing
            pages = []
            
            # DOCX typically has one logical "page" but may contain multiple sections
            page_data = {
                'page_number': 0,
                'width': 0,  # No physical dimensions for DOCX
                'height': 0,
                'elements': [],
                'text': '',
                'tables': []
            }
            
            # Extract elements from the assembled document
            if hasattr(conversion_result, 'assembled') and conversion_result.assembled:
                document = conversion_result.assembled
                
                for element in document.elements:
                    element_data = {
                        'type': element.__class__.__name__,
                        'bbox': None,
                        'text': getattr(element, 'text', ''),
                        'confidence': 1.0
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
            
            metadata = {
                'title': '',  # Docling v2 doesn't expose title directly
                'num_pages': 1,
                'processing_time': docling_time,
                'source': 'docling',
                'format': 'docx'
            }
            
            return ProcessedDocument(
                document_path=str(docx_path),
                format=DocumentFormat.DOCX,
                pages=pages,
                metadata=metadata,
                docling_result=conversion_result,
                text_content=page_data['text']
            )
            
        except Exception as e:
            self.logger.logger.error(f"DOCX processing failed: {e}")
            raise
