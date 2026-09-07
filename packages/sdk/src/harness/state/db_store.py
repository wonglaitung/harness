"""Database-backed shared-state backend (production, optional extra).

Requires the optional dependency ``aiosqlite`` (pinned as an extra). For Postgres
use the same schema via an async SQLAlchemy engine — this implementation uses
aiosqlite (file or :memory:) as the portable default and can be pointed at a
URL through an async driver. Multi-process production deployments swap in a
real RDBMS. Conflicts/versioning semantics mirror the other backends.
"""

from __future__ import annotations

import json
import threading
from typing import Any

from harness.state.base import (
    BlackboardItem,
    ConflictSet,
    ItemStatus,
    StateBackend,
    WriteKind,
)


def _require_aiosqlite() -> Any:
    try:
        import aiosqlite  # type: ignore
    except ImportError as e:  # pragma: no cover - optional dep
        raise ImportError(
            "DBBackend requires the 'aiosqlite' package. Install with: "
            "pip install 'harness-sdk[db]'"
        ) from e
    return aiosqlite


class DBBackend(StateBackend):
    """Async SQLite backend (swap the connect URL for Postgres in production)."""

    def __init__(self, path: str = ".harness/state.db") -> None:
        self._path = path
        self._lock = threading.Lock()
        self._conn: Any = None

    async def _ensure(self) -> Any:
        aiosqlite = _require_aiosqlite()
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._path)
            await self._conn.execute(
                "CREATE TABLE IF NOT EXISTS blackboard (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            await self._conn.commit()
        return self._conn

    @staticmethod
    def _row_to_item(row: tuple[Any, ...]) -> BlackboardItem:
        data = json.loads(row[0])
        data["status"] = ItemStatus(data.get("status", "proposed"))
        data["kind"] = WriteKind(data.get("kind", "additive"))
        return BlackboardItem(**data)

    async def put(self, item: BlackboardItem) -> BlackboardItem:
        db = await self._ensure()
        with self._lock:
            await db.execute(
                "INSERT OR REPLACE INTO blackboard (id, payload) VALUES (?, ?)",
                (item.id, json.dumps(item.__dict__)),
            )
            await db.commit()
        return item

    async def get(self, item_id: str) -> BlackboardItem | None:
        db = await self._ensure()
        with self._lock:
            cur = await db.execute("SELECT payload FROM blackboard WHERE id=?", (item_id,))
            row = await cur.fetchone()
        if row is None:
            return None
        return self._row_to_item(row)

    async def write_if_version(
        self, item_id: str, content: Any, base_version: int, **meta: Any
    ) -> tuple[bool, BlackboardItem | None]:
        db = await self._ensure()
        with self._lock:
            cur = await db.execute("SELECT payload FROM blackboard WHERE id=?", (item_id,))
            row = await cur.fetchone()
            cur_item = self._row_to_item(row) if row else None
            if cur_item is not None and cur_item.version != base_version:
                return False, cur_item
            new_item = cur_item or BlackboardItem(id=item_id)
            new_item.content = content
            new_item.base_version = base_version
            new_item.version = base_version + 1
            for k, v in meta.items():
                if hasattr(new_item, k):
                    setattr(new_item, k, v)
            await db.execute(
                "INSERT OR REPLACE INTO blackboard (id, payload) VALUES (?, ?)",
                (item_id, json.dumps(new_item.__dict__)),
            )
            await db.commit()
        return True, new_item

    async def list_items(
        self, type: str | None = None, status: ItemStatus | None = None
    ) -> list[BlackboardItem]:
        db = await self._ensure()
        with self._lock:
            cur = await db.execute("SELECT payload FROM blackboard")
            rows = await cur.fetchall()
        items = [self._row_to_item(r) for r in rows]
        if type is not None:
            items = [i for i in items if i.type == type]
        if status is not None:
            items = [i for i in items if i.status == status]
        return items

    async def get_conflicts(self) -> list[ConflictSet]:
        items = [i for i in await self.list_items() if i.kind == WriteKind.AUTHORITATIVE]
        conflicts: dict[str, ConflictSet] = {}
        for item in items:
            for other in items:
                if other.id == item.id or other.type != item.type:
                    continue
                if other.content != item.content:
                    cs = conflicts.setdefault(item.type, ConflictSet(key=item.type))
                    for iid in (item.id, other.id):
                        if iid not in cs.item_ids:
                            cs.item_ids.append(iid)
        return list(conflicts.values())
