"""
Connectors types for Phase 4 external system integration.

This module defines types for connecting to external systems:
- ConnectorType: Supported connector types
- ConnectorState: Connector lifecycle state
- ConnectorEvent: Standardized external event
- OutputChannel: Output routing configuration
- RoutingKeys: Standard routing metadata keys
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ConnectorType(Enum):
    """Supported connector types."""

    WEBHOOK = "webhook"
    SLACK = "slack"
    GITHUB = "github"
    DISCORD = "discord"
    EMAIL = "email"
    CUSTOM = "custom"


class ConnectorState(Enum):
    """Connector lifecycle state."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class RoutingKeys:
    """
    Standard routing metadata keys.

    Used in routing_metadata dict to ensure naming consistency
    across connectors and prevent typos.

    Example:
        ```python
        event = ConnectorEvent(
            ...,
            routing_metadata={
                RoutingKeys.SLACK_THREAD_TS: "17123456.0001",
            }
        )
        ```
    """

    # Slack related
    SLACK_THREAD_TS = "slack_thread_ts"
    SLACK_CHANNEL_ID = "slack_channel_id"

    # GitHub related
    GITHUB_PR_NUMBER = "github_pr_number"
    GITHUB_ISSUE_NUMBER = "github_issue_number"
    GITHUB_REPO = "github_repo"

    # Webhook related
    WEBHOOK_REQUEST_ID = "webhook_request_id"

    # Generic
    USER_ID = "user_id"
    TIMESTAMP = "timestamp"


@dataclass
class ConnectorEvent:
    """
    Standardized external event.

    All connectors must convert external events to this format.
    The routing_metadata field enables "reply to original thread" functionality.

    Attributes:
        connector_type: Type of connector that created this event
        connector_id: Unique ID of the connector instance
        event_type: Event type (e.g., "pr_opened", "message")
        source: Source identifier (e.g., username, repository name)
        timestamp: When the event occurred
        payload: Event-specific data
        user_id: Optional user ID for authentication
        channel_id: Optional channel ID
        routing_metadata: Metadata for routing responses back to source
            Example: {"slack_thread_ts": "17123456.0001", "github_pr_number": 42}
    """

    connector_type: ConnectorType
    connector_id: str
    event_type: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)

    # Optional authentication info
    user_id: str | None = None
    channel_id: str | None = None

    # Routing metadata for "reply to source"
    routing_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_command(self) -> bool:
        """Check if this is a command event."""
        return self.event_type.endswith(".command")


@dataclass
class OutputChannel:
    """
    Output channel configuration.

    Defines how to send results to external systems.

    Attributes:
        type: Channel type ("slack" | "email" | "webhook" | "file" | "github")
        name: Channel name for reference
        config: Channel-specific configuration
            Slack: {"channel": "#alerts", "webhook_url": "..."}
            Email: {"to": ["user@example.com"], "subject_prefix": "[Harness]"}
            Webhook: {"url": "https://...", "headers": {}}
            GitHub: {"repo": "owner/repo"}
    """

    type: str
    name: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputResult:
    """Result of an output operation."""

    channel_name: str
    success: bool
    message: str | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WebhookConfig:
    """Webhook connector configuration."""

    endpoint: str  # URL path (e.g., "/webhook/github")
    secret: str | None = None  # Signature verification secret
    allowed_ips: list[str] = field(default_factory=list)
    rate_limit: int = 100  # Requests per minute


@dataclass
class SlackConfig:
    """Slack connector configuration."""

    bot_token: str  # xoxb-...
    app_token: str | None = None  # xapp-... (for Socket Mode)
    signing_secret: str | None = None
    command_prefix: str = "/harness"
    allowed_channels: list[str] = field(default_factory=list)


@dataclass
class GitHubConfig:
    """GitHub connector configuration."""

    app_id: str
    private_key: str  # GitHub App private key
    webhook_secret: str
    events: list[str] = field(
        default_factory=lambda: ["push", "pull_request", "issues", "issue_comment"]
    )
