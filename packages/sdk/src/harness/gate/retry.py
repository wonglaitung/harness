"""Retry policy (already defined in models.py) — convenience re-export + helpers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from harness.gate.models import Backoff, RetryPolicy

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retry(
    policy: RetryPolicy,
    fn: Callable[[], Awaitable[T]],
    *,
    error_label: str = "operation",
    on_retry: Callable[[int, Exception, float], Any] | None = None,
) -> T:
    """Run an async ``fn`` under a deterministic :class:`RetryPolicy`.

    Retries up to ``max_retries`` with the configured backoff. Non-retryable
    errors or exhaustion re-raise the last error. This is the local
    self-healing primitive; escalation (terminate/downgrade/review) is the
    caller's responsibility after exhaustion.
    """
    last_err: Exception | None = None
    for attempt in range(policy.max_retries + 1):
        try:
            return await fn()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if not policy.should_retry(attempt, e):
                break
            delay = policy.delay_for(attempt)
            logger.warning(
                "%s failed (attempt %d): %s — retrying in %.1fs",
                error_label,
                attempt + 1,
                e,
                delay,
            )
            if on_retry:
                on_retry(attempt, e, delay)
            await asyncio.sleep(delay)
    assert last_err is not None
    raise last_err


__all__ = ["Backoff", "RetryPolicy", "with_retry"]
