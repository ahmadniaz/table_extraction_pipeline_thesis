from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_, or_, case, String, delete, update, text
from app.db import crud, schemas
from app.config import get_db
from app.db.models import StatementUpload, Company, EarnedCommission, User, UserSession, AllowedDomain
from app.dependencies.auth_dependencies import get_admin_user, get_current_user
from app.db.schemas import DomainManagementRequest, AllowedDomainResponse
from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timedelta

router = APIRouter(prefix="/api")

async def delete_user_related_data(db: AsyncSession, user_id: UUID, operation_name: str = "Operation"):
    """Helper function to delete all user-related data in the correct order"""
    # Get all statement uploads for this user first
    uploads_result = await db.execute(
        select(StatementUpload).where(StatementUpload.user_id == user_id)
    )
    user_uploads = uploads_result.scalars().all()
    upload_ids = [str(upload.id) for upload in user_uploads]

    print(f"🎯 {operation_name}: Found {len(upload_ids)} uploads to delete for user {user_id}")

    # Delete all user-related data in the correct order to maintain referential integrity
    
    # 1. Delete edited tables (references statement_uploads)
    if upload_ids:
        await db.execute(
            text("DELETE FROM edited_tables WHERE upload_id = ANY(:upload_ids)"),
            {"upload_ids": upload_ids}
        )
        print(f"🎯 {operation_name}: Deleted edited_tables for {len(upload_ids)} uploads")

    # 2. Remove uploads from earned commission records and recalculate totals
    if upload_ids:
        from app.db.crud.earned_commission import remove_upload_from_earned_commissions
        for upload_id in upload_ids:
            await remove_upload_from_earned_commissions(db, upload_id)
        print(f"🎯 {operation_name}: Removed uploads from earned commission records")

    # 3. Delete user data contributions (references statement_uploads)
    if upload_ids:
        await db.execute(
            text("DELETE FROM user_data_contributions WHERE upload_id = ANY(:upload_ids)"),
            {"upload_ids": upload_ids}
        )
        print(f"🎯 {operation_name}: Deleted user_data_contributions for {len(upload_ids)} uploads")

    # 4. Delete file duplicate records (references statement_uploads)
    if upload_ids:
        await db.execute(
            text("DELETE FROM file_duplicates WHERE original_upload_id = ANY(:upload_ids) OR duplicate_upload_id = ANY(:upload_ids)"),
            {"upload_ids": upload_ids}
        )
        print(f"🎯 {operation_name}: Deleted file_duplicates for {len(upload_ids)} uploads")

    # 5. Delete extractions (references users, not uploads)
    await db.execute(
        text("DELETE FROM extractions WHERE user_id = :user_id"),
        {"user_id": str(user_id)}
    )
    print(f"🎯 {operation_name}: Deleted extractions for user {user_id}")

    # 6. Delete statement uploads
    await db.execute(
        delete(StatementUpload).where(StatementUpload.user_id == user_id)
    )
    print(f"🎯 {operation_name}: Deleted {len(upload_ids)} statement uploads")
    
    return len(upload_ids)

