"""Tests for SQLite session storage."""

import asyncio
import importlib.util
import tempfile
from pathlib import Path

import pytest

from harness.memory.store import AsyncSQLiteSessionStore, SQLiteSessionStore
from harness.types import Message, Session

# Check if aiosqlite is available
AIOSQLITE_AVAILABLE = importlib.util.find_spec("aiosqlite") is not None


class TestSQLiteSessionStore:
    """Tests for synchronous SQLite session store."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def store(self, temp_db):
        """Create a session store."""
        return SQLiteSessionStore(temp_db)

    def test_save_and_load_session(self, store):
        """Test saving and loading a session."""
        session = Session(
            id="test-session-1",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!"),
            ],
            metadata={"user_id": "user-123"},
        )

        store.save(session)

        loaded = store.load("test-session-1")

        assert loaded is not None
        assert loaded.id == "test-session-1"
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "Hello"
        assert loaded.messages[1].content == "Hi there!"
        assert loaded.metadata.get("user_id") == "user-123"

    def test_load_nonexistent_session(self, store):
        """Test loading a session that doesn't exist."""
        loaded = store.load("nonexistent")
        assert loaded is None

    def test_delete_session(self, store):
        """Test deleting a session."""
        session = Session(id="test-session-delete")
        store.save(session)

        loaded = store.load("test-session-delete")
        assert loaded is not None

        store.delete("test-session-delete")

        loaded = store.load("test-session-delete")
        assert loaded is None

    def test_update_session(self, store):
        """Test updating an existing session."""
        session = Session(id="test-session-update")
        store.save(session)

        session.add_message(Message(role="user", content="New message"))
        store.save(session)

        loaded = store.load("test-session-update")
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "New message"

    def test_list_sessions(self, store):
        """Test listing all sessions."""
        store.save(Session(id="session-1"))
        store.save(Session(id="session-2"))
        store.save(Session(id="session-3"))

        sessions = store.list_sessions()
        assert len(sessions) == 3
        assert "session-1" in sessions
        assert "session-2" in sessions
        assert "session-3" in sessions

    def test_large_session(self, store):
        """Test saving and loading a large session."""
        messages = [
            Message(role="user", content=f"Message {i}")
            for i in range(100)
        ]
        session = Session(
            id="large-session",
            messages=messages,
        )

        store.save(session)

        loaded = store.load("large-session")
        assert len(loaded.messages) == 100


@pytest.mark.skipif(not AIOSQLITE_AVAILABLE, reason="aiosqlite not installed")
class TestAsyncSQLiteSessionStore:
    """Tests for async SQLite session store."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    async def store(self, temp_db):
        """Create an async session store."""
        store = AsyncSQLiteSessionStore(temp_db)
        yield store
        await store.close()

    @pytest.mark.asyncio
    async def test_save_and_load_session(self, store):
        """Test async saving and loading a session."""
        session = Session(
            id="async-test-session-1",
            messages=[
                Message(role="user", content="Hello async"),
            ],
        )

        await store.save(session)

        loaded = await store.load("async-test-session-1")

        assert loaded is not None
        assert loaded.id == "async-test-session-1"
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "Hello async"

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, store):
        """Test async loading a nonexistent session."""
        loaded = await store.load("nonexistent-async")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_session(self, store):
        """Test async deleting a session."""
        session = Session(id="async-delete-test")
        await store.save(session)

        loaded = await store.load("async-delete-test")
        assert loaded is not None

        await store.delete("async-delete-test")

        loaded = await store.load("async-delete-test")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, temp_db):
        """Test concurrent save operations."""
        store = AsyncSQLiteSessionStore(temp_db, pool_size=3)

        async def save_session(i: int):
            session = Session(
                id=f"concurrent-{i}",
                messages=[Message(role="user", content=f"Message {i}")],
            )
            await store.save(session)

        # Run 10 concurrent saves
        await asyncio.gather(*[save_session(i) for i in range(10)])

        # Verify all saved
        for i in range(10):
            loaded = await store.load(f"concurrent-{i}")
            assert loaded is not None
            assert loaded.messages[0].content == f"Message {i}"

        await store.close()
