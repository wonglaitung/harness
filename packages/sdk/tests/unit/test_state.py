"""Shared-state (Blackboard) unit tests: versioning, CAS, conflict detection."""

from __future__ import annotations

from pathlib import Path

from harness.state import (
    BlackboardItem,
    ConflictSet,
    InMemoryBackend,
    ItemStatus,
    WriteKind,
    create_state_store,
)


async def test_put_and_get() -> None:
    store = create_state_store("memory")
    item = await store.put_additive("observation", {"x": 1}, source_agent="a")
    got = await store.get(item.id)
    assert got is not None
    assert got.content == {"x": 1}


async def test_write_if_version_cas() -> None:
    backend = InMemoryBackend()
    item = BlackboardItem(id="k", type="decision", content="v1", kind=WriteKind.AUTHORITATIVE)
    await backend.put(item)

    # Correct base version -> success, version advances.
    ok, updated = await backend.write_if_version("k", "v2", base_version=1)
    assert ok is True
    assert updated is not None and updated.version == 2

    # Stale base version -> rejected (concurrent writer advanced it).
    ok2, _ = await backend.write_if_version("k", "v3", base_version=1)
    assert ok2 is False


async def test_authoritative_conflict_surfaces() -> None:
    backend = InMemoryBackend()
    await backend.put(
        BlackboardItem(id="d1", type="budget", content="100", kind=WriteKind.AUTHORITATIVE)
    )
    await backend.put(
        BlackboardItem(id="d2", type="budget", content="200", kind=WriteKind.AUTHORITATIVE)
    )
    conflicts: list[ConflictSet] = await backend.get_conflicts()
    assert len(conflicts) == 1
    assert set(conflicts[0].item_ids) == {"d1", "d2"}


async def test_file_backend_persists(tmp_path: Path) -> None:
    store = create_state_store("file", path=str(tmp_path / "state.db"))
    item = await store.put_authoritative("decision", "final", source_agent="planner")
    reopened = create_state_store("file", path=str(tmp_path / "state.db"))
    got = await reopened.get(item.id)
    assert got is not None
    assert got.content == "final"
    assert got.status == ItemStatus.CONFIRMED
