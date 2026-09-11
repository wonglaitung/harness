"""File-backed shared-state backend (worktree / dev) via SQLite.

Synchronous sqlite3 under a threading lock; async methods wrap the sync core.
No external dependency (sqlite3 is stdlib). Uses the rollback journal (not WAL)
so that cross-process readers always observe the latest committed state — WAL
caches a read-mark that only advances on checkpoint, which broke the
compare-and-swap under contention. Suitable for single-process dev and
multi-process (ProcessPoolExecutor) shared-state / review runs.
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
    data = json.loads(str(row[0]))
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
        # Autocommit: we manage transactions explicitly (BEGIN IMMEDIATE) so the
        # read-modify-write in write_if_version is a single serialized unit.
        self._conn.isolation_level = None
        # Multi-process safety: we deliberately use the rollback journal (NOT WAL).
        # WAL caches a read-mark in the -shm that only advances on checkpoint, so
        # readers (incl. a caller's get() before the CAS) can see a stale snapshot
        # and the conditional UPDATE matches a phantom version -> lost update across
        # processes. The rollback journal updates the main db file on COMMIT, so every
        # reader sees the latest committed state immediately. busy_timeout retries
        # instead of raising "database is locked" when ProcessPoolExecutor workers
        # share the same state/review file.
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blackboard (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )

    def _serialize(self, item: BlackboardItem) -> str:
        return json.dumps(item.as_dict() | {"content": item.content})

    def _persist(self, item: BlackboardItem) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO blackboard (id, payload) VALUES (?, ?)",
            (item.id, self._serialize(item)),
        )
        self._conn.commit()

    def _load(self, item_id: str) -> BlackboardItem | None:
        with self._lock:
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
            # BEGIN IMMEDIATE takes the exclusive write lock up front so the whole
            # read-modify-write is serialized across processes. We RE-READ the current
            # version INSIDE this transaction and compare it to base_version: a stale
            # caller-side get() (rollback journal has no read-mark caching) cannot slip
            # a phantom version past the conditional UPDATE. busy_timeout makes
            # contending workers queue instead of raising "database is locked".
            # NOTE: the fetched payload is materialized to a real str immediately,
            # because the sqlite3 row buffer is reused/clobbered on later access.
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    "SELECT payload FROM blackboard WHERE id=?", (item_id,)
                ).fetchone()
                cur = _row_to_item(row) if row is not None else None
                if cur is not None and cur.version != base_version:
                    self._conn.execute("ROLLBACK")
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
                    self._conn.execute(
                        "INSERT INTO blackboard (id, payload) VALUES (?, ?)",
                        (item_id, payload),
                    )
                else:
                    self._conn.execute(
                        "UPDATE blackboard SET payload=? "
                        "WHERE id=? AND json_extract(payload,'$.version')=?",
                        (payload, item_id, base_version),
                    )
                self._conn.execute("COMMIT")
                return True, new_item
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

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

    async def aclose(self) -> None:
        """Close the SQLite connection (async lifecycle counterpart of close)."""
        await asyncio.to_thread(self.close)

    def close(self) -> None:
        self._conn.close()
