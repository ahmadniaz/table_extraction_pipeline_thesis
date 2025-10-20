"""
Security Configuration for Commission Tracker Application

This module contains security-related configurations and utilities
to ensure the application follows industry best practices.
"""

import os
from typing import List, Dict, Any
from datetime import timedelta

# Security Headers Configuration
# Note: X-Frame-Options is conditionally set based on environment in get_security_headers()
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' ws: wss:; frame-src 'self'; object-src 'self';"
}

# CORS Configuration
# Default CORS origins - can be overridden by environment variable
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://commission-tracker-1.onrender.com",
    "https://commission-tracker-ochre.vercel.app",
    # Add your production domains here
]

# Allow environment variable to override CORS origins
CORS_ORIGINS_ENV = os.environ.get("CORS_ORIGINS")
if CORS_ORIGINS_ENV:
    # Parse comma-separated origins from environment variable
    # Handle potential malformed environment variables
    origins = []
    for origin in CORS_ORIGINS_ENV.split(","):
        origin = origin.strip()
        if origin:
            origins.append(origin)
    CORS_ORIGINS = origins if origins else DEFAULT_CORS_ORIGINS
else:
    CORS_ORIGINS = DEFAULT_CORS_ORIGINS

CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_HEADERS = ["*"]

# Trusted Hosts
TRUSTED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "*.onrender.com",
    "*.vercel.app",
    "*.herokuapp.com"
]

# Rate Limiting Configuration
RATE_LIMIT_CONFIG = {
    "otp_requests_per_hour": 10,
    "login_attempts_per_hour": 20,
    "api_requests_per_minute": 100,
    "file_uploads_per_hour": 50
}

# Session Configuration
SESSION_CONFIG = {
    "max_age_seconds": 3600,  # 1 hour
    "inactivity_timeout_minutes": 120,  # 2 hours
    "cleanup_interval_hours": 1,
    "max_concurrent_sessions": 5
}

# Token Configuration
TOKEN_CONFIG = {
    "access_token_expire_minutes": 60,
    "refresh_token_expire_days": 7,
    "algorithm": "HS256",
    "min_secret_key_length": 32
}

# Password Security Configuration
PASSWORD_CONFIG = {
    "min_length": 8,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_numbers": True,
    "require_special_chars": True,
    "max_age_days": 90
}

# File Upload Security
FILE_UPLOAD_CONFIG = {
    "max_file_size_mb": 50,
    "allowed_extensions": [".pdf", ".xlsx", ".xls", ".csv"],
    "scan_for_malware": True,
    "quarantine_suspicious_files": True
}

# Audit Logging Configuration
AUDIT_CONFIG = {
    "log_authentication_events": True,
    "log_file_access": True,
    "log_data_modifications": True,
    "retention_days": 90,
    "log_level": "INFO"
}

# Security Monitoring
MONITORING_CONFIG = {
    "enable_intrusion_detection": True,
    "failed_login_threshold": 5,
    "suspicious_activity_threshold": 10,
    "alert_on_privilege_escalation": True
}

def get_security_headers() -> Dict[str, str]:
    """Get security headers configuration"""
    headers = SECURITY_HEADERS.copy()
    
    # In development (localhost), don't set X-Frame-Options to allow iframe embedding
    # In production, set to SAMEORIGIN for security
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production":
        headers["X-Frame-Options"] = "SAMEORIGIN"
    # For development, we don't add X-Frame-Options to allow cross-origin iframe embedding
    # between localhost:3000 (frontend) and localhost:8000 (backend)
    
    return headers

def get_cors_config() -> Dict[str, Any]:
    """Get CORS configuration"""
    print(f"🌐 CORS Configuration - Allowed Origins: {CORS_ORIGINS}")
    return {
        "allow_origins": CORS_ORIGINS,
        "allow_methods": CORS_METHODS,
        "allow_headers": CORS_HEADERS,
        "allow_credentials": True
    }

def get_trusted_hosts() -> List[str]:
    """Get trusted hosts configuration"""
    return TRUSTED_HOSTS.copy()

def validate_secret_key(secret_key: str) -> bool:
    """Validate that the secret key meets security requirements"""
    if not secret_key or len(secret_key) < TOKEN_CONFIG["min_secret_key_length"]:
        return False
    
    # Check for common weak keys
    weak_keys = [
        "your-secret-key",
        "change-in-production",
        "secret",
        "password",
        "1234567890",
        "abcdefghijklmnopqrstuvwxyz"
    ]
    
    return secret_key not in weak_keys

def get_environment_security_check() -> Dict[str, bool]:
    """Check security-related environment variables"""
    checks = {
        "jwt_secret_configured": bool(os.getenv("JWT_SECRET_KEY")),
        "jwt_secret_secure": validate_secret_key(os.getenv("JWT_SECRET_KEY", "")),
        "database_ssl": "sslmode=require" in os.getenv("DATABASE_URL", ""),
        "production_mode": os.getenv("ENVIRONMENT") == "production",
        "debug_disabled": os.getenv("DEBUG", "true").lower() != "true"
    }
    
    return checks

def get_security_recommendations() -> List[str]:
    """Get security recommendations based on current configuration"""
    recommendations = []
    checks = get_environment_security_check()
    
    if not checks["jwt_secret_configured"]:
        recommendations.append("Set JWT_SECRET_KEY environment variable")
    
    if not checks["jwt_secret_secure"]:
        recommendations.append("Use a strong, unique JWT secret key (32+ characters)")
    
    if not checks["database_ssl"]:
        recommendations.append("Enable SSL for database connections")
    
    if not checks["production_mode"]:
        recommendations.append("Set ENVIRONMENT=production for production deployments")
    
    if not checks["debug_disabled"]:
        recommendations.append("Disable debug mode in production")
    
    return recommendations
