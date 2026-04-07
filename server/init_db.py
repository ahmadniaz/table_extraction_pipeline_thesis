#!/usr/bin/env python3
"""
Database initialization script for the thesis evaluation system.
Creates the 4 core tables: documents, ground_truth_tables, extraction_results, evaluation_scores.
"""

import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.models import Base
from app.db.database import engine


async def init_db():
    """Create all tables defined in the models."""
    try:
        print("Creating database tables...")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("Database tables created successfully!")

        tables_to_check = [
            'documents',
            'ground_truth_tables',
            'extraction_results',
            'evaluation_scores',
        ]

        async with engine.begin() as conn:
            from sqlalchemy import text
            for table_name in tables_to_check:
                result = await conn.execute(text(
                    f"SELECT EXISTS ("
                    f"  SELECT FROM information_schema.tables "
                    f"  WHERE table_schema = 'public' "
                    f"  AND table_name = '{table_name}'"
                    f");"
                ))
                exists = result.scalar()
                status = "OK" if exists else "MISSING"
                print(f"  [{status}] {table_name}")

    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise


if __name__ == "__main__":
    print("Initializing thesis evaluation database...")
    asyncio.run(init_db())
    print("Database initialization complete.")
