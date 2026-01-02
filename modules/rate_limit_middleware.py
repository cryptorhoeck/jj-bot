"""
API Rate Limiting Middleware for JJ-Bot
Provides sliding window rate limiting to protect API endpoints
"""

import time
import asyncio
import logging
from collections import defaultdict
from typing import Dict, Callable, Optional
from dataclasses import dataclass
from datetime import datetime

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 20  # Max requests in 1 second
    enabled: bool = True
    whitelist_ips: list = None
    exempt_paths: list = None

    def __post_init__(self):
        if self.whitelist_ips is None:
            self.whitelist_ips = ["127.0.0.1", "::1", "localhost"]
        if self.exempt_paths is None:
            self.exempt_paths = [
                "/docs",
                "/openapi.json",
                "/redoc",
                "/api/auth/status",
                "/api/system/health",
                "/ws"
            ]


class SlidingWindowCounter:
    """
    Sliding window rate limiter implementation
    More accurate than fixed window counters
    """

    def __init__(self, window_seconds: int, max_requests: int):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests: Dict[str, list] = defaultdict(list)
        self._cleanup_lock = asyncio.Lock()

    def _cleanup_old_requests(self, key: str, current_time: float):
        """Remove requests outside the window"""
        cutoff = current_time - self.window_seconds
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """
        Check if request is allowed
        Returns: (allowed, remaining, reset_seconds)
        """
        current_time = time.time()
        self._cleanup_old_requests(key, current_time)

        request_count = len(self.requests[key])
        remaining = max(0, self.max_requests - request_count)

        if request_count >= self.max_requests:
            # Calculate when the oldest request will expire
            if self.requests[key]:
                oldest = min(self.requests[key])
                reset_seconds = int(self.window_seconds - (current_time - oldest))
            else:
                reset_seconds = self.window_seconds
            return False, 0, reset_seconds

        # Add this request
        self.requests[key].append(current_time)
        return True, remaining - 1, self.window_seconds

    async def cleanup_all(self):
        """Periodic cleanup of old entries"""
        async with self._cleanup_lock:
            current_time = time.time()
            cutoff = current_time - self.window_seconds

            keys_to_delete = []
            for key in self.requests:
                self.requests[key] = [t for t in self.requests[key] if t > cutoff]
                if not self.requests[key]:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.requests[key]


class RateLimiter:
    """
    Multi-tier rate limiter with burst, minute, and hour limits
    """

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()

        # Create limiters for different time windows
        self.burst_limiter = SlidingWindowCounter(1, self.config.burst_limit)
        self.minute_limiter = SlidingWindowCounter(60, self.config.requests_per_minute)
        self.hour_limiter = SlidingWindowCounter(3600, self.config.requests_per_hour)

        # Track blocked IPs temporarily
        self.blocked_ips: Dict[str, float] = {}
        self.block_duration = 300  # 5 minutes

        # Stats
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "blocked_by_burst": 0,
            "blocked_by_minute": 0,
            "blocked_by_hour": 0
        }

    def get_client_key(self, request: Request) -> str:
        """Get unique client identifier from request"""
        # Use X-Forwarded-For if behind proxy, otherwise use client host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def is_whitelisted(self, client_ip: str) -> bool:
        """Check if IP is whitelisted"""
        return client_ip in self.config.whitelist_ips

    def is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from rate limiting"""
        return any(path.startswith(exempt) for exempt in self.config.exempt_paths)

    def is_blocked(self, client_ip: str) -> bool:
        """Check if IP is temporarily blocked"""
        if client_ip in self.blocked_ips:
            if time.time() < self.blocked_ips[client_ip]:
                return True
            else:
                del self.blocked_ips[client_ip]
        return False

    def block_ip(self, client_ip: str):
        """Temporarily block an IP"""
        self.blocked_ips[client_ip] = time.time() + self.block_duration
        logger.warning(f"Rate limit: Blocked IP {client_ip} for {self.block_duration} seconds")

    def check_rate_limit(self, request: Request) -> tuple[bool, dict]:
        """
        Check all rate limits for a request
        Returns: (allowed, headers_dict)
        """
        self.stats["total_requests"] += 1

        client_ip = self.get_client_key(request)
        path = request.url.path

        # Skip rate limiting if disabled
        if not self.config.enabled:
            return True, {}

        # Check whitelist
        if self.is_whitelisted(client_ip):
            return True, {"X-RateLimit-Whitelisted": "true"}

        # Check exempt paths
        if self.is_exempt_path(path):
            return True, {}

        # Check if blocked
        if self.is_blocked(client_ip):
            self.stats["blocked_requests"] += 1
            return False, {
                "X-RateLimit-Blocked": "true",
                "Retry-After": str(int(self.blocked_ips.get(client_ip, 0) - time.time()))
            }

        # Check burst limit (per second)
        burst_allowed, burst_remaining, burst_reset = self.burst_limiter.is_allowed(client_ip)
        if not burst_allowed:
            self.stats["blocked_requests"] += 1
            self.stats["blocked_by_burst"] += 1
            return False, {
                "X-RateLimit-Limit": str(self.config.burst_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(burst_reset),
                "Retry-After": str(burst_reset)
            }

        # Check minute limit
        minute_allowed, minute_remaining, minute_reset = self.minute_limiter.is_allowed(client_ip)
        if not minute_allowed:
            self.stats["blocked_requests"] += 1
            self.stats["blocked_by_minute"] += 1
            # Block IP temporarily after repeated violations
            if self.stats["blocked_by_minute"] > 10:
                self.block_ip(client_ip)
            return False, {
                "X-RateLimit-Limit": str(self.config.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(minute_reset),
                "Retry-After": str(minute_reset)
            }

        # Check hour limit
        hour_allowed, hour_remaining, hour_reset = self.hour_limiter.is_allowed(client_ip)
        if not hour_allowed:
            self.stats["blocked_requests"] += 1
            self.stats["blocked_by_hour"] += 1
            self.block_ip(client_ip)  # Block after hourly limit exceeded
            return False, {
                "X-RateLimit-Limit": str(self.config.requests_per_hour),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(hour_reset),
                "Retry-After": str(hour_reset)
            }

        # All limits passed
        return True, {
            "X-RateLimit-Limit": str(self.config.requests_per_minute),
            "X-RateLimit-Remaining": str(minute_remaining),
            "X-RateLimit-Reset": str(minute_reset)
        }

    def get_stats(self) -> dict:
        """Get rate limiting statistics"""
        return {
            **self.stats,
            "blocked_ips_count": len(self.blocked_ips),
            "config": {
                "enabled": self.config.enabled,
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_hour": self.config.requests_per_hour,
                "burst_limit": self.config.burst_limit
            }
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting
    """

    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting"""
        allowed, headers = self.rate_limiter.check_rate_limit(request)

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded. Please slow down.",
                    "retry_after": headers.get("Retry-After", "60")
                }
            )
            for key, value in headers.items():
                response.headers[key] = value
            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        for key, value in headers.items():
            response.headers[key] = value

        return response


# Global rate limiter instance
rate_limiter = RateLimiter()
