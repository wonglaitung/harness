"""Session storage implementations."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from harness.types import Session, Message


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