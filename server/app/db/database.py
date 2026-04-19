from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Local PostgreSQL connection (preferred)
LOCAL_DB_URL = os.environ.get("LOCAL_DB_KEY")

# Render PostgreSQL connection (fallback)
RENDER_DB_URL = os.environ.get("RENDER_DB_KEY")

# Supabase as last fallback
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_KEY")

# Use Local DB if available, otherwise use Render, then Supabase
if LOCAL_DB_URL:
    # Ensure we use asyncpg dialect
    if not LOCAL_DB_URL.startswith("postgresql+asyncpg://"):
        DATABASE_URL = LOCAL_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
    else:
        DATABASE_URL = LOCAL_DB_URL
    print("✅ Using Local PostgreSQL database")
elif RENDER_DB_URL:
    # Ensure we use asyncpg dialect
    if not RENDER_DB_URL.startswith("postgresql+asyncpg://"):
        DATABASE_URL = RENDER_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
    else:
        DATABASE_URL = RENDER_DB_URL
    print("⚠️  Using Render PostgreSQL database (fallback)")
elif SUPABASE_DB_URL:
    # Ensure we use asyncpg dialect
    if not SUPABASE_DB_URL.startswith("postgresql+asyncpg://"):
        DATABASE_URL = SUPABASE_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
    else:
        DATABASE_URL = SUPABASE_DB_URL
    print("⚠️  Using Supabase PostgreSQL database (fallback)")
else:
    # For local development, use a default database URL
    DATABASE_URL = "postgresql+asyncpg://postgres@localhost:5432/thesis_commission_tracker"
    print("⚠️  Using default local database (development mode)")

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
    # pool_pre_ping: verify connection is alive before checkout — avoids stale asyncpg
    # sockets after long LLM calls (e.g. 15+ min Mistral) that exceed server idle limits.
    pool_pre_ping=True,
    # pool_recycle: drop connections older than 10 min so pool does not hand out dead links
    # when extraction + commit runs long after the connection was opened.
    pool_recycle=600,
    pool_timeout=60,    # Wait up to 60 seconds for a connection
    max_overflow=20,    # Allow up to 20 extra connections
    pool_size=10,       # Maintain 10 connections in the pool
    echo=False,         # Set to True for debugging SQL queries
)
# async_sessionmaker: each ``async with AsyncSessionLocal() as db`` yields an AsyncSession
# that is a proper async context manager (required for runner.run_tool / short-lived writes).
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Synchronous version for initialization scripts
# Create synchronous engine for initialization
sync_database_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
sync_engine = create_engine(sync_database_url)
SyncSessionLocal = sessionmaker(bind=sync_engine)

def get_sync_db():
    return SyncSessionLocal()
