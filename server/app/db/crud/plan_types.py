from ..models import PlanType
from ..schemas import PlanTypeCreate, PlanTypeUpdate
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID

async def create_plan_type(db: AsyncSession, plan_type: PlanTypeCreate):
    db_plan_type = PlanType(
        display_name=plan_type.display_name,
        description=plan_type.description,
        is_active=1 if plan_type.is_active else 0
    )
    db.add(db_plan_type)
    await db.commit()
    await db.refresh(db_plan_type)
    return db_plan_type

async def get_all_plan_types(db: AsyncSession, active_only: bool = True):
    query = select(PlanType)
    if active_only:
        query = query.where(PlanType.is_active == 1)
    result = await db.execute(query)
    plan_types = result.scalars().all()
    return [
        {
            "id": str(pt.id),
            "display_name": pt.display_name,
            "description": pt.description,
            "is_active": bool(pt.is_active),
            "created_at": pt.created_at,
            "updated_at": pt.updated_at
        }
        for pt in plan_types
    ]

async def get_plan_type_by_id(db: AsyncSession, plan_type_id: UUID):
    result = await db.execute(select(PlanType).where(PlanType.id == plan_type_id))
    pt = result.scalar_one_or_none()
    if pt:
        return {
            "id": str(pt.id),
            "display_name": pt.display_name,
            "description": pt.description,
            "is_active": bool(pt.is_active),
            "created_at": pt.created_at,
            "updated_at": pt.updated_at
        }
    return None

async def get_plan_type_by_display_name(db: AsyncSession, display_name: str):
    result = await db.execute(select(PlanType).where(PlanType.display_name == display_name))
    return result.scalar_one_or_none()

async def update_plan_type(db: AsyncSession, plan_type_id: UUID, plan_type_update: PlanTypeUpdate):
    result = await db.execute(select(PlanType).where(PlanType.id == plan_type_id))
    db_plan_type = result.scalar_one_or_none()
    
    if not db_plan_type:
        return None
    
    update_data = {}
    if plan_type_update.display_name is not None:
        update_data["display_name"] = plan_type_update.display_name
    if plan_type_update.description is not None:
        update_data["description"] = plan_type_update.description
    if plan_type_update.is_active is not None:
        update_data["is_active"] = 1 if plan_type_update.is_active else 0
    
    for key, value in update_data.items():
        setattr(db_plan_type, key, value)
    
    db_plan_type.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_plan_type)
    
    return {
        "id": str(db_plan_type.id),
        "display_name": db_plan_type.display_name,
        "description": db_plan_type.description,
        "is_active": bool(db_plan_type.is_active),
        "created_at": db_plan_type.created_at,
        "updated_at": db_plan_type.updated_at
    }

async def delete_plan_type(db: AsyncSession, plan_type_id: UUID):
    result = await db.execute(select(PlanType).where(PlanType.id == plan_type_id))
    db_plan_type = result.scalar_one_or_none()
    
    if not db_plan_type:
        return False
    
    # Soft delete by setting is_active to 0
    db_plan_type.is_active = 0
    db_plan_type.updated_at = datetime.utcnow()
    await db.commit()
    return True

async def initialize_default_plan_types(db: AsyncSession):
    """
    Initialize default plan types if they don't exist.
    """
    default_plan_types = [
        {"display_name": "Medical", "description": "Medical insurance plans"},
        {"display_name": "Dental", "description": "Dental insurance plans"},
        {"display_name": "Vision", "description": "Vision insurance plans"},
        {"display_name": "Life", "description": "Life insurance plans"},
        {"display_name": "Disability", "description": "Disability insurance plans"},
        {"display_name": "Supplemental", "description": "Supplemental insurance plans"},
    ]
    
    for plan_type_data in default_plan_types:
        existing = await get_plan_type_by_display_name(db, plan_type_data["display_name"])
        if not existing:
            plan_type = PlanTypeCreate(**plan_type_data)
            await create_plan_type(db, plan_type)
