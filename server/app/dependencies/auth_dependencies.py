from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Union
from datetime import datetime

from app.db.database import get_db
from app.db.models import User
from app.utils.auth_utils import get_user_by_email, verify_token, update_session_activity, check_session_inactivity
from app.services.jwt_service import jwt_service

# Security schemes
security_bearer = HTTPBearer(auto_error=False)  # Don't auto-raise on missing token


async def get_current_user_hybrid(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user supporting both Bearer token and httpOnly cookie authentication
    """
    token = None
    token_source = None
    
    # Try Bearer token first (existing password auth)
    if credentials:
        token = credentials.credentials
        token_source = "bearer"
    else:
        # Try httpOnly cookie (OTP auth)
        token = request.cookies.get("access_token")
        token_source = "cookie"
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify token based on source
    if token_source == "bearer":
        # Legacy password-based authentication
        token_data = verify_token(token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        email = token_data.email
    else:
        # OTP-based authentication
        payload = jwt_service.verify_token(token, "access")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        email = payload["email"]
        
        # Check for session inactivity (for OTP auth with sessions)
        session_token = request.cookies.get("session_token")
        if session_token:
            try:
                is_inactive = await check_session_inactivity(db, session_token)
                if is_inactive:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session expired due to inactivity"
                    )
                # Update session activity (non-blocking)
                await update_session_activity(db, session_token)
            except Exception as e:
                # If session check fails, log but don't block the request
                print(f"Session activity check failed: {e}")
                # Continue with the request
    
    # Get user from database
    user = await get_user_by_email(db, email)
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user using Bearer token (legacy)."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = credentials.credentials
    token_data = verify_token(token)
    
    user = await get_user_by_email(db, token_data.email)
    if user is None:
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


async def get_admin_user(current_user: User = Depends(get_current_user_hybrid)) -> User:
    """Get current admin user."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_user_bearer(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from Bearer token (legacy password authentication)
    """
    token = credentials.credentials
    token_data = verify_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = await get_user_by_email(db, token_data.email)
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


async def get_current_user_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from httpOnly cookie (OTP authentication)
    """
    access_token = request.cookies.get("access_token")
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


async def require_admin(
    current_user: User = Depends(get_current_user_hybrid)
) -> User:
    """
    Require admin access
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_upload_permission(
    current_user: User = Depends(get_current_user_hybrid)
) -> User:
    """
    Require file upload permission
    """
    if current_user.role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Upload permission required"
        )
    return current_user


async def require_edit_permission(
    current_user: User = Depends(get_current_user_hybrid)
) -> User:
    """
    Require data editing permission
    """
    if current_user.role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit permission required"
        )
    return current_user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    """
    try:
        return await get_current_user_hybrid(request, credentials, db)
    except HTTPException:
        return None


def get_user_company_filter(current_user: User) -> dict:
    """
    Get company filter for user's data access
    """
    if current_user.role == "admin":
        return {}  # Admin can see all data
    elif current_user.company_id:
        return {"company_id": current_user.company_id}
    else:
        # User without company association - restrict access
        return {"company_id": None}


def check_user_access_level(current_user: User, required_level: str) -> bool:
    """
    Check if user has required access level
    """
    access_levels = ["basic", "advanced", "full"]
    user_level_index = access_levels.index(current_user.access_level) if current_user.access_level in access_levels else 0
    required_level_index = access_levels.index(required_level) if required_level in access_levels else 0
    
    return user_level_index >= required_level_index


async def require_access_level(
    required_level: str,
    current_user: User = Depends(get_current_user_hybrid)
) -> User:
    """
    Require specific access level
    """
    if not check_user_access_level(current_user, required_level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access level '{required_level}' required"
        )
    return current_user
