"""
Session management for Harness Client.
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime


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


class SessionManager:
    """
    Session manager - single source of truth for session state.

    All session operations should go through this class.
    UI components should observe changes, not store state.
    """

    def __init__(self, max_sessions: int = 50):
        self._sessions: OrderedDict[str, ClientSession] = OrderedDict()
        self._current_id: str | None = None
        self._max_sessions = max_sessions

    def create(self, session_id: str = None) -> ClientSession:
        """Create a new session and make it current."""
        import uuid

        sid = session_id or str(uuid.uuid4())[:8]
        session = ClientSession(id=sid)
        self._sessions[sid] = session
        self._current_id = sid
        return session

    def get_current(self) -> ClientSession | None:
        """Get the current active session."""
        if self._current_id:
            return self._sessions.get(self._current_id)
        return None

    def get(self, session_id: str) -> ClientSession | None:
        """Get a specific session by ID."""
        return self._sessions.get(session_id)

    def switch_to(self, session_id: str) -> bool:
        """Switch to a different session."""
        if session_id in self._sessions:
            self._current_id = session_id
            return True
        return False

    def archive_current(self) -> str | None:
        """
        Archive the current session when creating a new one.

        Returns the archived session ID, or None if it was empty and deleted.
        """
        current = self.get_current()
        if not current:
            return None

        if current.messages:
            # Has messages, keep it in history
            self._sessions.move_to_end(current.id, last=True)
            # Prune old sessions if needed
            while len(self._sessions) > self._max_sessions:
                # Remove oldest (first item)
                oldest_id = next(iter(self._sessions))
                if oldest_id != self._current_id:
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
        if session_id not in self._sessions:
            return False

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
        return True

    def get_history_list(self) -> list[ClientSession]:
        """Get list of historical sessions (excluding current)."""
        if not self._current_id:
            return list(self._sessions.values())

        # Return in reverse order (most recent first)
        history = [s for s in reversed(self._sessions.values()) if s.id != self._current_id]
        return history

    def add_message_to_current(self, role: str, content: str):
        """Add a message to the current session."""
        current = self.get_current()
        if current:
            current.add_message(role, content)

    def update_token_usage(self, input_tokens: int, output_tokens: int):
        """Update token usage for current session."""
        current = self.get_current()
        if current:
            current.token_usage["input"] += input_tokens
            current.token_usage["output"] += output_tokens

    @property
    def current_id(self) -> str | None:
        """Get the current session ID."""
        return self._current_id

    @property
    def session_count(self) -> int:
        """Get total number of sessions."""
        return len(self._sessions)
