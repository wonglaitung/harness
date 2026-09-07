"""Retry policy + with_retry helper tests (deterministic)."""

from __future__ import annotations

import pytest

from harness.gate.models import Backoff, RetryPolicy
from harness.gate.retry import with_retry


def test_should_retry_bounds() -> None:
    p = RetryPolicy(max_retries=2)
    assert p.should_retry(0, RuntimeError("x")) is True
    assert p.should_retry(1, RuntimeError("x")) is True
    assert p.should_retry(2, RuntimeError("x")) is False


def test_non_retryable_error_short_circuits() -> None:
    p = RetryPolicy(max_retries=5, retryable_errors=(ValueError,))
    assert p.should_retry(0, TypeError("x")) is False


def test_delay_within_cap() -> None:
    p = RetryPolicy(max_retries=10, backoff=Backoff.EXPONENTIAL, backoff_base=1.0, backoff_cap=30.0)
    for attempt in range(6):
        assert 0 < p.delay_for(attempt) <= 30.0


async def test_with_retry_succeeds_after_failures() -> None:
    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = await with_retry(RetryPolicy(max_retries=3), flaky, error_label="test")
    assert result == "ok"
    assert calls["n"] == 3


async def test_with_retry_exhausts_and_raises() -> None:
    async def always_fail() -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await with_retry(RetryPolicy(max_retries=2), always_fail)
