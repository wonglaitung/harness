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

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "source_agent": self.source_agent,
            "confidence": self.confidence,
            "version": self.version,
            "base_version": self.base_version,
            "status": self.status.value,
            "kind": self.kind.value,
        }


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
