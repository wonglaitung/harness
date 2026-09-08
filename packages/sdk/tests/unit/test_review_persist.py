"""Unit tests for ReviewQueue persistence bridge.

Covers backward-compatible in-memory behaviour, file-backed cross-process
durability, and the synchronous bridge working from inside a running event loop
(the path the deterministic gate uses when it calls submit synchronously).
"""

from __future__ import annotations

import asyncio

from harness.review import ReviewDecision, ReviewItem, ReviewQueue
from harness.state import create_state_store


def test_in_memory_backward_compatible() -> None:
    q = ReviewQueue()
    item = q.submit(ReviewItem(content="c", source="s"))
    assert len(q.pending()) == 1
    assert q.get(item) is not None
    res = asyncio.run(q.resolve(item, ReviewDecision.CONFIRM, actor="u"))
    assert res.decision is ReviewDecision.CONFIRM
    assert q.resolution(item) is not None
    assert len(q.pending()) == 0


def test_file_cross_process(tmp_path) -> None:
    db = str(tmp_path / "review.db")
    store = create_state_store("file", path=db)
    q1 = ReviewQueue(store=store)
    item = q1.submit(ReviewItem(content="spec", source="submit_spec"))
    assert len(q1.pending()) == 1

    # Simulated second process: new queue over the same file.
    reopened = ReviewQueue(store=create_state_store("file", path=db))
    assert len(reopened.pending()) == 1
    # Resolve in the second process; first process observes it.
    asyncio.run(reopened.resolve(item, ReviewDecision.EXEMPT, actor="rev", reason="ok"))
    assert reopened.resolution(item).decision is ReviewDecision.EXEMPT
    assert len(reopened.pending()) == 0
    assert q1.resolution(item).decision is ReviewDecision.EXEMPT


def test_submit_under_running_loop_persists(tmp_path) -> None:
    db = str(tmp_path / "review.db")
    q = ReviewQueue(store=create_state_store("file", path=db))

    async def _drive() -> str:
        # gate.check calls review_queue.submit synchronously from a running loop
        item_id = q.submit(ReviewItem(content="x", source="gate"))
        return item_id

    item_id = asyncio.run(_drive())

    reopened = ReviewQueue(store=create_state_store("file", path=db))
    assert len(reopened.pending()) == 1
    assert reopened.get(item_id) is not None
