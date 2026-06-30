"""
Connectors module for external system integration (Phase 4).

This module provides connectors for integrating with external systems:
- WebhookConnector: HTTP webhook receiver
- SlackConnector: Slack App integration
- GitHubConnector: GitHub App integration
- ConnectorManager: Orchestrates all connectors

Key features:
- Standardized event format (ConnectorEvent)
- Async event handling (non-blocking)
- Routing metadata for "reply to source"
- Output routing to multiple channels

Example:
    ```python
    from harness.connectors import (
        ConnectorManager,
        SlackConnector,
        GitHubConnector,
        OutputChannel,
        RoutingKeys,
    )

    # Initialize
    manager = ConnectorManager(trigger_manager)

    # Register Slack connector
    slack = SlackConnector(config=SlackConfig(
        bot_token="xoxb-...",
        app_token="xapp-...",
    ))
    manager.register_connector(slack)

    # Register output channel
    manager.register_output_channel(OutputChannel(
        type="slack",
        name="alerts",
        config={"channel": "#alerts"},
    ))

    # Start all connectors
    await manager.start()
    ```

For more details, see the design document:
    packages/sdk/design/phase4-connectors.md
"""

from harness.connectors.base import Connector, EventCallback
from harness.connectors.manager import ConnectorManager
from harness.connectors.types import (
    ConnectorEvent,
    ConnectorState,
    ConnectorType,
    GitHubConfig,
    OutputChannel,
    OutputResult,
    RoutingKeys,
    SlackConfig,
    WebhookConfig,
)

__all__ = [
    # Base
    "Connector",
    "EventCallback",
    # Manager
    "ConnectorManager",
    # Types
    "ConnectorType",
    "ConnectorState",
    "ConnectorEvent",
    "OutputChannel",
    "OutputResult",
    "RoutingKeys",
    # Configs
    "WebhookConfig",
    "SlackConfig",
    "GitHubConfig",
]
