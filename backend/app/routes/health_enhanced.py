"""
Enhanced Health Monitoring System
Comprehensive health checks for production monitoring.

Monitors:
- Database connectivity
- Model availability  
- System resources
- API response times
- Service dependencies
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import time
import psutil
import os

from app.db import get_db
import app.state as state


router = APIRouter(prefix="/health", tags=["Health Monitoring"])


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    version: str
    uptime_seconds: float
    checks: Dict[str, Dict]


class ServiceCheck(BaseModel):
    """Individual service check result."""
    status: str  # "pass", "fail", "warn"
    response_time_ms: Optional[float] = None
    message: str
    details: Optional[Dict] = None


# Track startup time for uptime calculation
startup_time = time.time()


@router.get(
    "/",
    response_model=HealthStatus,
    summary="Comprehensive Health Check",
    description="""
    Returns detailed health status of all system components.
    
    **Status Levels:**
    - `healthy`: All systems operational
    - `degraded`: Some non-critical issues
    - `unhealthy`: Critical systems failing
    
    **Monitored Components:**
    - Database connectivity
    - AI model availability
    - System resources (CPU, memory)
    - Service dependencies
    
    **Use Cases:**
    - Load balancer health checks
    - Monitoring system alerts
    - Development debugging
    """,
    responses={
        200: {"description": "Health check completed"},
        503: {"description": "Service unhealthy"}
    }
)
async def comprehensive_health_check(db: Session = Depends(get_db)) -> HealthStatus:
    """
    Perform comprehensive health check of all system components.
    
    Returns 200 for healthy/degraded, 503 for unhealthy.
    """
    start_time = time.time()
    checks = {}
    overall_status = "healthy"
    
    # 1. Database connectivity check
    db_check = await _check_database(db)
    checks["database"] = db_check
    if db_check["status"] == "fail":
        overall_status = "unhealthy"
    
    # 2. AI model availability check
    model_check = _check_ai_model()
    checks["ai_model"] = model_check
    if model_check["status"] == "fail":
        overall_status = "degraded"  # Can still serve some requests
    
    # 3. System resources check
    system_check = _check_system_resources()
    checks["system_resources"] = system_check
    if system_check["status"] == "fail":
        overall_status = "degraded"
    
    # 4. Environment configuration check
    config_check = _check_configuration()
    checks["configuration"] = config_check
    if config_check["status"] == "fail":
        overall_status = "degraded"
    
    # Calculate total response time
    total_time = (time.time() - start_time) * 1000
    
    health_status = HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=os.getenv("APP_VERSION", "1.0.0"),
        uptime_seconds=time.time() - startup_time,
        checks=checks
    )
    
    # Return appropriate HTTP status
    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status.dict()
        )
    
    return health_status


@router.get(
    "/quick",
    summary="Quick Health Check",
    description="Lightweight health check for high-frequency monitoring (load balancers)."
)
async def quick_health_check() -> Dict[str, str]:
    """
    Quick health check for load balancers.
    
    Returns minimal response for high-frequency polling.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ai-coding-mentor"
    }


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Check if service is ready to accept requests."
)
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Kubernetes-style readiness check.
    
    Returns 200 only when service can handle requests.
    """
    # Check critical dependencies
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get(
    "/live",
    summary="Liveness Check", 
    description="Check if service is alive (for container orchestration)."
)
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes-style liveness check.
    
    Returns 200 if process is alive and not deadlocked.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - startup_time
    }


# Helper functions for individual checks

async def _check_database(db: Session) -> Dict:
    """Check database connectivity and performance."""
    start = time.time()
    try:
        # Test basic connectivity
        result = db.execute(text("SELECT 1 as test"))
        test_value = result.scalar()
        
        # Test table existence (users table should exist)
        db.execute(text("SELECT COUNT(*) FROM users LIMIT 1"))
        
        response_time = (time.time() - start) * 1000
        
        if response_time > 1000:  # > 1 second is concerning
            return {
                "status": "warn",
                "response_time_ms": round(response_time, 2),
                "message": "Database responding slowly",
                "details": {"threshold_ms": 1000}
            }
        
        return {
            "status": "pass",
            "response_time_ms": round(response_time, 2),
            "message": "Database connected successfully",
            "details": {"test_query_result": test_value}
        }
        
    except Exception as e:
        return {
            "status": "fail",
            "response_time_ms": round((time.time() - start) * 1000, 2),
            "message": f"Database connection failed: {str(e)}",
            "details": {"error_type": type(e).__name__}
        }


def _check_ai_model() -> Dict:
    """Check AI model availability."""
    try:
        model_loaded = getattr(state, "model_loaded", False)
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        
        if model_loaded:
            return {
                "status": "pass",
                "message": "AI model loaded and ready",
                "details": {
                    "model_loaded": True,
                    "ollama_url": ollama_url
                }
            }
        else:
            return {
                "status": "warn", 
                "message": "AI model not loaded (functionality limited)",
                "details": {
                    "model_loaded": False,
                    "ollama_url": ollama_url,
                    "impact": "AI responses unavailable"
                }
            }
            
    except Exception as e:
        return {
            "status": "fail",
            "message": f"AI model check failed: {str(e)}",
            "details": {"error_type": type(e).__name__}
        }


def _check_system_resources() -> Dict:
    """Check system resource usage."""
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Define thresholds
        cpu_warning = 80.0
        memory_warning = 85.0
        disk_warning = 90.0
        
        warnings = []
        status = "pass"
        
        if cpu_percent > cpu_warning:
            warnings.append(f"High CPU usage: {cpu_percent}%")
            status = "warn"
            
        if memory.percent > memory_warning:
            warnings.append(f"High memory usage: {memory.percent}%")
            status = "warn"
            
        if disk.percent > disk_warning:
            warnings.append(f"High disk usage: {disk.percent}%")
            status = "warn"
        
        # Critical thresholds
        if cpu_percent > 95 or memory.percent > 95:
            status = "fail"
        
        message = "System resources normal"
        if warnings:
            message = f"Resource warnings: {'; '.join(warnings)}"
        
        return {
            "status": status,
            "message": message,
            "details": {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "disk_percent": round(disk.percent, 1),
                "memory_gb": round(memory.available / (1024**3), 2)
            }
        }
        
    except Exception as e:
        return {
            "status": "warn",
            "message": f"Could not check system resources: {str(e)}",
            "details": {"error_type": type(e).__name__}
        }


def _check_configuration() -> Dict:
    """Check critical environment configuration."""
    try:
        required_vars = [
            "DATABASE_URL",
            "OLLAMA_BASE_URL"
        ]
        
        missing = []
        present = []
        
        for var in required_vars:
            if os.getenv(var):
                present.append(var)
            else:
                missing.append(var)
        
        if missing:
            return {
                "status": "fail",
                "message": f"Missing required environment variables: {', '.join(missing)}",
                "details": {
                    "missing": missing,
                    "present": present
                }
            }
        
        return {
            "status": "pass",
            "message": "All required configuration present",
            "details": {
                "required_vars_count": len(required_vars),
                "present": present
            }
        }
        
    except Exception as e:
        return {
            "status": "warn",
            "message": f"Configuration check failed: {str(e)}",
            "details": {"error_type": type(e).__name__}
        }