# Apply compatibility fixes first
from app.new_extraction_services.utils.compatibility import apply_compatibility_fixes
apply_compatibility_fixes()

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from collections import defaultdict
import time
import os
import signal
import logging
from app.api import company, mapping, review, statements, database_fields, plan_types, table_editor, improve_extraction, pending, dashboard, format_learning, new_extract, summary_rows, date_extraction, excel_extract, user_management, admin, otp_auth, auth, websocket, ai_intelligent_mapping, ai_table_mapping, pdf_proxy
from app.utils.auth_utils import cleanup_expired_sessions
from app.db.database import get_db
from app.security_config import (
    get_security_headers, 
    get_cors_config, 
    get_trusted_hosts,
    get_environment_security_check,
    get_security_recommendations
)
import asyncio

# Initialize logging
logger = logging.getLogger(__name__)

app = FastAPI()

# Track background tasks for graceful shutdown
background_tasks = set()
shutdown_event = asyncio.Event()

@app.on_event("shutdown")
async def shutdown_event_handler():
    """FastAPI shutdown event - cleanup on server stop"""
    logger.info("FastAPI shutdown event triggered")
    
    try:
        # Set shutdown event to stop background tasks
        shutdown_event.set()
        
        # Stop process monitoring
        from app.services.process_monitor import process_monitor
        await process_monitor.stop_monitoring()
        logger.info("Process monitoring stopped")
        
        # Import connection manager
        from app.services.websocket_service import connection_manager
        
        # Notify active WebSocket connections
        for upload_id in list(connection_manager.active_connections.keys()):
            try:
                await connection_manager.send_error(
                    upload_id, 
                    "Server is shutting down",
                    "SERVER_SHUTDOWN"
                )
            except Exception as e:
                logger.error(f"Error notifying upload {upload_id}: {e}")
        
        # Cancel all background tasks
        for task in background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete cancellation (with timeout)
        if background_tasks:
            await asyncio.wait(background_tasks, timeout=2.0)
        
        logger.info("Graceful shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker and monitoring.
    Always returns quickly to prevent timeouts during long operations.
    """
    return {
        "status": "healthy", 
        "message": "Commission tracker backend is running",
        "timestamp": time.time()
    }

@app.get("/health/detailed")
async def health_check_detailed():
    """
    Detailed health check with resource monitoring and process tracking.
    Enhanced with long-running process monitoring for large file processing.
    """
    try:
        import psutil
        
        # Get system resources
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Get WebSocket connection info
        from app.services.websocket_service import connection_manager
        ws_connections = connection_manager.get_connection_count()
        
        # Get process monitor status
        from app.services.process_monitor import process_monitor
        process_status = process_monitor.get_health_status()
        
        return {
            "status": "healthy",
            "process_monitoring": process_status,
            "timestamp": time.time(),
            "resources": {
                "memory": {
                    "total_gb": round(memory.total / 1024**3, 2),
                    "used_gb": round(memory.used / 1024**3, 2),
                    "available_gb": round(memory.available / 1024**3, 2),
                    "percent": memory.percent
                },
                "cpu": {
                    "percent": cpu_percent
                }
            },
            "connections": {
                "websocket": ws_connections
            },
            "warnings": [
                "High memory usage" if memory.percent > 90 else None,
                "High CPU usage" if cpu_percent > 90 else None
            ]
        }
    except ImportError:
        # psutil not available - return basic health check
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "message": "Detailed monitoring not available (psutil not installed)"
        }
    except Exception as e:
        logger.error(f"Error in detailed health check: {e}")
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "error": str(e)
        }

@app.get("/security/status")
async def security_status():
    """Security status endpoint for monitoring"""
    security_checks = get_environment_security_check()
    recommendations = get_security_recommendations()
    
    return {
        "status": "secure" if not recommendations else "needs_attention",
        "checks": security_checks,
        "recommendations": recommendations,
        "timestamp": time.time()
    }

@app.get("/debug/cors")
async def debug_cors():
    """Debug endpoint to check CORS configuration"""
    cors_config = get_cors_config()
    return {
        "cors_origins": cors_config["allow_origins"],
        "cors_credentials": cors_config["allow_credentials"],
        "cors_methods": cors_config["allow_methods"],
        "cors_headers": cors_config["allow_headers"],
        "environment": os.getenv("ENVIRONMENT", "development"),
        "cors_origins_env": os.getenv("CORS_ORIGINS", "not_set")
    }

# Security Configuration
cors_config = get_cors_config()
trusted_hosts = get_trusted_hosts()
security_headers = get_security_headers()

# Security middleware - CORS must be added first
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config["allow_origins"],
    allow_credentials=cors_config["allow_credentials"],
    allow_methods=cors_config["allow_methods"],
    allow_headers=cors_config["allow_headers"],
    expose_headers=["Set-Cookie", "Authorization", "Content-Type", "X-Process-Time"],  # Important for cookie visibility
)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=trusted_hosts
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add security headers (but don't override if already set by endpoint)
    for header, value in security_headers.items():
        if header not in response.headers:
            response.headers[header] = value
    
    # Add HSTS header for HTTPS
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# Rate limiting storage
rate_limit_storage = defaultdict(list)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Clean old entries (older than 1 hour)
    rate_limit_storage[client_ip] = [
        timestamp for timestamp in rate_limit_storage[client_ip]
        if current_time - timestamp < 3600
    ]
    
    # Check rate limits based on endpoint
    if request.url.path.startswith("/auth/otp/request"):
        # OTP requests: 10 per hour
        if len(rate_limit_storage[client_ip]) >= 10:
            raise HTTPException(
                status_code=429,
                detail="Too many OTP requests. Please try again later."
            )
        rate_limit_storage[client_ip].append(current_time)
    
    response = await call_next(request)
    return response

# Request timing middleware for monitoring
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.include_router(auth.router)
app.include_router(otp_auth.router)
app.include_router(user_management.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(company.router)
app.include_router(mapping.router)
app.include_router(review.router)
app.include_router(statements.router)
app.include_router(database_fields.router)
app.include_router(plan_types.router)
app.include_router(table_editor.router)
app.include_router(improve_extraction.router)
app.include_router(pending.router)
app.include_router(format_learning.router)
app.include_router(new_extract.router)
app.include_router(summary_rows.router)
app.include_router(date_extraction.router)
app.include_router(excel_extract.router)
app.include_router(ai_intelligent_mapping.router)
app.include_router(ai_table_mapping.router)
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(pdf_proxy.router, tags=["PDF"], prefix="/api")

# Background task for session cleanup
async def cleanup_sessions_periodically():
    """Clean up expired and inactive sessions every hour"""
    try:
        while not shutdown_event.is_set():
            try:
                async for db in get_db():
                    cleaned_count = await cleanup_expired_sessions(db)
                    if cleaned_count > 0:
                        logger.info(f"Cleaned up {cleaned_count} expired/inactive sessions")
                    break
            except Exception as e:
                logger.error(f"Error during session cleanup: {e}")
            
            # Wait 1 hour before next cleanup (or until shutdown)
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=3600)
                break  # Shutdown signal received
            except asyncio.TimeoutError:
                continue  # Timeout after 1 hour, run cleanup again
    except asyncio.CancelledError:
        logger.info("Session cleanup task cancelled")
        raise

# Setup on startup
@app.on_event("startup")
async def startup_event():
    """Run startup tasks with process monitoring for large file processing"""
    # Start background cleanup task and track it
    task = asyncio.create_task(cleanup_sessions_periodically())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    
    # Start process monitoring for long-running document extractions
    from app.services.process_monitor import process_monitor
    await process_monitor.start_monitoring()
    logger.info("Process monitoring started for large file processing")
    
    logger.info("Application startup complete with enhanced monitoring")

if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    
    # Import timeout configuration
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
    from config.timeouts import timeout_settings
    
    # Configure Uvicorn for large file processing with enhanced timeout settings
    uvicorn_config = {
        "app": app,
        "host": "0.0.0.0",
        "port": 8000,
        "timeout_keep_alive": timeout_settings.uvicorn_keepalive,  # 30 minutes keep-alive
        "timeout_graceful_shutdown": timeout_settings.uvicorn_graceful_shutdown,  # 60 seconds graceful shutdown
        "limit_concurrency": 100,  # Adjust based on your needs
        "limit_max_requests": 1000,  # Prevent memory leaks from long-running processes
        "workers": 1,  # Single worker for debugging, increase for production
        "log_level": "info"
    }
    
    logger.info(f"Starting Uvicorn with timeout configuration: keep_alive={uvicorn_config['timeout_keep_alive']}s, graceful_shutdown={uvicorn_config['timeout_graceful_shutdown']}s")
    
    uvicorn.run(**uvicorn_config)
