"""
Session state synchronization for reconnection support.

This module provides:
1. Session state snapshot saving
2. State recovery after reconnection
3. Incremental event replay

Reference: packages/cloud/docs/02-agent.md (Session Sync section)

Note: This is an optional extension for MVP. Basic implementation provided.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class SessionState:
    """Session state snapshot."""

    session_id: str
    last_event_id: int = 0
    progress: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class SessionSync:
    """
    Session state synchronizer.

    Purpose:
    1. Save state snapshots during task execution
    2. Restore context after reconnection
    3. Support "resume from checkpoint"

    Note: State files stored in /tmp (tmpfs), auto-cleaned on container destroy.
    """

    def __init__(self, state_dir: str = "/tmp/harness_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)

    def save_state(self, state: SessionState) -> None:
        """Save state snapshot to local file."""
        state_file = self.state_dir / f"{state.session_id}.json"
        data = {
            "session_id": state.session_id,
            "last_event_id": state.last_event_id,
            "progress": state.progress,
            "timestamp": state.timestamp.isoformat(),
        }
        state_file.write_text(json.dumps(data))

    def load_state(self, session_id: str) -> SessionState | None:
        """Load state snapshot."""
        state_file = self.state_dir / f"{session_id}.json"
        if not state_file.exists():
            return None
        data = json.loads(state_file.read_text())
        return SessionState(
            session_id=data["session_id"],
            last_event_id=data["last_event_id"],
            progress=data["progress"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    def clear_state(self, session_id: str) -> None:
        """Clear session state."""
        state_file = self.state_dir / f"{session_id}.json"
        state_file.unlink(missing_ok=True)

    def has_state(self, session_id: str) -> bool:
        """Check if session state exists."""
        state_file = self.state_dir / f"{session_id}.json"
        return state_file.exists()
