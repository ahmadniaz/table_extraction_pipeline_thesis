from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_, or_, cast, Text
from app.db import crud, schemas
from app.config import get_db
from app.db.models import StatementUpload, Company, EarnedCommission, User
from app.dependencies.auth_dependencies import get_current_user_hybrid
from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

router = APIRouter(prefix="/api")

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics - automatically filters by user data for regular users, global for admins"""
    try:
        # For admin users, show global data. For regular users, show only their data
        is_admin = current_user.role == 'admin'
        
        # Base query condition - admin sees all, regular users see only their data
        user_condition = True if is_admin else (StatementUpload.user_id == current_user.id)
        
        # Get total statements count
        total_statements_result = await db.execute(
            select(func.count(StatementUpload.id))
            .where(user_condition)
        )
        total_statements = total_statements_result.scalar() or 0

        # Get total carriers count - for admin show carriers with statements, for regular users show carriers they've worked with
        # NOTE: Use COALESCE to support both old (company_id) and new (carrier_id) data
        if is_admin:
            # For admin, get all unique carriers (both old and new format)
            # Old format: carrier stored in company_id, carrier_id is NULL
            # New format: carrier stored in carrier_id
            total_carriers_result = await db.execute(
                select(func.count(func.distinct(
                    func.coalesce(StatementUpload.carrier_id, StatementUpload.company_id)
                )))
            )
        else:
            # For regular users, only count carriers they've worked with
            total_carriers_result = await db.execute(
                select(func.count(func.distinct(
                    func.coalesce(StatementUpload.carrier_id, StatementUpload.company_id)
                )))
                .where(StatementUpload.user_id == current_user.id)
            )
        total_carriers = total_carriers_result.scalar() or 0

        # Get pending reviews count (extracted and success are considered pending for review)
        pending_query = select(func.count(StatementUpload.id)).where(
            and_(
                StatementUpload.status.in_(['extracted', 'success']),
                user_condition
            )
        )
        pending_reviews_result = await db.execute(pending_query)
        pending_reviews = pending_reviews_result.scalar() or 0

        # Get approved statements count (completed and Approved are considered approved)
        approved_query = select(func.count(StatementUpload.id)).where(
            and_(
                StatementUpload.status.in_(['completed', 'Approved']),
                user_condition
            )
        )
        approved_statements_result = await db.execute(approved_query)
        approved_statements = approved_statements_result.scalar() or 0

        # Get rejected statements count
        rejected_query = select(func.count(StatementUpload.id)).where(
            and_(
                StatementUpload.status == 'rejected',
                user_condition
            )
        )
        rejected_statements_result = await db.execute(rejected_query)
        rejected_statements = rejected_statements_result.scalar() or 0

        return {
            "total_statements": total_statements,
            "total_carriers": total_carriers,
            "total_premium": None,  # Coming soon
            "policies_count": None,  # Coming soon
            "pending_reviews": pending_reviews,
            "approved_statements": approved_statements,
            "rejected_statements": rejected_statements
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")

@router.get("/dashboard/statements")
async def get_all_statements(
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get all statements with company information - automatically filters by user data for regular users"""
    try:
        # For admin users, show all statements. For regular users, show only their statements
        is_admin = current_user.role == 'admin'
        
        # Build query with user filter
        query = select(StatementUpload, Company.name.label('company_name'))
        query = query.join(Company, StatementUpload.company_id == Company.id)
        
        # Apply user filter - admin sees all, regular users see only their data
        if not is_admin:
            query = query.where(StatementUpload.user_id == current_user.id)
        
        query = query.order_by(StatementUpload.uploaded_at.desc())
        
        result = await db.execute(query)
        statements = result.all()
        
        formatted_statements = []
        for statement, company_name in statements:
            formatted_statements.append({
                "id": str(statement.id),
                "file_name": statement.file_name,
                "gcs_key": statement.file_name,  # file_name IS the gcs_key
                "company_name": company_name,
                "status": statement.status,
                "uploaded_at": statement.uploaded_at.isoformat() if statement.uploaded_at else None,
                "last_updated": statement.last_updated.isoformat() if statement.last_updated else None,
                "completed_at": statement.completed_at.isoformat() if statement.completed_at else None,
                "rejection_reason": statement.rejection_reason,
                "plan_types": statement.plan_types,
                "raw_data": statement.raw_data,
                "edited_tables": statement.edited_tables,
                "final_data": statement.final_data,
                "selected_statement_date": statement.selected_statement_date
            })
        
        return formatted_statements
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statements: {str(e)}")

