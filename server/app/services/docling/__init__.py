"""Docling + TableFormer extraction pipeline."""

# Core document processing
from .core.document_processor import DocumentProcessor
from .core.document_types import DocumentFormat, ProcessedDocument, DocumentProcessingError
from .core.table_extractor import TableExtractor
from .core.table_validator import TableValidator
from .core.multipage_handler import MultiPageTableHandler

# Models
from .models.tableformer import TableFormerModel, OCREngine, TableStructure
from .models.advanced_tableformer import ProductionTableFormer
from .models.advanced_ocr_engine import AdvancedOCREngine, OCRResult

# Pipeline
from .pipeline import ExtractionPipeline, ExtractionOptions, TableExtractionResult, ExtractionStage

# Processors
from .processors import SmartFinancialDocumentProcessor

# Evaluation
from .evaluation import AdvancedEvaluationMetrics

# Utils
from .utils.config import Config, get_config
from .utils.logging_utils import get_logger, setup_logging, LogExtractionOperation
from .utils.compatibility import apply_compatibility_fixes

__all__ = [
    # Core
    'DocumentProcessor',
    'DocumentFormat',
    'ProcessedDocument',
    'DocumentProcessingError',
    'TableExtractor',
    'TableValidator',
    'MultiPageTableHandler',
    # Models
    'TableFormerModel',
    'OCREngine',
    'TableStructure',
    'ProductionTableFormer',
    'AdvancedOCREngine',
    'OCRResult',
    # Pipeline
    'ExtractionPipeline',
    'ExtractionOptions',
    'TableExtractionResult',
    'ExtractionStage',
    # Processors
    'SmartFinancialDocumentProcessor',
    # Evaluation
    'AdvancedEvaluationMetrics',
    # Utils
    'Config',
    'get_config',
    'get_logger',
    'setup_logging',
    'LogExtractionOperation',
    'apply_compatibility_fixes',
]

