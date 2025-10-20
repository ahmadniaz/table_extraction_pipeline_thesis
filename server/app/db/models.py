from sqlalchemy import (
    Column, String, Integer, Text, TIMESTAMP, JSON, ForeignKey, DateTime, text, UniqueConstraint, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Company(Base):
    __tablename__ = 'companies'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)

class CompanyFieldMapping(Base):
    __tablename__ = 'company_field_mappings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    display_name = Column(String, nullable=False)  # Changed from field_key to display_name
    column_name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    
    # Add unique constraint for upsert operations
    __table_args__ = (
        UniqueConstraint('company_id', 'display_name', name='uq_company_field_mapping'),
    )

class CompanyConfiguration(Base):
    __tablename__ = 'company_configurations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False, unique=True)
    field_config = Column(JSON)  # Store field configuration for the company
    plan_types = Column(JSON)  # Store plan types for the company
    table_names = Column(JSON)  # Store table names for the company
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)

class CarrierFormatLearning(Base):
    __tablename__ = 'carrier_format_learning'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    
    # Format metadata
    format_signature = Column(String, nullable=False)  # Hash of headers and structure
    headers = Column(JSON, nullable=False)  # Array of column headers
    header_patterns = Column(JSON)  # Learned patterns for header detection
    
    # Data type analysis
    column_types = Column(JSON)  # Data types for each column (string, number, date, currency)
    column_patterns = Column(JSON)  # Regex patterns for each column
    sample_values = Column(JSON)  # Sample values for each column
    
    # Structure analysis
    table_structure = Column(JSON)  # Table layout, number of columns, typical row count
    data_quality_metrics = Column(JSON)  # Completeness, consistency metrics
    
    # Mapping information
    field_mapping = Column(JSON)  # Learned field mapping for this format
    table_editor_settings = Column(JSON)  # Table editor settings (headers, summary rows, etc.)
    confidence_score = Column(Integer, default=0)  # Confidence in this format (0-100)
    
    # Usage tracking
    usage_count = Column(Integer, default=1)  # How many times this format was used
    last_used = Column(DateTime, server_default=text('now()'), nullable=False)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    
    # Add unique constraint for company and format signature
    __table_args__ = (
        UniqueConstraint('company_id', 'format_signature', name='uq_carrier_format'),
    )

class StatementUpload(Base):
    __tablename__ = 'statement_uploads'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)  # User's company
    carrier_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=True)  # Insurance carrier company
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)  # User who uploaded the file
    file_name = Column(Text)
    file_hash = Column(String, nullable=True)  # SHA-256 hash for duplicate detection
    file_size = Column(Integer, nullable=True)  # File size in bytes
    uploaded_at = Column(TIMESTAMP)
    
    # Status Management
    status = Column(String, default='pending')  # pending, approved, rejected, processing
    current_step = Column(String, default='upload')  # upload, table_editor, field_mapper, dashboard, completed
    
    # Progress Data Storage
    progress_data = Column(JSON)  # Store intermediate data for each step
    raw_data = Column(JSON)  # Extracted table data
    edited_tables = Column(JSON)  # Tables after editing in TableEditor
    field_mapping = Column(JSON)  # Field mapping configuration
    final_data = Column(JSON)  # Final processed data
    
    # Metadata
    mapping_used = Column(JSON)
    field_config = Column(JSON)
    rejection_reason = Column(Text)
    plan_types = Column(JSON)  # Store list of plan types (Medical, Dental, etc)
    selected_statement_date = Column(JSON)  # Store selected statement date from TableEditor
    ai_intelligence = Column(JSON)  # Store AI intelligence data (table selection, field mapping, plan detection)
    
    # Timestamps
    last_updated = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    completed_at = Column(DateTime)  # When status changed to approved/rejected
    
    # User session tracking (optional)
    session_id = Column(String)  # Track user session for auto-save
    auto_save_enabled = Column(Integer, default=1)  # 1 for enabled, 0 for disabled

class Extraction(Base):
    __tablename__ = 'extractions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(String, nullable=False)  # Using string for flexibility
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # User who performed extraction
    filename = Column(String, nullable=False)
    s3_url = Column(String, nullable=False)
    total_tables = Column(Integer, nullable=False)
    valid_tables = Column(Integer, nullable=False)
    quality_score = Column(Integer, nullable=False)  # Store as integer (0-100)
    confidence = Column(String, nullable=False)
    extraction_metadata = Column(JSON)
    quality_metadata = Column(JSON)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)

class DatabaseField(Base):
    __tablename__ = 'database_fields'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)

class PlanType(Base):
    __tablename__ = 'plan_types'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)

