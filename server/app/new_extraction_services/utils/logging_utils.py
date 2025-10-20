"""Logging utilities for table extraction pipeline."""

import sys
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger
import json
import traceback
from datetime import datetime


class StructuredLogger:
    """Structured logger with JSON output support."""
    
    def __init__(self, config=None):
        """Initialize structured logger with configuration."""
        self.config = config
        self._setup_logger()
    
    def _setup_logger(self):
        """Set up loguru logger with configuration."""
        # Remove default logger
        logger.remove()
        
        if self.config and hasattr(self.config, 'logging'):
            log_config = self.config.logging
            
            # Console logging
            logger.add(
                sys.stderr,
                format=log_config.format,
                level=log_config.level,
                colorize=True,
                backtrace=True,
                diagnose=True
            )
            
            # File logging
            if log_config.log_file:
                log_path = Path(log_config.log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                logger.add(
                    log_path,
                    format=log_config.format,
                    level=log_config.level,
                    rotation=log_config.rotation,
                    retention=log_config.retention,
                    compression="zip",
                    backtrace=True,
                    diagnose=True
                )
                
                # JSON structured logging (disabled temporarily due to format issues)
                # json_log_path = log_path.with_suffix('.json.log')
                # logger.add(
                #     json_log_path,
                #     format=self._json_formatter,
                #     level=log_config.level,
                #     rotation=log_config.rotation,
                #     retention=log_config.retention,
                #     compression="zip"
                # )
        else:
            # Default console logging
            logger.add(
                sys.stderr,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
                level="INFO",
                colorize=True
            )
    
    def _json_formatter(self, record):
        """Format log record as JSON."""
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
            "module": record["module"],
            "process": record["process"].id,
            "thread": record["thread"].id
        }
        
        # Add exception info if present
        if record["exception"]:
            log_entry["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback
            }
        
        # Add extra fields from context
        if "extra" in record and record["extra"]:
            log_entry.update(record["extra"])
        
        return json.dumps(log_entry)


class ExtractionLogger:
    """Specialized logger for table extraction operations."""
    
    def __init__(self, name: str, config=None):
        """Initialize extraction logger."""
        self.name = name
        self.config = config
        self.logger = logger.bind(component=name)
        
        # Setup structured logging
        if not hasattr(logger, '_structured_setup'):
            structured_logger = StructuredLogger(config)
            logger._structured_setup = True
    
    def log_extraction_start(self, document_path: str, metadata: Optional[Dict[str, Any]] = None):
        """Log start of extraction process."""
        self.logger.info(
            "Starting table extraction",
            extra={
                "event": "extraction_start",
                "document_path": document_path,
                "metadata": metadata or {}
            }
        )
    
    def log_extraction_progress(self, stage: str, progress: float, details: Optional[Dict[str, Any]] = None):
        """Log extraction progress."""
        self.logger.info(
            f"Extraction progress: {stage} ({progress:.1%})",
            extra={
                "event": "extraction_progress",
                "stage": stage,
                "progress": progress,
                "details": details or {}
            }
        )
    
    def log_extraction_success(self, 
                             document_path: str, 
                             num_tables: int, 
                             processing_time: float,
                             quality_metrics: Optional[Dict[str, float]] = None):
        """Log successful extraction."""
        self.logger.success(
            f"Extraction completed: {num_tables} tables extracted in {processing_time:.2f}s",
            extra={
                "event": "extraction_success",
                "document_path": document_path,
                "num_tables": num_tables,
                "processing_time": processing_time,
                "quality_metrics": quality_metrics or {}
            }
        )
    
    def log_extraction_error(self, 
                           document_path: str, 
                           error: Exception, 
                           stage: Optional[str] = None,
                           context: Optional[Dict[str, Any]] = None):
        """Log extraction error."""
        self.logger.error(
            f"Extraction failed: {str(error)}",
            extra={
                "event": "extraction_error",
                "document_path": document_path,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "stage": stage,
                "context": context or {},
                "traceback": traceback.format_exc()
            }
        )
    
    def log_model_performance(self, 
                            model_name: str, 
                            inference_time: float, 
                            confidence_scores: Optional[Dict[str, float]] = None,
                            memory_usage: Optional[float] = None):
        """Log model performance metrics."""
        self.logger.debug(
            f"Model performance: {model_name} - {inference_time:.3f}s",
            extra={
                "event": "model_performance",
                "model_name": model_name,
                "inference_time": inference_time,
                "confidence_scores": confidence_scores or {},
                "memory_usage": memory_usage
            }
        )
    
    def log_quality_metrics(self, 
                          document_path: str, 
                          table_id: str, 
                          metrics: Dict[str, float]):
        """Log quality assessment metrics."""
        self.logger.info(
            f"Quality metrics for table {table_id}",
            extra={
                "event": "quality_metrics",
                "document_path": document_path,
                "table_id": table_id,
                "metrics": metrics
            }
        )
    
    def log_api_request(self, 
                       endpoint: str, 
                       method: str, 
                       file_size: Optional[int] = None,
                       user_id: Optional[str] = None):
        """Log API request."""
        self.logger.info(
            f"API request: {method} {endpoint}",
            extra={
                "event": "api_request",
                "endpoint": endpoint,
                "method": method,
                "file_size": file_size,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_api_response(self, 
                        endpoint: str, 
                        status_code: int, 
                        response_time: float,
                        response_size: Optional[int] = None):
        """Log API response."""
        level = "info" if status_code < 400 else "error"
        getattr(self.logger, level)(
            f"API response: {status_code} - {response_time:.3f}s",
            extra={
                "event": "api_response",
                "endpoint": endpoint,
                "status_code": status_code,
                "response_time": response_time,
                "response_size": response_size
            }
        )


def get_logger(name: str, config=None) -> ExtractionLogger:
    """Get a configured logger instance."""
    return ExtractionLogger(name, config)


def setup_logging(config=None):
    """Set up global logging configuration."""
    structured_logger = StructuredLogger(config)
    return structured_logger


# Context manager for logging extraction operations
class LogExtractionOperation:
    """Context manager for logging extraction operations."""
    
    def __init__(self, logger: ExtractionLogger, document_path: str, operation: str):
        self.logger = logger
        self.document_path = document_path
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.logger.info(
            f"Starting {self.operation}",
            extra={
                "event": f"{self.operation}_start",
                "document_path": self.document_path,
                "start_time": self.start_time.isoformat()
            }
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.logger.success(
                f"Completed {self.operation} in {duration:.2f}s",
                extra={
                    "event": f"{self.operation}_success",
                    "document_path": self.document_path,
                    "duration": duration,
                    "end_time": end_time.isoformat()
                }
            )
        else:
            self.logger.logger.error(
                f"Failed {self.operation} after {duration:.2f}s: {exc_val}",
                extra={
                    "event": f"{self.operation}_error",
                    "document_path": self.document_path,
                    "duration": duration,
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val),
                    "end_time": end_time.isoformat()
                }
            )
        
        return False  # Don't suppress exceptions
