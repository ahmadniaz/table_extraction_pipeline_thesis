"""Document processor for handling various input formats."""

import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import time
import numpy as np

from docling.document_converter import DocumentConverter

from ..utils.config import Config
from ..utils.logging_utils import get_logger, LogExtractionOperation
from ..utils.validation import DocumentValidator

from .document_types import DocumentFormat, ProcessedDocument, DocumentProcessingError
from .format_detector import FormatDetector
from .pdf_processor import PDFProcessor
from .image_processor import ImageProcessor
from .docx_processor import DOCXProcessor
from .table_extractor import TableExtractor
from .table_validator import TableValidator


class DocumentProcessor:
    """Main document processor class."""
    
    def __init__(self, config: Config):
        """Initialize document processor."""
        self.config = config
        self.processing_config = config.processing
        self.logger = get_logger(__name__, config)
        self.validator = DocumentValidator(max_file_size=config.api.max_file_size)
        
        # Initialize Docling converter
        self.docling_converter = DocumentConverter()
        
        # Initialize specialized processors
        self.format_detector = FormatDetector()
        self.pdf_processor = PDFProcessor(config, self.logger, self.docling_converter)
        self.image_processor = ImageProcessor(config, self.logger)
        self.docx_processor = DOCXProcessor(config, self.logger, self.docling_converter)
        self.table_extractor = TableExtractor(self.logger)
        self.table_validator = TableValidator(self.logger)
    
    async def process_document(self, document_path: Union[str, Path]) -> ProcessedDocument:
        """Process a document and prepare it for table extraction."""
        document_path = Path(document_path)
        
        with LogExtractionOperation(self.logger, str(document_path), "document_processing"):
            # Validate document
            validation_result = self.validator.validate_file(document_path)
            if not validation_result.is_valid:
                raise ValueError(f"Document validation failed: {validation_result.errors}")
            
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    self.logger.logger.warning(warning)
            
            # Detect format
            document_format = self.format_detector.detect_format(document_path)
            self.logger.logger.info(f"Detected document format: {document_format.value}")
            
            # Process based on format
            if document_format == DocumentFormat.PDF:
                processed_doc = await self.pdf_processor.process(document_path)
            elif document_format in [DocumentFormat.PNG, DocumentFormat.JPEG, DocumentFormat.TIFF]:
                processed_doc = await self.image_processor.process(document_path)
            elif document_format == DocumentFormat.DOCX:
                processed_doc = await self.docx_processor.process(document_path)
            else:
                raise ValueError(f"Unsupported document format: {document_format}")
            
            # Add validation metadata
            processed_doc.metadata.update(validation_result.metadata)
            
            self.logger.logger.info(
                f"Document processing completed: {processed_doc.num_pages} pages"
            )
            
            return processed_doc
    
    async def extract_images_from_pages(self, processed_doc: ProcessedDocument) -> List[np.ndarray]:
        """Extract images from processed document pages."""
        if processed_doc.raw_images:
            return processed_doc.raw_images
        
        if processed_doc.format == DocumentFormat.PDF:
            return await self.pdf_processor.extract_images(processed_doc)
        elif processed_doc.format in [DocumentFormat.PNG, DocumentFormat.JPEG, DocumentFormat.TIFF]:
            return await self.image_processor.extract_images(processed_doc)
        
        return []
    
    def get_page_text(self, processed_doc: ProcessedDocument, page_num: int) -> str:
        """Get text content from a specific page."""
        if page_num >= processed_doc.num_pages:
            raise IndexError(f"Page {page_num} not found. Document has {processed_doc.num_pages} pages")
        
        return processed_doc.pages[page_num].get('text', '')
    
    def get_page_tables(self, processed_doc: ProcessedDocument, page_num: int) -> List[Dict[str, Any]]:
        """Get table information from a specific page."""
        if page_num >= processed_doc.num_pages:
            raise IndexError(f"Page {page_num} not found. Document has {processed_doc.num_pages} pages")
        
        return processed_doc.pages[page_num].get('tables', [])
    