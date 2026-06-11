"""
Redis-based rate limiter.

Uses sliding window algorithm for accurate rate limiting.
Supports multi-instance deployment.

Reference: packages/cloud/docs/03-gateway.md (Rate Limiter section)
"""

from __future__ import annotations

import time
from typing import Optional

import redis


class RedisRateLimiter:
    """
    Redis-based sliding window rate limiter.

    ADR-010: Memory-based rate limiter fails in multi-instance deployment.
    Redis provides shared state across gateway replicas.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_requests: int = 100,
        window_seconds: int = 3600,
    ):
        """
        Initialize rate limiter.

        Args:
            redis_url: Redis connection URL
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.redis = redis.from_url(redis_url)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def check(self, user_id: str) -> bool:
        """
        Check if user has remaining quota.

        Uses sliding window algorithm:
        1. Remove expired records (older than window)
        2. Count current records
        3. Add new record
        4. Return True if under limit

        Args:
            user_id: User identifier

        Returns:
            True if request allowed, False if limit exceeded
        """
        key = f"rate_limit:{user_id}"
        now = time.time()
        window_start = now - self.window_seconds

        # Atomic pipeline for sliding window
        pipe = self.redis.pipeline()
        # Remove expired records
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current records
        pipe.zcard(key)
        # Add new record
        pipe.zadd(key, {str(now): now})
        # Set expiry
        pipe.expire(key, self.window_seconds)

        results = pipe.execute()
        current_count = results[1]

        return current_count < self.max_requests

    def get_remaining(self, user_id: str) -> int:
        """
        Get remaining requests for user.

        Args:
            user_id: User identifier

        Returns:
            Number of remaining requests
        """
        key = f"rate_limit:{user_id}"
        now = time.time()
        window_start = now - self.window_seconds

        # Remove expired and count
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        results = pipe.execute()

        current_count = results[1]
        return max(0, self.max_requests - current_count)

    def reset(self, user_id: str) -> None:
        """
        Reset rate limit for user.

        Args:
            user_id: User identifier
        """
        key = f"rate_limit:{user_id}"
        self.redis.delete(key)