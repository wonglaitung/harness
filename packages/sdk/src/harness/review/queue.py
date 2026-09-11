"""Human-in-the-loop review queue.

When the deterministic gate isolates a delivery (or a workflow step fails local
self-healing), the item is submitted here. A human resolves it with one of three
decisions (confirm / correct / exempt). Resolutions are recorded for audit and
can be harvested into a knowledge base (G-section: 人工兜底沉淀为 KB).

In-memory by default (single-process agents). Pass ``store=`` (a
:class:`~harness.state.SharedStateStore`) to make the queue durable and
cross-process: items are persisted synchronously (safe even when the gate calls
``submit`` from within a running event loop, via a thread-backed ``asyncio.run``)
so review items survive worker-process death — required for multi-process ingest
(e.g. ProcessPoolExecutor workers).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ReviewDecision(Enum):
    """Resolution a human can apply to a review item."""

    CONFIRM = "confirm"  # 确认隔离项可交付
    CORRECT = "correct"  # 修正后交付（附 corrected_content）
    EXEMPT = "exempt"  # 豁免（记录理由，后续审计）


@dataclass
class ReviewItem:
    """An item awaiting human resolution."""

    gate_findings: list[dict[str, Any]] = field(default_factory=list)
    content: str = ""
    source: str = "unknown"
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    decision: ReviewDecision | None = None
    resolved_by: str | None = None
    corrected_content: str | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "gate_findings": self.gate_findings,
            "content": self.content,
            "source": self.source,
            "created_at": self.created_at,
            "resolved": self.resolved,
            "decision": self.decision.value if self.decision is not None else None,
            "resolved_by": self.resolved_by,
            "corrected_content": self.corrected_content,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReviewItem:
        return cls(
            item_id=d.get("item_id", ""),
            gate_findings=d.get("gate_findings", []),
            content=d.get("content", ""),
            source=d.get("source", "unknown"),
            created_at=d.get("created_at", 0.0),
            resolved=d.get("resolved", False),
            decision=ReviewDecision(d["decision"]) if d.get("decision") else None,
            resolved_by=d.get("resolved_by"),
            corrected_content=d.get("corrected_content"),
            reason=d.get("reason"),
        )


@dataclass
class ReviewResolution:
    """Record of how a review item was resolved."""

    item_id: str
    decision: ReviewDecision
    resolved_by: str | None
    reason: str | None
    corrected_content: str | None
    at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "decision": self.decision.value,
            "resolved_by": self.resolved_by,
            "reason": self.reason,
            "corrected_content": self.corrected_content,
            "at": self.at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReviewResolution:
        return cls(
            item_id=d["item_id"],
            decision=ReviewDecision(d["decision"]),
            resolved_by=d.get("resolved_by"),
            reason=d.get("reason"),
            corrected_content=d.get("corrected_content"),
            at=d.get("at", 0.0),
        )


class ReviewQueue:
    """Review queue — in-memory by default, optionally store-backed + durable.

    Args:
        store: Optional :class:`~harness.state.SharedStateStore`. When set, items
            and resolutions are persisted through it (synchronously) so they
            survive process death and are visible across processes that point at
            the same store/backend.
        namespace: store ``type`` used for review items (and ``<namespace>:res``
            for resolutions).
    """

    def __init__(self, store: Any | None = None, namespace: str = "review_queue") -> None:
        self._items: dict[str, ReviewItem] = {}
        self._resolutions: dict[str, ReviewResolution] = {}
        self._lock = asyncio.Lock()
        self._store = store
        self._namespace = namespace

    # -- sync bridge to the (async) store, safe from a running event loop ------
    @staticmethod
    def _run_async(coro: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        # Called from within a running loop (e.g. the gate inside run_goal):
        # run the coroutine in a separate thread with its own loop so it blocks
        # until durable without disturbing the caller's loop.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(lambda: asyncio.run(coro)).result()

    def _item_id(self, item_id: str) -> str:
        return f"{self._namespace}:{item_id}"

    def _res_id(self, item_id: str) -> str:
        return f"{self._namespace}:res:{item_id}"

    def _persist_item(self, item: ReviewItem) -> None:
        if self._store is None:
            return
        from harness.state.base import BlackboardItem, ItemStatus, WriteKind

        bi = BlackboardItem(
            id=self._item_id(item.item_id),
            type=self._namespace,
            content=item.as_dict(),
            source_agent="review_queue",
            kind=WriteKind.AUTHORITATIVE,
            status=ItemStatus.CONFIRMED,
        )
        self._run_async(self._store._backend.put(bi))

    def _persist_resolution(self, res: ReviewResolution) -> None:
        if self._store is None:
            return
        from harness.state.base import BlackboardItem, ItemStatus, WriteKind

        bi = BlackboardItem(
            id=self._res_id(res.item_id),
            type=f"{self._namespace}:resolution",
            content=res.as_dict(),
            source_agent="review_queue",
            kind=WriteKind.AUTHORITATIVE,
            status=ItemStatus.CONFIRMED,
        )
        self._run_async(self._store._backend.put(bi))

    def _load_item(self, item_id: str) -> ReviewItem | None:
        if self._store is None:
            return None
        bi = self._run_async(self._store._backend.get(self._item_id(item_id)))
        return ReviewItem.from_dict(bi.content) if bi is not None else None

    def _load_resolution(self, item_id: str) -> ReviewResolution | None:
        if self._store is None:
            return None
        bi = self._run_async(self._store._backend.get(self._res_id(item_id)))
        return ReviewResolution.from_dict(bi.content) if bi is not None else None

    # -- public API -----------------------------------------------------------
    def submit(self, item: ReviewItem) -> str:
        """Submit an item; returns its id. Persists when a store is attached."""
        self._items[item.item_id] = item
        self._persist_item(item)
        logger.info("ReviewQueue submitted item %s (source=%s)", item.item_id, item.source)
        return item.item_id

    async def resolve(
        self,
        item_id: str,
        decision: ReviewDecision,
        *,
        actor: str = "human",
        corrected_content: str | None = None,
        reason: str | None = None,
        allow_auto_resolve: bool = False,
    ) -> ReviewResolution:
        """Resolve an item. ``actor`` identifies the resolver (audit).

        G3 guard: automated/non-human sign-off must never silently release a
        critical isolation item. Items carrying ERROR-severity gate findings are
        treated as critical and can ONLY be resolved by a human (``actor="human"``).
        Non-critical items may be auto-resolved only when ``allow_auto_resolve=True``.
        """
        async with self._lock:
            item = self._items.get(item_id) or self._load_item(item_id)
            if item is None:
                raise KeyError(f"Review item not found: {item_id}")
            if item.resolved:
                raise ValueError(f"Review item already resolved: {item_id}")

            is_critical = any(
                f.get("severity") == "error" for f in (item.gate_findings or [])
            )
            if is_critical and actor != "human":
                raise PermissionError(
                    "Critical isolation items (ERROR-level gate findings) can only be "
                    "resolved by a human; automated sign-off is forbidden (G3)."
                )
            if not is_critical and actor != "human" and not allow_auto_resolve:
                raise PermissionError(
                    "Automated resolution of non-critical items requires "
                    "allow_auto_resolve=True."
                )

            item.resolved = True
            item.decision = decision
            item.resolved_by = actor
            item.corrected_content = corrected_content
            item.reason = reason
            resolution = ReviewResolution(
                item_id=item_id,
                decision=decision,
                resolved_by=actor,
                reason=reason,
                corrected_content=corrected_content,
                at=time.time(),
            )
            self._resolutions[item_id] = resolution
            self._persist_item(item)
            self._persist_resolution(resolution)
            logger.info("ReviewQueue resolved %s -> %s by %s", item_id, decision.value, actor)
            return resolution

    def pending(self) -> list[ReviewItem]:
        """List unresolved items (across processes when store-backed)."""
        items = dict(self._items)  # local overlay
        if self._store is not None:
            bis = self._run_async(self._store._backend.list_items(type=self._namespace))
            for bi in bis:
                try:
                    remote = ReviewItem.from_dict(bi.content)
                except Exception:  # noqa: BLE001 - skip malformed rows
                    continue
                items.setdefault(remote.item_id, remote)
        return [i for i in items.values() if not i.resolved]

    def get(self, item_id: str) -> ReviewItem | None:
        return self._items.get(item_id) or self._load_item(item_id)

    def resolution(self, item_id: str) -> ReviewResolution | None:
        return self._resolutions.get(item_id) or self._load_resolution(item_id)
