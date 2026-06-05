"""
Tool Output Offload - Large output handling for context management.

When tool outputs are too large, they are offloaded to temporary files
to keep context windows manageable. The context retains a summary/reference
instead of the full content.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.types import ToolResult

logger = logging.getLogger(__name__)


@dataclass
class OffloadConfig:
    """
    Configuration for tool output offloading.

    Attributes:
        size_threshold_chars: Minimum output size to trigger offload (default 5000)
        size_threshold_tokens: Token-based threshold (~4 chars per token)
        max_outputs_per_session: Maximum offloaded outputs per session
        cleanup_on_session_end: Auto-cleanup when session ends
        preview_length: Length of preview to keep in context
        summary_prompt: Prompt for generating summaries (optional)
        temp_dir: Directory for offloaded files (default: .harness/offload in cwd)
    """

    size_threshold_chars: int = 5000
    size_threshold_tokens: int = 1250  # ~5000 / 4
    max_outputs_per_session: int = 50
    cleanup_on_session_end: bool = False  # Safety: default to keep files
    preview_length: int = 200  # Preview chars to keep in context
    summary_prompt: str | None = None  # Optional LLM-based summarization
    temp_dir: Path | None = None  # Default: .harness/offload in current working directory

    def __post_init__(self):
        """Validate configuration."""
        if self.size_threshold_chars < 100:
            raise ValueError("size_threshold_chars must be at least 100")
        if self.max_outputs_per_session < 1:
            raise ValueError("max_outputs_per_session must be at least 1")
        if self.preview_length < 50:
            raise ValueError("preview_length must be at least 50")


@dataclass
class OffloadedOutput:
    """
    Record of an offloaded tool output.

    Attributes:
        file_path: Path to the offloaded file
        tool_name: Name of the tool that produced this output
        tool_call_id: ID of the tool call
        original_size: Original output size in characters
        preview: Preview content kept in context
        summary: Optional summary (generated or provided)
        created_at: When this output was offloaded
        session_id: Session this output belongs to
        metadata: Additional metadata
    """
    file_path: Path
    tool_name: str
    tool_call_id: str
    original_size: int
    preview: str
    summary: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    metadata: dict = field(default_factory=dict)

    def get_reference_string(self) -> str:
        """
        Get a reference string to include in context.

        Returns:
            Reference string with preview and file location
        """
        parts = [
            f"[Output from {self.tool_name} ({self.original_size} chars)]",
            f"Preview: {self.preview}",
            f"Full output saved to: {self.file_path}",
        ]
        if self.summary:
            parts.insert(1, f"Summary: {self.summary}")
        return "\n".join(parts)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "file_path": str(self.file_path),
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "original_size": self.original_size,
            "preview": self.preview,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "session_id": self.session_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OffloadedOutput":
        """Deserialize from dictionary."""
        return cls(
            file_path=Path(data["file_path"]),
            tool_name=data["tool_name"],
            tool_call_id=data["tool_call_id"],
            original_size=data["original_size"],
            preview=data["preview"],
            summary=data.get("summary"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            session_id=data.get("session_id", ""),
            metadata=data.get("metadata", {}),
        )


class OutputOffloader:
    """
    Manages offloading of large tool outputs to temporary files.

    Features:
    - Automatic detection of large outputs
    - Offloading to temp files with unique names
    - Preview extraction for context retention
    - Session-based cleanup management
    - Reference generation for LLM context
    """

    def __init__(self, config: OffloadConfig | None = None):
        """Initialize the output offloader."""
        self.config = config or OffloadConfig()
        # Default to .harness/offload in current working directory
        # This ensures sandbox can access the files
        self._temp_dir = Path(self.config.temp_dir or Path.cwd() / ".harness" / "offload")
        self._temp_dir.mkdir(parents=True, exist_ok=True)

        # Track offloaded outputs per session
        self._session_outputs: dict[str, list[OffloadedOutput]] = {}
        self._total_outputs: int = 0

    def should_offload(self, content: str, session_id: str = "") -> bool:
        """
        Check if content should be offloaded.

        Args:
            content: Tool output content
            session_id: Session ID for tracking

        Returns:
            True if content should be offloaded
        """
        if not content:
            return False

        size = len(content)

        # Check size threshold
        if size < self.config.size_threshold_chars:
            return False

        # Check session limit
        session_outputs = self._session_outputs.get(session_id, [])
        if len(session_outputs) >= self.config.max_outputs_per_session:
            logger.warning(
                f"Session {session_id} has reached max outputs limit "
                f"({self.config.max_outputs_per_session})"
            )
            return False

        return True

    def offload(
        self,
        content: str,
        tool_name: str,
        tool_call_id: str,
        session_id: str = "",
        summary: str | None = None,
    ) -> OffloadedOutput:
        """
        Offload content to a temporary file.

        Args:
            content: Tool output content to offload
            tool_name: Name of the tool
            tool_call_id: ID of the tool call
            session_id: Session ID for tracking
            summary: Optional summary

        Returns:
            OffloadedOutput record
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{session_id}_{tool_name}_{tool_call_id}_{timestamp}.txt"
        filename = filename.replace("/", "_").replace("\\", "_")  # Sanitize
        file_path = self._temp_dir / filename

        # Write content to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Extract preview
        preview = content[:self.config.preview_length]
        if len(content) > self.config.preview_length:
            preview += "..."

        # Create record
        output = OffloadedOutput(
            file_path=file_path,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            original_size=len(content),
            preview=preview,
            summary=summary,
            session_id=session_id,
        )

        # Track output
        if session_id not in self._session_outputs:
            self._session_outputs[session_id] = []
        self._session_outputs[session_id].append(output)
        self._total_outputs += 1

        logger.info(
            f"Offloaded {len(content)} chars from {tool_name} to {file_path}"
        )

        return output

    def create_offloaded_result(
        self,
        original_result: "ToolResult",
        session_id: str = "",
    ) -> "ToolResult":
        """
        Create a ToolResult with offloaded content reference.

        Args:
            original_result: Original tool result with large content
            session_id: Session ID for tracking

        Returns:
            New ToolResult with reference instead of full content
        """
        from harness.types import ToolResult

        if not original_result.content:
            return original_result

        # Offload the content
        offloaded = self.offload(
            content=original_result.content,
            tool_name=original_result.metadata.get("tool_name", "unknown"),
            tool_call_id=original_result.tool_call_id,
            session_id=session_id,
            summary=original_result.metadata.get("summary"),
        )

        # Create new result with reference
        return ToolResult(
            tool_call_id=original_result.tool_call_id,
            success=original_result.success,
            content=offloaded.get_reference_string(),
            error=original_result.error,
            metadata={
                **original_result.metadata,
                "offloaded": True,
                "offload_path": str(offloaded.file_path),
                "original_size": offloaded.original_size,
            },
        )

    def load_offloaded(self, file_path: Path | str) -> str:
        """
        Load content from an offloaded file.

        Args:
            file_path: Path to the offloaded file

        Returns:
            Original content from the file
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Offloaded file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def cleanup_session(self, session_id: str) -> int:
        """
        Clean up all offloaded outputs for a session.

        Args:
            session_id: Session ID to clean up

        Returns:
            Number of files deleted
        """
        outputs = self._session_outputs.get(session_id, [])
        deleted = 0

        for output in outputs:
            try:
                if output.file_path.exists():
                    output.file_path.unlink()
                    deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete {output.file_path}: {e}")

        # Remove session tracking
        if session_id in self._session_outputs:
            del self._session_outputs[session_id]

        logger.info(f"Cleaned up {deleted} offloaded files for session {session_id}")
        return deleted

    def cleanup_all(self) -> int:
        """
        Clean up all offloaded outputs.

        Returns:
            Number of files deleted
        """
        deleted = 0
        for session_id in list(self._session_outputs.keys()):
            deleted += self.cleanup_session(session_id)
        return deleted

    def get_session_outputs(self, session_id: str) -> list[OffloadedOutput]:
        """
        Get all offloaded outputs for a session.

        Args:
            session_id: Session ID

        Returns:
            List of OffloadedOutput records
        """
        return self._session_outputs.get(session_id, [])

    def get_stats(self) -> dict:
        """
        Get offloader statistics.

        Returns:
            Statistics dictionary
        """
        total_files = sum(len(outputs) for outputs in self._session_outputs.values())
        total_size = sum(
            output.original_size
            for outputs in self._session_outputs.values()
            for output in outputs
        )

        return {
            "total_outputs": self._total_outputs,
            "active_files": total_files,
            "total_original_size": total_size,
            "sessions_with_outputs": len(self._session_outputs),
            "temp_dir": str(self._temp_dir),
        }