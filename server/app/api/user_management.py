"""
User Management API Endpoints

This module provides API endpoints for user profile management,
statistics, and multi-user functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.db.database import get_db
from app.db.models import User
from app.dependencies.auth_dependencies import get_current_user
from app.services.user_profile_service import UserProfileService
from app.services.duplicate_detection_service import DuplicateDetectionService
from app.db.schemas import UserProfile, UserStats

router = APIRouter(prefix="/api/user", tags=["user-management"])

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile information."""
    try:
        profile_service = UserProfileService(db)
        profile = await profile_service.get_user_profile(current_user.id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        return profile
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user profile: {str(e)}"
        )

@router.get("/stats", response_model=UserStats)
async def get_user_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's statistics and contribution data."""
    try:
        profile_service = UserProfileService(db)
        stats = await profile_service.get_user_statistics(current_user.id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User statistics not found"
            )
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user statistics: {str(e)}"
        )

@router.get("/contributions")
async def get_user_contributions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's contribution history."""
    try:
        profile_service = UserProfileService(db)
        contributions = await profile_service.get_user_contribution_history(
            current_user.id, limit
        )
        
        return {
            "contributions": contributions,
            "total_count": len(contributions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving contributions: {str(e)}"
        )

@router.get("/activity")
async def get_user_activity(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's activity summary."""
    try:
        profile_service = UserProfileService(db)
        activity = await profile_service.get_user_activity_summary(current_user.id)
        
        return activity
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user activity: {str(e)}"
        )

@router.get("/duplicates")
async def get_user_duplicates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's duplicate detection history."""
    try:
        duplicate_service = DuplicateDetectionService(db)
        duplicates = await duplicate_service.get_duplicate_history(current_user.id)
        
        return {
            "duplicates": duplicates,
            "total_count": len(duplicates)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving duplicate history: {str(e)}"
        )

@router.get("/uploads")
async def get_user_uploads(
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's uploads with optional status filtering."""
    try:
        from sqlalchemy import select, and_
        from app.db.models import StatementUpload, Company
        
        query = select(StatementUpload, Company.name.label('company_name'))
        query = query.join(Company, StatementUpload.company_id == Company.id)
        query = query.where(StatementUpload.user_id == current_user.id)
        
        if status_filter:
            query = query.where(StatementUpload.status == status_filter)
        
        query = query.order_by(StatementUpload.uploaded_at.desc()).limit(limit)
        
        result = await db.execute(query)
        uploads = result.all()
        
        formatted_uploads = []
        for upload, company_name in uploads:
            formatted_uploads.append({
                "id": str(upload.id),
                "file_name": upload.file_name,
                "company_name": company_name,
                "status": upload.status,
                "current_step": upload.current_step,
                "uploaded_at": upload.uploaded_at.isoformat() if upload.uploaded_at else None,
                "last_updated": upload.last_updated.isoformat() if upload.last_updated else None,
                "completed_at": upload.completed_at.isoformat() if upload.completed_at else None,
                "file_size": upload.file_size,
                "file_hash": upload.file_hash
            })
        
        return {
            "uploads": formatted_uploads,
            "total_count": len(formatted_uploads)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user uploads: {str(e)}"
        )

# Admin endpoints
@router.get("/admin/system-stats")
async def get_system_user_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide user statistics (admin only)."""
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        profile_service = UserProfileService(db)
        stats = await profile_service.get_system_user_statistics()
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving system statistics: {str(e)}"
        )

@router.get("/admin/duplicate-stats")
async def get_duplicate_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide duplicate detection statistics (admin only)."""
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        duplicate_service = DuplicateDetectionService(db)
        stats = await duplicate_service.get_duplicate_statistics()
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving duplicate statistics: {str(e)}"
        )
