from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

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
    # For local development, use a default database URL
    DATABASE_URL = "postgresql+asyncpg://user:password@localhost/commission_tracker"
    print("⚠️  Using local database (development mode)")

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

# Synchronous version for initialization scripts
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create synchronous engine for initialization
sync_database_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
sync_engine = create_engine(sync_database_url)
SyncSessionLocal = sessionmaker(bind=sync_engine)

def get_sync_db():
    return SyncSessionLocal()
