"""
User Profile and Statistics Service

This service handles user profile management, data contribution tracking,
and user statistics for the multi-user system.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.db.models import User, StatementUpload, UserDataContribution, EarnedCommission
from app.db.schemas import UserProfile, UserStats, UserDataContributionCreate

logger = logging.getLogger(__name__)

class UserProfileService:
    """Service for managing user profiles and statistics."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Get user profile information."""
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            return UserProfile.model_validate(user)
            
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            raise
    
    async def get_user_statistics(self, user_id: UUID) -> Optional[UserStats]:
        """Get comprehensive user statistics."""
        try:
            # Get basic upload statistics
            upload_stats = await self._get_upload_statistics(user_id)
            
            # Get commission contribution
            commission_contribution = await self._get_commission_contribution(user_id)
            
            # Get data contribution percentage
            contribution_percentage = await self._get_data_contribution_percentage(user_id)
            
            # Get last upload date
            last_upload = await self._get_last_upload_date(user_id)
            
            return UserStats(
                user_id=user_id,
                total_uploads=upload_stats['total'],
                total_approved=upload_stats['approved'],
                total_rejected=upload_stats['rejected'],
                total_pending=upload_stats['pending'],
                total_commission_contributed=commission_contribution,
                last_upload_date=last_upload,
                data_contribution_percentage=contribution_percentage
            )
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {str(e)}")
            raise
    
    async def _get_upload_statistics(self, user_id: UUID) -> Dict[str, int]:
        """Get upload statistics for a user."""
        result = await self.db.execute(
            select(
                func.count(StatementUpload.id).label('total'),
                func.count(StatementUpload.id).filter(StatementUpload.status == 'approved').label('approved'),
                func.count(StatementUpload.id).filter(StatementUpload.status == 'rejected').label('rejected'),
                func.count(StatementUpload.id).filter(StatementUpload.status == 'pending').label('pending')
            )
            .where(StatementUpload.user_id == user_id)
        )
        
        stats = result.first()
        return {
            'total': stats.total or 0,
            'approved': stats.approved or 0,
            'rejected': stats.rejected or 0,
            'pending': stats.pending or 0
        }
    
    async def _get_commission_contribution(self, user_id: UUID) -> float:
        """Calculate total commission contributed by user's uploads."""
        # Get all approved uploads by user
        result = await self.db.execute(
            select(StatementUpload.id)
            .where(
                and_(
                    StatementUpload.user_id == user_id,
                    StatementUpload.status == 'approved'
                )
            )
        )
        user_upload_ids = [str(row[0]) for row in result.all()]
        
        if not user_upload_ids:
            return 0.0
        
        # Calculate commission from earned commission records
        total_commission = 0.0
        for upload_id in user_upload_ids:
            result = await self.db.execute(
                select(EarnedCommission.commission_earned)
                .where(
                    func.json_contains(EarnedCommission.upload_ids, f'"{upload_id}"')
                )
            )
            commissions = result.scalars().all()
            total_commission += sum(commissions)
        
        return total_commission
    
    async def _get_data_contribution_percentage(self, user_id: UUID) -> float:
        """Calculate user's data contribution percentage."""
        # Get total uploads by user
        user_uploads_result = await self.db.execute(
            select(func.count(StatementUpload.id))
            .where(StatementUpload.user_id == user_id)
        )
        user_uploads = user_uploads_result.scalar() or 0
        
        # Get total uploads in system
        total_uploads_result = await self.db.execute(
            select(func.count(StatementUpload.id))
        )
        total_uploads = total_uploads_result.scalar() or 0
        
        if total_uploads == 0:
            return 0.0
        
        return (user_uploads / total_uploads) * 100
    
    async def _get_last_upload_date(self, user_id: UUID) -> Optional[datetime]:
        """Get the last upload date for a user."""
        result = await self.db.execute(
            select(StatementUpload.uploaded_at)
            .where(StatementUpload.user_id == user_id)
            .order_by(StatementUpload.uploaded_at.desc())
            .limit(1)
        )
        
        last_upload = result.scalar_one_or_none()
        return last_upload
    
    async def record_user_contribution(
        self, 
        user_id: UUID, 
        upload_id: UUID, 
        contribution_type: str,
        contribution_data: Optional[Dict[str, Any]] = None
    ) -> UserDataContribution:
        """Record a user data contribution."""
        try:
            contribution = UserDataContribution(
                user_id=user_id,
                upload_id=upload_id,
                contribution_type=contribution_type,
                contribution_data=contribution_data or {},
                created_at=datetime.utcnow()
            )
            
            self.db.add(contribution)
            await self.db.flush()
            
            logger.info(f"Recorded contribution: {contribution_type} for user {user_id}")
            
            return contribution
            
        except Exception as e:
            logger.error(f"Error recording user contribution: {str(e)}")
            raise
    
    async def get_user_contribution_history(
        self, 
        user_id: UUID, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's contribution history."""
        try:
            result = await self.db.execute(
                select(UserDataContribution, StatementUpload)
                .join(StatementUpload, UserDataContribution.upload_id == StatementUpload.id)
                .where(UserDataContribution.user_id == user_id)
                .order_by(UserDataContribution.created_at.desc())
                .limit(limit)
            )
            
            contributions = []
            for contribution, upload in result.all():
                contributions.append({
                    'id': str(contribution.id),
                    'contribution_type': contribution.contribution_type,
                    'upload_id': str(contribution.upload_id),
                    'file_name': upload.file_name,
                    'upload_status': upload.status,
                    'contribution_data': contribution.contribution_data,
                    'created_at': contribution.created_at.isoformat()
                })
            
            return contributions
            
        except Exception as e:
            logger.error(f"Error getting contribution history: {str(e)}")
            raise
    
    async def get_user_activity_summary(self, user_id: UUID) -> Dict[str, Any]:
        """Get user activity summary for the last 30 days."""
        try:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            # Recent uploads
            recent_uploads_result = await self.db.execute(
                select(func.count(StatementUpload.id))
                .where(
                    and_(
                        StatementUpload.user_id == user_id,
                        StatementUpload.uploaded_at >= thirty_days_ago
                    )
                )
            )
            recent_uploads = recent_uploads_result.scalar() or 0
            
            # Recent contributions
            recent_contributions_result = await self.db.execute(
                select(func.count(UserDataContribution.id))
                .where(
                    and_(
                        UserDataContribution.user_id == user_id,
                        UserDataContribution.created_at >= thirty_days_ago
                    )
                )
            )
            recent_contributions = recent_contributions_result.scalar() or 0
            
            # Activity by day (last 7 days)
            activity_by_day = await self._get_activity_by_day(user_id, days=7)
            
            return {
                'recent_uploads': recent_uploads,
                'recent_contributions': recent_contributions,
                'activity_by_day': activity_by_day,
                'period_days': 30
            }
            
        except Exception as e:
            logger.error(f"Error getting activity summary: {str(e)}")
            raise
    
    async def _get_activity_by_day(self, user_id: UUID, days: int = 7) -> List[Dict[str, Any]]:
        """Get user activity by day for the specified number of days."""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days-1)
            
            # Get uploads by day
            result = await self.db.execute(
                select(
                    func.date(StatementUpload.uploaded_at).label('date'),
                    func.count(StatementUpload.id).label('uploads')
                )
                .where(
                    and_(
                        StatementUpload.user_id == user_id,
                        func.date(StatementUpload.uploaded_at) >= start_date,
                        func.date(StatementUpload.uploaded_at) <= end_date
                    )
                )
                .group_by(func.date(StatementUpload.uploaded_at))
                .order_by(func.date(StatementUpload.uploaded_at))
            )
            
            activity_data = {}
            for row in result.all():
                activity_data[row.date] = row.uploads
            
            # Fill in missing days with 0
            activity_by_day = []
            current_date = start_date
            while current_date <= end_date:
                activity_by_day.append({
                    'date': current_date.isoformat(),
                    'uploads': activity_data.get(current_date, 0)
                })
                current_date += timedelta(days=1)
            
            return activity_by_day
            
        except Exception as e:
            logger.error(f"Error getting activity by day: {str(e)}")
            raise
    
    async def get_system_user_statistics(self) -> Dict[str, Any]:
        """Get system-wide user statistics."""
        try:
            # Total users
            total_users_result = await self.db.execute(
                select(func.count(User.id))
            )
            total_users = total_users_result.scalar() or 0
            
            # Active users (uploaded in last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            active_users_result = await self.db.execute(
                select(func.count(func.distinct(StatementUpload.user_id)))
                .where(StatementUpload.uploaded_at >= thirty_days_ago)
            )
            active_users = active_users_result.scalar() or 0
            
            # Top contributors
            top_contributors = await self._get_top_contributors(limit=10)
            
            # User role distribution
            role_distribution = await self._get_role_distribution()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'top_contributors': top_contributors,
                'role_distribution': role_distribution,
                'activity_period_days': 30
            }
            
        except Exception as e:
            logger.error(f"Error getting system user statistics: {str(e)}")
            raise
    
    async def _get_top_contributors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top contributors by upload count."""
        try:
            result = await self.db.execute(
                select(
                    User.id,
                    User.email,
                    User.first_name,
                    User.last_name,
                    func.count(StatementUpload.id).label('upload_count')
                )
                .join(StatementUpload, User.id == StatementUpload.user_id)
                .group_by(User.id, User.email, User.first_name, User.last_name)
                .order_by(func.count(StatementUpload.id).desc())
                .limit(limit)
            )
            
            contributors = []
            for row in result.all():
                contributors.append({
                    'user_id': str(row.id),
                    'email': row.email,
                    'name': f"{row.first_name or ''} {row.last_name or ''}".strip() or row.email,
                    'upload_count': row.upload_count
                })
            
            return contributors
            
        except Exception as e:
            logger.error(f"Error getting top contributors: {str(e)}")
            raise
    
    async def _get_role_distribution(self) -> Dict[str, int]:
        """Get user role distribution."""
        try:
            result = await self.db.execute(
                select(User.role, func.count(User.id))
                .group_by(User.role)
            )
            
            return {row[0]: row[1] for row in result.all()}
            
        except Exception as e:
            logger.error(f"Error getting role distribution: {str(e)}")
            raise
