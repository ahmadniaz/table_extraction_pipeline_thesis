from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.db import crud, schemas
from app.config import get_db
from typing import List
from uuid import UUID
from pydantic import BaseModel
from app.services.gcs_utils import generate_gcs_signed_url, gcs_service
from app.dependencies.auth_dependencies import get_current_user_hybrid
from app.db.models import User
import logging

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

class DeleteStatementsRequest(BaseModel):
    statement_ids: List[UUID]

@router.get("/companies/{company_id}/statements/")
async def get_statements_for_company(
    company_id: UUID, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Returns all uploads/statements for a given carrier - ALL DATA (admin or all users' data)"""
    # IMPORTANT: This endpoint fetches ALL statements for a carrier (all users)
    # For user-specific data, use /api/companies/user-specific/{company_id}/statements
    # NOTE: Support both old (company_id) and new (carrier_id) format for backwards compatibility
    
    # Admin can see all statements, regular users should use the user-specific endpoint
    # But for backward compatibility, we'll return all statements here
    statements = await crud.get_statements_for_carrier(db, company_id)
    
    # Convert ORM objects to dict format with gcs_key included
    formatted_statements = []
    for statement in statements:
        formatted_statements.append({
            "id": statement.id,
            "company_id": statement.company_id,
            "file_name": statement.file_name,
            "gcs_key": statement.file_name,  # file_name IS the gcs_key
            "uploaded_at": statement.uploaded_at,
            "status": statement.status,
            "current_step": statement.current_step,
            "final_data": statement.final_data,
            "edited_tables": statement.edited_tables,
            "field_config": statement.field_config,
            "rejection_reason": statement.rejection_reason,
            "plan_types": statement.plan_types,
            "raw_data": statement.raw_data,
            "selected_statement_date": statement.selected_statement_date,
            "last_updated": statement.last_updated
        })
    
    return formatted_statements

# In your CRUD:
async def get_statements_for_company(db, company_id):
    from app.db.models import StatementUpload
    # NOTE: Support both old and new format
    # Old format: carrier stored in company_id, carrier_id is NULL
    # New format: carrier stored in carrier_id
    result = await db.execute(
        select(StatementUpload)
        .where(
            or_(
                StatementUpload.carrier_id == company_id,
                and_(
                    StatementUpload.company_id == company_id,
                    StatementUpload.carrier_id.is_(None)
                )
            )
        )
        .order_by(StatementUpload.uploaded_at.desc())
    )
    return result.scalars().all()


@router.delete("/companies/{company_id}/statements/{statement_id}")
async def delete_statement(
    statement_id: str, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    try:
        statement = await crud.get_statement_by_id(db, statement_id)
        if not statement:
            raise HTTPException(status_code=404, detail="Statement not found")
        
        # Check user authorization: admin can delete any, regular users can only delete their own
        if current_user.role != "admin" and str(statement.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=403, 
                detail="You can only delete your own statements"
            )
        
        await crud.delete_statement(db, statement_id)
        return {"message": "Statement deleted successfully"}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Return error response with 500 status code for unexpected errors
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete statement: {str(e)}"
        )

@router.delete("/companies/{company_id}/statements/")
async def delete_multiple_statements(
    company_id: UUID,
    request: DeleteStatementsRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    statement_ids = request.statement_ids
    deleted_count = 0
    errors = []
    
    try:
        for statement_id in statement_ids:
            try:
                statement = await crud.get_statement_by_id(db, str(statement_id))
                if not statement:
                    errors.append(f"Statement with ID {statement_id} not found")
                    continue
                
                # Check user authorization: admin can delete any, regular users can only delete their own
                if current_user.role != "admin" and str(statement.user_id) != str(current_user.id):
                    errors.append(f"Unauthorized to delete statement {statement_id}")
                    continue
                
                await crud.delete_statement(db, str(statement_id))
                deleted_count += 1
            except Exception as e:
                errors.append(f"Failed to delete statement with ID {statement_id}: {str(e)}")
        
        if errors:
            # Return error response with 400 status code
            raise HTTPException(
                status_code=400, 
                detail=f"Some deletions failed. Deleted: {deleted_count}, Errors: {errors}"
            )
        
        return {"message": f"Successfully deleted {deleted_count} statements"}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Return error response with 500 status code for unexpected errors
        raise HTTPException(
            status_code=500, 
            detail=f"Transaction failed: {str(e)}"
        )

@router.get("/pdf-preview/")
async def get_pdf_preview_url(gcs_key: str, db: AsyncSession = Depends(get_db)):
    """
    Simple endpoint to get a signed URL for PDF preview.
    Returns a time-limited signed URL that can be used directly in an iframe.
    Includes backward compatibility for files uploaded with old path format.
    """
    if not gcs_key:
        logger.error("❌ Missing gcs_key parameter")
        raise HTTPException(status_code=400, detail="gcs_key parameter is required")
    
    logger.info(f"🔍 PDF preview requested for: {gcs_key}")
    
    # Check if GCS service is available
    if not gcs_service.is_available():
        logger.error("❌ GCS service is not available")
        raise HTTPException(status_code=503, detail="GCS service is not available")
    
    # Check if file exists in GCS
    logger.info(f"🔍 Checking if file exists in GCS: {gcs_key}")
    file_exists = gcs_service.file_exists(gcs_key)
    actual_gcs_key = gcs_key
    
    # BACKWARD COMPATIBILITY: If file not found, try to find it using old path format
    if not file_exists:
        logger.warning(f"⚠️ File not found at new path: {gcs_key}")
        logger.info(f"🔄 Attempting backward compatibility lookup...")
        
        # Extract upload_id from path (format: statements/{upload_id}/{filename})
        parts = gcs_key.split('/')
        if len(parts) >= 3 and parts[0] == 'statements':
            upload_id = parts[1]
            filename = '/'.join(parts[2:])  # Handle filenames with slashes
            
            logger.info(f"🔍 Extracted upload_id: {upload_id}, filename: {filename}")
            
            # Get statement from database to find carrier_id
            try:
                statement = await crud.get_statement_by_id(db, upload_id)
                if statement and statement.carrier_id:
                    # Try old path format: statements/{carrier_id}/{filename}
                    old_gcs_key = f"statements/{statement.carrier_id}/{filename}"
                    logger.info(f"🔍 Trying old path format with carrier_id: {old_gcs_key}")
                    
                    if gcs_service.file_exists(old_gcs_key):
                        logger.info(f"✅ File found at old path: {old_gcs_key}")
                        actual_gcs_key = old_gcs_key
                        file_exists = True
                elif statement and statement.company_id:
                    # Try old path format with company_id (even older format)
                    old_gcs_key = f"statements/{statement.company_id}/{filename}"
                    logger.info(f"🔍 Trying older path format with company_id: {old_gcs_key}")
                    
                    if gcs_service.file_exists(old_gcs_key):
                        logger.info(f"✅ File found at older path: {old_gcs_key}")
                        actual_gcs_key = old_gcs_key
                        file_exists = True
            except Exception as e:
                logger.error(f"❌ Error during backward compatibility lookup: {e}")
    
    if not file_exists:
        logger.error(f"❌ PDF file not found in storage (tried new and old paths): {gcs_key}")
        raise HTTPException(status_code=404, detail=f"PDF file not found in storage: {gcs_key}")
    
    logger.info(f"✅ File exists, generating signed URL: {actual_gcs_key}")
    
    # Generate signed URL (valid for 1 hour by default)
    signed_url = generate_gcs_signed_url(actual_gcs_key, expiration_hours=1)
    
    if not signed_url:
        logger.error(f"❌ Could not generate signed URL for: {actual_gcs_key}")
        raise HTTPException(status_code=500, detail="Could not generate signed URL")
    
    logger.info(f"✅ Signed URL generated successfully for: {actual_gcs_key}")
    
    return {
        "url": signed_url,
        "gcs_key": actual_gcs_key,
        "expires_in_hours": 1
    }


@router.get("/statements/{statement_id}/formatted-tables")
async def get_formatted_tables(statement_id: str, db: AsyncSession = Depends(get_db)):
    """Get formatted/edited tables for a statement"""
    try:
        statement = await crud.get_statement_by_id(db, statement_id)
        if not statement:
            raise HTTPException(status_code=404, detail="Statement not found")
        
        # Return edited_tables which contains the formatted tables after table editor
        formatted_tables = statement.edited_tables or []
        
        # If no edited tables, fall back to raw data
        if not formatted_tables and statement.raw_data:
            formatted_tables = statement.raw_data
        
        return {
            "statement_id": statement_id,
            "tables": formatted_tables,
            "table_count": len(formatted_tables)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching formatted tables: {str(e)}")
