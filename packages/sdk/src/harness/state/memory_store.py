"""In-memory shared-state backend (tests / single-process dev)."""

from __future__ import annotations

import asyncio
from typing import Any

from harness.state.base import (
    BlackboardItem,
    ConflictSet,
    ItemStatus,
    StateBackend,
    WriteKind,
)


class InMemoryBackend(StateBackend):
    """Process-local backend guarded by an asyncio lock."""

    def __init__(self) -> None:
        self._store: dict[str, BlackboardItem] = {}
        self._conflicts: dict[str, ConflictSet] = {}
        self._lock = asyncio.Lock()

    async def put(self, item: BlackboardItem) -> BlackboardItem:
        # A4: AUTHORITATIVE writes MUST carry provenance — fail-closed without it.
        if item.kind == WriteKind.AUTHORITATIVE and not item.provenance:
            raise ValueError(
                f"AUTHORITATIVE write requires provenance (item id={item.id}, "
                f"type={item.type}). Set item.provenance to a trusted source "
                f"reference (e.g. 'file:report.pdf:page=3') before writing."
            )
        async with self._lock:
            self._store[item.id] = item
            self._detect_conflict(item)
            return item

    async def get(self, item_id: str) -> BlackboardItem | None:
        async with self._lock:
            item = self._store.get(item_id)
            if item is None or item.expired:
                return None
            return item

    async def write_if_version(
        self, item_id: str, content: Any, base_version: int, **meta: Any
    ) -> tuple[bool, BlackboardItem | None]:
        # A4: Check provenance for AUTHORITATIVE writes via meta
        kind = meta.get("kind")
        provenance = meta.get("provenance")
        if kind == WriteKind.AUTHORITATIVE and not provenance:
            raise ValueError(
                f"AUTHORITATIVE write_if_version requires provenance "
                f"(item_id={item_id}). Set provenance= in meta before writing."
            )
        async with self._lock:
            cur = self._store.get(item_id)
            if cur is not None and cur.version != base_version:
                # Optimistic concurrency: version advanced -> reject (propose parallel).
                return False, cur
            new_item = cur or BlackboardItem(id=item_id)
            new_item.content = content
            new_item.base_version = base_version
            new_item.version = base_version + 1
            for k, v in meta.items():
                if hasattr(new_item, k):
                    setattr(new_item, k, v)
            self._store[item_id] = new_item
            return True, new_item

    async def list_items(
        self, type: str | None = None, status: ItemStatus | None = None
    ) -> list[BlackboardItem]:
        async with self._lock:
            items = [i for i in self._store.values() if not i.expired]
            if type is not None:
                items = [i for i in items if i.type == type]
            if status is not None:
                items = [i for i in items if i.status == status]
            return items

    async def get_conflicts(self) -> list[ConflictSet]:
        async with self._lock:
            return list(self._conflicts.values())

    def _detect_conflict(self, item: BlackboardItem) -> None:
        if item.kind != WriteKind.AUTHORITATIVE:
            return
        key = item.type
        for other in self._store.values():
            if other.id == item.id or other.type != key:
                continue
            if other.kind == WriteKind.AUTHORITATIVE and other.content != item.content:
                cs = self._conflicts.setdefault(key, ConflictSet(key=key))
                if item.id not in cs.item_ids:
                    cs.item_ids.append(item.id)
                if other.id not in cs.item_ids:
                    cs.item_ids.append(other.id)
                item.status = ItemStatus.CONFLICTED
