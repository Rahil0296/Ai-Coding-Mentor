"""
Structured Logging System
Production-ready logging with structured output, error tracking, and performance monitoring.

Features:
- JSON structured logging
- Different log levels per environment
- Request ID tracking
- Error aggregation
- Performance monitoring
- Log rotation
- Integration with monitoring systems
"""

import logging
import logging.handlers
import json
import time
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from functools import wraps
from pathlib import Path
import os

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import asyncio


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs logs in JSON format for easy parsing by log aggregation systems.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        
        # Base log structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add thread/process info
        log_data["thread_id"] = record.thread
        log_data["process_id"] = record.process
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        
        # Add user ID if available
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add stack trace for errors
        if record.levelno >= logging.ERROR and not record.exc_info:
            log_data["stack_trace"] = traceback.format_stack()
        
        return json.dumps(log_data, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    """Filter to add request context to log records."""
    
    def __init__(self):
        super().__init__()
        self.request_storage = {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record."""
        # Try to get current request ID from thread-local storage
        request_id = getattr(record, 'request_id', None)
        if not request_id:
            # Try to get from asyncio context
            try:
                import contextvars
                request_id = getattr(contextvars.copy_context().get('request_id', None), 'get', lambda: None)()
            except:
                pass
        
        if request_id:
            record.request_id = request_id
        
        return True


class PerformanceLogger:
    """Logger for tracking API performance metrics."""
    
    def __init__(self):
        self.logger = logging.getLogger("performance")
        self.response_times: List[float] = []
        self.error_counts: Dict[str, int] = {}
        self.endpoint_stats: Dict[str, Dict] = {}
    
    def log_request(self, 
                   endpoint: str, 
                   method: str, 
                   response_time: float, 
                   status_code: int,
                   user_id: Optional[int] = None,
                   request_id: Optional[str] = None):
        """Log API request performance."""
        
        # Update stats
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                "count": 0,
                "total_time": 0,
                "errors": 0
            }
        
        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_time"] += response_time
        
        if status_code >= 400:
            stats["errors"] += 1
            error_key = f"{endpoint}:{status_code}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log the request
        self.logger.info(
            "API request completed",
            extra={
                "extra_data": {
                    "endpoint": endpoint,
                    "method": method,
                    "response_time_ms": round(response_time * 1000, 2),
                    "status_code": status_code,
                    "user_id": user_id,
                    "request_id": request_id
                }
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {}
        
        for endpoint, data in self.endpoint_stats.items():
            avg_time = data["total_time"] / data["count"] if data["count"] > 0 else 0
            error_rate = data["errors"] / data["count"] if data["count"] > 0 else 0
            
            stats[endpoint] = {
                "total_requests": data["count"],
                "avg_response_time_ms": round(avg_time * 1000, 2),
                "error_rate": round(error_rate * 100, 2),
                "total_errors": data["errors"]
            }
        
        return stats


# Global instances
performance_logger = PerformanceLogger()


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = "app.log",
    enable_console: bool = True,
    enable_file: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    Set up production logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None to disable file logging)
        enable_console: Whether to enable console logging
        enable_file: Whether to enable file logging
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    
    # Create logs directory if it doesn't exist
    if log_file and enable_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    structured_formatter = StructuredFormatter()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        
        # Use structured format for production, simple for development
        if os.getenv("ENVIRONMENT", "development") == "production":
            console_handler.setFormatter(structured_formatter)
        else:
            console_handler.setFormatter(console_formatter)
        
        console_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if enable_file and log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(structured_formatter)
        file_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Create application-specific loggers
    app_logger = logging.getLogger("app")
    security_logger = logging.getLogger("security")
    performance_logger_obj = logging.getLogger("performance")
    
    logging.info("Logging system initialized", extra={
        "extra_data": {
            "log_level": log_level,
            "console_enabled": enable_console,
            "file_enabled": enable_file,
            "log_file": log_file
        }
    })


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    request_id: Optional[str] = None
):
    """
    Log an error with full context.
    
    Args:
        logger: Logger instance to use
        error: Exception that occurred
        context: Additional context data
        user_id: User ID if applicable
        request_id: Request ID for tracing
    """
    
    extra_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {}
    }
    
    if user_id:
        extra_data["user_id"] = user_id
    
    logger.error(
        f"Error occurred: {str(error)}",
        exc_info=True,
        extra={
            "extra_data": extra_data,
            "request_id": request_id
        }
    )


def log_security_event(
    event_type: str,
    details: Dict[str, Any],
    severity: str = "INFO",
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None
):
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event
        details: Event details
        severity: Log severity level
        user_id: User ID if applicable
        ip_address: Client IP address
    """
    
    security_logger = logging.getLogger("security")
    
    extra_data = {
        "event_type": event_type,
        "details": details,
        "ip_address": ip_address,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    getattr(security_logger, severity.lower())(
        f"Security event: {event_type}",
        extra={"extra_data": extra_data}
    )


def performance_monitor(endpoint_name: Optional[str] = None):
    """
    Decorator to monitor endpoint performance.
    
    Usage:
        @performance_monitor("user_analytics")
        async def get_analytics(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            request_id = str(uuid.uuid4())
            endpoint = endpoint_name or func.__name__
            
            # Add request ID to context
            logger = get_logger("app")
            
            try:
                # Log request start
                logger.info(
                    f"Starting {endpoint}",
                    extra={
                        "extra_data": {
                            "endpoint": endpoint,
                            "function": func.__name__
                        },
                        "request_id": request_id
                    }
                )
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Log successful completion
                response_time = time.time() - start_time
                performance_logger.log_request(
                    endpoint=endpoint,
                    method="async",
                    response_time=response_time,
                    status_code=200,
                    request_id=request_id
                )
                
                logger.info(
                    f"Completed {endpoint}",
                    extra={
                        "extra_data": {
                            "endpoint": endpoint,
                            "response_time_ms": round(response_time * 1000, 2),
                            "status": "success"
                        },
                        "request_id": request_id
                    }
                )
                
                return result
                
            except Exception as e:
                # Log error
                response_time = time.time() - start_time
                performance_logger.log_request(
                    endpoint=endpoint,
                    method="async",
                    response_time=response_time,
                    status_code=500,
                    request_id=request_id
                )
                
                log_error(
                    logger,
                    e,
                    context={"endpoint": endpoint, "function": func.__name__},
                    request_id=request_id
                )
                
                raise
        
        return async_wrapper
    return decorator


# Exception handler for FastAPI
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with logging."""
    
    request_id = str(uuid.uuid4())
    logger = get_logger("app")
    
    # Log the exception
    log_error(
        logger,
        exc,
        context={
            "url": str(request.url),
            "method": request.method,
            "headers": dict(request.headers)
        },
        request_id=request_id
    )
    
    # Log security event for suspicious requests
    if isinstance(exc, HTTPException) and exc.status_code == 429:
        log_security_event(
            "rate_limit_exceeded",
            {"url": str(request.url), "method": request.method},
            severity="WARNING",
            ip_address=request.client.host if request.client else None
        )
    
    # Return appropriate error response
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "Request failed",
                "detail": exc.detail,
                "request_id": request_id
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": "An unexpected error occurred",
                "request_id": request_id
            }
        )


# Middleware for request logging
async def logging_middleware(request: Request, call_next):
    """Middleware to log all requests."""
    
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Add request ID to context
    request.state.request_id = request_id
    
    logger = get_logger("app")
    
    # Log request start
    logger.info(
        "Request started",
        extra={
            "extra_data": {
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
            "request_id": request_id
        }
    )
    
    try:
        response = await call_next(request)
        
        # Log request completion
        response_time = time.time() - start_time
        
        performance_logger.log_request(
            endpoint=request.url.path,
            method=request.method,
            response_time=response_time,
            status_code=response.status_code,
            request_id=request_id
        )
        
        logger.info(
            "Request completed",
            extra={
                "extra_data": {
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "response_time_ms": round(response_time * 1000, 2)
                },
                "request_id": request_id
            }
        )
        
        return response
        
    except Exception as e:
        response_time = time.time() - start_time
        
        performance_logger.log_request(
            endpoint=request.url.path,
            method=request.method,
            response_time=response_time,
            status_code=500,
            request_id=request_id
        )
        
        raise


# Export common functions
__all__ = [
    "setup_logging",
    "get_logger", 
    "log_error",
    "log_security_event",
    "performance_monitor",
    "global_exception_handler",
    "logging_middleware",
    "performance_logger"
]
