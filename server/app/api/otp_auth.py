from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from typing import Optional
import uuid
import os

from app.db.database import get_db
from app.db.models import User, AllowedDomain, UserSession, OTPRequest
from app.db.otp_schemas import (
    OTPRequestSchema, OTPVerificationSchema, OTPResponseSchema,
    UserRegistrationSchema, LoginResponseSchema, TokenRefreshSchema,
    LogoutResponseSchema, UserProfileSchema, AuthStatusSchema
)
from app.services.otp_service import otp_service
from app.services.jwt_service import jwt_service
from app.utils.auth_utils import get_user_by_email, create_user_session, invalidate_session, check_session_inactivity, update_session_activity
from app.services.audit_logging_service import AuditLoggingService

router = APIRouter(prefix="/api/auth/otp", tags=["OTP Authentication"])
security = HTTPBearer()

def set_secure_cookie(response: Response, key: str, value: str, max_age: int, request: Request):
    """Set secure authentication cookie with proper security settings for cross-origin scenarios"""
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    
    # Check for HTTPS - handle proxy/load balancer scenarios
    is_https = (
        request.url.scheme == "https" or 
        request.headers.get("x-forwarded-proto") == "https" or
        request.headers.get("x-forwarded-ssl") == "on" or
        request.headers.get("x-forwarded-scheme") == "https"
    )
    
    # For cross-origin scenarios between different domains (Vercel + Render),
    # use "none" samesite for production to allow cookies to work across domains
    # Also check if we're on Render (which indicates production deployment)
    is_render = "onrender.com" in request.headers.get("host", "")
    
    # Check if this is a cross-origin request (different origin from host)
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    
    # Extract domain from origin (e.g., "https://commission-tracker-ochre.vercel.app" -> "commission-tracker-ochre.vercel.app")
    origin_domain = origin.replace("https://", "").replace("http://", "") if origin else ""
    
    # Check if origin domain is different from host
    is_cross_origin = origin and host and origin_domain != host
    
    # Debug: Print all environment variables that might affect cookie setting
    print(f"🍪 Environment variables:")
    print(f"🍪   ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not_set')}")
    print(f"🍪   NODE_ENV: {os.getenv('NODE_ENV', 'not_set')}")
    print(f"🍪   RENDER: {os.getenv('RENDER', 'not_set')}")
    print(f"🍪   PORT: {os.getenv('PORT', 'not_set')}")
    
    # Debug: Print HTTPS detection details
    print(f"🍪 HTTPS Detection:")
    print(f"🍪   request.url.scheme: {request.url.scheme}")
    print(f"🍪   x-forwarded-proto: {request.headers.get('x-forwarded-proto', 'not_set')}")
    print(f"🍪   x-forwarded-ssl: {request.headers.get('x-forwarded-ssl', 'not_set')}")
    print(f"🍪   x-forwarded-scheme: {request.headers.get('x-forwarded-scheme', 'not_set')}")
    print(f"🍪   Final is_https: {is_https}")
    
    # Use "none" samesite for cross-origin requests or production
    # BUT: samesite=none requires secure=true, so we need to handle this carefully
    if is_cross_origin and not is_https:
        # For local development cross-origin (localhost:3000 -> localhost:8000), use "lax"
        samesite_setting = "lax"
    elif is_production or is_render or (is_cross_origin and is_https):
        # For production or HTTPS cross-origin, use "none"
        samesite_setting = "none"
    else:
        # For same-origin requests, use "lax"
        samesite_setting = "lax"
    
    print(f"🍪 Environment check: is_production={is_production}, is_render={is_render}, is_https={is_https}")
    print(f"🍪 Cross-origin check: origin={origin}, host={host}, origin_domain={origin_domain}, is_cross_origin={is_cross_origin}")
    print(f"🍪 Using samesite={samesite_setting}")
    
    if is_cross_origin and not is_https:
        print("⚠️  Local development cross-origin detected - using samesite=lax (samesite=none requires HTTPS)")
    
    # Don't set domain for cross-origin deployments - let browsers handle it
    # Setting a domain that doesn't match the request origin causes browsers to reject cookies
    cookie_domain = None
    
    print(f"🍪 Setting cookie: {key} with samesite={samesite_setting}, secure={is_https}")
    
    try:
        # For local development, we might need to be more permissive with cookie settings
        if not is_https and not is_production:
            # Local development - use more permissive settings
            print(f"🍪 Using local development cookie settings for {key}")
            response.set_cookie(
                key=key,
                value=value,
                max_age=max_age,
                httponly=True,
                secure=False,  # Allow non-secure cookies in development
                samesite=samesite_setting,
                path="/",
            )
        else:
            # Production - use strict settings
            print(f"🍪 Using production cookie settings for {key}")
            response.set_cookie(
                key=key,
                value=value,
                max_age=max_age,
                httponly=True,
                secure=is_https,  # Always use HTTPS detection
                samesite=samesite_setting,
                path="/",
                # Don't set domain for cross-origin scenarios
            )
        
        print(f"🍪 Cookie {key} set successfully")
        
        # Debug: Check if the cookie was actually added to response headers
        # Note: FastAPI might use different header names or multiple headers
        all_headers = dict(response.headers)
        cookie_headers = [v for k, v in all_headers.items() if k.lower() == 'set-cookie']
        
        if cookie_headers:
            print(f"🍪 Set-Cookie headers for {key}: {cookie_headers}")
        else:
            print(f"⚠️  No Set-Cookie header found for {key}")
            print(f"🍪 All response headers: {all_headers}")
            
    except Exception as e:
        print(f"❌ Error setting cookie {key}: {e}")
        raise

