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
    """High-level shared-state facade for multi-agent coordination.

    Args:
        backend: Pluggable storage backend.
        verifier: Optional gate for authoritative (decision) writes. When set,
            :meth:`put_authoritative` and authoritative :meth:`write_if_version`
            updates reject any item for which ``verifier(item)`` is falsy —
            enforcing "authoritative writes only via the control layer /
            verifier" (H3: 防幻觉覆写).
        read_verifier: Optional gate applied on reads (:meth:`get` / :meth:`list_items`).
            When set, an item for which ``read_verifier(item)`` is falsy is dropped
            from read results (returned as ``None`` / filtered out). This closes the
            read-side gap — a forged/stale authoritative item written around the
            write verifier cannot be consumed by other agents (H: 无 read 校验).
    """

    def __init__(
        self,
        backend: StateBackend,
        verifier: Any | None = None,
        read_verifier: Any | None = None,
    ) -> None:
        self._backend = backend
        self._verifier = verifier
        self._read_verifier = read_verifier

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
        self,
        type: str,
        content: Any,
        source_agent: str,
        confidence: float = 0.9,
        *,
        writer_id: str | None = None,
        **meta: Any,
    ) -> BlackboardItem:
        """Write an authoritative (decision) item.

        ``source_agent`` is the author of the content; ``writer_id`` is the
        trusted channel performing the write (defaults to ``source_agent``). The
        control layer may write on behalf of a role by passing its own
        ``writer_id`` (e.g. ``"harness"``) while keeping ``source_agent=role``,
        so authorization and attribution stay separate (H3).
        """
        item = BlackboardItem(
            type=type,
            content=content,
            source_agent=source_agent,
            writer_id=writer_id or source_agent,
            confidence=confidence,
            kind=WriteKind.AUTHORITATIVE,
            status=ItemStatus.CONFIRMED,
            **meta,
        )
        if self._verifier is not None and not self._verifier(item):
            raise PermissionError(
                "Authoritative writes require the control-layer verifier (H3). "
                "Rejecting unauthorized authoritative write."
            )
        return await self._backend.put(item)

    async def get(self, item_id: str) -> BlackboardItem | None:
        item = await self._backend.get(item_id)
        if item is not None and self._read_verifier is not None and not self._read_verifier(item):
            return None
        return item

    async def write_if_version(
        self, item_id: str, content: Any, base_version: int, **meta: Any
    ) -> tuple[bool, BlackboardItem | None]:
        """Optimistic compare-and-swap update.

        When a verifier is attached, an update that would leave (or create) an
        authoritative item must pass the same control-layer verifier as
        :meth:`put_authoritative`. Without this, CAS was a bypass around H3.
        """
        if self._verifier is not None:
            existing = await self._backend.get(item_id)
            probe = existing or BlackboardItem(id=item_id)
            # Effective kind/status/writer for the write: meta wins, else inherit.
            kind = meta.get("kind", probe.kind)
            status = meta.get("status", probe.status)
            writer = meta.get("writer_id") or meta.get("source_agent") or probe.effective_writer
            if kind == WriteKind.AUTHORITATIVE and not self._verifier(
                BlackboardItem(
                    id=item_id,
                    type=meta.get("type", probe.type),
                    source_agent=meta.get("source_agent", probe.source_agent),
                    writer_id=writer,
                    kind=kind,
                    status=status,
                )
            ):
                raise PermissionError(
                    "Authoritative CAS writes require the control-layer verifier (H3). "
                    "Rejecting unauthorized write_if_version."
                )
        return await self._backend.write_if_version(item_id, content, base_version, **meta)

    async def list_items(
        self, type: str | None = None, status: ItemStatus | None = None
    ) -> list[BlackboardItem]:
        items = await self._backend.list_items(type=type, status=status)
        if self._read_verifier is not None:
            items = [i for i in items if self._read_verifier(i)]
        return items

    async def get_conflicts(self) -> list[ConflictSet]:
        return await self._backend.get_conflicts()

    async def aclose(self) -> None:
        """Release the backend's resources (connections/threads).

        Call before the event loop exits so file/db/redis workers do not
        outlive it.
        """
        await self._backend.aclose()


def create_state_store(
    backend: str = "memory",
    *,
    path: str | None = None,
    url: str | None = None,
    verifier: Any | None = None,
    read_verifier: Any | None = None,
) -> SharedStateStore:
    """Build a :class:`SharedStateStore` for the given backend name.

    backends: memory (tests) | file (worktree/dev) | redis | db (prod, extras).
    """
    if backend == "memory":
        return SharedStateStore(InMemoryBackend(), verifier=verifier, read_verifier=read_verifier)
    if backend == "file":
        return SharedStateStore(
            FileBackend(path or ".harness/state.db"), verifier=verifier, read_verifier=read_verifier
        )
    if backend == "redis":
        from harness.state.redis_store import RedisBackend

        return SharedStateStore(
            RedisBackend(url or "redis://localhost:6379/0"),
            verifier=verifier,
            read_verifier=read_verifier,
        )
    if backend == "db":
        from harness.state.db_store import DBBackend

        return SharedStateStore(
            DBBackend(path or ".harness/state.db"), verifier=verifier, read_verifier=read_verifier
        )
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
