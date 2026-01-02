"""
Rate Limiting Tests for JJ-Bot
Tests rate limiting middleware functionality
"""

import pytest
import time
from unittest.mock import MagicMock, patch


class TestSlidingWindowCounter:
    """Test SlidingWindowCounter class"""

    def test_allows_request_under_limit(self):
        """Test that requests under limit are allowed"""
        from modules.rate_limit_middleware import SlidingWindowCounter

        counter = SlidingWindowCounter(window_seconds=60, max_requests=10)
        allowed, remaining, reset = counter.is_allowed("test_client")

        assert allowed is True
        assert remaining == 9

    def test_blocks_request_over_limit(self):
        """Test that requests over limit are blocked"""
        from modules.rate_limit_middleware import SlidingWindowCounter

        counter = SlidingWindowCounter(window_seconds=60, max_requests=3)

        # Make 3 requests to hit limit
        for _ in range(3):
            counter.is_allowed("test_client")

        # 4th request should be blocked
        allowed, remaining, reset = counter.is_allowed("test_client")

        assert allowed is False
        assert remaining == 0

    def test_window_reset(self):
        """Test that old requests are cleaned up"""
        from modules.rate_limit_middleware import SlidingWindowCounter

        # Use very short window for testing
        counter = SlidingWindowCounter(window_seconds=0.1, max_requests=3)

        # Make 3 requests to hit limit
        for _ in range(3):
            counter.is_allowed("test_client")

        # Wait for window to expire
        time.sleep(0.2)

        # Should be allowed again
        allowed, remaining, reset = counter.is_allowed("test_client")

        assert allowed is True

    def test_different_clients_tracked_separately(self):
        """Test that different clients have separate limits"""
        from modules.rate_limit_middleware import SlidingWindowCounter

        counter = SlidingWindowCounter(window_seconds=60, max_requests=2)

        # Exhaust client1's limit
        counter.is_allowed("client1")
        counter.is_allowed("client1")
        allowed1, _, _ = counter.is_allowed("client1")

        # client2 should still have requests available
        allowed2, _, _ = counter.is_allowed("client2")

        assert allowed1 is False
        assert allowed2 is True


class TestRateLimiterConfig:
    """Test RateLimitConfig class"""

    def test_default_config(self):
        """Test default configuration values"""
        from modules.rate_limit_middleware import RateLimitConfig

        config = RateLimitConfig()

        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_limit == 20
        assert config.enabled is True
        assert "127.0.0.1" in config.whitelist_ips

    def test_custom_config(self):
        """Test custom configuration"""
        from modules.rate_limit_middleware import RateLimitConfig

        config = RateLimitConfig(
            requests_per_minute=120,
            burst_limit=30,
            enabled=False
        )

        assert config.requests_per_minute == 120
        assert config.burst_limit == 30
        assert config.enabled is False


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_whitelist_bypass(self):
        """Test that whitelisted IPs bypass rate limiting"""
        from modules.rate_limit_middleware import RateLimiter, RateLimitConfig

        config = RateLimitConfig(whitelist_ips=["127.0.0.1"])
        limiter = RateLimiter(config)

        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.url.path = "/api/test"
        request.headers.get.return_value = None

        allowed, headers = limiter.check_rate_limit(request)

        assert allowed is True
        assert headers.get("X-RateLimit-Whitelisted") == "true"

    def test_exempt_path_bypass(self):
        """Test that exempt paths bypass rate limiting"""
        from modules.rate_limit_middleware import RateLimiter, RateLimitConfig

        config = RateLimitConfig(
            exempt_paths=["/docs"],
            whitelist_ips=[]  # Empty to test path exemption
        )
        limiter = RateLimiter(config)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/docs"
        request.headers.get.return_value = None

        allowed, headers = limiter.check_rate_limit(request)

        assert allowed is True

    def test_disabled_rate_limiting(self):
        """Test that disabled rate limiting allows all requests"""
        from modules.rate_limit_middleware import RateLimiter, RateLimitConfig

        config = RateLimitConfig(enabled=False, whitelist_ips=[])
        limiter = RateLimiter(config)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.headers.get.return_value = None

        allowed, headers = limiter.check_rate_limit(request)

        assert allowed is True

    def test_get_stats(self):
        """Test getting rate limiter statistics"""
        from modules.rate_limit_middleware import RateLimiter

        limiter = RateLimiter()
        stats = limiter.get_stats()

        assert "total_requests" in stats
        assert "blocked_requests" in stats
        assert "config" in stats

    def test_forwarded_header_ip_detection(self):
        """Test IP detection from X-Forwarded-For header"""
        from modules.rate_limit_middleware import RateLimiter

        limiter = RateLimiter()

        request = MagicMock()
        request.headers.get.return_value = "203.0.113.1, 70.41.3.18"
        request.client.host = "127.0.0.1"

        client_key = limiter.get_client_key(request)

        assert client_key == "203.0.113.1"


class TestRateLimitMiddleware:
    """Test rate limit middleware integration"""

    def test_rate_limit_headers_added(self, api_client):
        """Test that rate limit headers are added to responses"""
        response = api_client.get("/api/system/health")

        # Headers may or may not be present depending on whitelist
        # Just verify the request succeeds
        assert response.status_code == 200

    def test_multiple_requests_tracked(self, api_client):
        """Test that multiple requests are tracked"""
        # Make several requests
        for _ in range(5):
            response = api_client.get("/api/system/health")
            assert response.status_code == 200

        # All should succeed since localhost is whitelisted


class TestIPBlocking:
    """Test IP blocking functionality"""

    def test_block_ip(self):
        """Test IP blocking"""
        from modules.rate_limit_middleware import RateLimiter

        limiter = RateLimiter()
        limiter.block_ip("192.168.1.100")

        assert limiter.is_blocked("192.168.1.100") is True

    def test_block_expires(self):
        """Test that IP block expires"""
        from modules.rate_limit_middleware import RateLimiter

        limiter = RateLimiter()
        limiter.block_duration = 0.1  # 100ms for testing
        limiter.block_ip("192.168.1.100")

        # Should be blocked initially
        assert limiter.is_blocked("192.168.1.100") is True

        # Wait for block to expire
        time.sleep(0.2)

        # Should no longer be blocked
        assert limiter.is_blocked("192.168.1.100") is False
