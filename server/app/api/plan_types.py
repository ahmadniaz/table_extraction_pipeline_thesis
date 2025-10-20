from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import crud, schemas
from app.config import get_db
from typing import List
from uuid import UUID

router = APIRouter(prefix="/api")

@router.get("/plan-types/", response_model=List[dict])
async def get_plan_types(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get all plan types"""
    try:
        plan_types = await crud.get_all_plan_types(db, active_only=active_only)
        return plan_types
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plan-types/{plan_type_id}", response_model=dict)
async def get_plan_type(
    plan_type_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific plan type by ID"""
    try:
        plan_type = await crud.get_plan_type_by_id(db, plan_type_id)
        if not plan_type:
            raise HTTPException(status_code=404, detail="Plan type not found")
        return plan_type
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plan-types/", response_model=dict)
async def create_plan_type(
    plan_type: schemas.PlanTypeCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new plan type"""
    try:
        # Check if display_name already exists
        existing_plan_type = await crud.get_plan_type_by_display_name(db, plan_type.display_name)
        if existing_plan_type:
            raise HTTPException(status_code=400, detail=f"Plan type with display name '{plan_type.display_name}' already exists")
        
        created_plan_type = await crud.create_plan_type(db, plan_type)
        return {
            "id": str(created_plan_type.id),
            "display_name": created_plan_type.display_name,
            "description": created_plan_type.description,
            "is_active": bool(created_plan_type.is_active),
            "created_at": created_plan_type.created_at,
            "updated_at": created_plan_type.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/plan-types/{plan_type_id}", response_model=dict)
async def update_plan_type(
    plan_type_id: UUID,
    plan_type_update: schemas.PlanTypeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a plan type"""
    try:
        # If display_name is being updated, check if it already exists
        if plan_type_update.display_name:
            existing_plan_type = await crud.get_plan_type_by_display_name(db, plan_type_update.display_name)
            if existing_plan_type and existing_plan_type.id != plan_type_id:
                raise HTTPException(status_code=400, detail=f"Plan type with display name '{plan_type_update.display_name}' already exists")
        
        updated_plan_type = await crud.update_plan_type(db, plan_type_id, plan_type_update)
        if not updated_plan_type:
            raise HTTPException(status_code=404, detail="Plan type not found")
        return updated_plan_type
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/plan-types/{plan_type_id}")
async def delete_plan_type(
    plan_type_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a plan type (soft delete)"""
    try:
        success = await crud.delete_plan_type(db, plan_type_id)
        if not success:
            raise HTTPException(status_code=404, detail="Plan type not found")
        return {"message": "Plan type deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plan-types/initialize/")
async def initialize_plan_types(db: AsyncSession = Depends(get_db)):
    """Initialize default plan types"""
    try:
        plan_types = await crud.initialize_default_plan_types(db)
        return {"message": f"Initialized {len(plan_types)} plan types", "plan_types": plan_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 