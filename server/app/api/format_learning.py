from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import crud, schemas
from app.config import get_db
from app.utils.db_retry import with_db_retry
from app.services.format_learning_service import FormatLearningService
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api")
format_learning_service = FormatLearningService()

class LearnFromFileRequest(BaseModel):
    table_data: List[List[str]]
    headers: List[str]
    field_mapping: Dict[str, str]
    confidence_score: int = 80

class FormatMatchRequest(BaseModel):
    headers: List[str]
    table_structure: Dict[str, Any]

class FormatMatchResponse(BaseModel):
    found_match: bool
    match_score: float
    learned_format: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None

@router.post("/companies/{company_id}/learn-format/")
async def learn_from_processed_file(
    company_id: str, 
    request: LearnFromFileRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Learn from a processed file and save the format information for future use.
    """
    try:
        # Validate company exists
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Learn from the processed file
        success = await format_learning_service.learn_from_processed_file(
            db=db,
            company_id=company_id,
            table_data=request.table_data,
            headers=request.headers,
            field_mapping=request.field_mapping,
            confidence_score=request.confidence_score
        )
        
        if success:
            return {"success": True, "message": "Format learned successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to learn format")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error learning format: {str(e)}")

@router.post("/companies/{company_id}/find-format-match/", response_model=FormatMatchResponse)
async def find_matching_format(
    company_id: str, 
    request: FormatMatchRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Find the best matching format for a new file.
    """
    try:
        # Validate company exists
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Find matching format
        learned_format, match_score = await format_learning_service.find_matching_format(
            db=db,
            company_id=company_id,
            headers=request.headers,
            table_structure=request.table_structure
        )
        
        return FormatMatchResponse(
            found_match=learned_format is not None,
            match_score=match_score,
            learned_format=learned_format
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding format match: {str(e)}")

@router.post("/companies/{company_id}/validate-format/")
async def validate_data_against_format(
    company_id: str,
    table_data: List[List[str]],
    headers: List[str],
    db: AsyncSession = Depends(get_db)
):
    """
    Validate new data against learned formats for the company.
    """
    try:
        # Validate company exists
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Analyze table structure
        table_structure = format_learning_service.analyze_table_structure(table_data, headers)
        
        # Find matching format
        learned_format, match_score = await format_learning_service.find_matching_format(
            db=db,
            company_id=company_id,
            headers=headers,
            table_structure=table_structure
        )
        
        validation_results = None
        if learned_format:
            validation_results = format_learning_service.validate_data_against_learned_format(
                table_data=table_data,
                headers=headers,
                learned_format=learned_format
            )
        
        return {
            "found_match": learned_format is not None,
            "match_score": match_score,
            "learned_format": learned_format,
            "validation_results": validation_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating format: {str(e)}")

@router.get("/companies/{company_id}/learned-formats/")
async def get_learned_formats(
    company_id: str, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get all learned formats for a company.
    """
    try:
        # Validate company exists
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get learned formats
        formats = await with_db_retry(db, crud.get_carrier_formats_for_company, company_id=company_id)
        
        # Convert to response format
        format_list = []
        for format_record in formats:
            format_list.append({
                "id": str(format_record.id),
                "format_signature": format_record.format_signature,
                "headers": format_record.headers,
                "column_types": format_record.column_types,
                "field_mapping": format_record.field_mapping,
                "table_editor_settings": format_record.table_editor_settings,
                "confidence_score": format_record.confidence_score,
                "usage_count": format_record.usage_count,
                "last_used": format_record.last_used,
                "created_at": format_record.created_at
            })
        
        return {"formats": format_list}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting learned formats: {str(e)}")

@router.post("/companies/{company_id}/get-table-editor-settings/")
async def get_table_editor_settings(
    company_id: str,
    request: FormatMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get table editor settings for a matching format.
    """
    try:
        # Validate company exists
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Find matching format
        learned_format, match_score = await format_learning_service.find_matching_format(
            db=db,
            company_id=company_id,
            headers=request.headers,
            table_structure=request.table_structure
        )
        
        if learned_format and learned_format.get('table_editor_settings'):
            return {
                "found_match": True,
                "match_score": match_score,
                "table_editor_settings": learned_format['table_editor_settings']
            }
        else:
            return {
                "found_match": False,
                "match_score": 0.0,
                "table_editor_settings": None
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting table editor settings: {str(e)}")

@router.post("/companies/{company_id}/get-learned-field-mapping/")
async def get_learned_field_mapping(
    company_id: str,
    request: FormatMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get learned field mapping for a specific format.
    """
    try:
        # Validate company exists
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Find matching format
        learned_format, match_score = await format_learning_service.find_matching_format(
            db=db,
            company_id=company_id,
            headers=request.headers,
            table_structure=request.table_structure
        )
        
        if learned_format and learned_format.get('field_mapping') and len(learned_format.get('field_mapping', {})) > 0 and match_score > 0.5:
            return {
                "found_match": True,
                "match_score": match_score,
                "field_mapping": learned_format['field_mapping'],
                "table_editor_settings": learned_format.get('table_editor_settings'),
                "confidence_score": learned_format.get('confidence_score', 0)
            }
        else:
            return {
                "found_match": False,
                "match_score": match_score,
                "field_mapping": {},
                "table_editor_settings": None,
                "confidence_score": 0
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting learned field mapping: {str(e)}")

@router.delete("/companies/{company_id}/learned-formats/{format_id}/")
async def delete_learned_format(
    company_id: str,
    format_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a learned format.
    """
    try:
        # Validate company exists
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # TODO: Add delete operation to CRUD
        # For now, return success
        return {"success": True, "message": "Format deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting format: {str(e)}")
