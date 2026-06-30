"""
Trigger types - Core type definitions for the Trigger System.

This module defines:
- TriggerType: Types of triggers (cron, interval, webhook, etc.)
- TriggerState: States a trigger can be in
- TriggerEvent: Event created when a trigger fires
- TriggerAction: Action to take when trigger fires
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness.loop.types import GoalConfig, LoopResult


class TriggerType(Enum):
    """
    Types of triggers.

    Each type defines a different way to trigger goal execution.
    """

    CRON = "cron"               # Cron expression scheduling
    INTERVAL = "interval"       # Fixed interval scheduling
    WEBHOOK = "webhook"         # HTTP webhook trigger
    HEARTBEAT = "heartbeat"     # Periodic heartbeat check
    FILE_WATCH = "file_watch"   # File system changes
    EVENT = "event"             # Event bus subscription


class TriggerState(Enum):
    """
    States a trigger can be in.

    Triggers transition between these states during their lifecycle.
    """

    IDLE = "idle"           # Not started yet
    RUNNING = "running"     # Active and waiting for trigger condition
    PAUSED = "paused"       # Temporarily paused
    STOPPED = "stopped"     # Permanently stopped
    ERROR = "error"         # Error state


@dataclass
class TriggerEvent:
    """
    Event created when a trigger fires.

    Contains metadata about the trigger and optional payload data.

    Attributes:
        trigger_type: Type of trigger that fired
        trigger_id: Unique identifier of the trigger
        timestamp: When the event occurred
        payload: Optional data associated with the event
        routing_metadata: Metadata for routing responses back to source
            Example: {"slack_thread_ts": "17123456.0001", "github_pr_number": 42}
            Used by ConnectorManager to route output to correct destination
    """

    trigger_type: TriggerType
    trigger_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)
    routing_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_scheduled(self) -> bool:
        """Check if this is a scheduled event (cron/interval)."""
        return self.trigger_type in (TriggerType.CRON, TriggerType.INTERVAL)

    @property
    def is_external(self) -> bool:
        """Check if this is an external event (webhook/event)."""
        return self.trigger_type in (TriggerType.WEBHOOK, TriggerType.EVENT)


@dataclass
class TriggerAction:
    """
    Action to take when a trigger fires.

    This configuration maps directly to GoalConfig for goal-driven execution.

    Attributes:
        goal: Goal description (maps to GoalConfig.description)
        workspace_dir: Working directory for execution
        max_iterations: Maximum iterations per execution
        timeout_seconds: Execution timeout in seconds
        custom_verifier: Optional custom verification function
        skills: Skills to activate for this action
        output_channels: Channels to send results to
        session_id: Optional session ID for context persistence

    Example:
        ```python
        action = TriggerAction(
            goal="Generate daily report",
            workspace_dir="/app/reports",
            skills=["report-generation"],
            output_channels=["slack", "email"],
        )
        ```
    """

    # Goal configuration
    goal: str

    # Execution environment
    workspace_dir: str = "."

    # Iteration control
    max_iterations: int = 50
    timeout_seconds: int = 3600

    # Verification
    custom_verifier: Callable[["LoopResult"], bool] | None = None

    # Skills and output
    skills: list[str] = field(default_factory=list)
    output_channels: list[str] = field(default_factory=list)

    # Session management
    session_id: str | None = None

    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: float = 5.0

    def to_goal_config(self, event: TriggerEvent | None = None) -> "GoalConfig":
        """
        Convert to GoalConfig for goal-driven execution.

        Args:
            event: Optional trigger event to include context from

        Returns:
            GoalConfig instance ready for execution
        """
        from harness.loop.types import GoalConfig

        # Build goal description with event context
        goal = self.goal
        if event and event.payload:
            context = "\n\nEvent context:\n"
            for key, value in event.payload.items():
                context += f"- {key}: {value}\n"
            goal += context

        return GoalConfig(
            description=goal,
            workspace_dir=self.workspace_dir,
            max_iterations=self.max_iterations,
            timeout_seconds=self.timeout_seconds,
            custom_verifier=self.custom_verifier,
        )

    def __post_init__(self):
        """Validate configuration."""
        if not self.goal:
            raise ValueError("goal cannot be empty")

        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be at least 1")


@dataclass
class TriggerRegistration:
    """
    Registration information for a trigger.

    Tracks the trigger, its action, and execution statistics.

    Attributes:
        trigger: The trigger instance
        action: The action to execute when triggered
        enabled: Whether this registration is active
        last_fired: When the trigger last fired
        fire_count: Number of times the trigger has fired
        error_count: Number of execution errors
        last_error: Most recent error message
    """

    trigger: "Trigger"
    action: TriggerAction
    enabled: bool = True

    # Statistics
    last_fired: datetime | None = None
    fire_count: int = 0
    error_count: int = 0
    last_error: str | None = None
