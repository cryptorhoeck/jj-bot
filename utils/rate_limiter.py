"""
Rate limiter for API requests
Prevents hitting API rate limits with token bucket algorithm
"""

import time
import threading
from typing import Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter"""
    requests_per_minute: int = 50
    burst_size: Optional[int] = None  # Max burst, defaults to requests_per_minute

    def __post_init__(self):
        if self.burst_size is None:
            self.burst_size = self.requests_per_minute


class TokenBucket:
    """
    Token bucket rate limiter implementation
    Thread-safe for concurrent access
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize token bucket

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.tokens = float(config.burst_size)
        self.max_tokens = float(config.burst_size)
        self.refill_rate = config.requests_per_minute / 60.0  # tokens per second
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait for tokens (seconds)

        Returns:
            True if tokens were acquired, False if timeout occurred
        """
        start_time = time.time()

        while True:
            with self.lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                # Calculate wait time for next token
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

                # Don't wait longer than remaining timeout
                wait_time = min(wait_time, timeout - elapsed)

            # Wait for tokens to refill
            time.sleep(min(wait_time, 0.1))  # Sleep in small increments

    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def available_tokens(self) -> float:
        """Get number of available tokens"""
        with self.lock:
            self._refill()
            return self.tokens

    def wait_time(self, tokens: int = 1) -> float:
        """
        Calculate wait time for tokens to be available

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                return 0.0

            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


class RateLimiter:
    """
    Multi-endpoint rate limiter
    Manages separate token buckets for different API endpoints
    """

    def __init__(self, default_config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter

        Args:
            default_config: Default configuration for new endpoints
        """
        self.default_config = default_config or RateLimitConfig()
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = threading.Lock()

    def add_endpoint(self, endpoint: str, config: Optional[RateLimitConfig] = None):
        """
        Add a rate-limited endpoint

        Args:
            endpoint: Endpoint identifier
            config: Configuration for this endpoint
        """
        config = config or self.default_config

        with self.lock:
            self.buckets[endpoint] = TokenBucket(config)

    def acquire(
        self,
        endpoint: str,
        tokens: int = 1,
        timeout: Optional[float] = None,
        auto_add: bool = True
    ) -> bool:
        """
        Acquire tokens for an endpoint

        Args:
            endpoint: Endpoint identifier
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait
            auto_add: Automatically add endpoint if not exists

        Returns:
            True if tokens were acquired
        """
        # Get or create bucket
        with self.lock:
            if endpoint not in self.buckets:
                if auto_add:
                    self.buckets[endpoint] = TokenBucket(self.default_config)
                else:
                    raise ValueError(f"Endpoint '{endpoint}' not configured")

            bucket = self.buckets[endpoint]

        return bucket.acquire(tokens, timeout)

    def try_acquire(self, endpoint: str, tokens: int = 1, auto_add: bool = True) -> bool:
        """
        Try to acquire tokens without blocking

        Args:
            endpoint: Endpoint identifier
            tokens: Number of tokens to acquire
            auto_add: Automatically add endpoint if not exists

        Returns:
            True if tokens were acquired
        """
        # Get or create bucket
        with self.lock:
            if endpoint not in self.buckets:
                if auto_add:
                    self.buckets[endpoint] = TokenBucket(self.default_config)
                else:
                    return False

            bucket = self.buckets[endpoint]

        return bucket.try_acquire(tokens)

    def wait_time(self, endpoint: str, tokens: int = 1) -> Optional[float]:
        """
        Get wait time for endpoint

        Args:
            endpoint: Endpoint identifier
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds, or None if endpoint not found
        """
        with self.lock:
            bucket = self.buckets.get(endpoint)

        if bucket is None:
            return None

        return bucket.wait_time(tokens)

    def get_stats(self, endpoint: str) -> Optional[Dict]:
        """
        Get statistics for an endpoint

        Args:
            endpoint: Endpoint identifier

        Returns:
            Statistics dictionary or None
        """
        with self.lock:
            bucket = self.buckets.get(endpoint)

        if bucket is None:
            return None

        return {
            'endpoint': endpoint,
            'available_tokens': bucket.available_tokens(),
            'max_tokens': bucket.max_tokens,
            'refill_rate': bucket.refill_rate,
            'requests_per_minute': bucket.config.requests_per_minute,
        }

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all endpoints"""
        stats = {}

        with self.lock:
            endpoints = list(self.buckets.keys())

        for endpoint in endpoints:
            stats[endpoint] = self.get_stats(endpoint)

        return stats


# Global rate limiter for CoinGecko API
coingecko_limiter = RateLimiter(
    default_config=RateLimitConfig(
        requests_per_minute=50,  # CoinGecko free tier limit
        burst_size=10  # Allow small bursts
    )
)


def wait_for_rate_limit(
    endpoint: str = "coingecko",
    tokens: int = 1,
    timeout: Optional[float] = 30.0
) -> bool:
    """
    Wait for rate limit before making API request

    Args:
        endpoint: API endpoint identifier
        tokens: Number of tokens needed (usually 1 per request)
        timeout: Maximum time to wait

    Returns:
        True if rate limit allows request, False if timeout

    Example:
        if wait_for_rate_limit("coingecko"):
            response = requests.get(api_url)
    """
    return coingecko_limiter.acquire(endpoint, tokens, timeout)


def can_make_request(endpoint: str = "coingecko", tokens: int = 1) -> bool:
    """
    Check if request can be made without waiting

    Args:
        endpoint: API endpoint identifier
        tokens: Number of tokens needed

    Returns:
        True if request can be made immediately
    """
    return coingecko_limiter.try_acquire(endpoint, tokens)


def get_rate_limit_wait_time(endpoint: str = "coingecko", tokens: int = 1) -> float:
    """
    Get estimated wait time for rate limit

    Args:
        endpoint: API endpoint identifier
        tokens: Number of tokens needed

    Returns:
        Wait time in seconds
    """
    wait_time = coingecko_limiter.wait_time(endpoint, tokens)
    return wait_time if wait_time is not None else 0.0


if __name__ == "__main__":
    # Test rate limiter
    print("Testing rate limiter...")

    # Create a rate limiter with 10 requests per minute
    config = RateLimitConfig(requests_per_minute=10, burst_size=5)
    limiter = RateLimiter(default_config=config)

    # Test burst
    print("\nTesting burst (should succeed immediately):")
    for i in range(5):
        success = limiter.try_acquire("test")
        print(f"Request {i+1}: {'✅ Success' if success else '❌ Limited'}")

    # Test rate limiting
    print("\nTesting rate limit (should be limited):")
    success = limiter.try_acquire("test")
    print(f"Request 6: {'✅ Success' if success else '❌ Limited (as expected)'}")

    # Test wait time
    wait_time = limiter.wait_time("test")
    print(f"\nWait time for next request: {wait_time:.2f} seconds")

    # Test stats
    print("\nRate limiter stats:")
    stats = limiter.get_stats("test")
    print(f"  Available tokens: {stats['available_tokens']:.2f}")
    print(f"  Max tokens: {stats['max_tokens']}")
    print(f"  Refill rate: {stats['refill_rate']:.2f} tokens/second")
    print(f"  Requests per minute: {stats['requests_per_minute']}")

    print("\n✅ Rate limiter test complete")
