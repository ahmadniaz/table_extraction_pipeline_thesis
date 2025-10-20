from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Set
from jose import JWTError, jwt
import secrets
import time

from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS


class JWTService:
    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = REFRESH_TOKEN_EXPIRE_DAYS
        self.revoked_tokens: Set[str] = set()  # In production, use Redis
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create access token with expiration"""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({
            "exp": expire, 
            "type": "access",
            "iat": now,
            "jti": secrets.token_hex(16)  # Unique token identifier
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create refresh token with longer expiration"""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({
            "exp": expire, 
            "type": "refresh",
            "iat": now,
            "jti": secrets.token_urlsafe(32)  # Unique token ID for revocation
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            # Check if token is revoked first
            if self.is_token_revoked(token):
                print("Token is revoked")
                return None
                
            # Decode with full verification - let JWT library handle time validation
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                print(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
                return None
            
            return payload
        except JWTError as e:
            print(f"JWT verification failed: {e}")
            return None
    
    def revoke_token(self, token: str) -> None:
        """Revoke a token by adding it to blacklist"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            jti = payload.get('jti', token[:32])  # Use JTI or token prefix
            self.revoked_tokens.add(jti)
        except JWTError:
            pass  # Invalid token, ignore
    
    def is_token_revoked(self, token: str) -> bool:
        """Check if token is revoked"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            jti = payload.get('jti', token[:32])
            return jti in self.revoked_tokens
        except JWTError:
            return True  # Invalid token is considered revoked
    
    def create_token_pair(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """Create both access and refresh tokens"""
        return {
            "access_token": self.create_access_token(user_data),
            "refresh_token": self.create_refresh_token(user_data)
        }
    
    def extract_user_data(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract user data from token without verification (for debugging)"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            return {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role"),
                "company_id": payload.get("company_id"),
                "access_level": payload.get("access_level"),
                "type": payload.get("type"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
        except JWTError:
            return None


# Global JWT service instance
jwt_service = JWTService()
