"""
Pydantic models for Claude Document AI service.

This module contains all the data models used for structured extraction
and response formatting.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ClaudeTableData(BaseModel):
    """Individual table structure for Claude extraction"""
    headers: List[str] = Field(description="Array of column headers")
    rows: List[List[str]] = Field(description="Array of arrays where each inner array is a row")
    table_type: str = Field(default="commission_table", description="Type of table")
    page_number: int = Field(description="Page number where table was found")
    confidence_score: float = Field(description="Confidence score for this table (0.0-1.0)")
    summary_rows: List[int] = Field(default_factory=list, description="Indices of summary/total rows")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional table metadata")
    borderless: bool = Field(default=False, description="Whether table has no visible borders")
    hierarchical: bool = Field(default=False, description="Whether table has hierarchical structure")
    company_sections: List[str] = Field(default_factory=list, description="Detected company section headers")


class ClaudeDocumentMetadata(BaseModel):
    """Document-level metadata extracted by Claude"""
    carrier_name: Optional[str] = Field(description="Insurance carrier name")
    carrier_confidence: float = Field(default=0.0, description="Confidence score for carrier detection")
    statement_date: Optional[str] = Field(description="Statement date from document")
    date_confidence: float = Field(default=0.0, description="Confidence score for date extraction")
    broker_company: Optional[str] = Field(description="Broker/agency company name")
    broker_confidence: float = Field(default=0.0, description="Confidence score for broker detection")
    broker_entity: Optional[str] = Field(default=None, description="Broker/agency entity (deprecated, use broker_company)")
    document_type: str = Field(default="commission_statement", description="Type of document")
    total_pages: int = Field(description="Total number of pages in document")
    file_size_mb: float = Field(description="File size in megabytes")
    extraction_method: str = Field(default="claude", description="Extraction method used")
    claude_model: str = Field(description="Claude model used for extraction")


class ClaudeQualityMetrics(BaseModel):
    """Quality assessment metrics for Claude extraction"""
    overall_confidence: float = Field(description="Overall extraction confidence (0.0-1.0)")
    table_structure_score: float = Field(description="Table structure preservation score")
    data_completeness: float = Field(description="Data completeness percentage")
    extraction_accuracy: float = Field(description="Estimated extraction accuracy")
    issues_detected: List[str] = Field(default_factory=list, description="List of detected issues")
    quality_grade: str = Field(description="Quality grade: A, B, C, D, F")


class ClaudeExtractionResponse(BaseModel):
    """Complete Claude extraction response"""
    success: bool = Field(description="Whether extraction was successful")
    tables: List[ClaudeTableData] = Field(default_factory=list, description="Extracted tables")
    document_metadata: ClaudeDocumentMetadata = Field(description="Document-level metadata")
    quality_metrics: ClaudeQualityMetrics = Field(description="Quality assessment")
    processing_time: float = Field(description="Processing time in seconds")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics")
    error_message: Optional[str] = Field(default=None, description="Error message if extraction failed")
    extraction_config: Dict[str, Any] = Field(default_factory=dict, description="Configuration used")


class ClaudeChunkMetadata(BaseModel):
    """Metadata for document chunks when processing large files"""
    chunk_index: int = Field(description="Index of this chunk")
    total_chunks: int = Field(description="Total number of chunks")
    page_range: List[int] = Field(description="Page range for this chunk [start, end]")
    chunk_size_bytes: int = Field(description="Size of this chunk in bytes")

