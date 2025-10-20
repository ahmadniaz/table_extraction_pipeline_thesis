import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, AllowedDomain, UserSession
from typing import TypedDict

class TokenData(TypedDict):
    user_id: str
    email: str

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15 minutes for security
SESSION_EXPIRE_DAYS = 7  # 7 days for refresh tokens
INACTIVITY_TIMEOUT_MINUTES = 120  # 2 hours inactivity timeout (increased for better UX)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, email=email)
    except JWTError:
        raise credentials_exception
    
    return token_data

def create_session_token() -> str:
    """Create a secure session token."""
    return secrets.token_urlsafe(32)

async def is_domain_allowed(db: AsyncSession, email: str) -> bool:
    """Check if the email domain is allowed."""
    domain = email.split('@')[1].lower()
    
    # Check if domain is in allowed domains
    from sqlalchemy import select
    stmt = select(AllowedDomain).filter(
        AllowedDomain.domain == domain,
        AllowedDomain.is_active == 1
    )
    result = await db.execute(stmt)
    allowed_domain = result.scalar_one_or_none()
    
    return allowed_domain is not None

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    from sqlalchemy import select
    stmt = select(User).filter(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def create_user_session(db: AsyncSession, user_id: str, session_token: str) -> UserSession:
    """Create a new user session."""
    expires_at = datetime.utcnow() + timedelta(days=SESSION_EXPIRE_DAYS)
    
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def get_user_session(db: AsyncSession, session_token: str) -> Optional[UserSession]:
    """Get user session by token."""
    from sqlalchemy import select
    stmt = select(UserSession).filter(
        UserSession.session_token == session_token,
        UserSession.is_active == 1,
        UserSession.expires_at > datetime.utcnow()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def invalidate_session(db: AsyncSession, session_token: str) -> bool:
    """Invalidate a user session."""
    from sqlalchemy import select, update
    stmt = select(UserSession).filter(
        UserSession.session_token == session_token
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if session:
        update_stmt = update(UserSession).filter(
            UserSession.session_token == session_token
        ).values(is_active=0)
        await db.execute(update_stmt)
        await db.commit()
        return True
    return False

async def update_session_activity(db: AsyncSession, session_token: str) -> bool:
    """Update session last_accessed timestamp."""
    from sqlalchemy import select, update
    stmt = update(UserSession).filter(
        UserSession.session_token == session_token,
        UserSession.is_active == 1
    ).values(last_accessed=datetime.utcnow())
    
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0

async def check_session_inactivity(db: AsyncSession, session_token: str) -> bool:
    """Check if session has been inactive for too long."""
    from sqlalchemy import select
    stmt = select(UserSession).filter(
        UserSession.session_token == session_token,
        UserSession.is_active == 1
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        return False
    
    # Check if last access was more than INACTIVITY_TIMEOUT_MINUTES ago
    inactivity_threshold = datetime.utcnow() - timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES)
    return session.last_accessed < inactivity_threshold

async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """Clean up expired sessions and inactive sessions."""
    from sqlalchemy import select, update
    
    # Clean up expired sessions
    expired_stmt = select(UserSession).filter(
        UserSession.expires_at < datetime.utcnow()
    )
    result = await db.execute(expired_stmt)
    expired_sessions = result.scalars().all()
    
    # Clean up inactive sessions
    inactivity_threshold = datetime.utcnow() - timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES)
    inactive_stmt = select(UserSession).filter(
        UserSession.last_accessed < inactivity_threshold,
        UserSession.is_active == 1
    )
    result = await db.execute(inactive_stmt)
    inactive_sessions = result.scalars().all()
    
    # Update all expired and inactive sessions
    all_sessions = expired_sessions + inactive_sessions
    if all_sessions:
        session_ids = [session.id for session in all_sessions]
        update_stmt = update(UserSession).filter(
            UserSession.id.in_(session_ids)
        ).values(is_active=0)
        await db.execute(update_stmt)
        await db.commit()
    
    return len(all_sessions)

def is_admin_user(user: User) -> bool:
    """Check if user is an admin."""
    return user.role == "admin"

def is_read_only_user(user: User) -> bool:
    """Check if user has read-only access."""
    return user.role == "read_only"

def can_upload_files(user: User) -> bool:
    """Check if user can upload files."""
    return user.role in ["admin", "user"] and user.is_active == 1

def can_edit_data(user: User) -> bool:
    """Check if user can edit data."""
    return user.role in ["admin", "user"] and user.is_active == 1
