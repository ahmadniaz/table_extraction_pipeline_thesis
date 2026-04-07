"""
Google Document AI extraction services.

This module provides a properly organized implementation of Google Document AI
for table extraction from PDF documents.
"""

from .extractor import GoogleDocAIExtractor
from .config import (
    HEADER_CONFIDENCE_THRESHOLD,
    CELL_CONFIDENCE_THRESHOLD,
    PATTERN_MATCH_THRESHOLD,
    HEADER_SIMILARITY_THRESHOLD,
    MAX_RETRIES,
    REGULAR_MODE_MAX_PAGES,
    IMAGELESS_MODE_MAX_PAGES,
    CHUNK_SIZE,
    ROW_THRESHOLD,
    MIN_TABLE_WIDTH,
    MIN_TABLE_HEIGHT,
    DEFAULT_PROJECT_ID,
    DEFAULT_PROCESSOR_ID,
    DEFAULT_LOCATION
)
from .utils import extract_rows_from_tableblock, adapt_tableblock_to_standard_format
from .processing import DocumentProcessor
from .table_extraction import TableExtractor
from .post_processing import TextCleaner, PatternAnalyzer

__all__ = [
    # Main extractor
    'GoogleDocAIExtractor',
    
    # Configuration
    'HEADER_CONFIDENCE_THRESHOLD',
    'CELL_CONFIDENCE_THRESHOLD',
    'PATTERN_MATCH_THRESHOLD',
    'HEADER_SIMILARITY_THRESHOLD',
    'MAX_RETRIES',
    'REGULAR_MODE_MAX_PAGES',
    'IMAGELESS_MODE_MAX_PAGES',
    'CHUNK_SIZE',
    'ROW_THRESHOLD',
    'MIN_TABLE_WIDTH',
    'MIN_TABLE_HEIGHT',
    'DEFAULT_PROJECT_ID',
    'DEFAULT_PROCESSOR_ID',
    'DEFAULT_LOCATION',
    
    # Utilities
    'extract_rows_from_tableblock',
    'adapt_tableblock_to_standard_format',
    
    # Components
    'DocumentProcessor',
    'TableExtractor',
    'TextCleaner',
    'PatternAnalyzer',
]

