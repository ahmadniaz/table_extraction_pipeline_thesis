"""
AI Intelligent Mapping API Endpoints

These endpoints provide AI-powered field mapping and plan type detection
for the commission tracker upload flow.

Features:
- Real-time AI field mapping suggestions
- Intelligent plan type detection
- Confidence scoring and alternatives
- User correction learning
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_db
from app.dependencies.auth_dependencies import get_current_user_hybrid
from app.db.models import User
from app.services.ai_field_mapping_service import AIFieldMappingService
from app.services.ai_plan_type_detection_service import AIPlanTypeDetectionService
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID
import logging

router = APIRouter(prefix="/api", tags=["ai-intelligent-mapping"])
logger = logging.getLogger(__name__)

# Initialize services
ai_field_mapping_service = AIFieldMappingService()
ai_plan_type_service = AIPlanTypeDetectionService()


# Pydantic models for request/response
class FieldMappingRequest(BaseModel):
    """Request model for AI field mapping"""
    extracted_headers: List[str]
    table_sample_data: List[List[str]]
    carrier_id: Optional[str] = None
    document_context: Optional[Dict[str, Any]] = None


class PlanTypeDetectionRequest(BaseModel):
    """Request model for AI plan type detection"""
    document_context: Dict[str, Any]
    table_headers: List[str]
    table_sample_data: List[List[str]]
    extracted_carrier: Optional[str] = None


class UserCorrectionRequest(BaseModel):
    """Request model for saving user corrections"""
    upload_id: str
    carrier_id: Optional[str] = None
    original_mappings: Dict[str, str]
    corrected_mappings: Dict[str, str]
    headers: List[str]


@router.post("/ai/map-fields")
async def ai_map_fields(
    request: FieldMappingRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-powered field mapping suggestions
    
    This endpoint uses Mistral AI to intelligently map extracted table headers
    to database fields without relying on hardcoded patterns.
    
    Args:
        request: Field mapping request with headers and sample data
        current_user: Authenticated user
        db: Database session
        
    Returns:
        AI-generated field mappings with confidence scores and reasoning
    """
    try:
        logger.info(f"🤖 AI Mapping Request: User {current_user.email} requesting field mapping for {len(request.extracted_headers)} headers")
        
        # Validate request
        if not request.extracted_headers:
            raise HTTPException(
                status_code=400,
                detail="No headers provided for mapping"
            )
        
        # Convert carrier_id to UUID if provided
        carrier_uuid = None
        if request.carrier_id:
            try:
                carrier_uuid = UUID(request.carrier_id)
            except ValueError:
                logger.warning(f"Invalid carrier_id format: {request.carrier_id}")
        
        # Get AI field mappings
        result = await ai_field_mapping_service.get_intelligent_field_mappings(
            db=db,
            extracted_headers=request.extracted_headers,
            table_sample_data=request.table_sample_data,
            carrier_id=carrier_uuid,
            document_context=request.document_context
        )
        
        if not result.get("success"):
            logger.error(f"AI mapping failed: {result.get('error')}")
            raise HTTPException(
                status_code=503,
                detail=f"AI field mapping failed: {result.get('error')}"
            )
        
        logger.info(f"✅ AI Mapping Success: Generated {result.get('suggestions_count', 0)} mappings with {result.get('overall_confidence', 0):.2f} confidence")
        
        return {
            "success": True,
            "mappings": result.get("mappings", []),
            "unmapped_fields": result.get("unmapped_fields", []),
            "overall_confidence": result.get("overall_confidence", 0.0),
            "reasoning": result.get("reasoning", {}),
            "statistics": result.get("mapping_statistics", {}),
            "learned_format_used": result.get("learned_format_used", False),
            "timestamp": result.get("timestamp")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Field mapping endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Field mapping failed: {str(e)}"
        )


