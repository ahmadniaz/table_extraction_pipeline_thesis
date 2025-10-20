"""Document types and data structures for document processing."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional
import numpy as np


class DocumentProcessingError(Exception):
    """Exception raised during document processing."""
    pass


class DocumentFormat(Enum):
    """Supported document formats."""
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"  
    TIFF = "tiff"
    DOCX = "docx"
    UNKNOWN = "unknown"


@dataclass
class ProcessedDocument:
    """Container for processed document data."""
    document_path: str
    format: DocumentFormat
    pages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    docling_result: Optional[Any] = None
    raw_images: Optional[List[np.ndarray]] = None
    text_content: Optional[str] = None
    extracted_tables: Optional[List[Dict[str, Any]]] = None
    
    @property
    def num_pages(self) -> int:
        """Get number of pages."""
        return len(self.pages)