class EarnedCommission(Base):
    __tablename__ = 'earned_commissions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    carrier_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    client_name = Column(String, nullable=False)  # Company name from the statement
    invoice_total = Column(Numeric(15, 2), default=0)  # Total invoice amount
    commission_earned = Column(Numeric(15, 2), default=0)  # Total commission earned
    statement_count = Column(Integer, default=0)  # Number of statements contributing to this data
    
    # Track which uploads contributed to this commission record
    upload_ids = Column(JSON, nullable=True)  # Array of upload IDs that contributed to this record
    
    # User isolation - each user has their own commission records
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # Nullable for backward compatibility
    
    # Statement date for monthly breakdown
    statement_date = Column(DateTime, nullable=True)  # Date from the statement
    statement_month = Column(Integer, nullable=True)  # Month (1-12) for easier querying
    statement_year = Column(Integer, nullable=True)  # Year for easier querying
    
    # Monthly breakdown columns
    jan_commission = Column(Numeric(15, 2), default=0)
    feb_commission = Column(Numeric(15, 2), default=0)
    mar_commission = Column(Numeric(15, 2), default=0)
    apr_commission = Column(Numeric(15, 2), default=0)
    may_commission = Column(Numeric(15, 2), default=0)
    jun_commission = Column(Numeric(15, 2), default=0)
    jul_commission = Column(Numeric(15, 2), default=0)
    aug_commission = Column(Numeric(15, 2), default=0)
    sep_commission = Column(Numeric(15, 2), default=0)
    oct_commission = Column(Numeric(15, 2), default=0)
    nov_commission = Column(Numeric(15, 2), default=0)
    dec_commission = Column(Numeric(15, 2), default=0)
    
    last_updated = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    
    # Add unique constraint for carrier, client, statement date, AND user_id for proper data isolation
    __table_args__ = (
        UniqueConstraint('carrier_id', 'client_name', 'statement_date', 'user_id', name='uq_carrier_client_date_user_commission'),
    )

class EditedTable(Base):
    __tablename__ = 'edited_tables'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID(as_uuid=True), ForeignKey('statement_uploads.id'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    name = Column(String, nullable=False)
    header = Column(JSON, nullable=False)  # Array of column names
    rows = Column(JSON, nullable=False)    # Array of arrays (table data)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)

class SummaryRowPattern(Base):
    __tablename__ = 'summary_row_patterns'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    
    # Pattern metadata
    pattern_name = Column(String, nullable=False)  # Human-readable name for the pattern
    table_signature = Column(String, nullable=False)  # Hash of table structure for matching
    
    # Pattern characteristics
    column_patterns = Column(JSON, nullable=False)  # Patterns for each column (regex, keywords, etc.)
    row_characteristics = Column(JSON, nullable=False)  # Characteristics that identify summary rows
    
    # Learning data
    sample_rows = Column(JSON, nullable=False)  # Sample rows that were marked as summary
    confidence_score = Column(Integer, default=80)  # Confidence in this pattern (0-100)
    
    # Usage tracking
    usage_count = Column(Integer, default=1)  # How many times this pattern was used
    last_used = Column(DateTime, server_default=text('now()'), nullable=False)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    
    # Add unique constraint for company and pattern name
    __table_args__ = (
        UniqueConstraint('company_id', 'pattern_name', name='uq_summary_row_pattern'),
    )

# Authentication and User Management Models
class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)  # Nullable for first-time admin login
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default='user')  # admin, user, read_only
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    is_verified = Column(Integer, default=0)  # 1 for verified, 0 for unverified
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=True)
    last_login = Column(DateTime, nullable=True)
    
    # OTP Authentication fields
    email_domain = Column(String, nullable=True)  # Extracted from email for faster queries
    is_email_verified = Column(Integer, default=0)  # 1 for verified, 0 for unverified
    auth_method = Column(String, default='password')  # password, otp, both
    access_level = Column(String, default='basic')  # basic, advanced, full
    
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)

class AllowedDomain(Base):
    __tablename__ = 'allowed_domains'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String, unique=True, nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=True)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)

class UserSession(Base):
    __tablename__ = 'user_sessions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    session_token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    last_accessed = Column(DateTime, server_default=text('now()'), nullable=False)

class FileDuplicate(Base):
    __tablename__ = 'file_duplicates'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_hash = Column(String, nullable=False, index=True)  # SHA-256 hash
    original_upload_id = Column(UUID(as_uuid=True), ForeignKey('statement_uploads.id'), nullable=False)
    duplicate_upload_id = Column(UUID(as_uuid=True), ForeignKey('statement_uploads.id'), nullable=False)
    detected_at = Column(DateTime, server_default=text('now()'), nullable=False)
    action_taken = Column(String, default='detected')  # detected, replaced, ignored
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)

class UserDataContribution(Base):
    __tablename__ = 'user_data_contributions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    upload_id = Column(UUID(as_uuid=True), ForeignKey('statement_uploads.id'), nullable=False)
    contribution_type = Column(String, nullable=False)  # upload, edit, approval, etc.
    contribution_data = Column(JSON)  # Store contribution metadata
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)

class OTPRequest(Base):
    __tablename__ = 'otp_requests'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, index=True)
    otp_code = Column(String, nullable=False)  # Hashed OTP for security
    purpose = Column(String, nullable=False)  # login, registration, password_reset
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Integer, default=0)  # 1 for used, 0 for unused
    attempts = Column(Integer, default=0)  # Number of verification attempts
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    used_at = Column(DateTime, nullable=True)
