"""Wiring / strict-propagation tests (no heavy AgentHarness construction).

Validates that governance layer is OFF by default (zero migration) and turns on
with strict=True, and that HARNESS_REQUIRE_STRICT fails fast when off.
"""

from __future__ import annotations

import pytest

from harness.sdk.config import HarnessConfig
from harness.sdk.harness import AgentHarness


class _Probe:
    """Expose governance-build methods without running AgentHarness.__init__."""

    def __init__(self, cfg: HarnessConfig) -> None:
        self.config = cfg
        self._review_queue = None

    _build_gate = AgentHarness._build_gate
    _build_state_store = AgentHarness._build_state_store
    _build_review_queue = AgentHarness._build_review_queue
    _require_strict_if_env = AgentHarness._require_strict_if_env


def test_default_off_is_zero_migration() -> None:
    c = HarnessConfig()
    assert c.strict is False
    assert c.gate is None and c.state is None and c.review is None
    p = _Probe(c)
    assert p._build_gate() is None
    assert p._build_state_store() is None
    assert p._build_review_queue() is None


def test_strict_builds_governance() -> None:
    c = HarnessConfig(strict=True)
    p = _Probe(c)
    assert p._build_gate() is not None
    assert p._build_state_store() is not None
    assert p._build_review_queue() is not None


def test_require_strict_env_fails_when_off(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_REQUIRE_STRICT", "1")
    try:
        p = _Probe(HarnessConfig(strict=False))
        with pytest.raises(RuntimeError):
            p._require_strict_if_env()
    finally:
        monkeypatch.delenv("HARNESS_REQUIRE_STRICT", raising=False)


def test_require_strict_env_ok_when_on(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_REQUIRE_STRICT", "1")
    try:
        p = _Probe(HarnessConfig(strict=True))
        p._require_strict_if_env()  # should not raise
    finally:
        monkeypatch.delenv("HARNESS_REQUIRE_STRICT", raising=False)
