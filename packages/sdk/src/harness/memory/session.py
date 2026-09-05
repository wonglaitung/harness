"""Session management."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from harness.types import Session

if TYPE_CHECKING:
    from harness.memory.store import SessionStore


class SessionManager:
    """Manages conversation sessions."""

    def __init__(self, store: Optional["SessionStore"] = None):
        self.store = store
        self._sessions: dict[str, Session] = {}

    def create_session(self, session_id: str | None = None) -> Session:
        """Create a new session."""
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:8]}"

        session = Session(id=session_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get an existing session."""
        # Check memory cache first
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try to load from store
        if self.store:
            session = self.store.load(session_id)
            if session:
                self._sessions[session_id] = session
                return session

        return None

    def get_or_create(self, session_id: str | None = None) -> Session:
        """Get existing session or create new one."""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        return self.create_session(session_id)

    def update_session(self, session: Session) -> None:
        """Update a session."""
        session.updated_at = datetime.now()
        self._sessions[session.id] = session

        if self.store:
            self.store.save(session)

    def clear_session(self, session_id: str) -> None:
        """Clear a session's messages."""
        if session_id in self._sessions:
            self._sessions[session_id].clear_messages()

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]

        if self.store:
            self.store.delete(session_id)
