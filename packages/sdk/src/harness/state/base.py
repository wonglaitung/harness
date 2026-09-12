"""Shared state — Blackboard-grade multi-agent collaboration store.

Multi-agent coordination MUST go through structured shared state, never
point-to-point text "notes" (防翻车清单 H). Every write carries a version +
writer id (防幻觉覆写); writes are layered into additive (observations/proposals)
vs authoritative (decisions, only via the verifier/control layer); concurrent
writes use optimistic CAS (``write_if_version``); conflicting facts surface in a
conflict set instead of silently overwriting.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WriteKind(Enum):
    """Write layering for shared state."""

    ADDITIVE = "additive"  # 观测/提议，任意 Agent 可写
    AUTHORITATIVE = "authoritative"  # 决策落定，仅控制层经 verifier


class ItemStatus(Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CONFLICTED = "conflicted"
    SUPERSEDED = "superseded"


@dataclass
class BlackboardItem:
    """A single shared-state record."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type: str = "observation"
    content: Any = None
    source_agent: str = "unknown"
    # Trusted write channel that performed the write (authorization), distinct
    # from ``source_agent`` (author attribution). Authoritative writes are only
    # allowed when this identifies the control layer (H3). Defaults to
    # ``source_agent`` so legacy/back-compat items authorize by author.
    writer_id: str | None = None
    # A4: Provenance — mandatory for AUTHORITATIVE writes. A short URI or
    # reference string identifying the trusted source that supports this item's
    # content (e.g. "file:report.pdf:page=3", "db:accounts:row=42",
    # "api:ledger:txn=abc123"). ADDITIVE items may omit this (observer role).
    provenance: str | None = None
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)
    base_version: int = 0
    version: int = 1
    ttl: float | None = None  # seconds; None = no expiry
    status: ItemStatus = ItemStatus.PROPOSED
    kind: WriteKind = WriteKind.ADDITIVE

    @property
    def expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    @property
    def effective_writer(self) -> str:
        """The channel to authorize on: explicit writer_id, else the author."""
        return self.writer_id or self.source_agent

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "source_agent": self.source_agent,
            "writer_id": self.writer_id,
            "provenance": self.provenance,
            "confidence": self.confidence,
            "version": self.version,
            "base_version": self.base_version,
            "status": self.status.value,
            "kind": self.kind.value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BlackboardItem":
        """Rebuild an item from :meth:`as_dict` output (enums restored)."""
        data = dict(d)
        if "status" in data and not isinstance(data["status"], ItemStatus):
            data["status"] = ItemStatus(data["status"])
        if "kind" in data and not isinstance(data["kind"], WriteKind):
            data["kind"] = WriteKind(data["kind"])
        return cls(**data)


@dataclass
class ConflictSet:
    """A set of mutually conflicting authoritative facts."""

    key: str
    item_ids: list[str] = field(default_factory=list)
    detected_at: float = field(default_factory=time.time)


class StateBackend(ABC):
    """Pluggable storage backend for the shared state."""

    @abstractmethod
    async def put(self, item: BlackboardItem) -> BlackboardItem: ...

    @abstractmethod
    async def get(self, item_id: str) -> BlackboardItem | None: ...

    @abstractmethod
    async def write_if_version(
        self, item_id: str, content: Any, base_version: int, **meta: Any
    ) -> tuple[bool, BlackboardItem | None]: ...

    @abstractmethod
    async def list_items(
        self, type: str | None = None, status: ItemStatus | None = None
    ) -> list[BlackboardItem]: ...

    @abstractmethod
    async def get_conflicts(self) -> list[ConflictSet]: ...

    async def aclose(self) -> None:
        """Release backend resources (connections, files, threads).

        Default no-op for stateless backends. Backends holding a connection
        (file/db/redis) override this so the event loop can shut down without
        an aiosqlite/redis worker thread outliving it.
        """
        return None
