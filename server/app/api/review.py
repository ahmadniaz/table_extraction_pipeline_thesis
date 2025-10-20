from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.config import get_db
from app.db import crud, schemas

router = APIRouter(prefix="/api/review", tags=["review"])

# --- Pydantic payload models for request bodies ---

class ApprovePayload(BaseModel):
    upload_id: UUID
    final_data: List[Dict[str, Any]]
    field_config: Optional[List[Dict[str, str]]] = None
    plan_types: Optional[List[str]] = None
    selected_statement_date: Optional[Dict[str, Any]] = None

class RejectPayload(BaseModel):
    upload_id: UUID
    final_data: List[Dict[str, Any]]
    rejection_reason: str
    field_config: Optional[List[Dict[str, str]]] = None
    plan_types: Optional[List[str]] = None
    selected_statement_date: Optional[Dict[str, Any]] = None

@router.post("/approve/")
async def approve_statement(
    payload: ApprovePayload,
    db: AsyncSession = Depends(get_db)
):
    try:
        updated = await crud.save_statement_review(
            db,
            upload_id=payload.upload_id,
            final_data=payload.final_data,
            status="Approved",
            field_config=payload.field_config,
            plan_types=payload.plan_types,
            selected_statement_date=payload.selected_statement_date,
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail=f"Upload with ID {payload.upload_id} not found")
            
        return {"success": True, "review": schemas.StatementReview.model_validate(updated)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reject/")
async def reject_statement(
    payload: RejectPayload,
    db: AsyncSession = Depends(get_db)
):
    try:
        updated = await crud.save_statement_review(
            db,
            upload_id=payload.upload_id,
            final_data=payload.final_data,
            status="Rejected",
            field_config=payload.field_config,
            rejection_reason=payload.rejection_reason,
            plan_types=payload.plan_types,
            selected_statement_date=payload.selected_statement_date,
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail=f"Upload with ID {payload.upload_id} not found")
            
        return {"success": True, "review": schemas.StatementReview.model_validate(updated)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all/")
async def get_all_reviews(db: AsyncSession = Depends(get_db)):
    rows = await crud.get_all_statement_reviews(db)
    return rows
