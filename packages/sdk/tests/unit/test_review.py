"""Human-in-the-loop review queue tests."""

from __future__ import annotations

import pytest

from harness.review import ReviewDecision, ReviewItem, ReviewQueue


async def test_submit_pending_resolve() -> None:
    q = ReviewQueue()
    item = ReviewItem(gate_findings=[{"id": "fact:no-source"}], content="x")
    item_id = q.submit(item)
    assert len(q.pending()) == 1

    resolution = await q.resolve(item_id, ReviewDecision.CONFIRM, actor="human")
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


async def test_critical_item_requires_human() -> None:
    q = ReviewQueue()
    iid = q.submit(
        ReviewItem(
            gate_findings=[{"id": "fact:no-source", "severity": "error"}],
            content="2024年Q1营收3.2亿元",
        )
    )
    # Human resolution is allowed.
    res = await q.resolve(iid, ReviewDecision.CONFIRM, actor="human")
    assert res.decision == ReviewDecision.CONFIRM


async def test_critical_item_blocks_automated_signoff() -> None:
    q = ReviewQueue()
    iid = q.submit(
        ReviewItem(
            gate_findings=[{"id": "fact:no-source", "severity": "error"}],
            content="2024年Q1营收3.2亿元",
        )
    )
    # Non-human actor must NOT be able to release a critical isolation item.
    with pytest.raises(PermissionError):
        await q.resolve(iid, ReviewDecision.EXEMPT, actor="system")
    # Even with the explicit flag, critical items stay human-only.
    with pytest.raises(PermissionError):
        await q.resolve(
            iid, ReviewDecision.EXEMPT, actor="system", allow_auto_resolve=True
        )


async def test_non_critical_auto_resolve_guarded() -> None:
    q = ReviewQueue()
    iid = q.submit(ReviewItem(content="minor note"))
    # Non-critical but non-human without opt-in -> blocked.
    with pytest.raises(PermissionError):
        await q.resolve(iid, ReviewDecision.EXEMPT, actor="system")
    # With explicit opt-in, non-critical automation is permitted.
    res = await q.resolve(
        iid, ReviewDecision.EXEMPT, actor="system", allow_auto_resolve=True
    )
    assert res.decision == ReviewDecision.EXEMPT
