"""
Mistral Document AI package.

Pipeline usage (entry points):
- Evaluation runner (`mistral` tool): `MistralDocumentAIService.extract_commission_data_via_ocr`
  → OCR markdown + optional `chat.parse` structured extraction (`SharedBenchmarkDocument`).
- App upload / new_extract: `extract_commission_data_intelligently` (and legacy fallbacks)
  → document + table intelligence, enhanced extraction, summary/bracket post-processing.

Supporting modules (all imported from `service.py`, not dead files):
`models`, `prompts`, `utils`, `enhanced_summary_detector`, `bracket_processor`, `enhancement_config`.
"""

from .service import MistralDocumentAIService
from .models import (
    DocumentIntelligence,
    TableIntelligence,
    IntelligentExtractionResponse,
    EnhancedCommissionDocument,
    EnhancedDocumentMetadata,
    EnhancedCommissionTable,
)

__all__ = [
    "MistralDocumentAIService",
    "DocumentIntelligence",
    "TableIntelligence",
    "IntelligentExtractionResponse",
    "EnhancedCommissionDocument",
    "EnhancedDocumentMetadata",
    "EnhancedCommissionTable",
]
