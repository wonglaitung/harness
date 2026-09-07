"""Redis-backed shared-state backend (production, optional extra).

Requires the optional dependency ``redis`` (pinned as an extra, not a core dep).
Importing/selecting this backend without the driver installed raises a clear
error. Use for multi-process / distributed multi-agent coordination.
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


def _require_redis() -> Any:
    try:
        import redis.asyncio as redis  # type: ignore
    except ImportError as e:  # pragma: no cover - optional dep
        raise ImportError(
            "RedisBackend requires the 'redis' package. Install with: "
            "pip install 'harness-sdk[redis]'"
        ) from e
    return redis


class RedisBackend(StateBackend):
    """Redis hash-backed backend (single key per item)."""

    def __init__(self, url: str = "redis://localhost:6379/0", prefix: str = "harness:bb:") -> None:
        redis = _require_redis()
        self._redis = redis.from_url(url, decode_responses=True)
        self._prefix = prefix

    def _key(self, item_id: str) -> str:
        return f"{self._prefix}{item_id}"

    async def put(self, item: BlackboardItem) -> BlackboardItem:
        import json

        await self._redis.hset(self._key(item.id), mapping={"v": json.dumps(item.__dict__)})
        return item

    async def get(self, item_id: str) -> BlackboardItem | None:
        import json

        raw = await self._redis.hget(self._key(item_id), "v")
        if raw is None:
            return None
        return BlackboardItem(**json.loads(raw))

    async def write_if_version(
        self, item_id: str, content: Any, base_version: int, **meta: Any
    ) -> tuple[bool, BlackboardItem | None]:
        import json

        cur = await self.get(item_id)
        if cur is not None and cur.version != base_version:
            return False, cur
        new_item = cur or BlackboardItem(id=item_id)
        new_item.content = content
        new_item.base_version = base_version
        new_item.version = base_version + 1
        for k, v in meta.items():
            if hasattr(new_item, k):
                setattr(new_item, k, v)
        await self._redis.hset(self._key(item_id), mapping={"v": json.dumps(new_item.__dict__)})
        return True, new_item

    async def list_items(
        self, type: str | None = None, status: ItemStatus | None = None
    ) -> list[BlackboardItem]:
        keys = [k async for k in self._redis.scan_iter(match=f"{self._prefix}*")]
        items = [i for k in keys if (i := await self.get(k.split(self._prefix)[-1]))]
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
