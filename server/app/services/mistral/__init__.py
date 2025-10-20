"""
Mistral Document AI Service Package

This package provides intelligent document extraction capabilities using Mistral's
Pixtral Large model for commission statement processing.

Main Components:
- models: Pydantic models for structured data
- service: Core extraction service
- utils: Utility functions for PDF processing and validation
- prompts: System prompts for different extraction phases
"""

from .service import MistralDocumentAIService
from .models import (
    DocumentIntelligence,
    TableIntelligence,
    IntelligentExtractionResponse,
    EnhancedCommissionDocument,
    EnhancedDocumentMetadata,
    EnhancedCommissionTable
)

__all__ = [
    'MistralDocumentAIService',
    'DocumentIntelligence',
    'TableIntelligence', 
    'IntelligentExtractionResponse',
    'EnhancedCommissionDocument',
    'EnhancedDocumentMetadata',
    'EnhancedCommissionTable'
]