@router.get("/dashboard/statements/{status}")
async def get_statements_by_status(
    status: str, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get statements filtered by status (pending, approved, rejected) - automatically filters by user data"""
    try:
        if status not in ['pending', 'approved', 'rejected']:
            raise HTTPException(status_code=400, detail="Invalid status. Must be pending, approved, or rejected")
        
        # For admin users, show all statements. For regular users, show only their statements
        is_admin = current_user.role == 'admin'
        
        # Map frontend status to database statuses
        status_mapping = {
            'pending': ['extracted', 'success'],
            'approved': ['completed', 'Approved'],
            'rejected': ['rejected']
        }
        
        db_statuses = status_mapping.get(status, [])
        
        query = select(StatementUpload, Company.name.label('company_name'))
        query = query.join(Company, StatementUpload.company_id == Company.id)
        query = query.where(StatementUpload.status.in_(db_statuses))
        
        # Apply user filter - admin sees all, regular users see only their data
        if not is_admin:
            query = query.where(StatementUpload.user_id == current_user.id)
        
        query = query.order_by(StatementUpload.uploaded_at.desc())
        
        result = await db.execute(query)
        statements = result.all()
        
        formatted_statements = []
        for statement, company_name in statements:
            formatted_statements.append({
                "id": str(statement.id),
                "file_name": statement.file_name,
                "gcs_key": statement.file_name,  # file_name IS the gcs_key
                "company_name": company_name,
                "status": statement.status,
                "uploaded_at": statement.uploaded_at.isoformat() if statement.uploaded_at else None,
                "last_updated": statement.last_updated.isoformat() if statement.last_updated else None,
                "completed_at": statement.completed_at.isoformat() if statement.completed_at else None,
                "rejection_reason": statement.rejection_reason,
                "plan_types": statement.plan_types,
                "raw_data": statement.raw_data,
                "edited_tables": statement.edited_tables,
                "final_data": statement.final_data,
                "selected_statement_date": statement.selected_statement_date
            })
        
        return formatted_statements
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statements: {str(e)}")

@router.get("/dashboard/carriers")
async def get_carriers_with_statement_counts(
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get carriers with their statement counts - automatically filters by user data for regular users"""
    try:
        # For admin users, show all carriers. For regular users, show only carriers they've worked with
        is_admin = current_user.role == 'admin'
        
        if is_admin:
            # Admin sees all carriers with total statement counts
            # NOTE: Support both old (company_id) and new (carrier_id) format
            result = await db.execute(
                select(
                    Company.id,
                    Company.name,
                    func.count(StatementUpload.id).label('statement_count')
                )
                .outerjoin(StatementUpload, or_(
                    Company.id == StatementUpload.carrier_id,
                    and_(
                        Company.id == StatementUpload.company_id,
                        StatementUpload.carrier_id.is_(None)
                    )
                ))
                .group_by(Company.id, Company.name)
                .order_by(Company.name)
            )
        else:
            # Regular users see only carriers they've uploaded statements for
            # NOTE: Support both old (company_id) and new (carrier_id) format
            result = await db.execute(
                select(
                    Company.id,
                    Company.name,
                    func.count(StatementUpload.id).label('statement_count')
                )
                .join(StatementUpload, or_(
                    Company.id == StatementUpload.carrier_id,
                    and_(
                        Company.id == StatementUpload.company_id,
                        StatementUpload.carrier_id.is_(None)
                    )
                ))
                .where(StatementUpload.user_id == current_user.id)
                .group_by(Company.id, Company.name)
                .order_by(Company.name)
            )
        
        carriers = result.all()
        
        formatted_carriers = []
        for carrier_id, name, statement_count in carriers:
            formatted_carriers.append({
                "id": str(carrier_id),
                "name": name,
                "statement_count": statement_count or 0
            })
        
        return formatted_carriers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching carriers: {str(e)}")

@router.get("/dashboard/carriers/{carrier_id}/statements")
async def get_statements_by_carrier(carrier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all statements for a specific carrier"""
    try:
        # Get carrier name
        carrier_result = await db.execute(
            select(Company.name).where(Company.id == carrier_id)
        )
        carrier_name = carrier_result.scalar()
        
        if not carrier_name:
            raise HTTPException(status_code=404, detail="Carrier not found")
        
        # Get statements for this carrier
        # NOTE: Support both old (company_id) and new (carrier_id) format
        result = await db.execute(
            select(StatementUpload)
            .where(
                or_(
                    StatementUpload.carrier_id == carrier_id,
                    and_(
                        StatementUpload.company_id == carrier_id,
                        StatementUpload.carrier_id.is_(None)
                    )
                )
            )
            .order_by(StatementUpload.uploaded_at.desc())
        )
        statements = result.scalars().all()
        
        formatted_statements = []
        for statement in statements:
            formatted_statements.append({
                "id": str(statement.id),
                "file_name": statement.file_name,
                "gcs_key": statement.file_name,  # file_name IS the gcs_key
                "company_name": carrier_name,
                "status": statement.status,
                "uploaded_at": statement.uploaded_at.isoformat() if statement.uploaded_at else None,
                "last_updated": statement.last_updated.isoformat() if statement.last_updated else None,
                "completed_at": statement.completed_at.isoformat() if statement.completed_at else None,
                "rejection_reason": statement.rejection_reason,
                "plan_types": statement.plan_types,
                "raw_data": statement.raw_data,
                "edited_tables": statement.edited_tables,
                "final_data": statement.final_data,
                "selected_statement_date": statement.selected_statement_date
            })
        
        return formatted_statements
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching carrier statements: {str(e)}")

@router.get("/dashboard/carriers/{carrier_id}/statements/{status}")
async def get_statements_by_carrier_and_status(
    carrier_id: UUID, 
    status: str, 
    db: AsyncSession = Depends(get_db)
):
    """Get statements for a specific carrier filtered by status"""
    try:
        if status not in ['pending', 'approved', 'rejected']:
            raise HTTPException(status_code=400, detail="Invalid status. Must be pending, approved, or rejected")
        
        # Get carrier name
        carrier_result = await db.execute(
            select(Company.name).where(Company.id == carrier_id)
        )
        carrier_name = carrier_result.scalar()
        
        if not carrier_name:
            raise HTTPException(status_code=404, detail="Carrier not found")
        
        # Map frontend status to database statuses
        status_mapping = {
            'pending': ['extracted', 'success', 'pending'],
            'approved': ['completed', 'Approved'],
            'rejected': ['rejected']
        }
        
        db_statuses = status_mapping.get(status, [])
        
        # Get statements for this carrier with status filter
        # NOTE: Support both old (company_id) and new (carrier_id) format
        result = await db.execute(
            select(StatementUpload)
            .where(
                or_(
                    StatementUpload.carrier_id == carrier_id,
                    and_(
                        StatementUpload.company_id == carrier_id,
                        StatementUpload.carrier_id.is_(None)
                    )
                )
            )
            .where(StatementUpload.status.in_(db_statuses))
            .order_by(StatementUpload.uploaded_at.desc())
        )
        statements = result.scalars().all()
        
        formatted_statements = []
        for statement in statements:
            formatted_statements.append({
                "id": str(statement.id),
                "file_name": statement.file_name,
                "gcs_key": statement.file_name,  # file_name IS the gcs_key
                "company_name": carrier_name,
                "status": statement.status,
                "uploaded_at": statement.uploaded_at.isoformat() if statement.uploaded_at else None,
                "last_updated": statement.last_updated.isoformat() if statement.last_updated else None,
                "completed_at": statement.completed_at.isoformat() if statement.completed_at else None,
                "rejection_reason": statement.rejection_reason,
                "plan_types": statement.plan_types,
                "raw_data": statement.raw_data,
                "edited_tables": statement.edited_tables,
                "final_data": statement.final_data,
                "selected_statement_date": statement.selected_statement_date
            })
        
        return formatted_statements
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching carrier statements: {str(e)}")

@router.get("/companies/user-specific")
async def get_user_specific_companies(
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get carriers that the current user has worked with"""
    try:
        # Get carriers that the user has uploaded statements for
        # NOTE: Support both old (company_id) and new (carrier_id) format
        # Old format: carrier stored in company_id, carrier_id is NULL
        # New format: carrier stored in carrier_id
        
        # Get all unique carrier IDs from both old and new format
        user_carriers_result = await db.execute(
            select(
                func.coalesce(StatementUpload.carrier_id, StatementUpload.company_id).label('carrier_id')
            )
            .where(StatementUpload.user_id == current_user.id)
            .distinct()
        )
        user_carrier_ids = [row[0] for row in user_carriers_result.all() if row[0] is not None]
        
        if not user_carrier_ids:
            return []
        
        # Get company details for user's carriers
        companies_result = await db.execute(
            select(Company.id, Company.name)
            .where(Company.id.in_(user_carrier_ids))
            .order_by(Company.name.asc())
        )
        
        companies = []
        for company_id, company_name in companies_result.all():
            companies.append({
                "id": str(company_id),
                "name": company_name
            })
        
        return companies

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user-specific companies: {str(e)}")

@router.get("/companies/user-specific/{company_id}/statements")
async def get_user_specific_company_statements(
    company_id: UUID,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get statements for a specific carrier that the current user has uploaded"""
    try:
        # Get statements for this carrier that the user has uploaded
        # NOTE: Support both old (company_id) and new (carrier_id) format
        statements_result = await db.execute(
            select(StatementUpload)
            .where(
                and_(
                    or_(
                        StatementUpload.carrier_id == company_id,
                        and_(
                            StatementUpload.company_id == company_id,
                            StatementUpload.carrier_id.is_(None)
                        )
                    ),
                    StatementUpload.user_id == current_user.id
                )
            )
            .order_by(StatementUpload.uploaded_at.desc())
        )
        
        statements = statements_result.scalars().all()
        
        formatted_statements = []
        for statement in statements:
            formatted_statements.append({
                "id": str(statement.id),
                "file_name": statement.file_name,
                "gcs_key": statement.file_name,  # file_name IS the gcs_key
                "uploaded_at": statement.uploaded_at.isoformat() if statement.uploaded_at else None,
                "status": statement.status,
                "rejection_reason": statement.rejection_reason,
                "selected_statement_date": statement.selected_statement_date,
                "final_data": statement.final_data,
                "edited_tables": statement.edited_tables,  # Include edited tables for preview
                "field_config": statement.field_config,
                "raw_data": statement.raw_data
            })
        
        return formatted_statements

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user-specific company statements: {str(e)}")

@router.get("/dashboard/earned-commissions")
async def get_all_earned_commissions(
    year: Optional[int] = None, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get earned commission data - user-specific for regular users, global for admins"""
    try:
        # For admin users, show global data. For regular users, show only their data
        is_admin = current_user.role == 'admin'
        
        # Build base query with proper user filtering using the new user_id field
        query = select(EarnedCommission, Company.name.label('carrier_name')).join(
            Company, EarnedCommission.carrier_id == Company.id
        )
        
        # Apply user filter for non-admin users - now using the user_id field directly
        if not is_admin:
            query = query.where(EarnedCommission.user_id == current_user.id)
        
        # Apply year filter if provided
        if year is not None:
            query = query.where(EarnedCommission.statement_year == year)
        
        query = query.order_by(Company.name, EarnedCommission.client_name)
        
        result = await db.execute(query)
        commissions = result.all()
        
        # Get statement counts per carrier from StatementUpload table (approved only)
        # CRITICAL FIX: For non-admin users, count only their statements
        carrier_statement_counts = {}
        unique_carrier_ids = list(set(commission.carrier_id for commission, _ in commissions))
        
        for carrier_id in unique_carrier_ids:
            statement_conditions = [
                or_(
                    StatementUpload.carrier_id == carrier_id,
                    and_(
                        StatementUpload.company_id == carrier_id,
                        StatementUpload.carrier_id.is_(None)
                    )
                ),
                StatementUpload.status.in_(['completed', 'Approved'])
            ]
            
            # Add user filter for non-admin users
            if not is_admin:
                statement_conditions.append(StatementUpload.user_id == current_user.id)
            
            count_result = await db.execute(
                select(func.count(StatementUpload.id))
                .where(and_(*statement_conditions))
            )
            carrier_statement_counts[carrier_id] = count_result.scalar() or 0
        
        formatted_commissions = []
        for commission, carrier_name in commissions:
            formatted_commissions.append({
                "id": str(commission.id),
                "carrier_id": str(commission.carrier_id),
                "carrier_name": carrier_name,
                "client_name": commission.client_name,
                "invoice_total": float(commission.invoice_total),
                "commission_earned": float(commission.commission_earned),
                "statement_count": commission.statement_count,
                "upload_ids": commission.upload_ids or [],
                "approved_statement_count": carrier_statement_counts.get(commission.carrier_id, 0),
                "statement_date": commission.statement_date.isoformat() if commission.statement_date else None,
                "statement_month": commission.statement_month,
                "statement_year": commission.statement_year,
                "monthly_breakdown": {
                    "jan": float(commission.jan_commission),
                    "feb": float(commission.feb_commission),
                    "mar": float(commission.mar_commission),
                    "apr": float(commission.apr_commission),
                    "may": float(commission.may_commission),
                    "jun": float(commission.jun_commission),
                    "jul": float(commission.jul_commission),
                    "aug": float(commission.aug_commission),
                    "sep": float(commission.sep_commission),
                    "oct": float(commission.oct_commission),
                    "nov": float(commission.nov_commission),
                    "dec": float(commission.dec_commission)
                },
                "last_updated": commission.last_updated.isoformat() if commission.last_updated else None,
                "created_at": commission.created_at.isoformat() if commission.created_at else None
            })
        
        return formatted_commissions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching earned commissions: {str(e)}")

@router.get("/dashboard/carriers/{carrier_id}/earned-commissions")
async def get_earned_commissions_by_carrier(carrier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get earned commission data for a specific carrier"""
    try:
        # Verify carrier exists
        carrier_result = await db.execute(
            select(Company.name).where(Company.id == carrier_id)
        )
        carrier_name = carrier_result.scalar()
        
        if not carrier_name:
            raise HTTPException(status_code=404, detail="Carrier not found")
        
        commissions = await crud.get_earned_commissions_by_carrier(db, carrier_id)
        
        formatted_commissions = []
        for commission in commissions:
            formatted_commissions.append({
                "id": str(commission.id),
                "carrier_id": str(commission.carrier_id),
                "carrier_name": carrier_name,
                "client_name": commission.client_name,
                "invoice_total": float(commission.invoice_total),
                "commission_earned": float(commission.commission_earned),
                "statement_count": commission.statement_count,
                "upload_ids": commission.upload_ids or [],
                "statement_date": commission.statement_date.isoformat() if commission.statement_date else None,
                "statement_month": commission.statement_month,
                "statement_year": commission.statement_year,
                "monthly_breakdown": {
                    "jan": float(commission.jan_commission),
                    "feb": float(commission.feb_commission),
                    "mar": float(commission.mar_commission),
                    "apr": float(commission.apr_commission),
                    "may": float(commission.may_commission),
                    "jun": float(commission.jun_commission),
                    "jul": float(commission.jul_commission),
                    "aug": float(commission.aug_commission),
                    "sep": float(commission.sep_commission),
                    "oct": float(commission.oct_commission),
                    "nov": float(commission.nov_commission),
                    "dec": float(commission.dec_commission)
                },
                "last_updated": commission.last_updated.isoformat() if commission.last_updated else None,
                "created_at": commission.created_at.isoformat() if commission.created_at else None
            })
        
        return formatted_commissions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching carrier earned commissions: {str(e)}")

@router.get("/dashboard/earned-commissions/years")
async def get_available_years(db: AsyncSession = Depends(get_db)):
    """Get all available years for earned commission data"""
    try:
        result = await db.execute(
            select(EarnedCommission.statement_year)
            .where(EarnedCommission.statement_year.isnot(None))
            .distinct()
            .order_by(EarnedCommission.statement_year.desc())
        )
        years = [row[0] for row in result.all() if row[0] is not None]
        return {"years": years}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching available years: {str(e)}")

@router.get("/dashboard/earned-commissions/summary")
async def get_earned_commissions_summary(db: AsyncSession = Depends(get_db)):
    """Get summary statistics for earned commissions"""
    try:
        commissions = await crud.get_all_earned_commissions(db)
        
        total_commission = sum(float(commission.commission_earned) for commission, _ in commissions)
        total_invoice = sum(float(commission.invoice_total) for commission, _ in commissions)
        total_clients = len(set(commission.client_name for commission, _ in commissions))
        total_carriers = len(set(commission.carrier_id for commission, _ in commissions))
        
        return {
            "total_commission_earned": total_commission,
            "total_invoice_amount": total_invoice,
            "total_clients": total_clients,
            "total_carriers": total_carriers,
            "total_records": len(commissions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching earned commissions summary: {str(e)}")

@router.get("/earned-commission/stats")
async def get_earned_commission_stats(
    year: Optional[int] = None, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get earned commission statistics - user-specific for regular users, global for admins"""
    try:
        # For admin users, show global data. For regular users, show only their data
        is_admin = current_user.role == 'admin'
        
        # Build base conditions using the new user_id field
        base_conditions = []
        if year is not None:
            base_conditions.append(EarnedCommission.statement_year == year)
        
        # Add user filter for non-admin users - now using the user_id field directly
        if not is_admin:
            base_conditions.append(EarnedCommission.user_id == current_user.id)

        # Get total invoice amounts
        if base_conditions:
            total_invoice_result = await db.execute(
                select(func.sum(EarnedCommission.invoice_total))
                .where(and_(*base_conditions))
            )
        else:
            total_invoice_result = await db.execute(
                select(func.sum(EarnedCommission.invoice_total))
            )
        total_invoice = float(total_invoice_result.scalar() or 0)

        # Get total commission earned
        if base_conditions:
            total_commission_result = await db.execute(
                select(func.sum(EarnedCommission.commission_earned))
                .where(and_(*base_conditions))
            )
        else:
            total_commission_result = await db.execute(
                select(func.sum(EarnedCommission.commission_earned))
            )
        total_commission = float(total_commission_result.scalar() or 0)

        # Get total carriers with commission data
        if base_conditions:
            total_carriers_result = await db.execute(
                select(func.count(func.distinct(EarnedCommission.carrier_id)))
                .where(and_(*base_conditions))
            )
        else:
            total_carriers_result = await db.execute(
                select(func.count(func.distinct(EarnedCommission.carrier_id)))
            )
        total_carriers = total_carriers_result.scalar() or 0

        # Get total companies/clients (normalized names)
        if base_conditions:
            total_companies_result = await db.execute(
                select(func.count(func.distinct(func.lower(func.trim(EarnedCommission.client_name)))))
                .where(and_(*base_conditions))
            )
        else:
            total_companies_result = await db.execute(
                select(func.count(func.distinct(func.lower(func.trim(EarnedCommission.client_name)))))
            )
        total_companies = total_companies_result.scalar() or 0

        # Get total approved statements count from StatementUpload table
        statement_conditions = [StatementUpload.status.in_(['completed', 'Approved'])]
        if year is not None:
            # Note: This would require a statement_year field in StatementUpload
            # For now, just count all approved statements
            pass
        
        if not is_admin:
            statement_conditions.append(StatementUpload.user_id == current_user.id)
        
        total_statements_result = await db.execute(
            select(func.count(StatementUpload.id))
            .where(and_(*statement_conditions))
        )
        total_statements = total_statements_result.scalar() or 0

        return {
            "total_invoice": total_invoice,
            "total_commission": total_commission,
            "total_carriers": total_carriers,
            "total_companies": total_companies,
            "total_statements": total_statements
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching earned commission stats: {str(e)}")

@router.get("/earned-commission/global/stats")
async def get_global_earned_commission_stats(
    year: Optional[int] = None, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get global earned commission statistics (all data) - requires admin or explicit permission"""
    try:
        # For now, allow all authenticated users to view global data
        # In production, you might want to add additional permission checks
        
        # Get total invoice amounts
        if year is not None:
            total_invoice_result = await db.execute(
                select(func.sum(EarnedCommission.invoice_total))
                .where(EarnedCommission.statement_year == year)
            )
        else:
            total_invoice_result = await db.execute(
                select(func.sum(EarnedCommission.invoice_total))
            )
        total_invoice = float(total_invoice_result.scalar() or 0)

        # Get total commission earned
        if year is not None:
            total_commission_result = await db.execute(
                select(func.sum(EarnedCommission.commission_earned))
                .where(EarnedCommission.statement_year == year)
            )
        else:
            total_commission_result = await db.execute(
                select(func.sum(EarnedCommission.commission_earned))
            )
        total_commission = float(total_commission_result.scalar() or 0)

        # Get total carriers with commission data
        if year is not None:
            total_carriers_result = await db.execute(
                select(func.count(func.distinct(EarnedCommission.carrier_id)))
                .where(EarnedCommission.statement_year == year)
            )
        else:
            total_carriers_result = await db.execute(
                select(func.count(func.distinct(EarnedCommission.carrier_id)))
            )
        total_carriers = total_carriers_result.scalar() or 0

        # Get total companies/clients (normalized names)
        if year is not None:
            total_companies_result = await db.execute(
                select(func.count(func.distinct(func.lower(func.trim(EarnedCommission.client_name)))))
                .where(EarnedCommission.statement_year == year)
            )
        else:
            total_companies_result = await db.execute(
                select(func.count(func.distinct(func.lower(func.trim(EarnedCommission.client_name)))))
            )
        total_companies = total_companies_result.scalar() or 0

        # Get total approved statements count from StatementUpload table
        total_statements_result = await db.execute(
            select(func.count(StatementUpload.id))
            .where(StatementUpload.status.in_(['completed', 'Approved']))
        )
        total_statements = total_statements_result.scalar() or 0

        return {
            "total_invoice": total_invoice,
            "total_commission": total_commission,
            "total_carriers": total_carriers,
            "total_companies": total_companies,
            "total_statements": total_statements
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching global earned commission stats: {str(e)}")

@router.get("/earned-commission/global/data")
async def get_global_earned_commissions(
    year: Optional[int] = None, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get global earned commission data (all data) - requires admin or explicit permission"""
    try:
        # For now, allow all authenticated users to view global data
        # In production, you might want to add additional permission checks
        
        # Get all earned commissions (global data)
        commissions = await crud.get_all_earned_commissions(db, year=year)
        
        # Get statement counts per carrier from StatementUpload table (approved only)
        carrier_statement_counts = {}
        unique_carrier_ids = list(set(commission.carrier_id for commission, _ in commissions))
        
        for carrier_id in unique_carrier_ids:
            count_result = await db.execute(
                select(func.count(StatementUpload.id))
                .where(
                    and_(
                        or_(
                            StatementUpload.carrier_id == carrier_id,
                            and_(
                                StatementUpload.company_id == carrier_id,
                                StatementUpload.carrier_id.is_(None)
                            )
                        ),
                        StatementUpload.status.in_(['completed', 'Approved'])
                    )
                )
            )
            carrier_statement_counts[carrier_id] = count_result.scalar() or 0
        
        formatted_commissions = []
        for commission, carrier_name in commissions:
            formatted_commissions.append({
                "id": str(commission.id),
                "carrier_id": str(commission.carrier_id),
                "carrier_name": carrier_name,
                "client_name": commission.client_name,
                "invoice_total": float(commission.invoice_total),
                "commission_earned": float(commission.commission_earned),
                "statement_count": commission.statement_count,
                "upload_ids": commission.upload_ids or [],
                "approved_statement_count": carrier_statement_counts.get(commission.carrier_id, 0),
                "statement_date": commission.statement_date.isoformat() if commission.statement_date else None,
                "statement_month": commission.statement_month,
                "statement_year": commission.statement_year,
                "monthly_breakdown": {
                    "jan": float(commission.jan_commission),
                    "feb": float(commission.feb_commission),
                    "mar": float(commission.mar_commission),
                    "apr": float(commission.apr_commission),
                    "may": float(commission.may_commission),
                    "jun": float(commission.jun_commission),
                    "jul": float(commission.jul_commission),
                    "aug": float(commission.aug_commission),
                    "sep": float(commission.sep_commission),
                    "oct": float(commission.oct_commission),
                    "nov": float(commission.nov_commission),
                    "dec": float(commission.dec_commission)
                },
                "last_updated": commission.last_updated.isoformat() if commission.last_updated else None,
                "created_at": commission.created_at.isoformat() if commission.created_at else None
            })
        
        return formatted_commissions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching global earned commission data: {str(e)}")

@router.get("/earned-commission/carrier/{carrier_id}/stats")
async def get_carrier_earned_commission_stats(carrier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get earned commission statistics for a specific carrier"""
    try:
        # Get carrier name
        carrier_result = await db.execute(
            select(Company.name).where(Company.id == carrier_id)
        )
        carrier_name = carrier_result.scalar()
        
        if not carrier_name:
            raise HTTPException(status_code=404, detail="Carrier not found")

        # CRITICAL FIX: Only count commission records that have valid upload_ids
        # This excludes orphaned records from deleted statements
        base_conditions = [
            EarnedCommission.carrier_id == carrier_id,
            EarnedCommission.upload_ids.isnot(None),
            cast(EarnedCommission.upload_ids, Text) != '[]'  # Exclude empty arrays (cast JSON to text for comparison)
        ]
        
        # Get total invoice amounts for this carrier
        total_invoice_result = await db.execute(
            select(func.sum(EarnedCommission.invoice_total))
            .where(and_(*base_conditions))
        )
        total_invoice = float(total_invoice_result.scalar() or 0)

        # Get total commission earned for this carrier
        total_commission_result = await db.execute(
            select(func.sum(EarnedCommission.commission_earned))
            .where(and_(*base_conditions))
        )
        total_commission = float(total_commission_result.scalar() or 0)

        # Get total companies for this carrier
        total_companies_result = await db.execute(
            select(func.count(func.distinct(EarnedCommission.client_name)))
            .where(and_(*base_conditions))
        )
        total_companies = total_companies_result.scalar() or 0

        # Get total statements (unique uploaded files) for this carrier
        # Collect all upload_ids from all records and count unique ones
        upload_ids_result = await db.execute(
            select(EarnedCommission.upload_ids)
            .where(and_(*base_conditions))
        )
        all_upload_ids = set()
        for row in upload_ids_result.all():
            if row[0]:  # upload_ids field
                all_upload_ids.update(row[0])
        total_statements = len(all_upload_ids)

        return {
            "carrier_name": carrier_name,
            "total_invoice": total_invoice,
            "total_commission": total_commission,
            "total_companies": total_companies,
            "total_statements": total_statements
        }
    except Exception as e:
        raise

@router.get("/earned-commission/carrier/user-specific/{carrier_id}/stats")
async def get_user_specific_carrier_earned_commission_stats(
    carrier_id: UUID, 
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get earned commission statistics for a specific carrier, filtered by user's uploaded statements
    
    Args:
        carrier_id: UUID of the carrier
        year: Optional year filter (e.g., 2025)
        month: Optional month filter (1-12)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Statistics for the carrier including total invoice, commission, companies, and statements
    """
    try:
        # Get carrier name
        carrier_result = await db.execute(
            select(Company.name).where(Company.id == carrier_id)
        )
        carrier_name = carrier_result.scalar()
        
        if not carrier_name:
            raise HTTPException(status_code=404, detail="Carrier not found")

        # Check if user has uploaded statements for this carrier
        # NOTE: Support both old (company_id) and new (carrier_id) format
        user_carrier_check = await db.execute(
            select(func.count(StatementUpload.id))
            .where(
                and_(
                    or_(
                        StatementUpload.carrier_id == carrier_id,
                        and_(
                            StatementUpload.company_id == carrier_id,
                            StatementUpload.carrier_id.is_(None)
                        )
                    ),
                    StatementUpload.user_id == current_user.id
                )
            )
        )
        user_has_statements = user_carrier_check.scalar() > 0

        if not user_has_statements:
            # User has no statements for this carrier, return zeros
            return {
                "carrier_name": carrier_name,
                "total_invoice": 0.0,
                "total_commission": 0.0,
                "total_companies": 0,
                "total_statements": 0
            }

        # Build query with proper user filtering using the new user_id field
        query_conditions = [
            EarnedCommission.carrier_id == carrier_id,
            EarnedCommission.user_id == current_user.id
        ]
        
        # Add year filter if provided
        if year is not None:
            query_conditions.append(EarnedCommission.statement_year == year)
        
        # Add month filter if provided
        if month is not None:
            query_conditions.append(EarnedCommission.statement_month == month)
        
        # Get all earned commissions for this carrier with filters
        earned_commissions_result = await db.execute(
            select(EarnedCommission)
            .where(and_(*query_conditions))
        )
        earned_commissions = earned_commissions_result.scalars().all()

        # Calculate totals directly
        total_invoice = sum(float(commission.invoice_total or 0) for commission in earned_commissions)
        total_commission = sum(float(commission.commission_earned or 0) for commission in earned_commissions)

        # Get unique companies from user's commission data
        unique_companies = set(commission.client_name for commission in earned_commissions if commission.client_name)
        total_companies = len(unique_companies)
        
        # Get user's statement count for this carrier
        statement_count_result = await db.execute(
            select(func.count(StatementUpload.id))
            .where(
                and_(
                    or_(
                        StatementUpload.carrier_id == carrier_id,
                        and_(
                            StatementUpload.company_id == carrier_id,
                            StatementUpload.carrier_id.is_(None)
                        )
                    ),
                    StatementUpload.user_id == current_user.id
                )
            )
        )
        total_statements = statement_count_result.scalar() or 0

        return {
            "carrier_name": carrier_name,
            "total_invoice": total_invoice,
            "total_commission": total_commission,
            "total_companies": total_companies,
            "total_statements": total_statements,
            "filters_applied": {
                "year": year,
                "month": month
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user-specific carrier stats: {str(e)}")

@router.get("/earned-commission/carriers")
async def get_carriers_with_commission_data(
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get carriers with earned commission data - user-specific for regular users, global for admins"""
    try:
        # For admin users, show all carriers. For regular users, show only carriers they've worked with
        is_admin = current_user.role == 'admin'
        
        # Build query with proper user filtering using the new user_id field
        query = select(
            Company.id, 
            Company.name, 
            func.sum(EarnedCommission.commission_earned).label('total_commission')
        ).join(
            EarnedCommission, Company.id == EarnedCommission.carrier_id
        )
        
        # Add user filter for non-admin users - now using the user_id field directly
        if not is_admin:
            query = query.where(EarnedCommission.user_id == current_user.id)
        
        query = query.group_by(Company.id, Company.name).order_by(
            func.sum(EarnedCommission.commission_earned).desc()
        )
        
        result = await db.execute(query)
        
        carriers = []
        for row in result.all():
            carriers.append({
                "id": str(row.id),
                "name": row.name,
                "total_commission": float(row.total_commission or 0)
            })
        
        return carriers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching carriers with commission data: {str(e)}")

@router.get("/earned-commission/carriers-detailed")
async def get_carriers_with_detailed_commission_data(
    year: int = None,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get carriers with detailed commission data including statement counts"""
    try:
        # For admin users, show all carriers. For regular users, show only carriers they've worked with
        is_admin = current_user.role == 'admin'
        
        # Build query with proper user filtering using the new user_id field
        commission_query = select(
            Company.id,
            Company.name,
            func.sum(EarnedCommission.commission_earned).label('total_commission')
        ).join(EarnedCommission, Company.id == EarnedCommission.carrier_id)
        
        # Add user filter for non-admin users - now using the user_id field directly
        if not is_admin:
            commission_query = commission_query.where(EarnedCommission.user_id == current_user.id)
        
        # Filter by year if provided
        if year:
            commission_query = commission_query.where(EarnedCommission.statement_year == year)
        
        commission_query = commission_query.group_by(Company.id, Company.name).order_by(
            func.sum(EarnedCommission.commission_earned).desc()
        )
        
        result = await db.execute(commission_query)
        
        carriers = []
        for row in result.all():
            carrier_id = row.id
            
            # Count statements for this carrier
            statement_count_query = select(func.count(StatementUpload.id)).where(
                func.coalesce(StatementUpload.carrier_id, StatementUpload.company_id) == carrier_id
            )
            
            # Add user filter for non-admin users
            if not is_admin:
                statement_count_query = statement_count_query.where(StatementUpload.user_id == current_user.id)
            
            statement_count_result = await db.execute(statement_count_query)
            statement_count = statement_count_result.scalar() or 0
            
            carriers.append({
                "id": str(carrier_id),
                "name": row.name,
                "total_commission": float(row.total_commission or 0),
                "statement_count": int(statement_count)
            })
        
        return carriers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching detailed carriers commission data: {str(e)}")

@router.get("/earned-commission/carrier/{carrier_id}/data")
async def get_carrier_commission_data(
    carrier_id: UUID, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed commission data for a specific carrier - user-specific for regular users"""
    try:
        # Get carrier name
        carrier_result = await db.execute(
            select(Company.name).where(Company.id == carrier_id)
        )
        carrier_name = carrier_result.scalar()
        
        if not carrier_name:
            raise HTTPException(status_code=404, detail="Carrier not found")

        # Get commission data for this carrier with proper user filtering using the new user_id field
        is_admin = current_user.role == 'admin'
        
        query = select(EarnedCommission).where(EarnedCommission.carrier_id == carrier_id)
        
        # Add user filter for non-admin users - now using the user_id field directly
        if not is_admin:
            query = query.where(EarnedCommission.user_id == current_user.id)
        
        query = query.order_by(EarnedCommission.client_name.asc())
        
        result = await db.execute(query)
        all_commissions = result.scalars().all()
        
        commission_data = []
        for row in all_commissions:
            commission_data.append({
                "id": str(row.id),
                "client_name": row.client_name,
                "invoice_total": float(row.invoice_total or 0),
                "commission_earned": float(row.commission_earned or 0),
                "statement_count": row.statement_count,
                "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        return {
            "carrier_name": carrier_name,
            "commission_data": commission_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching carrier commission data: {str(e)}")

@router.get("/earned-commission/all-data")
async def get_all_commission_data(
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """Get all commission data across all carriers - user-specific for regular users, global for admins"""
    try:
        # Build query with proper user filtering using the new user_id field
        is_admin = current_user.role == 'admin'
        
        query = select(
            EarnedCommission, 
            Company.name.label('carrier_name')
        ).join(
            Company, EarnedCommission.carrier_id == Company.id
        )
        
        # Add user filter for non-admin users - now using the user_id field directly
        if not is_admin:
            query = query.where(EarnedCommission.user_id == current_user.id)
        
        query = query.order_by(Company.name.asc(), EarnedCommission.client_name.asc())
        
        result = await db.execute(query)
        all_results = result.all()
        
        commission_data = []
        for row in all_results:
            commission_data.append({
                "id": str(row.EarnedCommission.id),
                "carrier_name": row.carrier_name,
                "client_name": row.EarnedCommission.client_name,
                "invoice_total": float(row.EarnedCommission.invoice_total or 0),
                "commission_earned": float(row.EarnedCommission.commission_earned or 0),
                "statement_count": row.EarnedCommission.statement_count,
                "last_updated": row.EarnedCommission.last_updated.isoformat() if row.EarnedCommission.last_updated else None,
                "created_at": row.EarnedCommission.created_at.isoformat() if row.EarnedCommission.created_at else None
            })
        
        return commission_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching all commission data: {str(e)}")

@router.put("/earned-commission/{commission_id}")
async def update_commission_data(commission_id: UUID, update_data: dict, db: AsyncSession = Depends(get_db)):
    """Update commission data for a specific record"""
    try:
        # Get the commission record
        result = await db.execute(
            select(EarnedCommission).where(EarnedCommission.id == commission_id)
        )
        commission = result.scalar_one_or_none()
        
        if not commission:
            raise HTTPException(status_code=404, detail="Commission record not found")
        
        # Check for duplicate company name if client_name is being updated
        if 'client_name' in update_data and update_data['client_name'] != commission.client_name:
            new_client_name = update_data['client_name'].strip()
            
            # Check if another record exists with the same name for this carrier
            existing_result = await db.execute(
                select(EarnedCommission).where(
                    EarnedCommission.carrier_id == commission.carrier_id,
                    EarnedCommission.client_name == new_client_name,
                    EarnedCommission.id != commission_id
                )
            )
            existing_commission = existing_result.scalar_one_or_none()
            
            if existing_commission:
                # Return information about the existing record for merge confirmation
                return {
                    "requires_merge_confirmation": True,
                    "existing_record": {
                        "id": str(existing_commission.id),
                        "client_name": existing_commission.client_name,
                        "invoice_total": float(existing_commission.invoice_total) if existing_commission.invoice_total else 0,
                        "commission_earned": float(existing_commission.commission_earned) if existing_commission.commission_earned else 0,
                        "statement_count": existing_commission.statement_count or 0,
                        "last_updated": existing_commission.last_updated.isoformat() if existing_commission.last_updated else None
                    },
                    "new_data": {
                        "client_name": new_client_name,
                        "invoice_total": update_data.get('invoice_total', 0),
                        "commission_earned": update_data.get('commission_earned', 0)
                    }
                }
        
        # Update the fields
        if 'client_name' in update_data:
            commission.client_name = update_data['client_name']
        if 'invoice_total' in update_data:
            commission.invoice_total = Decimal(str(update_data['invoice_total']))
        if 'commission_earned' in update_data:
            commission.commission_earned = Decimal(str(update_data['commission_earned']))
        
        # Update the last_updated timestamp
        commission.last_updated = datetime.utcnow()
        
        await db.commit()
        await db.refresh(commission)
        
        return {
            "id": str(commission.id),
            "client_name": commission.client_name,
            "invoice_total": float(commission.invoice_total),
            "commission_earned": float(commission.commission_earned),
            "statement_count": commission.statement_count,
            "last_updated": commission.last_updated.isoformat() if commission.last_updated else None,
            "created_at": commission.created_at.isoformat() if commission.created_at else None
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating commission data: {str(e)}")

@router.post("/earned-commission/merge")
async def merge_commission_records(merge_data: dict, db: AsyncSession = Depends(get_db)):
    """Merge two commission records"""
    try:
        source_id = UUID(merge_data['source_id'])
        target_id = UUID(merge_data['target_id'])
        
        # Get both records
        source_result = await db.execute(select(EarnedCommission).where(EarnedCommission.id == source_id))
        source_commission = source_result.scalar_one_or_none()
        
        target_result = await db.execute(select(EarnedCommission).where(EarnedCommission.id == target_id))
        target_commission = target_result.scalar_one_or_none()
        
        if not source_commission or not target_commission:
            raise HTTPException(status_code=404, detail="One or both commission records not found")
        
        # Merge data into target record
        # Merge invoice totals
        if source_commission.invoice_total:
            target_invoice = float(target_commission.invoice_total) if target_commission.invoice_total else 0
            source_invoice = float(source_commission.invoice_total)
            target_commission.invoice_total = target_invoice + source_invoice
        
        # Merge commission earned
        if source_commission.commission_earned:
            target_commission_val = float(target_commission.commission_earned) if target_commission.commission_earned else 0
            source_commission_val = float(source_commission.commission_earned)
            target_commission.commission_earned = target_commission_val + source_commission_val
        
        # Merge statement count
        target_commission.statement_count = (target_commission.statement_count or 0) + (source_commission.statement_count or 0)
        
        # Merge upload_ids
        if source_commission.upload_ids:
            target_upload_ids = target_commission.upload_ids or []
            for upload_id in source_commission.upload_ids:
                if upload_id not in target_upload_ids:
                    target_upload_ids.append(upload_id)
            target_commission.upload_ids = target_upload_ids
        
        # Merge monthly commissions
        month_columns = [
            'jan_commission', 'feb_commission', 'mar_commission', 'apr_commission',
            'may_commission', 'jun_commission', 'jul_commission', 'aug_commission',
            'sep_commission', 'oct_commission', 'nov_commission', 'dec_commission'
        ]
        
        for month_col in month_columns:
            if hasattr(source_commission, month_col) and getattr(source_commission, month_col):
                target_value = float(getattr(target_commission, month_col) or 0)
                source_value = float(getattr(source_commission, month_col))
                setattr(target_commission, month_col, target_value + source_value)
        
        # Update target record timestamp
        target_commission.last_updated = datetime.utcnow()
        
        # Delete source record
        await db.delete(source_commission)
        
        await db.commit()
        await db.refresh(target_commission)
        
        return {
            "success": True,
            "message": f"Successfully merged records. Source record deleted, target record updated.",
            "merged_record": {
                "id": str(target_commission.id),
                "client_name": target_commission.client_name,
                "invoice_total": float(target_commission.invoice_total) if target_commission.invoice_total else 0,
                "commission_earned": float(target_commission.commission_earned) if target_commission.commission_earned else 0,
                "statement_count": target_commission.statement_count,
                "last_updated": target_commission.last_updated.isoformat() if target_commission.last_updated else None
            }
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error merging commission records: {str(e)}")

 