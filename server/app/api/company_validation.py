"""
Company Name Validation API
Provides endpoints for validating detected company names
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.company_name_service import CompanyNameDetectionService

router = APIRouter(prefix="/api", tags=["company-validation"])

company_detector = CompanyNameDetectionService()


class CompanyValidationRequest(BaseModel):
    company_name: str


class CompanyValidationResponse(BaseModel):
    company_name: str
    is_valid: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    has_suffix: bool
    is_reasonable_length: bool
    has_valid_chars: bool


@router.post("/validate-company-name/")
async def validate_company_name(request: CompanyValidationRequest) -> CompanyValidationResponse:
    """
    Validate a detected company name.
    
    Args:
        request: Company name to validate
        
    Returns:
        Validation result with confidence score and suggestions
    """
    try:
        validation_result = company_detector.validate_company_name(request.company_name)
        
        return CompanyValidationResponse(
            company_name=validation_result["company_name"],
            is_valid=validation_result["is_valid"],
            confidence=validation_result["confidence"],
            issues=validation_result["issues"],
            suggestions=validation_result["suggestions"],
            has_suffix=validation_result["has_suffix"],
            is_reasonable_length=validation_result["is_reasonable_length"],
            has_valid_chars=validation_result["has_valid_chars"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Company validation failed: {str(e)}"
        )


class CompanyDetectionRequest(BaseModel):
    table_data: Dict[str, Any]
    extraction_method: str = "unknown"


class CompanyDetectionResponse(BaseModel):
    detected_companies: List[str]
    company_detection_metadata: Dict[str, Any]
    enhanced_table_data: Dict[str, Any]


@router.post("/detect-companies/")
async def detect_companies_in_table(request: CompanyDetectionRequest) -> CompanyDetectionResponse:
    """
    Detect company names in extracted table data.
    
    Args:
        request: Table data to analyze
        
    Returns:
        Detected companies and enhanced table data
    """
    try:
        enhanced_table = company_detector.detect_company_names_in_extracted_data(
            request.table_data, 
            request.extraction_method
        )
        
        return CompanyDetectionResponse(
            detected_companies=enhanced_table.get("detected_companies", []),
            company_detection_metadata=enhanced_table.get("company_detection_metadata", {}),
            enhanced_table_data=enhanced_table
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Company detection failed: {str(e)}"
        )


class CompanyTransactionMappingRequest(BaseModel):
    rows: List[List[str]]
    companies: List[str]


class CompanyTransactionMappingResponse(BaseModel):
    mapping: Dict[str, List[int]]


@router.post("/create-company-transaction-mapping/")
async def create_company_transaction_mapping(request: CompanyTransactionMappingRequest) -> CompanyTransactionMappingResponse:
    """
    Create mapping between companies and their transaction rows.
    
    Args:
        request: Table rows and detected companies
        
    Returns:
        Mapping of companies to row indices
    """
    try:
        mapping = company_detector.create_company_transaction_mapping(
            request.rows, 
            request.companies
        )
        
        return CompanyTransactionMappingResponse(mapping=mapping)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Company transaction mapping failed: {str(e)}"
        )
