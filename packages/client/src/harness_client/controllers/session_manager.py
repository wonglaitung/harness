"""
Session management for Harness Client.
"""

import json
import logging
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_sessions_dir() -> Path:
    """Get sessions storage directory."""
    from harness_client.utils.settings import get_config_dir

    return get_config_dir() / "sessions"


@dataclass
class ClientSession:
    """Single session state for the client."""

    id: str
    name: str = "新会话"
    messages: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    token_usage: dict = field(default_factory=lambda: {"input": 0, "output": 0})
    trusted_commands: set[str] = field(default_factory=set)  # Command-level trust cache

    def add_message(self, role: str, content: str):
        """Add a message and update timestamp."""
        self.messages.append({"role": role, "content": content})
        self.updated_at = datetime.now()
        # Auto-name from first user message
        if self.name == "新会话" and role == "user":
            self.name = self._generate_name(content)

    def trust_command(self, trust_key: str) -> None:
        """Mark a command as trusted for this session.

        Args:
            trust_key: "write", "edit", "bash:ls", "bash:rm", etc.
        """
        self.trusted_commands.add(trust_key)

    def is_command_trusted(self, trust_key: str) -> bool:
        """Check if a command is trusted for this session."""
        return trust_key in self.trusted_commands

    def clear_trust(self) -> None:
        """Clear all trusted commands."""
        self.trusted_commands.clear()

    def _generate_name(self, content: str) -> str:
        """Generate session name from content."""
        if isinstance(content, list):
            content = " ".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and "text" in block
            )
        first_line = str(content).strip().split("\n")[0]
        if len(first_line) > 20:
            return first_line[:20] + "..."
        return first_line or "新会话"

    def to_dict(self) -> dict[str, Any]:
        """Serialize session to dictionary for JSON storage."""
        return {
            "id": self.id,
            "name": self.name,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "token_usage": self.token_usage,
            "trusted_commands": list(self.trusted_commands),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClientSession":
        """Deserialize session from dictionary."""
        return cls(
            id=data["id"],
            name=data.get("name", "新会话"),
            messages=data.get("messages", []),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.now(),
            token_usage=data.get("token_usage", {"input": 0, "output": 0}),
            trusted_commands=set(data.get("trusted_commands", [])),
        )


class SessionManager:
    """
    Session manager - single source of truth for session state.

    All session operations should go through this class.
    UI components should observe changes, not store state.

    Supports persistent storage to disk via JSON files.
    """

    def __init__(self, max_sessions: int = 50, storage_dir: Path | None = None):
        self._sessions: OrderedDict[str, ClientSession] = OrderedDict()
        self._current_id: str | None = None
        self._max_sessions = max_sessions
        self._storage_dir = storage_dir or _get_sessions_dir()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazy load sessions from disk on first access."""
        if self._loaded:
            return

        self._load_sessions()
        self._loaded = True

    def _load_sessions(self) -> None:
        """Load all sessions from storage directory."""
        if not self._storage_dir.exists():
            logger.debug(f"Sessions directory does not exist: {self._storage_dir}")
            return

        sessions_files = sorted(
            self._storage_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,  # Most recent first
        )

        for session_file in sessions_files:
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                session = ClientSession.from_dict(data)
                self._sessions[session.id] = session
                logger.debug(f"Loaded session: {session.id} ({session.name})")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load session from {session_file}: {e}")

        logger.info(f"Loaded {len(self._sessions)} sessions from disk")

    def _save_session(self, session: ClientSession) -> None:
        """Save a session to disk."""
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        session_file = self._storage_dir / f"{session.id}.json"

        try:
            session_file.write_text(
                json.dumps(session.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(f"Saved session: {session.id} ({session.name})")
        except Exception as e:
            logger.error(f"Failed to save session {session.id}: {e}")

    def _delete_session_file(self, session_id: str) -> None:
        """Delete a session file from disk."""
        session_file = self._storage_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                session_file.unlink()
                logger.debug(f"Deleted session file: {session_id}")
            except Exception as e:
                logger.error(f"Failed to delete session file {session_id}: {e}")

    def create(self, session_id: str = None) -> ClientSession:
        """Create a new session and make it current."""
        self._ensure_loaded()

        sid = session_id or str(uuid.uuid4())[:8]
        session = ClientSession(id=sid)
        self._sessions[sid] = session
        self._current_id = sid
        return session

    def get_current(self) -> ClientSession | None:
        """Get the current active session."""
        self._ensure_loaded()

        if self._current_id:
            return self._sessions.get(self._current_id)
        return None

    def get(self, session_id: str) -> ClientSession | None:
        """Get a specific session by ID."""
        self._ensure_loaded()
        return self._sessions.get(session_id)

    def switch_to(self, session_id: str) -> bool:
        """Switch to a different session."""
        self._ensure_loaded()

        if session_id in self._sessions:
            self._current_id = session_id
            return True
        return False

    def archive_current(self) -> str | None:
        """
        Archive the current session when creating a new one.

        Returns the archived session ID, or None if it was empty and deleted.
        """
        self._ensure_loaded()

        current = self.get_current()
        if not current:
            return None

        if current.messages:
            # Has messages, keep it in history and save to disk
            self._sessions.move_to_end(current.id, last=True)
            self._save_session(current)

            # Prune old sessions if needed
            while len(self._sessions) > self._max_sessions:
                # Remove oldest (first item)
                oldest_id = next(iter(self._sessions))
                if oldest_id != self._current_id:
                    self._delete_session_file(oldest_id)
                    del self._sessions[oldest_id]
                else:
                    break
            return current.id
        else:
            # Empty session, delete it
            del self._sessions[current.id]
            return None

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        self._ensure_loaded()

        if session_id not in self._sessions:
            return False

        self._delete_session_file(session_id)
        del self._sessions[session_id]
        if self._current_id == session_id:
            self._current_id = None
        return True

    def clear_current_messages(self) -> bool:
        """Clear messages in current session without creating a new session."""
        current = self.get_current()
        if not current:
            return False

        current.messages = []
        current.clear_trust()
        # Update the saved session
        self._save_session(current)
        return True

    def get_history_list(self) -> list[ClientSession]:
        """Get list of historical sessions sorted by updated_at (most recent first)."""
        self._ensure_loaded()

        if not self._current_id:
            # Sort by updated_at descending
            return sorted(self._sessions.values(), key=lambda s: s.updated_at, reverse=True)

        # Sort by updated_at descending, excluding current
        history = sorted(
            [s for s in self._sessions.values() if s.id != self._current_id],
            key=lambda s: s.updated_at,
            reverse=True,
        )
        return history

    def add_message_to_current(self, role: str, content: str):
        """Add a message to the current session."""
        current = self.get_current()
        if current:
            current.add_message(role, content)
            # Auto-save after each message
            self._save_session(current)

    def update_token_usage(self, input_tokens: int, output_tokens: int):
        """Update token usage for current session."""
        current = self.get_current()
        if current:
            current.token_usage["input"] += input_tokens
            current.token_usage["output"] += output_tokens
            # Save updated token usage
            self._save_session(current)

    def save_current(self) -> bool:
        """Save the current session to disk."""
        current = self.get_current()
        if current:
            self._save_session(current)
            return True
        return False

    @property
    def current_id(self) -> str | None:
        """Get the current session ID."""
        return self._current_id

    @property
    def session_count(self) -> int:
        """Get total number of sessions."""
        self._ensure_loaded()
        return len(self._sessions)
