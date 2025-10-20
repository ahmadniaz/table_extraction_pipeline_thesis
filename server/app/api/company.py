from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db import crud, schemas
from app.config import get_db
from app.dependencies.auth_dependencies import get_current_user_hybrid
from app.db.models import User, StatementUpload
from typing import List
from pydantic import BaseModel

class CompanyIds(BaseModel):
    company_ids: List[str]

class CompanyUpdate(BaseModel):
    name: str

router = APIRouter(prefix="/api")

@router.get("/companies/", response_model=List[schemas.Company])
async def list_companies(db: AsyncSession = Depends(get_db)):
    return await crud.get_all_companies(db)

@router.get("/companies/{company_id}", response_model=schemas.Company)
async def get_company(company_id: str, db: AsyncSession = Depends(get_db)):
    company = await crud.get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.post("/companies/", response_model=schemas.Company)
async def create_company(company: schemas.CompanyCreate, db: AsyncSession = Depends(get_db)):
    db_company = await crud.get_company_by_name(db, name=company.name)
    if db_company:
        raise HTTPException(status_code=400, detail="Company already exists")
    return await crud.create_company(db, company)

@router.delete("/companies/{company_id}")
async def delete_company(
    company_id: str, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    company = await crud.get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if user has permission to delete this company/carrier
    # Non-admin users can only delete companies where ALL statements belong to them
    if current_user.role != "admin":
        # Get all statements for this carrier
        result = await db.execute(
            select(StatementUpload).where(
                or_(
                    StatementUpload.carrier_id == company_id,
                    StatementUpload.company_id == company_id
                )
            )
        )
        all_statements = result.scalars().all()
        
        # Check if ANY statement belongs to another user
        if all_statements:
            other_user_statements = [s for s in all_statements if str(s.user_id) != str(current_user.id)]
            if other_user_statements:
                raise HTTPException(
                    status_code=403, 
                    detail="You cannot delete a carrier that contains data from other users"
                )
        # If no statements exist, user can delete the empty carrier
    
    await crud.delete_company(db, company_id)
    return {"message": "Company deleted successfully"}

@router.delete("/companies/")
async def delete_multiple_companies(
    request: CompanyIds, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    company_ids = request.company_ids
    deleted_count = 0
    errors = []
    
    try:
        for company_id in company_ids:
            try:
                # Check if company exists
                company = await crud.get_company_by_id(db, company_id)
                if not company:
                    errors.append(f"Company with ID {company_id} not found")
                    continue
                
                # Check if user has permission to delete this company/carrier
                # Non-admin users can only delete companies where ALL statements belong to them
                if current_user.role != "admin":
                    # Get all statements for this carrier
                    result = await db.execute(
                        select(StatementUpload).where(
                            or_(
                                StatementUpload.carrier_id == company_id,
                                StatementUpload.company_id == company_id
                            )
                        )
                    )
                    all_statements = result.scalars().all()
                    
                    # Check if ANY statement belongs to another user
                    if all_statements:
                        other_user_statements = [s for s in all_statements if str(s.user_id) != str(current_user.id)]
                        if other_user_statements:
                            errors.append(f"Cannot delete carrier {company_id} - contains data from other users")
                            continue
                    # If no statements exist, user can delete the empty carrier
                
                await crud.delete_company(db, company_id)
                deleted_count += 1
            except Exception as e:
                errors.append(f"Failed to delete company with ID {company_id}: {str(e)}")
        
        if errors:
            # Return error response with 400 status code
            raise HTTPException(
                status_code=400, 
                detail=f"Some deletions failed. Deleted: {deleted_count}, Errors: {errors}"
            )
        
        return {"message": f"Successfully deleted {deleted_count} companies"}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Return error response with 500 status code for unexpected errors
        raise HTTPException(
            status_code=500, 
            detail=f"Transaction failed: {str(e)}"
        )

@router.patch("/companies/{company_id}", response_model=schemas.Company)
async def update_company(company_id: str, update: CompanyUpdate, db: AsyncSession = Depends(get_db)):
    company = await crud.get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    updated_company = await crud.update_company_name(db, company_id, update.name)
    return updated_company
