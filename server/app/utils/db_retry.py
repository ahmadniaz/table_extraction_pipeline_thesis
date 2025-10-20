import asyncio
import logging
from typing import Callable, Any, Optional
from sqlalchemy.exc import InterfaceError, OperationalError, DisconnectionError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def retry_db_operation(
    operation: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    *args,
    **kwargs
) -> Any:
    # Ensure parameters are the correct type
    max_retries = int(max_retries)
    base_delay = float(base_delay)
    max_delay = float(max_delay)
    """
    Retry a database operation with exponential backoff.
    
    Args:
        operation: The async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        *args: Arguments to pass to the operation
        **kwargs: Keyword arguments to pass to the operation
    
    Returns:
        The result of the operation
    
    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await operation(*args, **kwargs)
        except (InterfaceError, OperationalError, DisconnectionError) as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.2f}s...")
            
            await asyncio.sleep(delay)
        except Exception as e:
            # For non-database errors, don't retry
            logger.error(f"Non-database error occurred: {e}")
            raise
    
    # This should never be reached, but just in case
    raise last_exception

async def with_db_retry(
    db: AsyncSession,
    operation: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    *args,
    **kwargs
) -> Any:
    """
    Execute a database operation with retry logic and proper session handling.
    
    Args:
        db: Database session
        operation: The async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        *args: Arguments to pass to the operation
        **kwargs: Keyword arguments to pass to the operation
    
    Returns:
        The result of the operation
    """
    async def wrapped_operation():
        try:
            return await operation(db, *args, **kwargs)
        except (InterfaceError, OperationalError, DisconnectionError):
            # If we get a connection error, try to refresh the session
            try:
                await db.rollback()
            except:
                pass
            raise
    
    return await retry_db_operation(
        wrapped_operation,
        max_retries=int(max_retries),
        base_delay=float(base_delay),
        max_delay=float(max_delay)
    )

def with_db_retry_sync(
    operation: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    *args,
    **kwargs
) -> Any:
    """
    Execute a synchronous database operation with retry logic.
    This is a simplified version for non-async contexts.
    
    Args:
        operation: The function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        *args: Arguments to pass to the operation
        **kwargs: Keyword arguments to pass to the operation
    
    Returns:
        The result of the operation
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return operation(*args, **kwargs)
        except (InterfaceError, OperationalError, DisconnectionError) as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.2f}s...")
            
            import time
            time.sleep(delay)
        except Exception as e:
            # For non-database errors, don't retry
            logger.error(f"Non-database error occurred: {e}")
            raise
    
    # This should never be reached, but just in case
    raise last_exception