# Dependency to get current user from OTP authentication
async def get_current_user_otp(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from httpOnly cookies"""
    access_token = request.cookies.get("access_token")
    
    # Debug logging for cookie issues
    all_cookies = dict(request.cookies)
    print(f"🔍 Debug OTP - All cookies received: {list(all_cookies.keys())}")
    print(f"🔍 Debug OTP - Access token present: {bool(access_token)}")
    
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

# Dependency to get admin user
async def get_admin_user_otp(current_user: User = Depends(get_current_user_otp)) -> User:
    """Get admin user"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.post("/request", response_model=OTPResponseSchema)
async def request_otp(
    otp_request: OTPRequestSchema,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Request OTP for email verification"""
    audit_service = AuditLoggingService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    try:
        # Send OTP
        success = await otp_service.send_otp(
            email=otp_request.email,
            purpose=otp_request.purpose,
            ip_address=client_ip,
            user_agent=user_agent,
            db=db
        )
        
        if success:
            # Log successful OTP request
            await audit_service.log_user_authentication(
                user_id=uuid.uuid4(),  # Placeholder for unknown user
                action=f"otp_request_{otp_request.purpose}",
                success=True,
                ip_address=client_ip,
                user_agent=user_agent,
                failure_reason=None
            )
            
            return OTPResponseSchema(
                message="OTP sent to your email address",
                expires_in_minutes=10
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP. Please try again."
            )
    
    except ValueError as e:
        # Log failed OTP request
        await audit_service.log_user_authentication(
            user_id=uuid.uuid4(),
            action=f"otp_request_{otp_request.purpose}",
            success=False,
            ip_address=client_ip,
            user_agent=user_agent,
            failure_reason=str(e)
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify", response_model=LoginResponseSchema)
async def verify_otp(
    verification: OTPVerificationSchema,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP and authenticate user"""
    audit_service = AuditLoggingService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    try:
        # Verify OTP
        try:
            is_valid = await otp_service.verify_otp(
                email=verification.email,
                provided_otp=verification.otp,
                purpose=verification.purpose,
                db=db
            )
        except Exception as e:
            print(f"OTP verification error: {e}")
            # Log failed verification
            await audit_service.log_user_authentication(
                user_id=uuid.uuid4(),
                action=f"otp_verify_{verification.purpose}",
                success=False,
                ip_address=client_ip,
                user_agent=user_agent,
                failure_reason=f"OTP verification error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP verification failed. Please try again."
            )
        
        if not is_valid:
            # Log failed verification
            await audit_service.log_user_authentication(
                user_id=uuid.uuid4(),
                action=f"otp_verify_{verification.purpose}",
                success=False,
                ip_address=client_ip,
                user_agent=user_agent,
                failure_reason="Invalid or expired OTP"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        # Get or create user
        user = await get_user_by_email(db, verification.email)
        if not user:
            # For registration, create new user
            if verification.purpose == "registration":
                user = await create_user_from_email(verification.email, db)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
        
        # Update user login time and email verification status
        user.last_login = datetime.utcnow()
        user.is_email_verified = 1
        user.email_domain = verification.email.split('@')[1].lower()
        await db.commit()
        await db.refresh(user)
        
        # Create tokens
        user_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "company_id": str(user.company_id) if user.company_id else None,
            "access_level": user.access_level
        }
        tokens = jwt_service.create_token_pair(user_data)
        
        # Create session first
        session_token = str(uuid.uuid4())
        await create_user_session(db, str(user.id), session_token)
        
        # Set httpOnly cookies with proper security settings
        print(f"🍪 Setting cookies for user {user.email}")
        print(f"🍪 Request origin: {request.headers.get('origin', 'unknown')}")
        print(f"🍪 Request host: {request.headers.get('host', 'unknown')}")
        print(f"🍪 Request URL: {request.url}")
        print(f"🍪 Request scheme: {request.url.scheme}")
        
        # Debug: Check if response object is valid
        print(f"🍪 Response object type: {type(response)}")
        print(f"🍪 Response has set_cookie method: {hasattr(response, 'set_cookie')}")
        print(f"🍪 Response headers before: {dict(response.headers)}")
        print(f"🍪 Response status code: {response.status_code}")
        
        set_secure_cookie(response, "access_token", tokens["access_token"], 3600, request)  # 1 hour
        set_secure_cookie(response, "refresh_token", tokens["refresh_token"], 604800, request)  # 1 week
        set_secure_cookie(response, "session_token", session_token, 604800, request)  # 1 week
        
        print(f"🍪 Cookies set successfully")
        
        # Debug: Check if cookies were actually set
        print(f"🍪 Response headers after setting cookies: {dict(response.headers)}")
        
        # Log successful authentication
        await audit_service.log_user_authentication(
            user_id=user.id,
            action=f"otp_login_{verification.purpose}",
            success=True,
            ip_address=client_ip,
            user_agent=user_agent,
            failure_reason=None
        )
        
        return LoginResponseSchema(
            message="Authentication successful",
            user={
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "is_active": bool(user.is_active),
                "is_verified": bool(user.is_verified),
                "is_email_verified": bool(user.is_email_verified),
                "company_id": str(user.company_id) if user.company_id else None,
                "access_level": user.access_level,
                "auth_method": user.auth_method,
                "last_login": user.last_login,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected error
        await audit_service.log_user_authentication(
            user_id=uuid.uuid4(),
            action=f"otp_verify_{verification.purpose}",
            success=False,
            ip_address=client_ip,
            user_agent=user_agent,
            failure_reason=f"Unexpected error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again."
        )


@router.post("/register", response_model=OTPResponseSchema)
async def register_user(
    registration: UserRegistrationSchema,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register new user with OTP verification"""
    audit_service = AuditLoggingService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Check if user already exists
    existing_user = await get_user_by_email(db, registration.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered"
        )
    
    try:
        # Send OTP for registration
        success = await otp_service.send_otp(
            email=registration.email,
            purpose="registration",
            ip_address=client_ip,
            user_agent=user_agent,
            db=db
        )
        
        if success:
            # Log successful registration request
            await audit_service.log_user_authentication(
                user_id=uuid.uuid4(),
                action="otp_request_registration",
                success=True,
                ip_address=client_ip,
                user_agent=user_agent,
                failure_reason=None
            )
            
            return OTPResponseSchema(
                message="OTP sent to your email for registration",
                expires_in_minutes=10
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP. Please try again."
            )
    
    except ValueError as e:
        # Log failed registration request
        await audit_service.log_user_authentication(
            user_id=uuid.uuid4(),
            action="otp_request_registration",
            success=False,
            ip_address=client_ip,
            user_agent=user_agent,
            failure_reason=str(e)
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    payload = jwt_service.verify_token(refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user to ensure they still exist and are active
    user = await get_user_by_email(db, payload["email"])
    if not user or user.is_active == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Check session token if present
    session_token = request.cookies.get("session_token")
    if session_token:
        try:
            is_inactive = await check_session_inactivity(db, session_token)
            if is_inactive:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired due to inactivity"
                )
            # Update session activity
            await update_session_activity(db, session_token)
        except Exception as e:
            print(f"Session activity check failed during refresh: {e}")
            # Continue with refresh even if session check fails
    
    # Create new token pair
    user_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "company_id": str(user.company_id) if user.company_id else None,
        "access_level": user.access_level
    }
    tokens = jwt_service.create_token_pair(user_data)
    
    # Update cookies with proper security settings
    set_secure_cookie(response, "access_token", tokens["access_token"], 3600, request)  # 1 hour
    set_secure_cookie(response, "refresh_token", tokens["refresh_token"], 604800, request)  # 1 week
    
    return {"message": "Tokens refreshed successfully"}


@router.post("/logout", response_model=LogoutResponseSchema)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Logout user and invalidate session"""
    # Get tokens from cookies
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    
    # Revoke tokens if they exist
    if access_token:
        jwt_service.revoke_token(access_token)
    if refresh_token:
        jwt_service.revoke_token(refresh_token)
    
    # Get user from token before clearing cookies
    if access_token:
        payload = jwt_service.verify_token(access_token, "access")
        if payload:
            # Invalidate user session
            await invalidate_session(db, payload["sub"])
    
    # Clear all authentication cookies with proper security settings
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    
    # Check for HTTPS - handle proxy/load balancer scenarios
    is_https = (
        request.url.scheme == "https" or 
        request.headers.get("x-forwarded-proto") == "https" or
        request.headers.get("x-forwarded-ssl") == "on" or
        request.headers.get("x-forwarded-scheme") == "https"
    )
    is_render = "onrender.com" in request.headers.get("host", "")
    
    # Check if this is a cross-origin request (different origin from host)
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    
    # Extract domain from origin (e.g., "https://commission-tracker-ochre.vercel.app" -> "commission-tracker-ochre.vercel.app")
    origin_domain = origin.replace("https://", "").replace("http://", "") if origin else ""
    
    # Check if origin domain is different from host
    is_cross_origin = origin and host and origin_domain != host
    
    # Use same logic as cookie creation
    if is_cross_origin and not is_https:
        # For local development cross-origin (localhost:3000 -> localhost:8000), use "lax"
        samesite_setting = "lax"
    elif is_production or is_render or (is_cross_origin and is_https):
        # For production or HTTPS cross-origin, use "none"
        samesite_setting = "none"
    else:
        # For same-origin requests, use "lax"
        samesite_setting = "lax"
    
    response.delete_cookie(
        "access_token", 
        httponly=True, 
        secure=is_https, 
        samesite=samesite_setting,
        path="/"
    )
    response.delete_cookie(
        "refresh_token", 
        httponly=True, 
        secure=is_https, 
        samesite=samesite_setting,
        path="/"
    )
    response.delete_cookie(
        "session_token", 
        httponly=True, 
        secure=is_https, 
        samesite=samesite_setting,
        path="/"
    )
    
    return LogoutResponseSchema(message="Logged out successfully")


@router.post("/cleanup")
async def cleanup_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Clean up session on browser close/tab close"""
    session_token = request.cookies.get("session_token")
    if session_token:
        await invalidate_session(db, session_token)
    
    # Clear cookies with proper security settings
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    
    # Check for HTTPS - handle proxy/load balancer scenarios
    is_https = (
        request.url.scheme == "https" or 
        request.headers.get("x-forwarded-proto") == "https" or
        request.headers.get("x-forwarded-ssl") == "on" or
        request.headers.get("x-forwarded-scheme") == "https"
    )
    is_render = "onrender.com" in request.headers.get("host", "")
    
    # Check if this is a cross-origin request (different origin from host)
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    
    # Extract domain from origin (e.g., "https://commission-tracker-ochre.vercel.app" -> "commission-tracker-ochre.vercel.app")
    origin_domain = origin.replace("https://", "").replace("http://", "") if origin else ""
    
    # Check if origin domain is different from host
    is_cross_origin = origin and host and origin_domain != host
    
    # Use same logic as cookie creation
    if is_cross_origin and not is_https:
        # For local development cross-origin (localhost:3000 -> localhost:8000), use "lax"
        samesite_setting = "lax"
    elif is_production or is_render or (is_cross_origin and is_https):
        # For production or HTTPS cross-origin, use "none"
        samesite_setting = "none"
    else:
        # For same-origin requests, use "lax"
        samesite_setting = "lax"
    
    response.delete_cookie(
        "access_token", 
        httponly=True, 
        secure=is_https, 
        samesite=samesite_setting,
        path="/"
    )
    response.delete_cookie(
        "refresh_token", 
        httponly=True, 
        secure=is_https, 
        samesite=samesite_setting,
        path="/"
    )
    response.delete_cookie(
        "session_token", 
        httponly=True, 
        secure=is_https, 
        samesite=samesite_setting,
        path="/"
    )
    
    return {"message": "Session cleaned up"}

@router.get("/status", response_model=AuthStatusSchema)
async def auth_status(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Check authentication status"""
    access_token = request.cookies.get("access_token")
    
    # Debug logging for auth status check
    all_cookies = dict(request.cookies)
    print(f"🔍 Auth Status - All cookies: {list(all_cookies.keys())}")
    print(f"🔍 Auth Status - Access token present: {bool(access_token)}")
    print(f"🔍 Auth Status - Request host: {request.headers.get('host', 'unknown')}")
    print(f"🔍 Auth Status - Request origin: {request.headers.get('origin', 'unknown')}")
    
    # Debug: Print all cookie values (without sensitive data)
    for cookie_name, cookie_value in all_cookies.items():
        if cookie_name in ['access_token', 'refresh_token', 'session_token']:
            print(f"🔍 Auth Status - Cookie {cookie_name}: {cookie_value[:20]}...")
        else:
            print(f"🔍 Auth Status - Cookie {cookie_name}: {cookie_value}")
    
    if not access_token:
        return AuthStatusSchema(is_authenticated=False)
    
    payload = jwt_service.verify_token(access_token, "access")
    if not payload:
        return AuthStatusSchema(is_authenticated=False)
    
    user = await get_user_by_email(db, payload["email"])
    if not user or user.is_active == 0:
        return AuthStatusSchema(is_authenticated=False)
    
    # Calculate token expiration
    exp_timestamp = payload.get("exp")
    token_expires_at = datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None
    
    return AuthStatusSchema(
        is_authenticated=True,
        user=UserProfileSchema(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            is_active=bool(user.is_active),
            is_verified=bool(user.is_verified),
            is_email_verified=bool(user.is_email_verified),
            company_id=str(user.company_id) if user.company_id else None,
            access_level=user.access_level,
            auth_method=user.auth_method,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at
        ),
        token_expires_at=token_expires_at
    )


@router.get("/profile", response_model=UserProfileSchema)
async def get_profile(
    current_user: User = Depends(get_current_user_otp)
):
    """Get current user profile"""
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

@router.post("/test-cookies")
async def test_cookies(
    request: Request,
    response: Response
):
    """Test endpoint to verify cookie setting works"""
    print("🧪 Testing cookie setting...")
    
    # Test setting a simple cookie
    test_cookie_value = "test_value_123"
    
    try:
        set_secure_cookie(response, "test_cookie", test_cookie_value, 3600, request)
        print("✅ Test cookie set successfully")
        
        return {
            "message": "Test cookie set",
            "cookie_value": test_cookie_value,
            "response_headers": dict(response.headers)
        }
    except Exception as e:
        print(f"❌ Error setting test cookie: {e}")
        return {
            "error": str(e),
            "response_headers": dict(response.headers)
        }



async def create_user_from_email(email: str, db: AsyncSession) -> User:
    """Create a new user from email address"""
    user = User(
        email=email,
        email_domain=email.split('@')[1].lower(),
        role="user",
        is_active=1,
        is_verified=0,
        is_email_verified=1,  # Verified via OTP
        auth_method="otp",
        access_level="basic"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
