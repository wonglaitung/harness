"""
Redis-based session storage for distributed deployment.

Provides session storage backed by Redis for multi-instance deployments.
Uses JSON serialization (not pickle) for cross-language compatibility.

Key features:
- JSON serialization (compatible with Java/Spring services)
- Schema versioning for backward compatibility
- TTL support for automatic cleanup
- Connection pooling via redis-py

Requirements:
    pip install redis

Example:
    >>> store = RedisSessionStore("redis://localhost:6379")
    >>> await store.save(session)
    >>> session = await store.load("session-123")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from harness.types import Session, Message

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Check if Redis is available
try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis as AsyncRedis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None
    AsyncRedis = Any

# Schema version for backward compatibility
SCHEMA_VERSION = 1


@dataclass
class RedisSessionConfig:
    """Configuration for Redis session storage."""

    redis_url: str = "redis://localhost:6379"
    key_prefix: str = "harness:session"
    ttl_seconds: int = 3600  # 1 hour default TTL
    connection_pool_size: int = 10


class RedisSessionStore:
    """
    Redis-based session storage for distributed deployment.

    This store uses JSON serialization (not pickle) to ensure
    compatibility with other services (e.g., Java Spring services)
    that may need to read session data.

    Key format: {key_prefix}:{session_id}

    Schema versioning is included to handle future schema changes
    without breaking existing data.

    Example:
        >>> store = RedisSessionStore("redis://localhost:6379")
        >>> await store.save(session)
        >>> session = await store.load("session-123")
        >>> await store.delete("session-123")
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        config: RedisSessionConfig | None = None,
    ):
        """
        Initialize Redis session store.

        Args:
            redis_url: Redis connection URL
            config: Optional configuration object
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis is required for RedisSessionStore. "
                "Install with: pip install redis"
            )

        self.config = config or RedisSessionConfig(redis_url=redis_url)
        self._redis: AsyncRedis | None = None

    async def _get_redis(self) -> AsyncRedis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.config.redis_url,
                max_connections=self.config.connection_pool_size,
                decode_responses=True,  # Return strings, not bytes
            )
        return self._redis

    def _session_key(self, session_id: str) -> str:
        """Get Redis key for a session."""
        return f"{self.config.key_prefix}:{session_id}"

    def _serialize(self, session: Session) -> str:
        """
        Serialize session to JSON.

        Uses strict JSON (not pickle) for cross-language compatibility.
        """
        data = {
            "_schema_version": SCHEMA_VERSION,
            "id": session.id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content if isinstance(m.content, str) else m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in session.messages
            ],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "metadata": session.metadata,
        }
        return json.dumps(data, ensure_ascii=False)

    def _deserialize(self, data: str) -> Optional[Session]:
        """
        Deserialize session from JSON.

        Handles schema versioning for backward compatibility.
        """
        try:
            raw = json.loads(data)

            # Check schema version
            schema_version = raw.get("_schema_version", 1)

            # Handle schema migration if needed
            if schema_version > SCHEMA_VERSION:
                logger.warning(
                    f"Session schema version {schema_version} is newer than "
                    f"supported version {SCHEMA_VERSION}. Some features may not work."
                )

            session = Session(
                id=raw["id"],
                created_at=datetime.fromisoformat(raw["created_at"]),
                updated_at=datetime.fromisoformat(raw["updated_at"]),
                metadata=raw.get("metadata", {}),
            )

            # Load messages
            for msg_data in raw.get("messages", []):
                session.messages.append(Message(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    metadata=msg_data.get("metadata", {}),
                ))

            return session

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to deserialize session: JSON error: {e}")
            return None
        except KeyError as e:
            logger.warning(f"Failed to deserialize session: missing key: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to deserialize session: {e}")
            return None

    async def save(self, session: Session) -> None:
        """
        Save a session to Redis.

        Args:
            session: The session to save
        """
        redis = await self._get_redis()
        key = self._session_key(session.id)
        data = self._serialize(session)

        await redis.set(
            key,
            data,
            ex=self.config.ttl_seconds,
        )
        logger.debug(f"Saved session {session.id} to Redis")

    async def load(self, session_id: str) -> Optional[Session]:
        """
        Load a session from Redis.

        Args:
            session_id: The session ID to load

        Returns:
            The session, or None if not found or invalid
        """
        redis = await self._get_redis()
        key = self._session_key(session_id)

        data = await redis.get(key)
        if data is None:
            return None

        session = self._deserialize(data)

        # If deserialization failed, delete the corrupted data
        if session is None:
            logger.warning(f"Deleting corrupted session data: {session_id}")
            await redis.delete(key)
            return None

        return session

    async def delete(self, session_id: str) -> None:
        """
        Delete a session from Redis.

        Args:
            session_id: The session ID to delete
        """
        redis = await self._get_redis()
        key = self._session_key(session_id)
        await redis.delete(key)
        logger.debug(f"Deleted session {session_id} from Redis")

    async def exists(self, session_id: str) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: The session ID to check

        Returns:
            True if the session exists
        """
        redis = await self._get_redis()
        key = self._session_key(session_id)
        return await redis.exists(key) > 0

    async def touch(self, session_id: str) -> bool:
        """
        Refresh the TTL for a session.

        Args:
            session_id: The session ID to refresh

        Returns:
            True if the session was found and refreshed
        """
        redis = await self._get_redis()
        key = self._session_key(session_id)
        return await redis.expire(key, self.config.ttl_seconds)

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


class RedisDistributedLock:
    """
    Distributed lock using Redis.

    Uses SET NX EX for atomic lock acquisition.

    Example:
        >>> lock = RedisDistributedLock("redis://localhost:6379")
        >>> async with lock.acquire("my-resource", timeout=10):
        ...     # Do work while holding the lock
        ...     pass
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "harness:lock",
    ):
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis is required for RedisDistributedLock. "
                "Install with: pip install redis"
            )

        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis: AsyncRedis | None = None

    async def _get_redis(self) -> AsyncRedis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._redis

    def _lock_key(self, resource: str) -> str:
        """Get Redis key for a lock."""
        return f"{self.key_prefix}:{resource}"

    async def acquire(
        self,
        resource: str,
        timeout: float = 30.0,
        retry_interval: float = 0.1,
    ) -> str | None:
        """
        Acquire a distributed lock.

        Args:
            resource: The resource to lock
            timeout: Lock timeout in seconds (auto-release)
            retry_interval: Interval between retries

        Returns:
            Lock token (used for release), or None if failed
        """
        import uuid
        import asyncio

        redis = await self._get_redis()
        key = self._lock_key(resource)
        token = str(uuid.uuid4())

        # SET key value NX EX timeout
        # NX: Only set if not exists
        # EX: Set expiry in seconds
        acquired = await redis.set(
            key,
            token,
            nx=True,
            ex=int(timeout),
        )

        if acquired:
            return token
        return None

    async def release(self, resource: str, token: str) -> bool:
        """
        Release a distributed lock.

        Uses Lua script to ensure atomic check-and-delete.

        Args:
            resource: The locked resource
            token: The lock token returned by acquire

        Returns:
            True if lock was released
        """
        redis = await self._get_redis()
        key = self._lock_key(resource)

        # Lua script for atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        result = await redis.eval(lua_script, 1, key, token)
        return result == 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
