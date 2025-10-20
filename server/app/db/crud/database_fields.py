from ..models import DatabaseField
from ..schemas import DatabaseFieldCreate, DatabaseFieldUpdate
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID

async def create_database_field(db: AsyncSession, field: DatabaseFieldCreate):
    """
    Create a new database field.
    """
    db_field = DatabaseField(
        display_name=field.display_name,
        description=field.description,
        is_active=field.is_active
    )
    db.add(db_field)
    await db.commit()
    await db.refresh(db_field)
    return db_field

async def get_all_database_fields(db: AsyncSession, active_only: bool = True):
    """
    Get all database fields, optionally filtered by active status.
    """
    query = select(DatabaseField)
    if active_only:
        query = query.where(DatabaseField.is_active == 1)
    result = await db.execute(query)
    return result.scalars().all()

async def get_database_field_by_id(db: AsyncSession, field_id: UUID):
    """
    Get database field by ID.
    """
    result = await db.execute(select(DatabaseField).where(DatabaseField.id == field_id))
    return result.scalar_one_or_none()

async def get_database_field_by_display_name(db: AsyncSession, display_name: str):
    """
    Get database field by display name.
    """
    result = await db.execute(select(DatabaseField).where(DatabaseField.display_name == display_name))
    return result.scalar_one_or_none()

async def update_database_field(db: AsyncSession, field_id: UUID, field_update: DatabaseFieldUpdate):
    """
    Update database field.
    """
    db_field = await get_database_field_by_id(db, field_id)
    if not db_field:
        return None
    
    update_data = {}
    if field_update.display_name is not None:
        update_data["display_name"] = field_update.display_name
    if field_update.description is not None:
        update_data["description"] = field_update.description
    if field_update.is_active is not None:
        update_data["is_active"] = field_update.is_active
    
    for field, value in update_data.items():
        setattr(db_field, field, value)
    
    db_field.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_field)
    return db_field

async def delete_database_field(db: AsyncSession, field_id: UUID):
    """
    Delete database field (soft delete by setting is_active to 0).
    """
    db_field = await get_database_field_by_id(db, field_id)
    if not db_field:
        return False
    
    db_field.is_active = 0
    db_field.updated_at = datetime.utcnow()
    await db.commit()
    return True

async def initialize_default_database_fields(db: AsyncSession):
    """
    Initialize default database fields if none exist.
    """
    existing_fields = await get_all_database_fields(db, active_only=False)
    if existing_fields:
        return existing_fields
    
    default_fields = [
        {"display_name": "Company Name", "description": "Name of the company"},
        {"display_name": "Group Id", "description": "Unique identifier for the group"},
        {"display_name": "Policy Number", "description": "Policy identification number"},
        {"display_name": "Commission Earned", "description": "Commission amount earned"},
        {"display_name": "Commission Rate", "description": "Commission rate percentage"},
        {"display_name": "Total Commission Paid", "description": "Total commission amount paid"},
        {"display_name": "Individual Commission", "description": "Individual commission amount"}
    ]
    
    created_fields = []
    for field_data in default_fields:
        field = DatabaseFieldCreate(**field_data)
        created_field = await create_database_field(db, field)
        created_fields.append(created_field)
    
    return created_fields
