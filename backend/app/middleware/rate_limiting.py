"""
API Rate Limiting System
Production-ready rate limiting for API security and resource protection.

Features:
- Per-IP rate limiting
- Different limits per endpoint type
- Redis backend for distributed systems
- Graceful degradation (in-memory fallback)
- Detailed rate limit headers
- Custom error responses
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Optional, Callable
import time
import asyncio
import hashlib
from collections import defaultdict, deque
from functools import wraps
import logging

# Try to import Redis, fallback to in-memory if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Production-ready rate limiter with Redis backend and in-memory fallback.

    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.memory_store = defaultdict(lambda: deque())
        self.memory_cleanup_interval = 60  # Clean memory every 60 seconds
        self.last_cleanup = time.time()
        
        # Try to connect to Redis
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()  # Test connection
                logger.info("Rate limiter: Redis connected successfully")
            except Exception as e:
                logger.warning(f"Rate limiter: Redis connection failed, using in-memory store: {e}")
                self.redis_client = None
        else:
            logger.info("Rate limiter: Using in-memory store (Redis not available)")
    
    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier (IP address, user ID, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            (allowed, info) tuple where info contains rate limit details
        """
        now = int(time.time())
        
        if self.redis_client:
            return await self._check_redis(key, limit, window, now)
        else:
            return self._check_memory(key, limit, window, now)
    
    async def _check_redis(self, key: str, limit: int, window: int, now: int) -> tuple[bool, Dict[str, int]]:
        """Check rate limit using Redis sliding window."""
        try:
            pipe = self.redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, now - window)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request with score as timestamp
            pipe.zadd(key, {str(now): now})
            
            # Set expiration for the key
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_count = results[1] + 1  # +1 for the request we just added
            
            # Calculate rate limit info
            remaining = max(0, limit - current_count)
            reset_time = now + window
            
            allowed = current_count <= limit
            
            if not allowed:
                # Remove the request we just added since it's not allowed
                self.redis_client.zrem(key, str(now))
            
            return allowed, {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "current": current_count
            }
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fallback to memory store
            return self._check_memory(key, limit, window, now)
    
    def _check_memory(self, key: str, limit: int, window: int, now: int) -> tuple[bool, Dict[str, int]]:
        """Check rate limit using in-memory store."""
        # Clean up old entries periodically
        if now - self.last_cleanup > self.memory_cleanup_interval:
            self._cleanup_memory(now, window)
            self.last_cleanup = now
        
        # Get request timestamps for this key
        timestamps = self.memory_store[key]
        
        # Remove old entries outside the window
        while timestamps and timestamps[0] <= now - window:
            timestamps.popleft()
        
        # Check if we can add another request
        current_count = len(timestamps)
        allowed = current_count < limit
        
        if allowed:
            timestamps.append(now)
            current_count += 1
        
        remaining = max(0, limit - current_count)
        reset_time = now + window
        
        return allowed, {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
            "current": current_count
        }
    
    def _cleanup_memory(self, now: int, default_window: int = 3600):
        """Clean up old entries from memory store."""
        keys_to_remove = []
        
        for key, timestamps in self.memory_store.items():
            # Remove old timestamps
            while timestamps and timestamps[0] <= now - default_window:
                timestamps.popleft()
            
            # Remove empty deques
            if not timestamps:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.memory_store[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


# Rate limit configurations for different endpoint types
RATE_LIMITS = {
    # High-frequency endpoints
    "health": {"limit": 100, "window": 60},      # 100/minute for health checks
    "analytics_summary": {"limit": 30, "window": 60},  # 30/minute for summaries
    
    # Medium-frequency endpoints
    "analytics": {"limit": 10, "window": 60},     # 10/minute for full analytics
    "users": {"limit": 5, "window": 60},          # 5/minute for user operations
    
    # Resource-intensive endpoints
    "ask": {"limit": 20, "window": 300},          # 20 per 5 minutes for AI questions
    "execute": {"limit": 10, "window": 300},      # 10 per 5 minutes for code execution
    "roadmaps": {"limit": 3, "window": 300},      # 3 per 5 minutes for roadmap generation
}


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Handles X-Forwarded-For header for load balancers/proxies.
    """
    # Check for forwarded headers (load balancer/proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


def create_rate_limit_key(ip: str, endpoint: str) -> str:
    """Create a unique key for rate limiting."""
    # Hash IP for privacy in logs
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
    return f"rate_limit:{endpoint}:{ip_hash}"


def rate_limit(endpoint_type: str):
    """
    Decorator for rate limiting endpoints.
    
    Usage:
        @rate_limit("ask")
        async def ask_question(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from function arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Check kwargs for request
            if not request:
                request = kwargs.get('request')
            
            if not request:
                logger.warning(f"Rate limit decorator on {func.__name__}: No request object found")
                return await func(*args, **kwargs)
            
            # Get rate limit config
            config = RATE_LIMITS.get(endpoint_type, {"limit": 60, "window": 60})
            
            # Get client IP and create rate limit key
            client_ip = get_client_ip(request)
            rate_key = create_rate_limit_key(client_ip, endpoint_type)
            
            # Check rate limit
            allowed, info = await rate_limiter.is_allowed(
                rate_key, 
                config["limit"], 
                config["window"]
            )
            
            if not allowed:
                # Return rate limit exceeded error
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {info['limit']} per {config['window']} seconds",
                        "retry_after": info["reset"] - int(time.time()),
                        "endpoint": endpoint_type
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset"]),
                        "Retry-After": str(info["reset"] - int(time.time()))
                    }
                )
            
            # Add rate limit headers to response
            response = await func(*args, **kwargs)
            
            # Add headers if response supports it
            if hasattr(response, 'headers'):
                response.headers["X-RateLimit-Limit"] = str(info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(info["reset"])
            
            return response
        
        return wrapper
    return decorator


# Middleware for global rate limiting
async def rate_limit_middleware(request: Request, call_next):
    """
    Global rate limiting middleware.
    
    Applies basic rate limiting to all endpoints not covered by specific decorators.
    """
    # Skip rate limiting for health checks in middleware
    if request.url.path.startswith("/health"):
        return await call_next(request)
    
    # Apply global rate limit
    client_ip = get_client_ip(request)
    rate_key = create_rate_limit_key(client_ip, "global")
    
    allowed, info = await rate_limiter.is_allowed(rate_key, 1000, 3600)  # 1000/hour global limit
    
    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Global rate limit exceeded",
                "message": "Too many requests from your IP address",
                "retry_after": info["reset"] - int(time.time())
            },
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset"]),
                "Retry-After": str(info["reset"] - int(time.time()))
            }
        )
    
    response = await call_next(request)
    
    # Add global rate limit headers
    if hasattr(response, 'headers'):
        response.headers["X-RateLimit-Global-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Global-Remaining"] = str(info["remaining"])
    
    return response


# Example usage functions

def configure_rate_limiter(redis_url: Optional[str] = None):
    """Configure the global rate limiter with Redis URL."""
    global rate_limiter
    rate_limiter = RateLimiter(redis_url)


def get_rate_limit_status(ip: str, endpoint: str) -> Dict:
    """Get current rate limit status for debugging."""
    config = RATE_LIMITS.get(endpoint, {"limit": 60, "window": 60})
    rate_key = create_rate_limit_key(ip, endpoint)
    
    # This would need to be async in real usage
    # Just return config for now
    return {
        "endpoint": endpoint,
        "limit": config["limit"],
        "window": config["window"],
        "key": rate_key
    }
