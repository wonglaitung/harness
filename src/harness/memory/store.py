"""Session storage implementations."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from harness.types import Session, Message

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SessionStore(ABC):
    """Abstract base class for session storage."""

    @abstractmethod
    def save(self, session: Session) -> None:
        """Save a session."""
        pass

    @abstractmethod
    def load(self, session_id: str) -> Optional[Session]:
        """Load a session by ID."""
        pass

    @abstractmethod
    def delete(self, session_id: str) -> None:
        """Delete a session."""
        pass


class FileSessionStore(SessionStore):
    """File-based session storage."""

    def __init__(self, storage_dir: str = ".harness/sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        """Get path for a session file."""
        return self.storage_dir / f"{session_id}.json"

    def save(self, session: Session) -> None:
        """Save a session to file."""
        data = {
            "id": session.id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in session.messages
            ],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "metadata": session.metadata,
        }

        path = self._session_path(session.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, session_id: str) -> Optional[Session]:
        """Load a session from file."""
        path = self._session_path(session_id)

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            session = Session(
                id=data["id"],
                messages=[
                    Message(
                        role=m["role"],
                        content=m["content"],
                        timestamp=datetime.fromisoformat(m["timestamp"]),
                    )
                    for m in data.get("messages", [])
                ],
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                metadata=data.get("metadata", {}),
            )

            return session

        except Exception:
            return None

    def delete(self, session_id: str) -> None:
        """Delete a session file."""
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()


class SQLiteSessionStore(SessionStore):
    """
    SQLite-based session storage.

    Provides persistent storage with better performance for large sessions.

    Example:
        >>> store = SQLiteSessionStore("~/.harness/harness.db")
        >>> store.save(session)
        >>> session = store.load("session-123")
    """

    def __init__(self, db_path: str = ".harness/harness.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        if self._initialized:
            return

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    user_id TEXT,
                    working_directory TEXT,
                    summary TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    tool_call_id TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id)
            """)
            conn.commit()
            self._initialized = True
        finally:
            conn.close()

    def save(self, session: Session) -> None:
        """Save a session to SQLite."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO sessions
                (id, created_at, updated_at, user_id, working_directory, summary, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session.id,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.metadata.get("user_id"),
                session.metadata.get("working_directory", ""),
                session.metadata.get("summary"),
                json.dumps(session.metadata),
            ))

            # Delete old messages
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session.id,))

            # Save new messages
            for msg in session.messages:
                conn.execute("""
                    INSERT INTO messages
                    (session_id, role, content, timestamp, tool_call_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session.id,
                    msg.role,
                    msg.content if isinstance(msg.content, str) else json.dumps(msg.content),
                    msg.timestamp.isoformat(),
                    msg.metadata.get("tool_call_id"),
                    json.dumps(msg.metadata),
                ))

            conn.commit()
        finally:
            conn.close()

    def load(self, session_id: str) -> Optional[Session]:
        """Load a session from SQLite."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            session = Session(
                id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                updated_at=datetime.fromisoformat(row[2]),
                metadata=json.loads(row[6]) if row[6] else {},
            )

            # Load messages
            cursor = conn.execute(
                "SELECT role, content, timestamp, metadata FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            )
            for msg_row in cursor.fetchall():
                session.messages.append(Message(
                    role=msg_row[0],
                    content=msg_row[1],
                    timestamp=datetime.fromisoformat(msg_row[2]),
                    metadata=json.loads(msg_row[3]) if msg_row[3] else {},
                ))

            return session
        except Exception:
            return None
        finally:
            conn.close()

    def delete(self, session_id: str) -> None:
        """Delete a session from SQLite."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def list_sessions(self, user_id: str | None = None) -> list[str]:
        """List all session IDs."""
        conn = sqlite3.connect(self.db_path)
        try:
            if user_id:
                cursor = conn.execute(
                    "SELECT id FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
                    (user_id,),
                )
            else:
                cursor = conn.execute("SELECT id FROM sessions ORDER BY updated_at DESC")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()