@router.get("/admin/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard data with company overview and user statistics"""
    try:
        # Get company statistics
        # Total statements
        total_statements_result = await db.execute(
            select(func.count(StatementUpload.id))
        )
        total_statements = total_statements_result.scalar() or 0

        # Total carriers (only count companies that have statements)
        total_carriers_result = await db.execute(
            select(func.count(func.distinct(StatementUpload.company_id)))
        )
        total_carriers = total_carriers_result.scalar() or 0

        # Total commission earned
        total_commission_result = await db.execute(
            select(func.sum(EarnedCommission.commission_earned))
        )
        total_commission = float(total_commission_result.scalar() or 0)

        # Pending reviews
        pending_reviews_result = await db.execute(
            select(func.count(StatementUpload.id))
            .where(StatementUpload.status.in_(['extracted', 'success']))
        )
        pending_reviews = pending_reviews_result.scalar() or 0

        # Approved statements
        approved_statements_result = await db.execute(
            select(func.count(StatementUpload.id))
            .where(StatementUpload.status.in_(['completed', 'Approved']))
        )
        approved_statements = approved_statements_result.scalar() or 0

        # Rejected statements
        rejected_statements_result = await db.execute(
            select(func.count(StatementUpload.id))
            .where(StatementUpload.status == 'rejected')
        )
        rejected_statements = rejected_statements_result.scalar() or 0

        # User statistics
        # Total users
        total_users_result = await db.execute(
            select(func.count(User.id))
        )
        total_users = total_users_result.scalar() or 0

        # Active users (logged in within last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users_result = await db.execute(
            select(func.count(User.id))
            .where(
                and_(
                    User.last_login.isnot(None),
                    User.last_login >= thirty_days_ago
                )
            )
        )
        active_users = active_users_result.scalar() or 0

        # Get detailed user statistics
        users_query = select(
            User.id,
            User.email,
            User.first_name,
            User.last_name,
            User.role,
            User.is_active,
            User.last_login,
            User.created_at,
            func.count(StatementUpload.id).label('total_uploads'),
            func.count(func.distinct(StatementUpload.company_id)).label('carriers_worked_with'),
            func.sum(
                case(
                    (StatementUpload.status.in_(['completed', 'Approved']), 1),
                    else_=0
                )
            ).label('total_approved'),
            func.sum(
                case(
                    (StatementUpload.status == 'rejected', 1),
                    else_=0
                )
            ).label('total_rejected'),
            func.sum(
                case(
                    (StatementUpload.status.in_(['extracted', 'success']), 1),
                    else_=0
                )
            ).label('total_pending')
        ).outerjoin(StatementUpload, User.id == StatementUpload.user_id).group_by(
            User.id,
            User.email,
            User.first_name,
            User.last_name,
            User.role,
            User.is_active,
            User.last_login,
            User.created_at
        ).order_by(User.created_at.desc())

        users_result = await db.execute(users_query)
        users_data = users_result.all()

        # Get commission contribution for each user
        users_with_commission = []
        for user_data in users_data:
            # Get commission contributed by this user
            # For now, we'll set commission to 0 since the JSON query is complex
            # This can be optimized later with proper JSONB migration or different approach
            user_commission = 0.0

            users_with_commission.append({
                "id": str(user_data.id),
                "email": user_data.email,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "role": user_data.role,
                "is_active": bool(user_data.is_active),
                "last_login": user_data.last_login.isoformat() if user_data.last_login else None,
                "created_at": user_data.created_at.isoformat(),
                "total_uploads": user_data.total_uploads or 0,
                "total_approved": user_data.total_approved or 0,
                "total_rejected": user_data.total_rejected or 0,
                "total_pending": user_data.total_pending or 0,
                "carriers_worked_with": user_data.carriers_worked_with or 0,
                "total_commission_contributed": user_commission
            })

        return {
            "company_stats": {
                "total_statements": total_statements,
                "total_carriers": total_carriers,
                "total_commission": total_commission,
                "pending_reviews": pending_reviews,
                "approved_statements": approved_statements,
                "rejected_statements": rejected_statements
            },
            "users": users_with_commission,
            "total_users": total_users,
            "active_users": active_users
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching admin dashboard data: {str(e)}")

@router.get("/admin/users")
async def get_all_users(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all users with detailed statistics"""
    try:
        users_query = select(
            User.id,
            User.email,
            User.first_name,
            User.last_name,
            User.role,
            User.is_active,
            User.is_verified,
            User.last_login,
            User.created_at,
            User.updated_at,
            func.count(StatementUpload.id).label('total_uploads'),
            func.count(func.distinct(StatementUpload.company_id)).label('carriers_worked_with')
        ).outerjoin(StatementUpload, User.id == StatementUpload.user_id).group_by(
            User.id,
            User.email,
            User.first_name,
            User.last_name,
            User.role,
            User.is_active,
            User.is_verified,
            User.last_login,
            User.created_at,
            User.updated_at
        ).order_by(User.created_at.desc())

        result = await db.execute(users_query)
        users = result.all()

        formatted_users = []
        for user_data in users:
            formatted_users.append({
                "id": str(user_data.id),
                "email": user_data.email,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "role": user_data.role,
                "is_active": bool(user_data.is_active),
                "is_verified": bool(user_data.is_verified),
                "last_login": user_data.last_login.isoformat() if user_data.last_login else None,
                "created_at": user_data.created_at.isoformat(),
                "updated_at": user_data.updated_at.isoformat(),
                "total_uploads": user_data.total_uploads or 0,
                "carriers_worked_with": user_data.carriers_worked_with or 0
            })

        return formatted_users

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@router.get("/admin/users/{user_id}")
async def get_user_details(
    user_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific user"""
    try:
        # Get user basic info
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's statements
        statements_result = await db.execute(
            select(StatementUpload, Company.name.label('company_name'))
            .join(Company, StatementUpload.company_id == Company.id)
            .where(StatementUpload.user_id == user_id)
            .order_by(StatementUpload.uploaded_at.desc())
        )
        statements = statements_result.all()

        formatted_statements = []
        for statement, company_name in statements:
            formatted_statements.append({
                "id": str(statement.id),
                "file_name": statement.file_name,
                "company_name": company_name,
                "status": statement.status,
                "uploaded_at": statement.uploaded_at.isoformat() if statement.uploaded_at else None,
                "last_updated": statement.last_updated.isoformat() if statement.last_updated else None,
                "completed_at": statement.completed_at.isoformat() if statement.completed_at else None,
                "rejection_reason": statement.rejection_reason,
                "plan_types": statement.plan_types
            })

        # Get user statistics
        stats_result = await db.execute(
            select(
                func.count(StatementUpload.id).label('total_uploads'),
                func.sum(
                    func.case(
                        (StatementUpload.status.in_(['completed', 'Approved']), 1),
                        else_=0
                    )
                ).label('total_approved'),
                func.sum(
                    func.case(
                        (StatementUpload.status == 'rejected', 1),
                        else_=0
                    )
                ).label('total_rejected'),
                func.sum(
                    func.case(
                        (StatementUpload.status.in_(['extracted', 'success']), 1),
                        else_=0
                    )
                ).label('total_pending'),
                func.count(func.distinct(StatementUpload.company_id)).label('carriers_worked_with')
            ).where(StatementUpload.user_id == user_id)
        )
        stats = stats_result.first()

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "is_active": bool(user.is_active),
                "is_verified": bool(user.is_verified),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat()
            },
            "statistics": {
                "total_uploads": stats.total_uploads or 0,
                "total_approved": stats.total_approved or 0,
                "total_rejected": stats.total_rejected or 0,
                "total_pending": stats.total_pending or 0,
                "carriers_worked_with": stats.carriers_worked_with or 0
            },
            "statements": formatted_statements
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user details: {str(e)}")

@router.put("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    status_data: dict,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user status (active/inactive)"""
    try:
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent admin from deactivating themselves
        if user_id == current_user.id and not status_data.get('is_active', True):
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

        # Update user status
        user.is_active = 1 if status_data.get('is_active', True) else 0
        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        return {
            "id": str(user.id),
            "email": user.email,
            "is_active": bool(user.is_active),
            "updated_at": user.updated_at.isoformat()
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user status: {str(e)}")

@router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    role_data: dict,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user role"""
    try:
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent admin from changing their own role
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot change your own role")

        new_role = role_data.get('role')
        if new_role not in ['admin', 'user', 'read_only']:
            raise HTTPException(status_code=400, detail="Invalid role. Must be admin, user, or read_only")

        user.role = new_role
        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "updated_at": user.updated_at.isoformat()
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user role: {str(e)}")

@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user and all their data"""
    try:
        # Prevent admin from deleting themselves
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        # Get user to delete
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Delete all user-related data using helper function
        upload_count = await delete_user_related_data(db, user_id, "Delete User")
        
        # 7. Delete user sessions
        await db.execute(
            delete(UserSession).where(UserSession.user_id == user_id)
        )
        print(f"🎯 Delete User: Deleted user sessions for user {user_id}")
        
        # 8. Finally, delete user
        await db.execute(
            delete(User).where(User.id == user_id)
        )
        print(f"🎯 Delete User: Deleted user {user_id}")

        await db.commit()
        print(f"🎯 Delete User: Successfully deleted user {user_id} and all related data")

        return {"message": "User deleted successfully"}

    except Exception as e:
        await db.rollback()
        print(f"❌ Delete User: Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")

@router.post("/admin/users/{user_id}/reset-data")
async def reset_user_data(
    user_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset user data (keep user but clear all uploaded data)"""
    try:
        # Get user
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Delete all user-related data using helper function
        upload_count = await delete_user_related_data(db, user_id, "Reset User Data")

        await db.commit()
        print(f"🎯 Reset User Data: Successfully reset all data for user {user_id}")

        return {"message": "User data reset successfully"}

    except Exception as e:
        await db.rollback()
        print(f"❌ Reset User Data: Error resetting user data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resetting user data: {str(e)}")

@router.post("/admin/domains", response_model=AllowedDomainResponse)
async def add_allowed_domain(
    domain_data: DomainManagementRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a new allowed domain."""
    # Check if domain already exists
    stmt = select(AllowedDomain).filter(
        AllowedDomain.domain == domain_data.domain.lower()
    )
    result = await db.execute(stmt)
    existing_domain = result.scalar_one_or_none()
    
    if existing_domain:
        raise HTTPException(
            status_code=400,
            detail="Domain already exists"
        )
    
    # Create new domain
    new_domain = AllowedDomain(
        domain=domain_data.domain.lower(),
        company_id=domain_data.company_id,
        is_active=1 if domain_data.is_active else 0,
        created_by=current_user.id
    )
    
    db.add(new_domain)
    await db.commit()
    await db.refresh(new_domain)
    
    return AllowedDomainResponse.model_validate(new_domain)

@router.get("/admin/domains", response_model=list[AllowedDomainResponse])
async def get_allowed_domains(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all allowed domains."""
    stmt = select(AllowedDomain)
    result = await db.execute(stmt)
    domains = result.scalars().all()
    return [AllowedDomainResponse.model_validate(domain) for domain in domains]

@router.put("/admin/domains/{domain_id}")
async def update_domain(
    domain_id: str,
    domain_data: DomainManagementRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update domain status."""
    stmt = select(AllowedDomain).filter(AllowedDomain.id == domain_id)
    result = await db.execute(stmt)
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=404,
            detail="Domain not found"
        )
    
    update_stmt = update(AllowedDomain).filter(
        AllowedDomain.id == domain_id
    ).values(
        is_active=1 if domain_data.is_active else 0,
        company_id=domain_data.company_id if domain_data.company_id else domain.company_id
    )
    await db.execute(update_stmt)
    await db.commit()
    return {"message": "Domain updated successfully"}

@router.delete("/admin/domains/{domain_id}")
async def delete_domain(
    domain_id: str,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a domain."""
    stmt = select(AllowedDomain).filter(AllowedDomain.id == domain_id)
    result = await db.execute(stmt)
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=404,
            detail="Domain not found"
        )
    
    delete_stmt = delete(AllowedDomain).filter(AllowedDomain.id == domain_id)
    await db.execute(delete_stmt)
    await db.commit()
    return {"message": "Domain deleted successfully"}
