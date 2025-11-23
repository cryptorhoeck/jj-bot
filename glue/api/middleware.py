"""
API Middleware for Security and Performance
- Rate Limiting
- Request Logging
- Error Handling
"""
import time
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
from functools import wraps
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from api_utils import error_response, ErrorCodes


# ===== RATE LIMITER =====

class RateLimiter:
    """
    Token bucket rate limiter for API endpoints
    Configurable per-endpoint limits
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size

        # Track requests per IP
        self.minute_requests: Dict[str, list] = defaultdict(list)
        self.hour_requests: Dict[str, list] = defaultdict(list)

        # Per-endpoint limits (can be customized)
        self.endpoint_limits: Dict[str, int] = {
            "/api/bot/start": 5,      # 5 per minute
            "/api/bot/stop": 5,
            "/api/data/clear": 2,     # 2 per minute
            "/api/data/export": 10,
            "/api/backtest/run": 5,
        }

    def _clean_old_requests(self, requests: list, window_seconds: int) -> list:
        """Remove requests older than the window"""
        cutoff = time.time() - window_seconds
        return [r for r in requests if r > cutoff]

    def is_allowed(self, client_ip: str, endpoint: str = None) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed under rate limits
        Returns: (is_allowed, retry_after_seconds)
        """
        now = time.time()

        # Clean old requests
        self.minute_requests[client_ip] = self._clean_old_requests(
            self.minute_requests[client_ip], 60
        )
        self.hour_requests[client_ip] = self._clean_old_requests(
            self.hour_requests[client_ip], 3600
        )

        # Check per-minute limit
        minute_limit = self.endpoint_limits.get(endpoint, self.requests_per_minute)
        if len(self.minute_requests[client_ip]) >= minute_limit:
            oldest = min(self.minute_requests[client_ip])
            retry_after = int(60 - (now - oldest))
            return False, max(1, retry_after)

        # Check per-hour limit
        if len(self.hour_requests[client_ip]) >= self.requests_per_hour:
            oldest = min(self.hour_requests[client_ip])
            retry_after = int(3600 - (now - oldest))
            return False, max(1, retry_after)

        # Record this request
        self.minute_requests[client_ip].append(now)
        self.hour_requests[client_ip].append(now)

        return True, None

    def get_remaining(self, client_ip: str) -> Dict[str, int]:
        """Get remaining requests for an IP"""
        # Clean old requests first
        self.minute_requests[client_ip] = self._clean_old_requests(
            self.minute_requests[client_ip], 60
        )
        self.hour_requests[client_ip] = self._clean_old_requests(
            self.hour_requests[client_ip], 3600
        )

        return {
            "minute_remaining": max(0, self.requests_per_minute - len(self.minute_requests[client_ip])),
            "hour_remaining": max(0, self.requests_per_hour - len(self.hour_requests[client_ip]))
        }


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=100,  # Generous for development
    requests_per_hour=5000,
    burst_size=20
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to all requests"""

    # Endpoints exempt from rate limiting
    EXEMPT_PATHS = {
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/health",
        "/api/system/health",
        "/ws",  # WebSocket
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip rate limiting for WebSocket upgrades
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        is_allowed, retry_after = rate_limiter.is_allowed(client_ip, request.url.path)

        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content=error_response(
                    message="Rate limit exceeded. Please slow down.",
                    error_code=ErrorCodes.RATE_LIMITED,
                    details={"retry_after": retry_after}
                ),
                headers={"Retry-After": str(retry_after)}
            )

        # Add rate limit headers to response
        response = await call_next(request)
        remaining = rate_limiter.get_remaining(client_ip)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute_remaining"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour_remaining"])

        return response


# ===== REQUEST LOGGING MIDDLEWARE =====

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log API requests for debugging and analytics"""

    # Don't log these paths (too noisy)
    SKIP_LOGGING = {
        "/api/system/health",
        "/api/websocket/stats",
        "/ws",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for noisy endpoints
        if request.url.path in self.SKIP_LOGGING:
            return await call_next(request)

        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log slow requests (> 1 second)
        if duration_ms > 1000:
            print(f"⚠️  SLOW: {request.method} {request.url.path} - {duration_ms:.0f}ms")

        return response


# ===== ERROR HANDLING MIDDLEWARE =====

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return proper JSON responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise
        except Exception as e:
            # Log the error
            print(f"❌ Unhandled error: {type(e).__name__}: {e}")

            # Return a clean error response
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message="An internal server error occurred",
                    error_code=ErrorCodes.SERVER_ERROR,
                    details=str(e) if __debug__ else None
                )
            )


# ===== CORS CONFIGURATION =====

# Allowed origins for production
ALLOWED_ORIGINS = [
    "http://localhost:5173",      # Vite dev server
    "http://127.0.0.1:5173",
    "http://localhost:3000",      # Alternative React port
    "http://127.0.0.1:3000",
    "http://localhost:8000",      # Same-origin API calls
    "http://127.0.0.1:8000",
]

# For development, you can use this to allow all origins
DEV_ORIGINS = ["*"]


def get_cors_config(production: bool = False):
    """Get CORS configuration based on environment"""
    if production:
        return {
            "allow_origins": ALLOWED_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"],
            "expose_headers": [
                "X-RateLimit-Remaining-Minute",
                "X-RateLimit-Remaining-Hour"
            ],
            "max_age": 600,  # Cache preflight for 10 minutes
        }
    else:
        return {
            "allow_origins": DEV_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }


# ===== UTILITY FUNCTIONS =====

def rate_limit(requests_per_minute: int = 10):
    """
    Decorator for rate limiting specific endpoints

    Usage:
        @app.post("/api/expensive-operation")
        @rate_limit(requests_per_minute=5)
        async def expensive_operation():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            endpoint_key = f"{func.__name__}:{client_ip}"

            # Use the global rate limiter with custom limit
            original_limit = rate_limiter.requests_per_minute
            rate_limiter.endpoint_limits[request.url.path] = requests_per_minute

            is_allowed, retry_after = rate_limiter.is_allowed(client_ip, request.url.path)

            if not is_allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
