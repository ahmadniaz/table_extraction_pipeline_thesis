import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import crud
from app.config import get_db
from app.db.schemas import PendingFile, StatementUploadUpdate
from app.db.models import User
from app.dependencies.auth_dependencies import get_current_user
from uuid import UUID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/pending", tags=["pending"])

@router.get("/files/{company_id}")
async def get_pending_files(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending files for a specific company - automatically filters by user data for regular users.
    """
    try:
        # For admin users, show all files. For regular users, show only their files
        is_admin = current_user.role == 'admin'
        
        if is_admin:
            pending_files = await crud.get_pending_files_for_company(db, company_id)
        else:
            pending_files = await crud.get_pending_files_for_company_by_user(db, company_id, current_user.id)
        
        return JSONResponse({
            "success": True,
            "pending_files": [{
                "id": str(file.id),
                "company_id": str(file.company_id),
                "file_name": file.file_name,
                "uploaded_at": file.uploaded_at.isoformat() if file.uploaded_at else None,
                "current_step": file.current_step,
                "last_updated": file.last_updated.isoformat() if file.last_updated else None,
                "progress_summary": file.progress_summary
            } for file in pending_files],
            "count": len(pending_files),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting pending files for company {company_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pending files: {str(e)}"
        )

@router.get("/files/single/{upload_id}")
async def get_pending_file(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single pending file by upload ID - automatically filters by user data for regular users.
    """
    try:
        upload = await crud.get_statement_upload_by_id(db, upload_id)
        
        if not upload:
            raise HTTPException(
                status_code=404,
                detail="Upload not found"
            )
        
        # For regular users, ensure they can only access their own uploads
        is_admin = current_user.role == 'admin'
        if not is_admin and upload.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only access your own uploads"
            )
        
        return JSONResponse({
            "success": True,
            "upload": {
                "id": str(upload.id),
                "company_id": str(upload.company_id),
                "file_name": upload.file_name,
                "uploaded_at": upload.uploaded_at.isoformat() if upload.uploaded_at else None,
                "status": upload.status,
                "current_step": upload.current_step,
                "progress_data": upload.progress_data,
                "raw_data": upload.raw_data,
                "edited_tables": upload.edited_tables,
                "field_mapping": upload.field_mapping,
                "final_data": upload.final_data,
                "mapping_used": upload.mapping_used,
                "field_config": upload.field_config,
                "rejection_reason": upload.rejection_reason,
                "plan_types": upload.plan_types,
                "last_updated": upload.last_updated.isoformat() if upload.last_updated else None,
                "completed_at": upload.completed_at.isoformat() if upload.completed_at else None,
                "session_id": upload.session_id,
                "auto_save_enabled": upload.auto_save_enabled
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending file {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pending file: {str(e)}"
        )

@router.get("/resume/{upload_id}")
async def resume_upload_session(
    upload_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Resume an upload session with all saved progress data.
    """
    try:
        session_data = await crud.resume_upload_session(db, upload_id)
        
        if not session_data:
            raise HTTPException(
                status_code=404,
                detail="Upload session not found or not in pending status"
            )
        
        return JSONResponse({
            "success": True,
            "session_data": session_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming upload session {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume upload session: {str(e)}"
        )

@router.post("/save-progress/{upload_id}")
async def save_progress(
    upload_id: UUID,
    step: str = Query(..., description="Current step in the process"),
    data: Dict[str, Any] = None,
    session_id: Optional[str] = Query(None, description="User session ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Save progress data for a specific step.
    """
    try:
        success = await crud.save_progress_data(db, upload_id, step, data or {}, session_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Upload not found"
            )
        
        return JSONResponse({
            "success": True,
            "message": f"Progress saved for step: {step}",
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving progress for upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save progress: {str(e)}"
        )

@router.get("/progress/{upload_id}/{step}")
async def get_progress(
    upload_id: str,
    step: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get progress data for a specific step.
    """
    try:
        # Try to convert string to UUID if it's a valid UUID format
        try:
            upload_id_uuid = UUID(upload_id)
        except (ValueError, AttributeError):
            # If not a valid UUID, it might be a custom format - try to find by string ID
            raise HTTPException(
                status_code=400,
                detail=f"Invalid upload_id format. Expected UUID, got: {upload_id}"
            )
        
        progress_data = await crud.get_progress_data(db, upload_id_uuid, step)
        
        return JSONResponse({
            "success": True,
            "progress_data": progress_data,
            "step": step,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting progress for upload {upload_id}, step {step}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get progress: {str(e)}"
        )

@router.put("/update/{upload_id}")
async def update_upload(
    upload_id: UUID,
    update_data: StatementUploadUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update upload with new data and status changes.
    """
    try:
        updated_upload = await crud.update_statement_upload(db, upload_id, update_data)
        
        if not updated_upload:
            raise HTTPException(
                status_code=404,
                detail="Upload not found"
            )
        
        return JSONResponse({
            "success": True,
            "message": "Upload updated successfully",
            "upload_id": str(upload_id),
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update upload: {str(e)}"
        )

@router.delete("/delete/{upload_id}")
async def delete_pending_upload(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a pending upload - users can only delete their own pending uploads.
    """
    try:
        # First, get the upload to check ownership
        upload = await crud.get_statement_upload_by_id(db, upload_id)
        
        if not upload:
            raise HTTPException(
                status_code=404,
                detail="Pending upload not found"
            )
        
        # Check user authorization: admin can delete any, regular users can only delete their own
        if current_user.role != "admin" and str(upload.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own pending uploads"
            )
        
        success = await crud.delete_pending_upload(db, upload_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Pending upload not found"
            )
        
        return JSONResponse({
            "success": True,
            "message": "Pending upload deleted successfully",
            "upload_id": str(upload_id),
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pending upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete pending upload: {str(e)}"
        )

@router.get("/status/{upload_id}")
async def get_upload_status(
    upload_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current status and progress of an upload.
    """
    try:
        upload = await crud.get_statement_upload_by_id(db, upload_id)
        
        if not upload:
            raise HTTPException(
                status_code=404,
                detail="Upload not found"
            )
        
        # Generate progress summary
        progress_summary = crud.get_progress_summary(upload.current_step, upload.progress_data)
        
        return JSONResponse({
            "success": True,
            "status": {
                "id": str(upload.id),
                "company_id": str(upload.company_id),
                "file_name": upload.file_name,
                "status": upload.status,
                "current_step": upload.current_step,
                "progress_summary": progress_summary,
                "uploaded_at": upload.uploaded_at.isoformat() if upload.uploaded_at else None,
                "last_updated": upload.last_updated.isoformat() if upload.last_updated else None,
                "completed_at": upload.completed_at.isoformat() if upload.completed_at else None
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get upload status: {str(e)}"
        )

@router.post("/auto-save/{upload_id}")
async def auto_save_progress(
    upload_id: UUID,
    step: str = Query(..., description="Current step in the process"),
    data: Dict[str, Any] = None,
    session_id: Optional[str] = Query(None, description="User session ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-save progress data (same as save-progress but with auto-save semantics).
    """
    try:
        success = await crud.save_progress_data(db, upload_id, step, data or {}, session_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Upload not found"
            )
        
        return JSONResponse({
            "success": True,
            "message": f"Auto-save completed for step: {step}",
            "auto_saved": True,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-saving progress for upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to auto-save progress: {str(e)}"
        ) 