"""Tests for GoalLoop.stream() — Phase 2 streaming goal execution."""

from __future__ import annotations

from unittest.mock import MagicMock

from harness.loop import GoalConfig, GoalLoop, GoalStatus, VerificationMethod
from harness.types import LoopResult, LoopState, Session, StreamEvent


def _make_result(content: str = "done", iterations: int = 1) -> LoopResult:
    r = LoopResult(
        status=LoopState.COMPLETED,
        session=Session(id="s"),
        iterations=iterations,
        final_response=content,
    )
    r.token_usage = MagicMock(input_tokens=50, output_tokens=20)
    return r


class _MockAgent:
    def __init__(self, responses: list[LoopResult] | None = None):
        self.responses = responses or [_make_result()]
        self._call = 0
        self._loop = _MockLoop()
        self.config = type("C", (), {"get_context_window": lambda s: 200_000})()
        self._llm = None

    async def run(self, prompt: str, session_id: str | None = None, **kw) -> LoopResult:
        r = self.responses[min(self._call, len(self.responses) - 1)]
        self._call += 1
        return r

    async def stream(self, prompt: str, session_id: str | None = None, **kw):
        r = self.responses[min(self._call, len(self.responses) - 1)]
        self._call += 1
        self._loop._stream_result = r
        yield StreamEvent(type="text", text=r.final_response or "")

    def get_session(self, sid: str) -> Session | None:
        return Session(id=sid, messages=[])


class _MockLoop:
    def __init__(self):
        self._stream_result = None


def _cfg(**kw) -> GoalConfig:
    defaults = {
        "description": "g",
        "max_iterations": 10,
        "verification_method": VerificationMethod.CUSTOM,
        "custom_verifier": lambda r: True,
    }
    defaults.update(kw)
    return GoalConfig(**defaults)


# ── Basic streaming ──────────────────────────────────────────────────────────


async def test_stream_yields_text_and_goal_done():
    agent = _MockAgent([_make_result("output text")])
    loop = GoalLoop(agent=agent, config=_cfg())

    events = [e async for e in loop.stream()]
    types = [e.type for e in events]
    assert "text" in types
    assert "goal_done" in types

    done = [e for e in events if e.type == "goal_done"][0]
    assert done.goal_result is not None
    assert done.goal_result.status == GoalStatus.ACHIEVED


async def test_stream_carries_text_content():
    agent = _MockAgent([_make_result("hello world")])
    loop = GoalLoop(agent=agent, config=_cfg())

    events = [e async for e in loop.stream()]
    text_events = [e for e in events if e.type == "text"]
    assert any("hello world" in e.text for e in text_events)


# ── Iteration tracking ───────────────────────────────────────────────────────


async def test_stream_yields_goal_iteration():
    agent = _MockAgent([_make_result("r1"), _make_result("r2", 2)])
    loop = GoalLoop(agent=agent, config=_cfg())

    events = [e async for e in loop.stream()]
    iters = [e for e in events if e.type == "goal_iteration"]
    assert len(iters) >= 1
    assert iters[0].iteration >= 1


# ── Verification ─────────────────────────────────────────────────────────────


async def test_stream_yields_goal_verification():
    agent = _MockAgent([_make_result("done")])
    loop = GoalLoop(agent=agent, config=_cfg())

    events = [e async for e in loop.stream()]
    verifs = [e for e in events if e.type == "goal_verification"]
    assert len(verifs) >= 1
    assert verifs[0].achieved is True


# ── Max iterations ───────────────────────────────────────────────────────────


async def test_stream_max_iterations():
    agent = _MockAgent([_make_result(f"iter {i}") for i in range(20)])

    def never_pass(r):
        return False

    loop = GoalLoop(
        agent=agent,
        config=_cfg(max_iterations=3, custom_verifier=never_pass),
    )

    events = [e async for e in loop.stream()]
    done = [e for e in events if e.type == "goal_done"]
    assert len(done) == 1
    assert done[0].goal_result.status == GoalStatus.MAX_ITERATIONS


# ── Error handling ───────────────────────────────────────────────────────────


async def test_stream_exception_yields_goal_done_error():
    class _FailAgent(_MockAgent):
        async def stream(self, **kw):
            raise RuntimeError("boom")
            yield  # make it a generator

    agent = _FailAgent()
    loop = GoalLoop(agent=agent, config=_cfg())

    events = [e async for e in loop.stream()]
    done = [e for e in events if e.type == "goal_done"]
    assert done[0].goal_result.status == GoalStatus.ERROR
    assert "boom" in done[0].goal_result.error


# ── _stream_result accessible ────────────────────────────────────────────────


async def test_stream_result_available_after_iteration():
    agent = _MockAgent([_make_result("final")])
    loop = GoalLoop(agent=agent, config=_cfg())

    _ = [e async for e in loop.stream()]
    assert loop._stream_result is not None
    assert loop._stream_result.status == GoalStatus.ACHIEVED


# ── Multi-iteration streaming ────────────────────────────────────────────────


async def test_stream_multi_iteration():
    """Goal achieved on 3rd iteration: text events from all iterations."""
    call = 0

    def verifier(r):
        nonlocal call
        call += 1
        return call >= 3

    agent = _MockAgent([
        _make_result("attempt 1"),
        _make_result("attempt 2"),
        _make_result("attempt 3 done"),
    ])
    loop = GoalLoop(
        agent=agent,
        config=_cfg(max_iterations=10, custom_verifier=verifier),
    )

    events = [e async for e in loop.stream()]
    text_events = [e for e in events if e.type == "text"]
    assert len(text_events) >= 3
    assert "attempt 3 done" in text_events[-1].text

    done = [e for e in events if e.type == "goal_done"][0]
    assert done.goal_result.total_iterations >= 2
