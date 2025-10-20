"""
Pydantic models for Mistral Document AI service.

This module contains all the data models used for structured extraction
and response formatting.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DocumentIntelligence(BaseModel):
    """Phase 1A: Document Intelligence Analysis Results"""
    identified_carrier: Optional[str] = Field(description="Primary insurance carrier identified from document structure")
    carrier_confidence: float = Field(description="Confidence score for carrier identification (0.0-1.0)")
    carrier_location_evidence: str = Field(description="Where the carrier was found (header, logo, footer, etc.)")
    statement_date: Optional[str] = Field(description="Statement date extracted from document context")
    date_confidence: float = Field(description="Confidence score for date extraction (0.0-1.0)")
    date_location_evidence: str = Field(description="Where the date was found (header, footer, statement section)")
    broker_entity: Optional[str] = Field(description="Broker/agency entity receiving commissions")
    document_classification: str = Field(description="Type of document (commission_statement, billing_statement, etc.)")
    confidence_score: float = Field(description="Overall document intelligence confidence (0.0-1.0)")


class TableData(BaseModel):
    """Individual table structure for TableIntelligence"""
    headers: List[str] = Field(description="Array of column headers")
    rows: List[List[str]] = Field(description="Array of arrays where each inner array is a row")
    table_type: str = Field(default="commission_table", description="Type of table")
    company_name: Optional[str] = Field(default=None, description="Company name if detected")
    confidence: Optional[float] = Field(default=None, description="Confidence score for this table (0.0-1.0)")


class TableIntelligence(BaseModel):
    """Phase 1B: Table Structure Intelligence Results"""
    structured_tables: List[TableData] = Field(default_factory=list, description="All tables with business context")
    business_logic_consistency: float = Field(description="Business logic validation score (0.0-1.0)")
    entity_classification_accuracy: float = Field(description="Accuracy of carrier/broker/company classification (0.0-1.0)")
    data_integrity_score: float = Field(description="Data integrity and completeness score (0.0-1.0)")
    confidence_score: float = Field(description="Overall table intelligence confidence (0.0-1.0)")


class IntelligentExtractionResponse(BaseModel):
    """Complete intelligent extraction response with separated concerns"""
    success: bool = Field(description="Whether extraction was successful")
    extraction_intelligence: Dict[str, Any] = Field(description="Intelligence analysis metadata")
    document_metadata: Dict[str, Any] = Field(description="Document-level intelligence (carrier, dates, etc.)")
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="Table business data")
    extraction_quality: Dict[str, Any] = Field(description="Quality assessment and validation")


class HierarchicalMetadata(BaseModel):
    """Model for hierarchical structure detection"""
    company_sections_detected: bool = Field(default=False, description="Whether company header rows were detected")
    company_names: List[str] = Field(default_factory=list, description="List of detected company names")
    hierarchical_levels: int = Field(description="Number of hierarchical levels detected")
    structure_type: str = Field(default="flat", description="Type of hierarchical structure")


class QualityMetrics(BaseModel):
    """Model for quality assessment metrics"""
    extraction_completeness: float = Field(description="Percentage of cells captured (0.0-1.0)")
    structure_accuracy: float = Field(description="Table structure preservation score (0.0-1.0)")
    data_fidelity: float = Field(description="Data accuracy vs source (0.0-1.0)")
    hierarchical_detection: float = Field(description="Company structure detection score (0.0-1.0)")
    confidence_score: float = Field(description="Overall confidence score (0.0-1.0)")


class EnhancedCommissionTable(BaseModel):
    """Enhanced model for commission table extraction"""
    headers: List[str] = Field(default_factory=list, description="Column headers of the commission table")
    rows: List[List[str]] = Field(default_factory=list, description="Data rows of the commission table")
    table_type: str = Field(default="commission_table", description="Type of table")
    company_name: Optional[str] = Field(description="Company name if detected")
    hierarchical_metadata: HierarchicalMetadata = Field(default_factory=HierarchicalMetadata, description="Hierarchical structure information")
    quality_metrics: QualityMetrics = Field(default_factory=QualityMetrics, description="Quality assessment metrics")
    borderless_detected: bool = Field(default=False, description="Whether table has no visible borders")
    page_number: int = Field(description="Page number where table was found")


class EnhancedDocumentMetadata(BaseModel):
    """Enhanced model for document metadata extraction with carrier detection"""
    company_name: Optional[str] = Field(description="Main company name from the document")
    carrier_name: Optional[str] = Field(description="Detected carrier name (e.g., Aetna, BCBS, Cigna)")
    carrier_confidence: Optional[float] = Field(description="Confidence score for carrier detection (0.0-1.0)")
    document_date: Optional[str] = Field(description="Statement date or document date")
    statement_month: Optional[str] = Field(description="Statement month if available")
    agent_company: Optional[str] = Field(description="Agent or broker company name")
    agent_id: Optional[str] = Field(description="Agent ID or number")
    total_commission: Optional[str] = Field(description="Total commission amount")
    document_type: str = Field(default="commission_statement", description="Type of document")
    pdf_type: str = Field(default="unknown", description="PDF type: digital, scanned, or hybrid")
    total_pages: int = Field(description="Total number of pages in document")
    format_patterns: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Detected format patterns for learning")


class EnhancedCommissionDocument(BaseModel):
    """Enhanced model for complete commission document extraction"""
    document_metadata: EnhancedDocumentMetadata = Field(default_factory=EnhancedDocumentMetadata, description="Document-level metadata")
    tables: List[EnhancedCommissionTable] = Field(default_factory=list, description="All tables found in the document")
    total_tables: int = Field(description="Total number of tables found")
    extraction_confidence: str = Field(default="0.9", description="Confidence score for the extraction")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata and insights")
