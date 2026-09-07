"""File-backed shared-state backend (worktree / dev) via SQLite.

Synchronous sqlite3 under a threading lock; async methods wrap the sync core.
No external dependency (sqlite3 is stdlib). Suitable for single-process dev and
worktree-isolated multi-agent runs.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from harness.state.base import (
    BlackboardItem,
    ConflictSet,
    ItemStatus,
    StateBackend,
    WriteKind,
)


def _row_to_item(row: tuple[Any, ...]) -> BlackboardItem:
    data = json.loads(row[0])
    # Rehydrate enums that were serialized as their string values.
    data["status"] = ItemStatus(data.get("status", "proposed"))
    data["kind"] = WriteKind(data.get("kind", "additive"))
    return BlackboardItem(**data)


class FileBackend(StateBackend):
    """SQLite-backed persistent backend."""

    def __init__(self, path: str = ".harness/state.db") -> None:
        self._path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blackboard (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def _serialize(self, item: BlackboardItem) -> str:
        return json.dumps(item.as_dict() | {"content": item.content})

    def _persist(self, item: BlackboardItem) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO blackboard (id, payload) VALUES (?, ?)",
            (item.id, self._serialize(item)),
        )
        self._conn.commit()

    def _load(self, item_id: str) -> BlackboardItem | None:
        cur = self._conn.execute("SELECT payload FROM blackboard WHERE id=?", (item_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return _row_to_item(row)

    async def put(self, item: BlackboardItem) -> BlackboardItem:
        await asyncio.to_thread(self._safe_put, item)
        return item

    def _safe_put(self, item: BlackboardItem) -> None:
        with self._lock:
            self._persist(item)

    async def get(self, item_id: str) -> BlackboardItem | None:
        return await asyncio.to_thread(self._load, item_id)

    async def write_if_version(
        self, item_id: str, content: Any, base_version: int, **meta: Any
    ) -> tuple[bool, BlackboardItem | None]:
        return await asyncio.to_thread(
            self._safe_write_if_version, item_id, content, base_version, meta
        )

    def _safe_write_if_version(
        self, item_id: str, content: Any, base_version: int, meta: dict[str, Any]
    ) -> tuple[bool, BlackboardItem | None]:
        with self._lock:
            cur = self._load(item_id)
            if cur is not None and cur.version != base_version:
                return False, cur
            new_item = cur or BlackboardItem(id=item_id)
            new_item.content = content
            new_item.base_version = base_version
            new_item.version = base_version + 1
            for k, v in meta.items():
                if hasattr(new_item, k):
                    setattr(new_item, k, v)
            self._persist(new_item)
            return True, new_item

    async def list_items(
        self, type: str | None = None, status: ItemStatus | None = None
    ) -> list[BlackboardItem]:
        return await asyncio.to_thread(self._safe_list, type, status)

    def _safe_list(
        self, type: str | None, status: ItemStatus | None
    ) -> list[BlackboardItem]:
        with self._lock:
            cur = self._conn.execute("SELECT payload FROM blackboard")
            rows = cur.fetchall()
        items = [_row_to_item(r) for r in rows]
        items = [i for i in items if not i.expired]
        if type is not None:
            items = [i for i in items if i.type == type]
        if status is not None:
            items = [i for i in items if i.status == status]
        return items

    async def get_conflicts(self) -> list[ConflictSet]:
        # Conflicts are derived by scanning authoritative items of same type.
        items = await self.list_items()
        conflicts: dict[str, ConflictSet] = {}
        for item in items:
            if item.kind != WriteKind.AUTHORITATIVE:
                continue
            for other in items:
                if other.id == item.id or other.type != item.type:
                    continue
                if other.kind == WriteKind.AUTHORITATIVE and other.content != item.content:
                    cs = conflicts.setdefault(item.type, ConflictSet(key=item.type))
                    for iid in (item.id, other.id):
                        if iid not in cs.item_ids:
                            cs.item_ids.append(iid)
        return list(conflicts.values())

    def close(self) -> None:
        self._conn.close()
