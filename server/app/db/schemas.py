from pydantic import BaseModel, field_validator
from typing import Any, List, Optional, Dict
from uuid import UUID
from datetime import datetime

class CompanyBase(BaseModel):
    name: str

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class CompanyFieldMappingBase(BaseModel):
    display_name: str
    column_name: str

class CompanyFieldMappingCreate(CompanyFieldMappingBase):
    company_id: UUID

class CompanyFieldMapping(CompanyFieldMappingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CompanyConfigurationBase(BaseModel):
    field_config: Optional[List[Dict[str, str]]] = None
    plan_types: Optional[List[str]] = None
    table_names: Optional[List[str]] = None

class CompanyConfigurationCreate(CompanyConfigurationBase):
    company_id: UUID

class CompanyConfigurationUpdate(CompanyConfigurationBase):
    pass

class CompanyConfiguration(CompanyConfigurationBase):
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CarrierFormatLearningBase(BaseModel):
    format_signature: str
    headers: List[str]
    header_patterns: Optional[Dict[str, Any]] = None
    column_types: Optional[Dict[str, str]] = None
    column_patterns: Optional[Dict[str, str]] = None
    sample_values: Optional[Dict[str, List[str]]] = None
    table_structure: Optional[Dict[str, Any]] = None
    data_quality_metrics: Optional[Dict[str, Any]] = None
    field_mapping: Optional[Dict[str, str]] = None
    table_editor_settings: Optional[Dict[str, Any]] = None
    confidence_score: int = 0
    usage_count: int = 1

class CarrierFormatLearningCreate(CarrierFormatLearningBase):
    company_id: UUID

class CarrierFormatLearningUpdate(BaseModel):
    header_patterns: Optional[Dict[str, Any]] = None
    column_types: Optional[Dict[str, str]] = None
    column_patterns: Optional[Dict[str, str]] = None
    sample_values: Optional[Dict[str, List[str]]] = None
    table_structure: Optional[Dict[str, Any]] = None
    data_quality_metrics: Optional[Dict[str, Any]] = None
    field_mapping: Optional[Dict[str, str]] = None
    table_editor_settings: Optional[Dict[str, Any]] = None
    confidence_score: Optional[int] = None
    usage_count: Optional[int] = None

class CarrierFormatLearning(CarrierFormatLearningBase):
    id: UUID
    company_id: UUID
    last_used: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StatementUpload(BaseModel):
    id: UUID
    company_id: UUID  # User's company
    carrier_id: Optional[UUID] = None  # Insurance carrier company
    user_id: UUID  # User who uploaded the file
    file_name: str
    file_hash: Optional[str] = None  # SHA-256 hash for duplicate detection
    file_size: Optional[int] = None  # File size in bytes
    uploaded_at: datetime
    
    # Status Management
    status: str  # pending, approved, rejected, processing
    current_step: str  # upload, table_editor, field_mapper, dashboard, completed
    
    # Progress Data Storage
    progress_data: Optional[Dict[str, Any]] = None
    raw_data: Optional[List[Dict[str, Any]]] = None
    edited_tables: Optional[List[Dict[str, Any]]] = None
    field_mapping: Optional[Dict[str, Any]] = None
    final_data: Optional[List[Dict[str, Any]]] = None
    
    # Metadata
    mapping_used: Optional[Dict[str, Any]] = None
    field_config: Optional[Any] = None  # Can be list or dict to handle both old and new formats
    rejection_reason: Optional[str] = None
    plan_types: Optional[List[str]] = None
    selected_statement_date: Optional[Dict[str, Any]] = None
    
    # Timestamps
    last_updated: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # User session tracking
    session_id: Optional[str] = None
    auto_save_enabled: bool = True

    class Config:
        from_attributes = True

class StatementUploadCreate(BaseModel):
    company_id: UUID  # User's company
    carrier_id: Optional[UUID] = None  # Insurance carrier company
    user_id: UUID  # User who uploaded the file
    file_name: str
    file_hash: Optional[str] = None  # SHA-256 hash for duplicate detection
    file_size: Optional[int] = None  # File size in bytes
    status: str = "pending"
    current_step: str = "upload"
    progress_data: Optional[Dict[str, Any]] = None

class StatementUploadUpdate(BaseModel):
    status: Optional[str] = None
    current_step: Optional[str] = None
    carrier_id: Optional[UUID] = None  # Insurance carrier company
    progress_data: Optional[Dict[str, Any]] = None
    raw_data: Optional[List[Dict[str, Any]]] = None
    edited_tables: Optional[List[Dict[str, Any]]] = None
    field_mapping: Optional[Dict[str, Any]] = None
    final_data: Optional[List[Dict[str, Any]]] = None
    field_config: Optional[Any] = None  # Can be list or dict to handle both old and new formats
    rejection_reason: Optional[str] = None
    plan_types: Optional[List[str]] = None
    selected_statement_date: Optional[Dict[str, Any]] = None
    ai_intelligence: Optional[Dict[str, Any]] = None  # AI intelligence data (table selection, field mapping, plan detection)
    session_id: Optional[str] = None
    auto_save_enabled: Optional[bool] = None

class ExtractionCreate(BaseModel):
    company_id: str
    filename: str
    s3_url: str
    total_tables: int
    valid_tables: int
    quality_score: float
    confidence: str
    extraction_metadata: Dict[str, Any]
    quality_metadata: Dict[str, Any]

class Extraction(ExtractionCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# app/api/schemas.py

class StatementReview(BaseModel):
    id: UUID
    company_id: UUID
    file_name: str
    uploaded_at: datetime
    status: str  # "Approved" | "Rejected" | "Pending"
    current_step: str  # Current step in the process
    final_data: Optional[List[Dict[str, Any]]] = None
    edited_tables: Optional[List[Dict[str, Any]]] = None  # Include edited tables for preview
    field_config: Optional[Any] = None  # Can be list or dict to handle both old and new formats
    rejection_reason: Optional[str] = None
    plan_types: Optional[List[str]] = None
    raw_data: Optional[List[Dict[str, Any]]] = None
    selected_statement_date: Optional[Dict[str, Any]] = None
    last_updated: datetime

    class Config:
        from_attributes = True  # For Pydantic v2

class PendingFile(BaseModel):
    id: UUID
    company_id: UUID
    file_name: str
    uploaded_at: datetime
    current_step: str
    last_updated: datetime
    progress_summary: Optional[str] = None  # Human-readable summary of progress

    class Config:
        from_attributes = True

class MappingConfig(BaseModel):
    mapping: Dict[str, str]
    plan_types: List[str] = []
    table_names: List[str] = []
    field_config: List[Dict[str, str]] = []

class DatabaseFieldBase(BaseModel):
    display_name: str
    description: Optional[str] = None
    is_active: bool = True

class DatabaseFieldCreate(DatabaseFieldBase):
    pass

class DatabaseFieldUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class DatabaseField(DatabaseFieldBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PlanTypeBase(BaseModel):
    display_name: str
    description: Optional[str] = None
    is_active: bool = True

class PlanTypeCreate(PlanTypeBase):
    pass

class PlanTypeUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class PlanType(PlanTypeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EarnedCommissionBase(BaseModel):
    carrier_id: UUID
    client_name: str
    invoice_total: float
    commission_earned: float
    statement_count: int
    upload_ids: Optional[List[str]] = []
    user_id: Optional[UUID] = None  # NEW: User ID for data isolation
    statement_date: Optional[datetime] = None
    statement_month: Optional[int] = None
    statement_year: Optional[int] = None
    jan_commission: float = 0
    feb_commission: float = 0
    mar_commission: float = 0
    apr_commission: float = 0
    may_commission: float = 0
    jun_commission: float = 0
    jul_commission: float = 0
    aug_commission: float = 0
    sep_commission: float = 0
    oct_commission: float = 0
    nov_commission: float = 0
    dec_commission: float = 0

class EarnedCommissionCreate(EarnedCommissionBase):
    pass

class EarnedCommissionUpdate(BaseModel):
    invoice_total: Optional[float] = None
    commission_earned: Optional[float] = None
    statement_count: Optional[int] = None
    upload_ids: Optional[List[str]] = None
    statement_date: Optional[datetime] = None
    statement_month: Optional[int] = None
    statement_year: Optional[int] = None
    jan_commission: Optional[float] = None
    feb_commission: Optional[float] = None
    mar_commission: Optional[float] = None
    apr_commission: Optional[float] = None
    may_commission: Optional[float] = None
    jun_commission: Optional[float] = None
    jul_commission: Optional[float] = None
    aug_commission: Optional[float] = None
    sep_commission: Optional[float] = None
    oct_commission: Optional[float] = None
    nov_commission: Optional[float] = None
    dec_commission: Optional[float] = None

class EarnedCommission(EarnedCommissionBase):
    id: UUID
    last_updated: datetime
    created_at: datetime

    class Config:
        from_attributes = True

# New schemas for multi-user functionality
class FileDuplicateBase(BaseModel):
    file_hash: str
    original_upload_id: UUID
    duplicate_upload_id: UUID
    action_taken: str = "detected"

class FileDuplicateCreate(FileDuplicateBase):
    pass

class FileDuplicate(FileDuplicateBase):
    id: UUID
    detected_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class UserDataContributionBase(BaseModel):
    user_id: UUID
    upload_id: UUID
    contribution_type: str
    contribution_data: Optional[Dict[str, Any]] = None

class UserDataContributionCreate(UserDataContributionBase):
    pass

class UserDataContribution(UserDataContributionBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# User profile and statistics schemas
class UserProfile(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    company_id: Optional[UUID] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserStats(BaseModel):
    user_id: UUID
    total_uploads: int
    total_approved: int
    total_rejected: int
    total_pending: int
    total_commission_contributed: float
    last_upload_date: Optional[datetime] = None
    data_contribution_percentage: float  # Percentage of total system data

    class Config:
        from_attributes = True


# Admin schemas
class DomainManagementRequest(BaseModel):
    domain: str
    company_id: Optional[UUID] = None
    is_active: bool = True

class AllowedDomainResponse(BaseModel):
    id: UUID
    domain: str
    company_id: Optional[UUID]
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @field_validator('is_active', mode='before')
    @classmethod
    def convert_is_active(cls, v):
        if isinstance(v, int):
            return bool(v)
        return v

    class Config:
        from_attributes = True


