#!/usr/bin/env python3
"""
Database initialization script to create all tables.
Run this script to create missing tables in your database.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.models import Base, PlanType, SummaryRowPattern, Company, CompanyFieldMapping, CompanyConfiguration, EarnedCommission
from app.config import engine

async def init_db():
    """Create all tables defined in the models."""
    try:
        print("Creating database tables...")
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created successfully!")
        
        # Verify all important tables were created
        tables_to_check = [
            'plan_types',
            'summary_row_patterns', 
            'companies',
            'company_field_mappings',
            'company_configurations',
            'database_fields',
            'earned_commissions'
        ]
        
        async with engine.begin() as conn:
            from sqlalchemy import text
            for table_name in tables_to_check:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table_name}'
                    );
                """))
                table_exists = result.scalar()
                
                if table_exists:
                    print(f"✅ {table_name} table exists!")
                else:
                    print(f"❌ {table_name} table was not created!")
                
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Initializing database...")
    asyncio.run(init_db())
    print("✨ Database initialization complete!") 