"""
Minimal Authentication API Endpoints

This module provides only the missing endpoints that the client needs:
- /auth/me
- /auth/permissions
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.db.database import get_db
from app.db.models import User
from app.db.otp_schemas import UserProfileSchema
from app.services.jwt_service import jwt_service
from app.utils.auth_utils import get_user_by_email

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Dependency to get current user from OTP authentication
async def get_current_user_otp(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from httpOnly cookies"""
    access_token = request.cookies.get("access_token")
    
    # Debug logging for cookie issues
    all_cookies = dict(request.cookies)
    print(f"🔍 Debug - All cookies received: {list(all_cookies.keys())}")
    print(f"🔍 Debug - Access token present: {bool(access_token)}")
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = jwt_service.verify_token(access_token, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = await get_user_by_email(db, payload["email"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if user.is_active == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    return user

@router.get("/me", response_model=UserProfileSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_user_otp)
):
    """Get current user information"""
    return UserProfileSchema(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        is_active=bool(current_user.is_active),
        is_verified=bool(current_user.is_verified),
        is_email_verified=bool(current_user.is_email_verified),
        company_id=str(current_user.company_id) if current_user.company_id else None,
        access_level=current_user.access_level,
        auth_method=current_user.auth_method,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@router.get("/permissions")
async def get_user_permissions(
    current_user: User = Depends(get_current_user_otp)
) -> Dict[str, Any]:
    """Get user permissions"""
    # Define access level hierarchy
    access_levels = ["basic", "advanced", "full"]
    user_access_index = access_levels.index(current_user.access_level) if current_user.access_level in access_levels else 0
    
    # Define permissions based on user role and access level
    permissions = {
        "can_upload": True,  # All authenticated users can upload
        "can_edit": current_user.role in ["admin", "user"] and user_access_index >= 1,  # advanced or full
        "is_admin": current_user.role == "admin",
        "is_read_only": user_access_index == 0  # basic access level
    }
    
    return permissions
