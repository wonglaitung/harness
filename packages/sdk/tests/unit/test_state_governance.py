"""Shared-state governance tests (H3): authoritative write authorization.

These deliberately avoid the module-level ``aiosqlite`` importorskip in
``test_state.py`` so the memory/file backends are always exercised — including
the CAS path that previously bypassed the write verifier.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.state import BlackboardItem, ItemStatus, WriteKind, create_state_store
from harness.state.file_store import FileBackend

_ALLOWED = {"harness", "review_queue"}


def _write_verifier(item: BlackboardItem) -> bool:
    return (
        item.effective_writer in _ALLOWED
        and item.kind == WriteKind.AUTHORITATIVE
        and item.status == ItemStatus.CONFIRMED
    )


async def test_write_if_version_enforces_authoritative_verifier() -> None:
    """Gap 2: CAS must not be a bypass around the authoritative write verifier."""
    store = create_state_store("memory", verifier=_write_verifier)
    item = await store.put_authoritative(
        "decision", "v1", source_agent="planner", writer_id="harness"
    )
    assert item.version == 1 and item.source_agent == "planner"

    # Unauthorized channel cannot CAS an authoritative item...
    with pytest.raises(PermissionError):
        await store.write_if_version(item.id, "v2", base_version=1, writer_id="rogue")
    # ...nor create a new authoritative item via CAS.
    with pytest.raises(PermissionError):
        await store.write_if_version(
            "new",
            "x",
            base_version=0,
            kind=WriteKind.AUTHORITATIVE,
            status=ItemStatus.CONFIRMED,
            writer_id="rogue",
        )
    # Authorized control channel succeeds and preserves kind/writer.
    ok, updated = await store.write_if_version(
        item.id, "v2", base_version=1, writer_id="harness"
    )
    assert ok is True
    assert updated is not None
    assert updated.kind == WriteKind.AUTHORITATIVE
    assert updated.effective_writer == "harness"


async def test_write_if_version_allows_additive_without_verifier() -> None:
    """Additive CAS updates are unrestricted (observations/proposals)."""
    store = create_state_store("memory", verifier=_write_verifier)
    add = await store.put_additive("obs", "v1", source_agent="agent1")
    ok, updated = await store.write_if_version(add.id, "v2", base_version=1)
    assert ok is True and updated is not None and updated.content == "v2"


async def test_file_backend_cas_preserves_kind_and_writer(tmp_path: Path) -> None:
    """The CAS path must not reset kind/status/writer_id to defaults."""
    backend = FileBackend(str(tmp_path / "state.db"))
    await backend.put(
        BlackboardItem(
            id="k",
            type="decision",
            content="v1",
            source_agent="planner",
            writer_id="harness",
            kind=WriteKind.AUTHORITATIVE,
            status=ItemStatus.CONFIRMED,
        )
    )
    ok, updated = await backend.write_if_version("k", "v2", base_version=1)
    assert ok is True
    assert updated is not None
    assert updated.kind == WriteKind.AUTHORITATIVE
    assert updated.status == ItemStatus.CONFIRMED
    assert updated.writer_id == "harness"

    reloaded_backend = FileBackend(str(tmp_path / "state.db"))
    reloaded = await reloaded_backend.get("k")
    assert reloaded is not None
    assert reloaded.kind == WriteKind.AUTHORITATIVE
    assert reloaded.effective_writer == "harness"

    await backend.aclose()
    await reloaded_backend.aclose()


async def test_file_backend_cas_enforces_verifier(tmp_path: Path) -> None:
    """CAS on a file backend goes through the same control-layer verifier."""
    store = create_state_store(
        "file", path=str(tmp_path / "state.db"), verifier=_write_verifier
    )
    item = await store.put_authoritative(
        "decision", "v1", source_agent="planner", writer_id="harness"
    )
    with pytest.raises(PermissionError):
        await store.write_if_version(item.id, "v2", base_version=1, writer_id="rogue")
    ok, _ = await store.write_if_version(
        item.id, "v2", base_version=1, writer_id="harness"
    )
    assert ok is True
    await store.aclose()


async def test_db_backend_cas_preserves_kind_and_writer(tmp_path: Path) -> None:
    """DB backend CAS must preserve kind/status/writer_id and enforce the verifier."""
    pytest.importorskip("aiosqlite")
    store = create_state_store(
        "db", path=str(tmp_path / "state.db"), verifier=_write_verifier
    )
    item = await store.put_authoritative(
        "decision", "v1", source_agent="planner", writer_id="harness"
    )
    # Unauthorized channel rejected.
    with pytest.raises(PermissionError):
        await store.write_if_version(item.id, "v2", base_version=1, writer_id="rogue")
    # Authorized CAS succeeds and preserves governance fields.
    ok, updated = await store.write_if_version(
        item.id, "v2", base_version=1, writer_id="harness"
    )
    assert ok is True
    assert updated is not None
    assert updated.kind == WriteKind.AUTHORITATIVE
    assert updated.status == ItemStatus.CONFIRMED
    assert updated.effective_writer == "harness"
    await store.aclose()


@pytest.mark.redis
async def test_redis_write_if_version_enforces_verifier() -> None:
    """Redis backend CAS goes through the control-layer verifier (H3)."""
    pytest.importorskip("redis")
    import uuid

    url = "redis://localhost:6379/13"
    store = None
    try:
        store = create_state_store("redis", url=url, verifier=_write_verifier)
        item = await store.put_authoritative(
            f"decision:{uuid.uuid4().hex}",
            "v1",
            source_agent="planner",
            writer_id="harness",
        )
        with pytest.raises(PermissionError):
            await store.write_if_version(item.id, "v2", base_version=1, writer_id="rogue")
        ok, updated = await store.write_if_version(
            item.id, "v2", base_version=1, writer_id="harness"
        )
        assert ok is True
        assert updated is not None
        assert updated.kind == WriteKind.AUTHORITATIVE
        assert updated.effective_writer == "harness"
    except PermissionError:
        raise
    except Exception as e:  # redis not reachable in this environment
        pytest.skip(f"Redis unavailable: {e}")
    finally:
        if store is not None:
            import contextlib

            with contextlib.suppress(Exception):
                await store.aclose()

