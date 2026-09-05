"""
Audit Logger - Record all operations for security auditing.

Provides comprehensive logging of tool calls, file access, and commands.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class AuditLogEntry:
    """
    Audit log entry.

    Records a single operation or event.
    """

    timestamp: datetime
    session_id: str
    event_type: str  # tool_call, file_access, command, etc.
    action: str
    resource: str
    arguments: dict[str, Any]
    result: str  # success, denied, error
    details: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """
        Convert to JSON string.

        Returns:
            JSON representation
        """
        return json.dumps(
            {
                "timestamp": self.timestamp.isoformat(),
                "session_id": self.session_id,
                "event_type": self.event_type,
                "action": self.action,
                "resource": self.resource,
                "arguments": self._sanitize_arguments(self.arguments),
                "result": self.result,
                "details": self.details,
            },
            ensure_ascii=False,
        )

    def _sanitize_arguments(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize sensitive arguments.

        Args:
            args: Arguments dictionary

        Returns:
            Sanitized dictionary
        """
        sensitive_keys = {"password", "token", "secret", "key", "credential", "api_key"}
        sanitized = {}
        for k, v in args.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized

    @classmethod
    def from_json(cls, json_str: str) -> AuditLogEntry:
        """
        Create entry from JSON string.

        Args:
            json_str: JSON string

        Returns:
            AuditLogEntry
        """
        data = json.loads(json_str)
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            session_id=data["session_id"],
            event_type=data["event_type"],
            action=data["action"],
            resource=data["resource"],
            arguments=data["arguments"],
            result=data["result"],
            details=data.get("details", {}),
        )


class AuditLogger:
    """
    Audit logger.

    Records all operations to JSON Lines files for later analysis.
    """

    def __init__(
        self,
        log_dir: str = "~/.harness/audit",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        retention_days: int = 30,
        enabled: bool = True,
    ):
        """
        Initialize audit logger.

        Args:
            log_dir: Directory for log files
            max_file_size: Maximum log file size
            retention_days: Days to retain logs
            enabled: Whether logging is enabled
        """
        self.log_dir = Path(log_dir).expanduser()
        self.max_file_size = max_file_size
        self.retention_days = retention_days
        self.enabled = enabled
        self._current_file: Path | None = None

        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, entry: AuditLogEntry) -> None:
        """
        Log an entry.

        Args:
            entry: Entry to log
        """
        if not self.enabled:
            return

        log_file = self._get_log_file()

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry.to_json() + "\n")

    def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log a tool call.

        Args:
            session_id: Session ID
            tool_name: Tool name
            arguments: Tool arguments
            result: Result status
            details: Additional details
        """
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            session_id=session_id,
            event_type="tool_call",
            action=tool_name,
            resource=arguments.get("path", arguments.get("file", "")),
            arguments=arguments,
            result=result,
            details=details or {},
        )
        self.log(entry)

    def log_file_access(
        self,
        session_id: str,
        action: str,
        path: str,
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log a file access.

        Args:
            session_id: Session ID
            action: Action (read, write, delete)
            path: File path
            result: Result status
            details: Additional details
        """
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            session_id=session_id,
            event_type="file_access",
            action=action,
            resource=path,
            arguments={},
            result=result,
            details=details or {},
        )
        self.log(entry)

    def log_command(
        self,
        session_id: str,
        command: str,
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log a command execution.

        Args:
            session_id: Session ID
            command: Command executed
            result: Result status
            details: Additional details
        """
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            session_id=session_id,
            event_type="command",
            action="execute",
            resource=command,
            arguments={},
            result=result,
            details=details or {},
        )
        self.log(entry)

    def _get_log_file(self) -> Path:
        """
        Get current log file.

        Returns:
            Path to log file
        """
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit-{today}.log"

        # Check file size
        if log_file.exists() and log_file.stat().st_size > self.max_file_size:
            # Create new file with index
            index = 1
            while True:
                new_file = self.log_dir / f"audit-{today}-{index}.log"
                if not new_file.exists():
                    log_file = new_file
                    break
                index += 1

        return log_file

    def query(
        self,
        session_id: str | None = None,
        event_type: str | None = None,
        action: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """
        Query audit logs.

        Args:
            session_id: Filter by session ID
            event_type: Filter by event type
            action: Filter by action
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results

        Returns:
            List of matching entries
        """
        if not self.log_dir.exists():
            return []

        results = []

        for log_file in self.log_dir.glob("audit-*.log"):
            try:
                with open(log_file, encoding="utf-8") as f:
                    for line in f:
                        try:
                            entry = AuditLogEntry.from_json(line)

                            # Apply filters
                            if session_id and entry.session_id != session_id:
                                continue
                            if event_type and entry.event_type != event_type:
                                continue
                            if action and entry.action != action:
                                continue
                            if start_time and entry.timestamp < start_time:
                                continue
                            if end_time and entry.timestamp > end_time:
                                continue

                            results.append(entry)

                            if len(results) >= limit:
                                break
                        except Exception:
                            continue

                if len(results) >= limit:
                    break
            except Exception:
                continue

        return sorted(results, key=lambda e: e.timestamp, reverse=True)

    def cleanup_old_logs(self) -> int:
        """
        Remove logs older than retention period.

        Returns:
            Number of files removed
        """
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed = 0

        for log_file in self.log_dir.glob("audit-*.log"):
            try:
                # Extract date from filename
                file_date_str = log_file.stem.split("-")[1]
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")

                if file_date < cutoff:
                    log_file.unlink()
                    removed += 1
            except Exception:
                continue

        return removed

    def get_stats(self) -> dict[str, Any]:
        """
        Get audit log statistics.

        Returns:
            Statistics dictionary
        """
        if not self.log_dir.exists():
            return {"total_files": 0, "total_size": 0}

        files = list(self.log_dir.glob("audit-*.log"))
        total_size = sum(f.stat().st_size for f in files)

        return {
            "total_files": len(files),
            "total_size": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "log_dir": str(self.log_dir),
        }