@router.post("/ai/detect-plan-types")
async def ai_detect_plan_types(
    request: PlanTypeDetectionRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-powered plan type detection
    
    This endpoint uses Mistral AI to intelligently detect insurance plan types
    without relying on hardcoded keyword lists.
    
    Args:
        request: Plan type detection request with document context and table data
        current_user: Authenticated user
        db: Database session
        
    Returns:
        AI-detected plan types with confidence scores and reasoning
    """
    try:
        logger.info(f"🔍 AI Plan Detection Request: User {current_user.email} requesting plan type detection")
        
        # Validate request
        if not request.table_headers:
            raise HTTPException(
                status_code=400,
                detail="No table headers provided for plan type detection"
            )
        
        # Get AI plan type detection
        result = await ai_plan_type_service.detect_plan_types(
            db=db,
            document_context=request.document_context,
            table_headers=request.table_headers,
            table_sample_data=request.table_sample_data,
            extracted_carrier=request.extracted_carrier
        )
        
        if not result.get("success"):
            logger.error(f"AI plan type detection failed: {result.get('error')}")
            raise HTTPException(
                status_code=503,
                detail=f"AI plan type detection failed: {result.get('error')}"
            )
        
        detected_count = len(result.get("detected_plan_types", []))
        logger.info(f"✅ AI Plan Detection Success: Detected {detected_count} plan types with {result.get('overall_confidence', 0):.2f} confidence")
        
        return {
            "success": True,
            "detected_plan_types": result.get("detected_plan_types", []),
            "overall_confidence": result.get("overall_confidence", 0.0),
            "reasoning": result.get("reasoning", {}),
            "multi_plan_document": result.get("multi_plan_document", False),
            "statistics": result.get("detection_statistics", {}),
            "timestamp": result.get("timestamp")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plan type detection endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Plan type detection failed: {str(e)}"
        )


@router.post("/ai/enhanced-extraction-analysis")
async def enhanced_extraction_analysis(
    request: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """
    Comprehensive AI analysis combining field mapping and plan type detection
    
    This endpoint performs both field mapping and plan type detection in a single call,
    providing a complete AI-powered analysis of the extracted data.
    
    Args:
        request: Combined request with headers, sample data, and document context
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Combined AI analysis with field mappings and plan type detections
    """
    try:
        logger.info(f"🚀 Enhanced AI Analysis Request: User {current_user.email}")
        
        # Extract request data
        extracted_headers = request.get("extracted_headers", [])
        table_sample_data = request.get("table_sample_data", [])
        document_context = request.get("document_context", {})
        carrier_id = request.get("carrier_id")
        extracted_carrier = request.get("extracted_carrier")
        
        # Validate request
        if not extracted_headers:
            raise HTTPException(
                status_code=400,
                detail="No headers provided for analysis"
            )
        
        # Convert carrier_id to UUID if provided
        carrier_uuid = None
        if carrier_id:
            try:
                carrier_uuid = UUID(carrier_id)
            except ValueError:
                logger.warning(f"Invalid carrier_id format: {carrier_id}")
        
        # Perform AI analysis sequentially to avoid database session conflicts
        # Note: Running these sequentially avoids "concurrent operations not permitted" error
        # since both services need to use the database session
        
        # First, get field mappings
        field_mapping_result = await ai_field_mapping_service.get_intelligent_field_mappings(
            db=db,
            extracted_headers=extracted_headers,
            table_sample_data=table_sample_data,
            carrier_id=carrier_uuid,
            document_context=document_context
        )
        
        # Then, get plan type detection
        plan_type_result = await ai_plan_type_service.detect_plan_types(
            db=db,
            document_context=document_context,
            table_headers=extracted_headers,
            table_sample_data=table_sample_data,
            extracted_carrier=extracted_carrier
        )
        
        # Validate results (no exception handling needed since we're not using gather anymore)
        # If either service fails, it will raise an exception that will be caught by the outer try-except
        
        # Calculate overall analysis confidence
        overall_confidence = 0.0
        confidence_count = 0
        
        if field_mapping_result.get("success"):
            overall_confidence += field_mapping_result.get("overall_confidence", 0.0)
            confidence_count += 1
        
        if plan_type_result.get("success"):
            overall_confidence += plan_type_result.get("overall_confidence", 0.0)
            confidence_count += 1
        
        if confidence_count > 0:
            overall_confidence /= confidence_count
        
        logger.info(f"✅ Enhanced AI Analysis Complete: Overall confidence {overall_confidence:.2f}")
        
        return {
            "success": True,
            "field_mapping": {
                "success": field_mapping_result.get("success", False),
                "mappings": field_mapping_result.get("mappings", []),
                "unmapped_fields": field_mapping_result.get("unmapped_fields", []),
                "confidence": field_mapping_result.get("overall_confidence", 0.0),
                "learned_format_used": field_mapping_result.get("learned_format_used", False)
            },
            "plan_type_detection": {
                "success": plan_type_result.get("success", False),
                "detected_plan_types": plan_type_result.get("detected_plan_types", []),
                "confidence": plan_type_result.get("overall_confidence", 0.0),
                "multi_plan_document": plan_type_result.get("multi_plan_document", False)
            },
            "overall_confidence": overall_confidence,
            "analysis_complete": field_mapping_result.get("success", False) or plan_type_result.get("success", False),
            "timestamp": request.get("timestamp")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced extraction analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Enhanced extraction analysis failed: {str(e)}"
        )


@router.post("/ai/save-user-corrections")
async def save_user_corrections(
    request: UserCorrectionRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """
    Save user corrections to improve AI learning
    
    This endpoint allows the system to learn from user corrections,
    improving future mapping suggestions.
    
    Args:
        request: User correction data
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success status
    """
    try:
        logger.info(f"📚 Learning from User Corrections: User {current_user.email}, Upload {request.upload_id}")
        
        # Convert IDs to UUID
        upload_uuid = UUID(request.upload_id)
        carrier_uuid = UUID(request.carrier_id) if request.carrier_id else None
        
        # Save corrections for learning
        success = await ai_field_mapping_service.save_user_corrections(
            db=db,
            upload_id=upload_uuid,
            carrier_id=carrier_uuid,
            original_mappings=request.original_mappings,
            corrected_mappings=request.corrected_mappings,
            headers=request.headers
        )
        
        if not success:
            logger.warning("Failed to save user corrections")
            return {
                "success": False,
                "message": "Failed to save corrections for learning"
            }
        
        logger.info("✅ User corrections saved successfully - AI will learn from this")
        
        return {
            "success": True,
            "message": "User corrections saved successfully. The AI will use this to improve future suggestions."
        }
        
    except ValueError as e:
        logger.error(f"Invalid UUID format: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ID format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to save user corrections: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save corrections: {str(e)}"
        )


@router.get("/ai/service-status")
async def get_ai_services_status(
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Get status of AI intelligent mapping services
    
    Returns:
        Status information for field mapping and plan type detection services
    """
    try:
        field_mapping_status = ai_field_mapping_service.get_service_status()
        plan_type_status = ai_plan_type_service.get_service_status()
        
        return {
            "success": True,
            "services": {
                "field_mapping": field_mapping_status,
                "plan_type_detection": plan_type_status
            },
            "overall_status": "active" if (
                field_mapping_status.get("status") == "active" and 
                plan_type_status.get("status") == "active"
            ) else "degraded",
            "ai_intelligence_enabled": ai_field_mapping_service.is_available() and ai_plan_type_service.is_available()
        }
        
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get service status: {str(e)}"
        )