class AsyncSQLiteSessionStore:
    """
    Async SQLite-based session storage with connection pooling.

    Designed for production use with proper WAL mode and connection management.

    Example:
        >>> store = AsyncSQLiteSessionStore("~/.harness/harness.db")
        >>> await store.save(session)
        >>> session = await store.load("session-123")
    """

    def __init__(
        self,
        db_path: str = ".harness/harness.db",
        pool_size: int = 5,
        timeout: float = 30.0,
    ):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: list[Any] = []
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _init_connection(self, conn: Any) -> None:
        """Initialize connection with production settings."""
        # Enable WAL mode (critical for write concurrency)
        await conn.execute("PRAGMA journal_mode=WAL")
        # Sync mode for balance of safety and performance
        await conn.execute("PRAGMA synchronous=NORMAL")
        # Busy timeout to wait for locks
        await conn.execute(f"PRAGMA busy_timeout={int(self.timeout * 1000)}")
        # Cache size (negative = KB)
        await conn.execute("PRAGMA cache_size=-64000")  # 64MB
        # Foreign key constraints
        await conn.execute("PRAGMA foreign_keys=ON")

    async def _ensure_initialized(self) -> None:
        """Ensure database is initialized."""
        if self._initialized:
            return

        async with self._get_connection() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    user_id TEXT,
                    working_directory TEXT,
                    summary TEXT,
                    metadata TEXT
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    tool_call_id TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id)
            """)
            await conn.commit()
        self._initialized = True

    @asynccontextmanager
    async def _get_connection(self):
        """Get a connection from the pool."""
        async with self._lock:
            if self._pool:
                conn = self._pool.pop()
            else:
                try:
                    import aiosqlite
                    conn = await aiosqlite.connect(self.db_path)
                    await self._init_connection(conn)
                except ImportError:
                    raise ImportError(
                        "aiosqlite is required for async SQLite support. "
                        "Install with: pip install aiosqlite"
                    )

        try:
            yield conn
        finally:
            async with self._lock:
                if len(self._pool) < self.pool_size:
                    self._pool.append(conn)
                else:
                    await conn.close()

    async def save(self, session: Session) -> None:
        """Save a session asynchronously."""
        await self._ensure_initialized()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self._get_connection() as conn:
                    await conn.execute("""
                        INSERT OR REPLACE INTO sessions
                        (id, created_at, updated_at, user_id, working_directory, summary, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session.id,
                        session.created_at.isoformat(),
                        session.updated_at.isoformat(),
                        session.metadata.get("user_id"),
                        session.metadata.get("working_directory", ""),
                        session.metadata.get("summary"),
                        json.dumps(session.metadata),
                    ))

                    # Delete old messages
                    await conn.execute("DELETE FROM messages WHERE session_id = ?", (session.id,))

                    # Save new messages
                    for msg in session.messages:
                        await conn.execute("""
                            INSERT INTO messages
                            (session_id, role, content, timestamp, tool_call_id, metadata)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            session.id,
                            msg.role,
                            msg.content if isinstance(msg.content, str) else json.dumps(msg.content),
                            msg.timestamp.isoformat(),
                            msg.metadata.get("tool_call_id"),
                            json.dumps(msg.metadata),
                        ))

                    await conn.commit()
                return
            except Exception as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    continue
                raise

    async def load(self, session_id: str) -> Optional[Session]:
        """Load a session asynchronously."""
        await self._ensure_initialized()

        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            session = Session(
                id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                updated_at=datetime.fromisoformat(row[2]),
                metadata=json.loads(row[6]) if row[6] else {},
            )

            # Load messages
            cursor = await conn.execute(
                "SELECT role, content, timestamp, metadata FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            )
            async for msg_row in cursor:
                session.messages.append(Message(
                    role=msg_row[0],
                    content=msg_row[1],
                    timestamp=datetime.fromisoformat(msg_row[2]),
                    metadata=json.loads(msg_row[3]) if msg_row[3] else {},
                ))

            return session

    async def delete(self, session_id: str) -> None:
        """Delete a session asynchronously."""
        async with self._get_connection() as conn:
            await conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            await conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await conn.commit()

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self._lock:
            for conn in self._pool:
                await conn.close()
            self._pool.clear()