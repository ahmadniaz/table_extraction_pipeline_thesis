from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class OTPRequestSchema(BaseModel):
    email: EmailStr
    purpose: str = Field(default="login", description="Purpose: login, registration, password_reset")


class OTPVerificationSchema(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    purpose: str = Field(default="login", description="Purpose: login, registration, password_reset")


class OTPResponseSchema(BaseModel):
    message: str
    expires_in_minutes: int = 10


class UserRegistrationSchema(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None


class LoginResponseSchema(BaseModel):
    message: str
    user: dict
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class TokenRefreshSchema(BaseModel):
    refresh_token: str


class LogoutResponseSchema(BaseModel):
    message: str


class UserProfileSchema(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    is_email_verified: bool
    company_id: Optional[str]
    access_level: str
    auth_method: str
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AuthStatusSchema(BaseModel):
    is_authenticated: bool
    user: Optional[UserProfileSchema] = None
    token_expires_at: Optional[datetime] = None
