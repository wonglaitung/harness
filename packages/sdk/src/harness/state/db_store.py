"""Database-backed shared-state backend (production, optional extra).

Requires the optional dependency ``aiosqlite`` (pinned as an extra). For Postgres
use the same schema via an async SQLAlchemy engine — this implementation uses
aiosqlite (file or :memory:) as the portable default and can be pointed at a
URL through an async driver. Multi-process production deployments swap in a
real RDBMS. Conflicts/versioning semantics mirror the other backends.
"""

from __future__ import annotations

import asyncio
import json
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
        # asyncio.Lock (not threading.Lock): the methods await while holding it,
        # so a threading.Lock would deadlock the event loop under concurrency.
        self._lock = asyncio.Lock()
        self._conn: Any = None

    async def _ensure(self) -> Any:
        aiosqlite = _require_aiosqlite()
        if self._conn is None:
            # Autocommit: transactions are managed explicitly (BEGIN IMMEDIATE) so
            # write_if_version's read-modify-write is one serialized unit. Rollback
            # journal (not WAL): cross-process readers must see the latest committed
            # state, and WAL only advances its read-mark on checkpoint — which broke
            # the compare-and-swap under contention. busy_timeout queues contenders.
            # isolation_level must be passed to connect(): aiosqlite owns the
            # sqlite3 connection on its own worker thread, so assigning the
            # property from the event-loop thread raises
            # "SQLite objects created in a thread can only be used in that thread".
            self._conn = await aiosqlite.connect(self._path, isolation_level=None)
            await self._conn.execute("PRAGMA busy_timeout=5000")
            await self._conn.execute(
                "CREATE TABLE IF NOT EXISTS blackboard (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
        return self._conn

    @staticmethod
    def _serialize(item: BlackboardItem) -> str:
        return json.dumps(item.as_dict() | {"content": item.content})

    @staticmethod
    def _row_to_item(row: tuple[Any, ...]) -> BlackboardItem:
        data = json.loads(str(row[0]))
        # Rehydrate enums that were serialized as their string values.
        data["status"] = ItemStatus(data.get("status", "proposed"))
        data["kind"] = WriteKind(data.get("kind", "additive"))
        return BlackboardItem(**data)

    async def put(self, item: BlackboardItem) -> BlackboardItem:
        db = await self._ensure()
        async with self._lock:
            await db.execute(
                "INSERT OR REPLACE INTO blackboard (id, payload) VALUES (?, ?)",
                (item.id, self._serialize(item)),
            )
            await db.commit()
        return item

    async def get(self, item_id: str) -> BlackboardItem | None:
        db = await self._ensure()
        async with self._lock:
            cur = await db.execute("SELECT payload FROM blackboard WHERE id=?", (item_id,))
            row = await cur.fetchone()
        if row is None:
            return None
        return self._row_to_item(row)

    async def write_if_version(
        self, item_id: str, content: Any, base_version: int, **meta: Any
    ) -> tuple[bool, BlackboardItem | None]:
        await self._ensure()
        async with self._lock:
            # BEGIN IMMEDIATE takes the exclusive write lock up front so the whole
            # read-modify-write is serialized across processes. We RE-READ the current
            # version INSIDE this transaction and compare it to base_version: a stale
            # caller-side get() (rollback journal has no read-mark caching) cannot slip
            # a phantom version past the conditional UPDATE. busy_timeout makes
            # contending workers queue instead of raising "database is locked".
            # NOTE: the fetched payload is materialized to a real str immediately,
            # because the row buffer is reused/clobbered on later access.
            await self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = await (
                    await self._conn.execute(
                        "SELECT payload FROM blackboard WHERE id=?", (item_id,)
                    )
                ).fetchone()
                cur = self._row_to_item(row) if row is not None else None
                if cur is not None and cur.version != base_version:
                    await self._conn.execute("ROLLBACK")
                    return False, cur
                # Base the update on the current item so kind/status/writer_id
                # (and other fields) are preserved rather than reset to defaults.
                new_item = cur or BlackboardItem(id=item_id)
                new_item.content = content
                new_item.base_version = base_version
                new_item.version = base_version + 1
                for k, v in meta.items():
                    if hasattr(new_item, k):
                        setattr(new_item, k, v)
                payload = self._serialize(new_item)
                if cur is None:
                    await self._conn.execute(
                        "INSERT INTO blackboard (id, payload) VALUES (?, ?)",
                        (item_id, payload),
                    )
                else:
                    await self._conn.execute(
                        "UPDATE blackboard SET payload=? "
                        "WHERE id=? AND json_extract(payload,'$.version')=?",
                        (payload, item_id, base_version),
                    )
                await self._conn.execute("COMMIT")
                return True, new_item
            except Exception:
                await self._conn.execute("ROLLBACK")
                raise

    async def list_items(
        self, type: str | None = None, status: ItemStatus | None = None
    ) -> list[BlackboardItem]:
        db = await self._ensure()
        async with self._lock:
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

    async def aclose(self) -> None:
        """Close the aiosqlite connection and stop its worker thread.

        Must be awaited before the event loop shuts down, otherwise aiosqlite's
        background thread may call back into a closed loop
        ("Event loop is closed").
        """
        conn, self._conn = self._conn, None
        if conn is not None:
            await conn.close()
