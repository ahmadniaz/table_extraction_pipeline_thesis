"""
Process monitoring and health check system for long-running document extractions.
Tracks active processes, detects stuck processes, and provides recovery mechanisms.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """Status of a long-running process"""
    ACTIVE = "active"
    STUCK = "stuck"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ProcessInfo:
    """Information about an active process"""
    upload_id: str
    process_type: str
    start_time: datetime
    last_heartbeat: datetime
    status: ProcessStatus
    metadata: Dict[str, Any]


class ProcessMonitor:
    """
    Monitor and manage long-running processes.
    Detects stuck processes and provides cleanup mechanisms.
    """
    
    def __init__(self, max_process_time: int = 1800, heartbeat_timeout: int = 300):
        """
        Initialize the process monitor.
        
        Args:
            max_process_time: Maximum time a process can run (seconds)
            heartbeat_timeout: Time without heartbeat before considering stuck (seconds)
        """
        self.active_processes: Dict[str, ProcessInfo] = {}
        self.max_process_time = max_process_time
        self.heartbeat_timeout = heartbeat_timeout
        self.monitoring_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        logger.info(f"Process monitor initialized: max_time={max_process_time}s, heartbeat_timeout={heartbeat_timeout}s")
    
    async def register_process(
        self, 
        upload_id: str, 
        process_type: str, 
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Register a new long-running process for monitoring.
        
        Args:
            upload_id: Unique identifier for the upload/process
            process_type: Type of process (e.g., 'mistral_extraction', 'gpt_processing')
            metadata: Additional metadata about the process
        """
        self.active_processes[upload_id] = ProcessInfo(
            upload_id=upload_id,
            process_type=process_type,
            start_time=datetime.utcnow(),
            last_heartbeat=datetime.utcnow(),
            status=ProcessStatus.ACTIVE,
            metadata=metadata or {}
        )
        logger.info(f"Registered process: {upload_id} ({process_type})")
    
    async def heartbeat(self, upload_id: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Update heartbeat for an active process.
        
        Args:
            upload_id: Process identifier
            metadata: Optional metadata to update
            
        Returns:
            True if process is still valid, False if should terminate
        """
        if upload_id not in self.active_processes:
            logger.warning(f"Heartbeat for unregistered process: {upload_id}")
            return False
        
        process = self.active_processes[upload_id]
        process.last_heartbeat = datetime.utcnow()
        
        if metadata:
            process.metadata.update(metadata)
        
        # Check if process has exceeded maximum time
        elapsed = (datetime.utcnow() - process.start_time).total_seconds()
        if elapsed > self.max_process_time:
            logger.warning(f"Process {upload_id} exceeded max time: {elapsed}s > {self.max_process_time}s")
            process.status = ProcessStatus.TIMEOUT
            return False
        
        logger.debug(f"Heartbeat: {upload_id}, elapsed: {elapsed:.1f}s")
        return True
    
    async def unregister_process(
        self, 
        upload_id: str, 
        status: ProcessStatus = ProcessStatus.COMPLETED
    ) -> None:
        """
        Unregister a process (completed or terminated).
        
        Args:
            upload_id: Process identifier
            status: Final status of the process
        """
        if upload_id in self.active_processes:
            process = self.active_processes[upload_id]
            process.status = status
            elapsed = (datetime.utcnow() - process.start_time).total_seconds()
            
            logger.info(f"Unregistered process: {upload_id}, status: {status.value}, elapsed: {elapsed:.1f}s")
            del self.active_processes[upload_id]
    
    async def get_process_info(self, upload_id: str) -> Optional[ProcessInfo]:
        """Get information about a specific process."""
        return self.active_processes.get(upload_id)
    
    async def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """Get information about all active processes."""
        return self.active_processes.copy()
    
    async def get_stuck_processes(self) -> Dict[str, ProcessInfo]:
        """
        Identify processes that appear to be stuck.
        
        Returns:
            Dictionary of stuck processes
        """
        current_time = datetime.utcnow()
        stuck = {}
        
        for upload_id, process in self.active_processes.items():
            elapsed_since_heartbeat = (current_time - process.last_heartbeat).total_seconds()
            elapsed_total = (current_time - process.start_time).total_seconds()
            
            # Check if stuck
            if elapsed_since_heartbeat > self.heartbeat_timeout:
                process.status = ProcessStatus.STUCK
                stuck[upload_id] = process
                logger.warning(
                    f"Stuck process detected: {upload_id}, "
                    f"last_heartbeat: {elapsed_since_heartbeat:.1f}s ago, "
                    f"total_elapsed: {elapsed_total:.1f}s"
                )
            elif elapsed_total > self.max_process_time:
                process.status = ProcessStatus.TIMEOUT
                stuck[upload_id] = process
                logger.warning(
                    f"Timeout process detected: {upload_id}, "
                    f"elapsed: {elapsed_total:.1f}s > {self.max_process_time}s"
                )
        
        return stuck
    
    async def monitor_processes(self) -> None:
        """
        Continuously monitor active processes for stuck/timeout conditions.
        This should run as a background task.
        """
        logger.info("Starting process monitoring loop")
        
        while not self._shutdown:
            try:
                # Check for stuck processes
                stuck_processes = await self.get_stuck_processes()
                
                if stuck_processes:
                    logger.warning(f"Found {len(stuck_processes)} stuck/timeout processes")
                    
                    # Cleanup stuck processes
                    for upload_id, process in stuck_processes.items():
                        await self._cleanup_stuck_process(upload_id, process)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                logger.info("Process monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Process monitor error: {e}", exc_info=True)
                await asyncio.sleep(60)
        
        logger.info("Process monitoring loop stopped")
    
    async def _cleanup_stuck_process(self, upload_id: str, process: ProcessInfo) -> None:
        """
        Cleanup a stuck or timed-out process.
        
        Args:
            upload_id: Process identifier
            process: Process information
        """
        try:
            elapsed = (datetime.utcnow() - process.start_time).total_seconds()
            
            # Send timeout notification via WebSocket if available
            try:
                from app.services.websocket_service import connection_manager
                await connection_manager.send_error(
                    upload_id,
                    f"Processing timeout - the document processing exceeded {elapsed:.0f} seconds. "
                    f"This may indicate the document is too large or complex.",
                    "PROCESS_TIMEOUT"
                )
            except Exception as e:
                logger.warning(f"Failed to send timeout notification: {e}")
            
            # Remove from active processes
            if upload_id in self.active_processes:
                del self.active_processes[upload_id]
            
            logger.info(
                f"Cleaned up stuck process: {upload_id}, "
                f"type: {process.process_type}, "
                f"elapsed: {elapsed:.1f}s, "
                f"status: {process.status.value}"
            )
            
        except Exception as e:
            logger.error(f"Failed to cleanup stuck process {upload_id}: {e}", exc_info=True)
    
    async def start_monitoring(self) -> None:
        """Start the monitoring background task."""
        if self.monitoring_task is None or self.monitoring_task.done():
            self._shutdown = False
            self.monitoring_task = asyncio.create_task(self.monitor_processes())
            logger.info("Process monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring background task."""
        self._shutdown = True
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Process monitoring stopped")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the monitoring system.
        
        Returns:
            Dictionary with health status information
        """
        current_time = datetime.utcnow()
        
        active_count = len([p for p in self.active_processes.values() if p.status == ProcessStatus.ACTIVE])
        stuck_count = len([p for p in self.active_processes.values() if p.status == ProcessStatus.STUCK])
        timeout_count = len([p for p in self.active_processes.values() if p.status == ProcessStatus.TIMEOUT])
        
        # Get process details
        process_details = []
        for upload_id, process in self.active_processes.items():
            elapsed = (current_time - process.start_time).total_seconds()
            since_heartbeat = (current_time - process.last_heartbeat).total_seconds()
            
            process_details.append({
                'upload_id': upload_id,
                'process_type': process.process_type,
                'status': process.status.value,
                'elapsed_seconds': int(elapsed),
                'since_heartbeat': int(since_heartbeat),
                'metadata': process.metadata
            })
        
        return {
            'monitoring_active': not self._shutdown and self.monitoring_task and not self.monitoring_task.done(),
            'total_active_processes': len(self.active_processes),
            'active_processes': active_count,
            'stuck_processes': stuck_count,
            'timeout_processes': timeout_count,
            'max_process_time': self.max_process_time,
            'heartbeat_timeout': self.heartbeat_timeout,
            'processes': process_details
        }


# Global process monitor instance
process_monitor = ProcessMonitor()

