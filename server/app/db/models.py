from sqlalchemy import (
    Column, String, Integer, Text, JSON, ForeignKey, DateTime, text, Boolean, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class Document(Base):
    __tablename__ = 'documents'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    complexity_tier = Column(String, nullable=False)  # 'low' | 'medium' | 'high'
    page_count = Column(Integer)
    is_digital = Column(Boolean)  # True = digital PDF, False = scanned
    uploaded_at = Column(DateTime, server_default=text('now()'), nullable=False)
    file_path = Column(String)  # local path to PDF


class GroundTruthTable(Base):
    __tablename__ = 'ground_truth_tables'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    table_index = Column(Integer, nullable=False)  # 0-based table order in doc
    headers = Column(JSON, nullable=False)
    rows = Column(JSON, nullable=False)
    annotated_at = Column(DateTime, server_default=text('now()'), nullable=False)
    notes = Column(Text, nullable=True)  # annotation edge-case notes
    confirmed = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    source = Column(String, nullable=False, default='manual', server_default=text("'manual'"))
    correction_log = Column(JSON, nullable=False, default=list, server_default=text("'[]'::json"))
    correction_count = Column(Integer, nullable=False, default=0, server_default=text('0'))


class ExtractionResult(Base):
    __tablename__ = 'extraction_results'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    tool_name = Column(String, nullable=False)  # 'pymupdf' | 'docling' | 'aws_textract' | 'google_docai' | 'gpt5' | 'claude_sonnet' | 'mistral'
    table_index = Column(Integer, nullable=False)
    extracted_headers = Column(JSON)
    extracted_rows = Column(JSON)
    processing_time_ms = Column(Integer)
    cost_usd = Column(Numeric(10, 6))
    error_message = Column(Text, nullable=True)
    extracted_at = Column(DateTime, server_default=text('now()'), nullable=False)
    failure_reason = Column(String, nullable=True)
    is_transient_failure = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    raw_output = Column(JSON, nullable=True)


class EvaluationScore(Base):
    __tablename__ = 'evaluation_scores'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_result_id = Column(UUID(as_uuid=True), ForeignKey('extraction_results.id', ondelete='CASCADE'), nullable=False)
    precision = Column(Numeric(6, 4))
    recall = Column(Numeric(6, 4))
    f1_score = Column(Numeric(6, 4))
    teds_score = Column(Numeric(6, 4))
    grits_top = Column(Numeric(6, 4))
    grits_con = Column(Numeric(6, 4))
    grits_loc = Column(Numeric(6, 4))
    computed_at = Column(DateTime, server_default=text('now()'), nullable=False)
