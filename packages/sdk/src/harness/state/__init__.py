"""Shared state public API + store factory.

``SharedStateStore`` wraps a :class:`StateBackend` and exposes the Blackboard
operations multi-agent roles use. Selection is by ``backend`` name; unknown or
uninstalled backends raise a clear error (optional extras are pinned, not core).
"""

from __future__ import annotations

from typing import Any

from harness.state.base import (
    BlackboardItem,
    ConflictSet,
    ItemStatus,
    StateBackend,
    WriteKind,
)
from harness.state.file_store import FileBackend
from harness.state.memory_store import InMemoryBackend


class SharedStateStore:
    """High-level shared-state facade for multi-agent coordination."""

    def __init__(self, backend: StateBackend) -> None:
        self._backend = backend

    async def put_additive(
        self, type: str, content: Any, source_agent: str, confidence: float = 0.5, **meta: Any
    ) -> BlackboardItem:
        item = BlackboardItem(
            type=type,
            content=content,
            source_agent=source_agent,
            confidence=confidence,
            kind=WriteKind.ADDITIVE,
            **meta,
        )
        return await self._backend.put(item)

    async def put_authoritative(
        self, type: str, content: Any, source_agent: str, confidence: float = 0.9, **meta: Any
    ) -> BlackboardItem:
        item = BlackboardItem(
            type=type,
            content=content,
            source_agent=source_agent,
            confidence=confidence,
            kind=WriteKind.AUTHORITATIVE,
            status=ItemStatus.CONFIRMED,
            **meta,
        )
        return await self._backend.put(item)

    async def get(self, item_id: str) -> BlackboardItem | None:
        return await self._backend.get(item_id)

    async def write_if_version(
        self, item_id: str, content: Any, base_version: int, **meta: Any
    ) -> tuple[bool, BlackboardItem | None]:
        return await self._backend.write_if_version(item_id, content, base_version, **meta)

    async def list_items(
        self, type: str | None = None, status: ItemStatus | None = None
    ) -> list[BlackboardItem]:
        return await self._backend.list_items(type=type, status=status)

    async def get_conflicts(self) -> list[ConflictSet]:
        return await self._backend.get_conflicts()


def create_state_store(
    backend: str = "memory",
    *,
    path: str | None = None,
    url: str | None = None,
) -> SharedStateStore:
    """Build a :class:`SharedStateStore` for the given backend name.

    backends: memory (tests) | file (worktree/dev) | redis | db (prod, extras).
    """
    if backend == "memory":
        return SharedStateStore(InMemoryBackend())
    if backend == "file":
        return SharedStateStore(FileBackend(path or ".harness/state.db"))
    if backend == "redis":
        from harness.state.redis_store import RedisBackend

        return SharedStateStore(RedisBackend(url or "redis://localhost:6379/0"))
    if backend == "db":
        from harness.state.db_store import DBBackend

        return SharedStateStore(DBBackend(path or ".harness/state.db"))
    raise ValueError(f"Unknown state backend: {backend!r}")


__all__ = [
    "SharedStateStore",
    "create_state_store",
    "BlackboardItem",
    "StateBackend",
    "WriteKind",
    "ItemStatus",
    "ConflictSet",
]
