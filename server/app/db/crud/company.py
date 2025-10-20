from ..models import Company
from ..schemas import CompanyCreate
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import Optional

async def get_company_by_name(db, name: str):
    result = await db.execute(select(Company).where(Company.name == name))
    return result.scalar_one_or_none()

async def create_company(db, company: CompanyCreate):
    db_company = Company(name=company.name)
    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)
    return db_company

async def get_all_companies(db):
    result = await db.execute(select(Company))
    return result.scalars().all()

async def get_company_by_id(db, company_id):
    try:
        # Convert string to UUID if needed
        if isinstance(company_id, str):
            company_id = UUID(company_id)
        result = await db.execute(select(Company).where(Company.id == company_id))
        return result.scalar_one_or_none()
    except ValueError:
        # Invalid UUID format
        return None

async def delete_company(db: AsyncSession, company_id: str):
    # Fetch the company to ensure it exists
    company = await get_company_by_id(db, company_id)
    if not company:
        raise ValueError(f"Company with ID {company_id} not found")
    
    try:
        # Check which tables exist before trying to delete from them
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('company_field_mappings', 'edited_tables', 'statement_uploads', 'extractions', 'company_configurations', 'carrier_format_learning')
        """))
        existing_tables = {row[0] for row in result.fetchall()}
        
        # Delete related data first (cascade delete)
        # Delete company configurations
        if 'company_configurations' in existing_tables:
            await db.execute(
                text("DELETE FROM company_configurations WHERE company_id = :company_id"),
                {"company_id": company_id}
            )
        
        # Delete carrier format learning
        if 'carrier_format_learning' in existing_tables:
            await db.execute(
                text("DELETE FROM carrier_format_learning WHERE company_id = :company_id"),
                {"company_id": company_id}
            )
        
        # Delete company field mappings
        if 'company_field_mappings' in existing_tables:
            await db.execute(
                text("DELETE FROM company_field_mappings WHERE company_id = :company_id"),
                {"company_id": company_id}
            )
        
        # Delete edited tables (only if table exists)
        if 'edited_tables' in existing_tables:
            await db.execute(
                text("DELETE FROM edited_tables WHERE company_id = :company_id"),
                {"company_id": company_id}
            )
        
        # Delete statement uploads
        if 'statement_uploads' in existing_tables:
            await db.execute(
                text("DELETE FROM statement_uploads WHERE company_id = :company_id"),
                {"company_id": company_id}
            )
        
        # Delete extractions
        if 'extractions' in existing_tables:
            await db.execute(
                text("DELETE FROM extractions WHERE company_id = :company_id"),
                {"company_id": company_id}
            )
        
        # Finally delete the company
        await db.delete(company)
        
        # Commit the transaction
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise ValueError(f"Failed to delete company: {str(e)}")

async def update_company_name(db, company_id: str, new_name: str):
    company = await get_company_by_id(db, company_id)
    if not company:
        raise ValueError(f"Company with ID {company_id} not found")
    
    company.name = new_name
    await db.commit()
    await db.refresh(company)
    return company

async def get_latest_statement_upload_for_company(db, company_id):
    from ..models import StatementUpload as StatementUploadModel
    result = await db.execute(
        select(StatementUploadModel)
        .where(StatementUploadModel.company_id == company_id)
        .order_by(StatementUploadModel.uploaded_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
