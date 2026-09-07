"""Human-in-the-loop review queue.

When the deterministic gate isolates a delivery (or a workflow step fails local
self-healing), the item is submitted here. A human resolves it with one of three
decisions (confirm / correct / exempt). Resolutions are recorded for audit and
can be harvested into a knowledge base (G-section: 人工兜底沉淀为 KB).

This implementation is an in-memory queue sufficient for single-process agents.
For multi-process production, back it with the same store as SharedStateStore.
"""

from __future__ import annotations

import asyncio
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


@dataclass
class ReviewResolution:
    """Record of how a review item was resolved."""

    item_id: str
    decision: ReviewDecision
    resolved_by: str | None
    reason: str | None
    corrected_content: str | None
    at: float


class ReviewQueue:
    """Simple in-memory review queue with deterministic resolution."""

    def __init__(self) -> None:
        self._items: dict[str, ReviewItem] = {}
        self._resolutions: dict[str, ReviewResolution] = {}
        self._lock = asyncio.Lock()

    def submit(self, item: ReviewItem) -> str:
        """Submit an item; returns its id."""
        self._items[item.item_id] = item
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
    ) -> ReviewResolution:
        """Resolve an item. ``actor`` identifies the resolver (audit)."""
        async with self._lock:
            item = self._items.get(item_id)
            if item is None:
                raise KeyError(f"Review item not found: {item_id}")
            if item.resolved:
                raise ValueError(f"Review item already resolved: {item_id}")
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
            logger.info("ReviewQueue resolved %s -> %s by %s", item_id, decision.value, actor)
            return resolution

    def pending(self) -> list[ReviewItem]:
        """List unresolved items."""
        return [i for i in self._items.values() if not i.resolved]

    def get(self, item_id: str) -> ReviewItem | None:
        return self._items.get(item_id)

    def resolution(self, item_id: str) -> ReviewResolution | None:
        return self._resolutions.get(item_id)
