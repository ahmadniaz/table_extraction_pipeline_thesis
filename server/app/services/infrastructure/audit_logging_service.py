"""
Audit Logging Service

This service handles audit logging for all user actions and data operations
to ensure security and compliance in the multi-user system.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from enum import Enum

from app.db.models import User, UserSession

logger = logging.getLogger(__name__)

class AuditActionType(Enum):
    """Types of audit actions."""
    LOGIN = "login"
    LOGOUT = "logout"
    FILE_UPLOAD = "file_upload"
    FILE_DELETE = "file_delete"
    FILE_REPLACE = "file_replace"
    DATA_VIEW = "data_view"
    DATA_EDIT = "data_edit"
    DATA_APPROVE = "data_approve"
    DATA_REJECT = "data_reject"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    PERMISSION_CHANGE = "permission_change"
    SYSTEM_ACCESS = "system_access"
    DUPLICATE_DETECTED = "duplicate_detected"
    SECURITY_VIOLATION = "security_violation"

class AuditLogLevel(Enum):
    """Audit log levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AuditLoggingService:
    """Service for audit logging and security monitoring."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_action(
        self,
        user_id: UUID,
        action_type: AuditActionType,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        level: AuditLogLevel = AuditLogLevel.INFO,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """
        Log an audit action.
        
        Args:
            user_id: ID of the user performing the action
            action_type: Type of action being performed
            resource_type: Type of resource being accessed/modified
            resource_id: ID of the specific resource
            details: Additional details about the action
            level: Log level for the action
            ip_address: IP address of the user
            user_agent: User agent string
            session_id: Session ID for the action
        """
        try:
            # Create audit log entry
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": str(user_id),
                "action_type": action_type.value,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "level": level.value,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_id": session_id
            }
            
            # Log to application logger
            log_message = f"Audit: {action_type.value} by user {user_id} on {resource_type}"
            if resource_id:
                log_message += f" (ID: {resource_id})"
            
            if level == AuditLogLevel.ERROR or level == AuditLogLevel.CRITICAL:
                logger.error(log_message, extra=audit_entry)
            elif level == AuditLogLevel.WARNING:
                logger.warning(log_message, extra=audit_entry)
            else:
                logger.info(log_message, extra=audit_entry)
            
            # In a production system, you would also store this in a dedicated audit table
            # For now, we'll rely on the application logger
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {str(e)}")
    
    async def log_file_upload(
        self,
        user_id: UUID,
        file_name: str,
        file_size: int,
        file_hash: str,
        company_id: UUID,
        upload_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log file upload action."""
        await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.FILE_UPLOAD,
            resource_type="statement_upload",
            resource_id=str(upload_id),
            details={
                "file_name": file_name,
                "file_size": file_size,
                "file_hash": file_hash,
                "company_id": str(company_id)
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
    
    async def log_extraction_start(
        self,
        user_id: UUID,
        company_id: str,
        file_name: str,
        extraction_method: str,
        upload_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log extraction start action."""
        await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.DATA_VIEW,  # Using DATA_VIEW as closest match
            resource_type="extraction_process",
            resource_id=str(upload_id),
            details={
                "file_name": file_name,
                "extraction_method": extraction_method,
                "company_id": company_id,
                "upload_id": str(upload_id)
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
    
    async def log_duplicate_detection(
        self,
        user_id: UUID,
        file_hash: str,
        duplicate_type: str,
        original_upload_id: UUID,
        duplicate_upload_id: UUID,
        action_taken: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log duplicate detection action."""
        await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.DUPLICATE_DETECTED,
            resource_type="file_duplicate",
            resource_id=str(duplicate_upload_id),
            details={
                "file_hash": file_hash,
                "duplicate_type": duplicate_type,
                "original_upload_id": str(original_upload_id),
                "duplicate_upload_id": str(duplicate_upload_id),
                "action_taken": action_taken
            },
            level=AuditLogLevel.WARNING,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
    
    async def log_data_access(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: str,
        access_type: str = "view",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log data access action."""
        action_type = AuditActionType.DATA_VIEW if access_type == "view" else AuditActionType.DATA_EDIT
        
        await self.log_action(
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details={"access_type": access_type},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
    
    async def log_security_violation(
        self,
        user_id: Optional[UUID],
        violation_type: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log security violation."""
        await self.log_action(
            user_id=user_id or UUID('00000000-0000-0000-0000-000000000000'),
            action_type=AuditActionType.SECURITY_VIOLATION,
            resource_type="security",
            details={
                "violation_type": violation_type,
                **details
            },
            level=AuditLogLevel.CRITICAL,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
    
    async def log_user_authentication(
        self,
        user_id: UUID,
        action: str,  # "login" or "logout"
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> None:
        """Log user authentication action."""
        action_type = AuditActionType.LOGIN if action == "login" else AuditActionType.LOGOUT
        level = AuditLogLevel.INFO if success else AuditLogLevel.WARNING
        
        details = {"success": success}
        if not success and failure_reason:
            details["failure_reason"] = failure_reason
        
        await self.log_action(
            user_id=user_id,
            action_type=action_type,
            resource_type="user_authentication",
            details=details,
            level=level,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
    
    async def log_extraction_complete(
        self,
        user_id: UUID,
        company_id: str,
        upload_id: UUID,
        processing_time: float,
        tables_count: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log extraction completion action."""
        await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.DATA_VIEW,  # Using DATA_VIEW as closest match
            resource_type="extraction_complete",
            resource_id=str(upload_id),
            details={
                "company_id": company_id,
                "upload_id": str(upload_id),
                "processing_time": processing_time,
                "tables_count": tables_count,
                "status": "completed"
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
    
    async def get_user_audit_logs(
        self,
        user_id: UUID,
        limit: int = 100,
        action_types: Optional[List[AuditActionType]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a specific user.
        
        Note: This is a simplified implementation. In production, you would
        query a dedicated audit log table.
        """
        # In a real implementation, you would query the audit log table
        # For now, we'll return a placeholder
        return [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action_type": "placeholder",
                "resource_type": "placeholder",
                "details": {"message": "Audit logs would be stored in a dedicated table"}
            }
        ]
    
    async def get_security_violations(
        self,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get security violations from audit logs.
        
        Note: This is a simplified implementation. In production, you would
        query a dedicated audit log table.
        """
        # In a real implementation, you would query the audit log table
        # for entries with level=CRITICAL and action_type=SECURITY_VIOLATION
        return [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": "placeholder",
                "violation_type": "placeholder",
                "details": {"message": "Security violations would be stored in a dedicated table"}
            }
        ]
    
    async def check_suspicious_activity(
        self,
        user_id: UUID,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Check for suspicious activity patterns for a user.
        
        Args:
            user_id: ID of the user to check
            time_window_hours: Time window to check for suspicious activity
            
        Returns:
            Dict containing suspicious activity analysis
        """
        # In a real implementation, you would analyze audit logs for patterns
        # such as:
        # - Multiple failed login attempts
        # - Unusual access patterns
        # - High volume of operations
        # - Access from unusual locations
        
        return {
            "user_id": str(user_id),
            "time_window_hours": time_window_hours,
            "suspicious_activities": [],
            "risk_score": 0,
            "recommendations": []
        }
