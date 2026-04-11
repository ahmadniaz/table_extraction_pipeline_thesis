"""Extraction services for document and table extraction."""

# NOTE: Do not import EnhancedExtractionService here — it depends on ClaudeDocumentAIService,
# while claude.service imports extraction_utils. Eager import creates a circular import at startup.

from .new_extraction_service import NewExtractionService, get_new_extraction_service
from .date_extraction_service import DateExtractionService, get_date_extraction_service
from .excel_extraction_service import get_excel_extraction_service
from app.services.google_docai import GoogleDocAIExtractor
from .extraction_utils import stitch_multipage_tables

__all__ = [
    'NewExtractionService',
    'get_new_extraction_service',
    'DateExtractionService',
    'get_date_extraction_service',
    'get_excel_extraction_service',
    'EnhancedExtractionService',  # lazy via __getattr__
    'GoogleDocAIExtractor',
    'stitch_multipage_tables',
]


def __getattr__(name: str):
    if name == 'EnhancedExtractionService':
        from .enhanced_extraction_service import EnhancedExtractionService
        return EnhancedExtractionService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

