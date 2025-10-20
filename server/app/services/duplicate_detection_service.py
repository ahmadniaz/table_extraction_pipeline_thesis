"""
Duplicate Detection Service

This service handles file duplicate detection using SHA-256 hashing
and provides functionality to check for duplicates across user uploads
and global system uploads.
"""

import hashlib
import logging
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.db.models import StatementUpload, FileDuplicate, User
from app.db.schemas import FileDuplicateCreate, FileDuplicate as FileDuplicateSchema

logger = logging.getLogger(__name__)

class DuplicateDetectionService:
    """Service for detecting and managing file duplicates."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()
    
    async def check_duplicate(
        self, 
        file_hash: str, 
        user_id: UUID, 
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check for file duplicates.
        
        Args:
            file_hash: SHA-256 hash of the file
            user_id: ID of the user uploading the file
            file_name: Optional file name for additional checking
            
        Returns:
            Dict containing duplicate information:
            {
                'is_duplicate': bool,
                'duplicate_type': 'user' | 'global' | None,
                'existing_upload': StatementUpload | None,
                'message': str
            }
        """
        try:
            # Check for duplicates in user's own uploads
            user_duplicate = await self._check_user_duplicate(file_hash, user_id)
            if user_duplicate:
                return {
                    'is_duplicate': True,
                    'duplicate_type': 'user',
                    'existing_upload': user_duplicate,
                    'message': "This file has already been uploaded"
                }
            
            # Check for global duplicates
            global_duplicate = await self._check_global_duplicate(file_hash, user_id)
            if global_duplicate:
                return {
                    'is_duplicate': True,
                    'duplicate_type': 'global',
                    'existing_upload': global_duplicate,
                    'message': "This file already exists in the database"
                }
            
            return {
                'is_duplicate': False,
                'duplicate_type': None,
                'existing_upload': None,
                'message': 'No duplicates found'
            }
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
            raise
    
    async def _check_user_duplicate(self, file_hash: str, user_id: UUID) -> Optional[StatementUpload]:
        """Check for duplicates in user's own uploads."""
        result = await self.db.execute(
            select(StatementUpload)
            .where(
                and_(
                    StatementUpload.file_hash == file_hash,
                    StatementUpload.user_id == user_id
                )
            )
            .order_by(StatementUpload.uploaded_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def _check_global_duplicate(self, file_hash: str, user_id: UUID) -> Optional[StatementUpload]:
        """Check for duplicates across all users (excluding current user)."""
        result = await self.db.execute(
            select(StatementUpload)
            .where(
                and_(
                    StatementUpload.file_hash == file_hash,
                    StatementUpload.user_id != user_id
                )
            )
            .order_by(StatementUpload.uploaded_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def record_duplicate(
        self, 
        file_hash: str, 
        original_upload_id: UUID, 
        duplicate_upload_id: UUID,
        action_taken: str = "detected"
    ) -> FileDuplicateSchema:
        """
        Record a duplicate detection in the database.
        
        Args:
            file_hash: SHA-256 hash of the duplicate file
            original_upload_id: ID of the original upload
            duplicate_upload_id: ID of the duplicate upload
            action_taken: Action taken ('detected', 'replaced', 'ignored')
            
        Returns:
            FileDuplicateSchema: The created duplicate record
        """
        try:
            duplicate_record = FileDuplicate(
                file_hash=file_hash,
                original_upload_id=original_upload_id,
                duplicate_upload_id=duplicate_upload_id,
                action_taken=action_taken,
                detected_at=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            
            self.db.add(duplicate_record)
            await self.db.flush()
            
            logger.info(f"Recorded duplicate: {duplicate_upload_id} is duplicate of {original_upload_id}")
            
            return FileDuplicateSchema.model_validate(duplicate_record)
            
        except Exception as e:
            logger.error(f"Error recording duplicate: {str(e)}")
            raise
    
    async def get_duplicate_history(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get duplicate detection history for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of duplicate records with upload details
        """
        try:
            # Get duplicates where user was involved (either as original or duplicate uploader)
            result = await self.db.execute(
                select(FileDuplicate, StatementUpload, User)
                .join(StatementUpload, FileDuplicate.original_upload_id == StatementUpload.id)
                .join(User, StatementUpload.user_id == User.id)
                .where(
                    or_(
                        StatementUpload.user_id == user_id,
                        FileDuplicate.duplicate_upload_id.in_(
                            select(StatementUpload.id).where(StatementUpload.user_id == user_id)
                        )
                    )
                )
                .order_by(FileDuplicate.detected_at.desc())
            )
            
            duplicates = []
            for duplicate, upload, user in result.all():
                duplicates.append({
                    'duplicate_id': str(duplicate.id),
                    'file_hash': duplicate.file_hash,
                    'original_upload_id': str(duplicate.original_upload_id),
                    'duplicate_upload_id': str(duplicate.duplicate_upload_id),
                    'action_taken': duplicate.action_taken,
                    'detected_at': duplicate.detected_at.isoformat(),
                    'original_uploader': {
                        'id': str(user.id),
                        'email': user.email,
                        'name': f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
                    },
                    'file_name': upload.file_name
                })
            
            return duplicates
            
        except Exception as e:
            logger.error(f"Error getting duplicate history: {str(e)}")
            raise
    
    async def get_duplicate_statistics(self) -> Dict[str, Any]:
        """
        Get system-wide duplicate detection statistics.
        
        Returns:
            Dict containing duplicate statistics
        """
        try:
            # Total duplicates detected
            total_duplicates_result = await self.db.execute(
                select(FileDuplicate).count()
            )
            total_duplicates = total_duplicates_result.scalar()
            
            # Duplicates by action
            action_stats_result = await self.db.execute(
                select(FileDuplicate.action_taken, FileDuplicate.id.count())
                .group_by(FileDuplicate.action_taken)
            )
            action_stats = {row[0]: row[1] for row in action_stats_result.all()}
            
            # Recent duplicates (last 30 days)
            thirty_days_ago = datetime.utcnow().replace(day=datetime.utcnow().day - 30)
            recent_duplicates_result = await self.db.execute(
                select(FileDuplicate)
                .where(FileDuplicate.detected_at >= thirty_days_ago)
                .count()
            )
            recent_duplicates = recent_duplicates_result.scalar()
            
            return {
                'total_duplicates': total_duplicates,
                'action_statistics': action_stats,
                'recent_duplicates': recent_duplicates,
                'duplicate_rate': (total_duplicates / max(1, await self._get_total_uploads())) * 100
            }
            
        except Exception as e:
            logger.error(f"Error getting duplicate statistics: {str(e)}")
            raise
    
    async def _get_total_uploads(self) -> int:
        """Get total number of uploads in the system."""
        result = await self.db.execute(select(StatementUpload).count())
        return result.scalar()
    
    async def handle_duplicate_upload(
        self, 
        file_hash: str, 
        user_id: UUID, 
        file_name: str,
        replace_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Handle a duplicate upload with user choice.
        
        Args:
            file_hash: SHA-256 hash of the file
            user_id: ID of the user uploading
            file_name: Name of the file
            replace_existing: Whether to replace existing file
            
        Returns:
            Dict containing handling result
        """
        try:
            duplicate_check = await self.check_duplicate(file_hash, user_id, file_name)
            
            if not duplicate_check['is_duplicate']:
                return {
                    'success': True,
                    'action': 'upload',
                    'message': 'No duplicates found, proceeding with upload'
                }
            
            if duplicate_check['duplicate_type'] == 'user' and replace_existing:
                # Replace user's existing file
                existing_upload = duplicate_check['existing_upload']
                existing_upload.file_name = file_name
                existing_upload.uploaded_at = datetime.utcnow()
                existing_upload.status = 'pending'
                
                await self.record_duplicate(
                    file_hash=file_hash,
                    original_upload_id=existing_upload.id,
                    duplicate_upload_id=existing_upload.id,  # Same file, updated
                    action_taken="replaced"
                )
                
                return {
                    'success': True,
                    'action': 'replaced',
                    'message': f'Replaced existing file: {existing_upload.file_name}',
                    'upload_id': str(existing_upload.id)
                }
            
            # Duplicate found, return information for user decision
            return {
                'success': False,
                'action': 'duplicate_detected',
                'message': duplicate_check['message'],
                'duplicate_info': {
                    'type': duplicate_check['duplicate_type'],
                    'existing_upload_id': str(duplicate_check['existing_upload'].id),
                    'existing_file_name': duplicate_check['existing_upload'].file_name,
                    'existing_upload_date': duplicate_check['existing_upload'].uploaded_at.isoformat() if duplicate_check['existing_upload'].uploaded_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling duplicate upload: {str(e)}")
            raise
