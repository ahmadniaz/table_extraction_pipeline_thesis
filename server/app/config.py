from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

# Render PostgreSQL connection (preferred)
RENDER_DB_URL = os.environ.get("RENDER_DB_KEY")

# Fallback to Supabase if Render not configured
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_KEY")

# Use Render if available, otherwise use Supabase
if RENDER_DB_URL:
    # Ensure we use asyncpg dialect
    if not RENDER_DB_URL.startswith("postgresql+asyncpg://"):
        DATABASE_URL = RENDER_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
    else:
        DATABASE_URL = RENDER_DB_URL
    print("✅ Using Render PostgreSQL database")
elif SUPABASE_DB_URL:
    # Ensure we use asyncpg dialect
    if not SUPABASE_DB_URL.startswith("postgresql+asyncpg://"):
        DATABASE_URL = SUPABASE_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
    else:
        DATABASE_URL = SUPABASE_DB_URL
    print("⚠️  Using Supabase PostgreSQL database (fallback)")
else:
    raise ValueError("No database URL configured! Set either RENDER_DB_KEY or SUPABASE_DB_KEY")

engine = create_async_engine(
    DATABASE_URL,
    connect_args={
        "statement_cache_size": 0,
        # Database timeout settings for long-running operations
        "server_settings": {
            "statement_timeout": "600000",  # 10 minutes in milliseconds
            "idle_in_transaction_session_timeout": "600000",  # 10 minutes
        }
    },
    # SQLAlchemy pool settings for long-running operations
    pool_pre_ping=True,
    pool_recycle=1800,  # Recycle connections every 30 minutes (more frequent)
    pool_timeout=60,    # Wait up to 60 seconds for a connection
    max_overflow=20,    # Allow up to 20 extra connections
    pool_size=10,       # Maintain 10 connections in the pool
    echo=False,         # Set to True for debugging SQL queries
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Authentication and OTP Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))  # 1 hour for better UX
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
INACTIVITY_TIMEOUT_MINUTES = int(os.environ.get("INACTIVITY_TIMEOUT_MINUTES", "120"))  # 2 hours inactivity timeout for better UX

# Email Configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

# OTP Configuration
OTP_EXPIRY_MINUTES = int(os.environ.get("OTP_EXPIRY_MINUTES", "10"))
OTP_RATE_LIMIT_PER_HOUR = int(os.environ.get("OTP_RATE_LIMIT_PER_HOUR", "10"))
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "3"))

# Redis Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Domain Whitelisting is handled by the existing AllowedDomain database table
# No environment variable needed - use the admin dashboard to manage domains

# Claude Document AI Configuration (Primary Extraction Method)
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
CLAUDE_MODEL_PRIMARY = os.environ.get("CLAUDE_MODEL_PRIMARY", "claude-sonnet-4-20250514")
CLAUDE_MODEL_FALLBACK = os.environ.get("CLAUDE_MODEL_FALLBACK", "claude-sonnet-4-20250514")  # Use same as primary
CLAUDE_MAX_FILE_SIZE = int(os.environ.get("CLAUDE_MAX_FILE_SIZE", "33554432"))  # 32MB in bytes
CLAUDE_MAX_PAGES = int(os.environ.get("CLAUDE_MAX_PAGES", "100"))
CLAUDE_TIMEOUT_SECONDS = int(os.environ.get("CLAUDE_TIMEOUT_SECONDS", "300"))  # 5 minutes
