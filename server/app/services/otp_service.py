import random
import asyncio
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

# Optional imports with fallback
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis not available - OTP service will use database-only mode")

try:
    import aiosmtplib
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False
    print("⚠️ SMTP not available - email sending will be disabled")

from app.config import (
    REDIS_URL, SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD,
    OTP_EXPIRY_MINUTES, OTP_RATE_LIMIT_PER_HOUR, OTP_MAX_ATTEMPTS
)
from app.db.models import OTPRequest, AllowedDomain
from app.utils.auth_utils import get_password_hash


class OTPService:
    def __init__(self):
        self.redis = None
        self._redis_initialized = False
    
    async def init_redis(self):
        """Initialize Redis connection"""
        if not self._redis_initialized and REDIS_AVAILABLE:
            try:
                self.redis = redis.from_url(REDIS_URL)
                self.redis.ping()  # Test connection
                self._redis_initialized = True
                print("✅ Redis connection established")
            except Exception as e:
                print(f"⚠️ Redis connection failed: {e}")
                print("⚠️ OTP service will use database-only mode")
                self._redis_initialized = False
        elif not REDIS_AVAILABLE:
            print("⚠️ Redis not available - using database-only mode")
            self._redis_initialized = False
    
    def generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    def hash_otp(self, otp: str) -> str:
        """Hash OTP for secure storage"""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    async def validate_email_domain(self, email: str, db: AsyncSession) -> bool:
        """Validate if email domain is allowed using existing domain whitelist system"""
        from app.utils.auth_utils import is_domain_allowed
        import os
        
        # In development, allow all domains if no domains are configured
        if os.getenv("ENVIRONMENT", "development") == "development":
            # Check if any domains are configured
            from sqlalchemy import select, func
            from app.db.models import AllowedDomain
            result = await db.execute(select(func.count(AllowedDomain.id)))
            domain_count = result.scalar()
            
            # If no domains configured, allow all in development
            if domain_count == 0:
                print(f"⚠️ No domains configured, allowing {email} in development mode")
                return True
        
        return await is_domain_allowed(db, email)
    
    async def check_rate_limit(self, email: str, db: AsyncSession) -> bool:
        """Check rate limiting for OTP requests"""
        # Check Redis first if available
        if self.redis and self._redis_initialized:
            try:
                key = f"rate_limit:{email}"
                current_count = self.redis.get(key)
                
                if current_count is None:
                    self.redis.setex(key, 3600, 1)  # 1 hour expiry
                    return True
                
                if int(current_count) >= OTP_RATE_LIMIT_PER_HOUR:
                    return False
                
                self.redis.incr(key)
                return True
            except Exception as e:
                print(f"Redis rate limit check failed: {e}")
        
        # Fallback to database rate limiting
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        result = await db.execute(
            select(func.count(OTPRequest.id)).where(
                and_(
                    OTPRequest.email == email,
                    OTPRequest.created_at >= one_hour_ago
                )
            )
        )
        recent_requests = result.scalar()
        return recent_requests < OTP_RATE_LIMIT_PER_HOUR
    
    async def store_otp(self, email: str, otp: str, purpose: str, ip_address: str = None, user_agent: str = None, db: AsyncSession = None) -> str:
        """Store OTP in database and optionally Redis"""
        hashed_otp = self.hash_otp(otp)
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        
        # Store in database
        otp_request = OTPRequest(
            email=email,
            otp_code=hashed_otp,
            purpose=purpose,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(otp_request)
        await db.commit()
        await db.refresh(otp_request)
        
        # Store in Redis for faster access (optional)
        if self.redis and self._redis_initialized:
            try:
                otp_key = f"otp:{email}:{purpose}"
                self.redis.setex(otp_key, OTP_EXPIRY_MINUTES * 60, otp)
            except Exception as e:
                print(f"Redis OTP storage failed: {e}")
        
        return str(otp_request.id)
    
    async def verify_otp(self, email: str, provided_otp: str, purpose: str, db: AsyncSession) -> bool:
        """Verify OTP against stored value"""
        hashed_provided_otp = self.hash_otp(provided_otp)
        
        # Check Redis first if available
        if self.redis and self._redis_initialized:
            try:
                otp_key = f"otp:{email}:{purpose}"
                stored_otp = self.redis.get(otp_key)
                
                if stored_otp and stored_otp.decode() == provided_otp:
                    self.redis.delete(otp_key)  # Single use
                    # Mark as used in database
                    await self._mark_otp_used(email, hashed_provided_otp, purpose, db)
                    return True
            except Exception as e:
                print(f"Redis OTP verification failed: {e}")
        
        # Fallback to database verification
        result = await db.execute(
            select(OTPRequest).where(
                and_(
                    OTPRequest.email == email,
                    OTPRequest.otp_code == hashed_provided_otp,
                    OTPRequest.purpose == purpose,
                    OTPRequest.expires_at > datetime.utcnow(),
                    OTPRequest.is_used == 0,
                    OTPRequest.attempts < OTP_MAX_ATTEMPTS
                )
            )
        )
        otp_request = result.scalar_one_or_none()
        
        if otp_request:
            # Mark as used
            otp_request.is_used = 1
            otp_request.used_at = datetime.utcnow()
            await db.commit()
            return True
        
        # Increment attempts for failed verification
        await self._increment_otp_attempts(email, hashed_provided_otp, purpose, db)
        return False
    
    async def _mark_otp_used(self, email: str, hashed_otp: str, purpose: str, db: AsyncSession):
        """Mark OTP as used in database"""
        result = await db.execute(
            select(OTPRequest).where(
                and_(
                    OTPRequest.email == email,
                    OTPRequest.otp_code == hashed_otp,
                    OTPRequest.purpose == purpose,
                    OTPRequest.is_used == 0
                )
            )
        )
        otp_request = result.scalar_one_or_none()
        if otp_request:
            otp_request.is_used = 1
            otp_request.used_at = datetime.utcnow()
            await db.commit()
    
    async def _increment_otp_attempts(self, email: str, hashed_otp: str, purpose: str, db: AsyncSession):
        """Increment OTP verification attempts"""
        result = await db.execute(
            select(OTPRequest).where(
                and_(
                    OTPRequest.email == email,
                    OTPRequest.otp_code == hashed_otp,
                    OTPRequest.purpose == purpose,
                    OTPRequest.is_used == 0
                )
            )
        )
        otp_request = result.scalar_one_or_none()
        if otp_request:
            otp_request.attempts += 1
            await db.commit()
    
    async def send_otp_email(self, email: str, otp: str, purpose: str) -> bool:
        """Send OTP via email"""
        if not SMTP_AVAILABLE:
            print("⚠️ SMTP not available - OTP email sending disabled")
            print(f"📧 OTP for {email}: {otp} (purpose: {purpose})")
            return True  # Return True for testing purposes
        
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("⚠️ Email credentials not configured")
            print(f"📧 OTP for {email}: {otp} (purpose: {purpose})")
            return True  # Return True for testing purposes
        
        subject = f"Commission Tracker - Verification Code"
        body = f"""
        Your verification code for Commission Tracker is: {otp}
        
        This code will expire in {OTP_EXPIRY_MINUTES} minutes.
        Purpose: {purpose.title()}
        
        If you didn't request this code, please ignore this email.
        
        For security reasons, do not share this code with anyone.
        """
        
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USER
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            await aiosmtplib.send(
                msg,
                hostname=SMTP_SERVER,
                port=SMTP_PORT,
                start_tls=True,
                username=EMAIL_USER,
                password=EMAIL_PASSWORD,
            )
            print(f"✅ OTP email sent to {email}")
            return True
        except Exception as e:
            print(f"❌ Error sending email to {email}: {e}")
            print(f"📧 OTP for {email}: {otp} (purpose: {purpose})")
            return True  # Return True for testing purposes
    
    async def send_otp(self, email: str, purpose: str = "login", ip_address: str = None, user_agent: str = None, db: AsyncSession = None) -> bool:
        """Main method to send OTP with all validations"""
        # Initialize Redis if not done
        await self.init_redis()
        
        # Check domain validation
        if not await self.validate_email_domain(email, db):
            raise ValueError("Email domain not authorized")
        
        # Check rate limiting
        if not await self.check_rate_limit(email, db):
            raise ValueError("Rate limit exceeded. Try again later.")
        
        # Generate and store OTP
        otp = self.generate_otp()
        await self.store_otp(email, otp, purpose, ip_address, user_agent, db)
        
        # Send email
        return await self.send_otp_email(email, otp, purpose)
    
    async def cleanup_expired_otps(self, db: AsyncSession):
        """Clean up expired OTPs from database"""
        try:
            result = await db.execute(
                select(OTPRequest).where(
                    OTPRequest.expires_at < datetime.utcnow()
                )
            )
            expired_otps = result.scalars().all()
            
            for otp in expired_otps:
                await db.delete(otp)
            
            await db.commit()
            print(f"✅ Cleaned up {len(expired_otps)} expired OTPs")
        except Exception as e:
            print(f"❌ Error cleaning up expired OTPs: {e}")


# Global OTP service instance
otp_service = OTPService()
