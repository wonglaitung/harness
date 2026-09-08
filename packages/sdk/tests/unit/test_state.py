"""Shared-state (Blackboard) unit tests: versioning, CAS, conflict detection."""

from __future__ import annotations

import asyncio
import multiprocessing
from pathlib import Path

import pytest

aiosqlite = pytest.importorskip("aiosqlite")

from harness.state import (
    BlackboardItem,
    ConflictSet,
    InMemoryBackend,
    ItemStatus,
    WriteKind,
    create_state_store,
)
from harness.state.file_store import FileBackend
from harness.state.db_store import DBBackend


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


async def test_file_backend_cas_singleproc(tmp_path: Path) -> None:
    backend = FileBackend(str(tmp_path / "state.db"))
    await backend.put(
        BlackboardItem(id="k", type="decision", content="v1", kind=WriteKind.AUTHORITATIVE)
    )

    ok, updated = await backend.write_if_version("k", "v2", base_version=1)
    assert ok is True
    assert updated is not None and updated.version == 2

    # Stale base version -> rejected (someone advanced it).
    ok2, _ = await backend.write_if_version("k", "v3", base_version=1)
    assert ok2 is False

    # Missing row -> created.
    ok3, created = await backend.write_if_version("new", "x", base_version=0)
    assert ok3 is True
    assert created is not None and created.version == 1


def _cas_worker(path: str, item_id: str, target: int, q: multiprocessing.Queue[int]) -> None:
    import asyncio

    async def run() -> int:
        backend = FileBackend(path)
        done = 0
        while done < target:
            cur = await backend.get(item_id)
            base = cur.version if cur is not None else 0
            ok, _ = await backend.write_if_version(item_id, {"n": base + 1}, base_version=base)
            if ok:
                done += 1
        return done

    q.put(asyncio.run(run()))


async def test_file_backend_cas_crossprocess(tmp_path: Path) -> None:
    """Two+ processes racing on the same id must not lose updates.

    Each successful CAS advances version by exactly one; with N processes each
    doing `target` successful writes, the final version must be 1 + N*target and
    every successful write must map to a distinct base version. A non-atomic
    read-then-write would let two workers pass the same base and silently drop a
    write (lost update) -> final version would be < expected.
    """
    path = str(tmp_path / "state.db")
    seed = FileBackend(path)
    await seed.put(
        BlackboardItem(id="c", type="counter", content={"n": 0}, kind=WriteKind.AUTHORITATIVE)
    )

    n_procs = 4
    target = 25
    ctx = multiprocessing.get_context("spawn")
    q: multiprocessing.Queue[int] = ctx.Queue()
    procs = [
        ctx.Process(target=_cas_worker, args=(path, "c", target, q))
        for _ in range(n_procs)
    ]
    for p in procs:
        p.start()
    results = [q.get() for _ in range(n_procs)]
    for p in procs:
        p.join(timeout=30)

    assert sum(results) == n_procs * target  # every attempted success was real
    final = await FileBackend(path).get("c")
    assert final is not None
    assert final.version == n_procs * target + 1
    assert final.content["n"] == n_procs * target + 1


async def test_db_backend_cas_singleproc(tmp_path: Path) -> None:
    backend = DBBackend(str(tmp_path / "state.db"))
    await backend.put(
        BlackboardItem(id="k", type="decision", content="v1", kind=WriteKind.AUTHORITATIVE)
    )

    ok, updated = await backend.write_if_version("k", "v2", base_version=1)
    assert ok is True
    assert updated is not None and updated.version == 2

    # Stale base version -> rejected.
    ok2, _ = await backend.write_if_version("k", "v3", base_version=1)
    assert ok2 is False

    # Missing row -> created.
    ok3, created = await backend.write_if_version("new", "x", base_version=0)
    assert ok3 is True
    assert created is not None and created.version == 1


async def test_db_backend_cas_concurrent(tmp_path: Path) -> None:
    """Async concurrency must not lose updates (no gaps in base versions)."""
    backend = DBBackend(str(tmp_path / "state.db"))
    await backend.put(
        BlackboardItem(id="c", type="counter", content={"n": 0}, kind=WriteKind.AUTHORITATIVE)
    )

    n_tasks = 8
    per = 25

    async def worker() -> int:
        done = 0
        while done < per:
            cur = await backend.get("c")
            base = cur.version if cur is not None else 0
            ok, _ = await backend.write_if_version("c", {"n": base + 1}, base_version=base)
            if ok:
                done += 1
        return done

    results = await asyncio.gather(*[worker() for _ in range(n_tasks)])
    assert sum(results) == n_tasks * per
    final = await backend.get("c")
    assert final is not None
    assert final.version == n_tasks * per + 1


def _db_cas_worker(path: str, item_id: str, target: int, q: multiprocessing.Queue[int]) -> None:
    async def run() -> int:
        backend = DBBackend(path)
        done = 0
        while done < target:
            cur = await backend.get(item_id)
            base = cur.version if cur is not None else 0
            ok, _ = await backend.write_if_version(item_id, {"n": base + 1}, base_version=base)
            if ok:
                done += 1
        return done

    q.put(asyncio.run(run()))


async def test_db_backend_cas_crossprocess(tmp_path: Path) -> None:
    """Multi-process CAS on a shared sqlite file must not lose updates."""
    path = str(tmp_path / "state.db")
    seed = DBBackend(path)
    await seed.put(
        BlackboardItem(id="c", type="counter", content={"n": 0}, kind=WriteKind.AUTHORITATIVE)
    )

    n_procs = 4
    target = 25
    ctx = multiprocessing.get_context("spawn")
    q: multiprocessing.Queue[int] = ctx.Queue()
    procs = [
        ctx.Process(target=_db_cas_worker, args=(path, "c", target, q))
        for _ in range(n_procs)
    ]
    for p in procs:
        p.start()
    results = [q.get() for _ in range(n_procs)]
    for p in procs:
        p.join(timeout=30)

    assert sum(results) == n_procs * target
    final = await DBBackend(path).get("c")
    assert final is not None
    assert final.version == n_procs * target + 1
    assert final.content["n"] == n_procs * target + 1

