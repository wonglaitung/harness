"""Human-in-the-loop review queue tests."""

from __future__ import annotations

import pytest

from harness.review import ReviewDecision, ReviewItem, ReviewQueue


async def test_submit_pending_resolve() -> None:
    q = ReviewQueue()
    item = ReviewItem(gate_findings=[{"id": "fact:no-source"}], content="x")
    item_id = q.submit(item)
    assert len(q.pending()) == 1

    resolution = await q.resolve(item_id, ReviewDecision.CONFIRM, actor="reviewer")
    assert resolution.decision == ReviewDecision.CONFIRM
    assert q.get(item_id).resolved is True
    assert len(q.pending()) == 0
    assert q.resolution(item_id) is not None


async def test_resolve_missing_raises() -> None:
    q = ReviewQueue()
    with pytest.raises(KeyError):
        await q.resolve("nope", ReviewDecision.EXEMPT)


async def test_double_resolve_raises() -> None:
    q = ReviewQueue()
    iid = q.submit(ReviewItem(content="y"))
    await q.resolve(iid, ReviewDecision.CORRECT, corrected_content="fixed")
    with pytest.raises(ValueError):
        await q.resolve(iid, ReviewDecision.EXEMPT)
