"""
Connector manager for orchestrating all connectors.

This module provides ConnectorManager for:
- Managing connector lifecycle
- Routing events to TriggerManager
- Managing output channels
- Routing results to correct destinations
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from harness.connectors.base import Connector
from harness.connectors.types import (
    ConnectorEvent,
    ConnectorType,
    OutputChannel,
    OutputResult,
    RoutingKeys,
)
from harness.triggers.types import TriggerEvent, TriggerType

if TYPE_CHECKING:
    from harness.triggers.manager import TriggerManager

logger = logging.getLogger(__name__)


class ConnectorManager:
    """
    Connector manager for lifecycle and routing.

    Responsibilities:
    - Manage connector lifecycle (start/stop)
    - Route events from connectors to TriggerManager
    - Manage output channels
    - Route Goal results to correct destinations

    Example:
        ```python
        from harness.connectors import (
            ConnectorManager,
            SlackConnector,
            OutputChannel,
        )

        # Initialize
        manager = ConnectorManager(trigger_manager)

        # Register connectors
        slack = SlackConnector(config=SlackConfig(bot_token="..."))
        manager.register_connector(slack)

        # Register output channels
        manager.register_output_channel(OutputChannel(
            type="slack",
            name="alerts",
            config={"channel": "#alerts"},
        ))

        # Start all
        await manager.start()
        ```
    """

    def __init__(self, trigger_manager: TriggerManager):
        """
        Initialize ConnectorManager.

        Args:
            trigger_manager: TriggerManager instance for event routing
        """
        self.trigger_manager = trigger_manager
        self._connectors: dict[str, Connector] = {}
        self._output_channels: dict[str, OutputChannel] = {}
        self._running = False

    def register_connector(
        self,
        connector: Connector,
        enabled: bool = True,
    ) -> str:
        """
        Register a connector.

        Args:
            connector: Connector instance
            enabled: Whether connector is enabled

        Returns:
            Connector ID
        """
        if not connector.id:
            connector.id = f"{connector.connector_type.value}_{id(connector)}"

        self._connectors[connector.id] = connector
        logger.info(f"Registered connector: {connector.id}")
        return connector.id

    def unregister_connector(self, connector_id: str) -> bool:
        """
        Unregister a connector.

        Args:
            connector_id: Connector ID to unregister

        Returns:
            True if connector was removed
        """
        if connector_id in self._connectors:
            del self._connectors[connector_id]
            logger.info(f"Unregistered connector: {connector_id}")
            return True
        return False

    def register_output_channel(
        self,
        channel: OutputChannel,
    ) -> str:
        """
        Register an output channel.

        Args:
            channel: OutputChannel configuration

        Returns:
            Channel name
        """
        self._output_channels[channel.name] = channel
        logger.info(f"Registered output channel: {channel.name}")
        return channel.name

    def unregister_output_channel(self, name: str) -> bool:
        """
        Unregister an output channel.

        Args:
            name: Channel name

        Returns:
            True if channel was removed
        """
        if name in self._output_channels:
            del self._output_channels[name]
            return True
        return False

    async def start(self) -> None:
        """Start all connectors."""
        self._running = True

        for connector in self._connectors.values():
            try:
                await connector.start(self._on_connector_event)
                logger.info(f"Started connector: {connector.id}")
            except Exception as e:
                logger.error(f"Failed to start connector {connector.id}: {e}")

    async def stop(self) -> None:
        """Stop all connectors."""
        self._running = False

        for connector in self._connectors.values():
            try:
                await connector.stop()
            except Exception as e:
                logger.error(f"Error stopping connector {connector.id}: {e}")

    async def _on_connector_event(self, event: ConnectorEvent) -> None:
        """
        Handle connector event (async).

        Converts ConnectorEvent to TriggerEvent and sends to TriggerManager.

        Note: This method is async to avoid blocking in async event loops
        (e.g., Slack Socket Mode).
        """
        # Import here to avoid circular dependency

        # Convert to TriggerEvent
        trigger_event = TriggerEvent(
            trigger_type=TriggerType.EVENT,
            trigger_id=event.connector_id,
            payload={
                "connector_type": event.connector_type.value,
                "event_type": event.event_type,
                "source": event.source,
                "user_id": event.user_id,
                "channel_id": event.channel_id,
                **event.payload,
            },
            routing_metadata=event.routing_metadata,
        )

        # Send to TriggerManager (async)
        await self.trigger_manager.enqueue_event(trigger_event)

    async def route_output(
        self,
        result: Any,  # GoalResult
        channels: list[str],
        routing_metadata: dict[str, Any] | None = None,
    ) -> list[OutputResult]:
        """
        Route Goal result to specified channels.

        Args:
            result: Goal execution result
            channels: List of output channel names
            routing_metadata: Metadata for "reply to source"
                Example: {"slack_thread_ts": "17123456.0001"}

        Returns:
            List of OutputResult
        """
        outputs = []

        for channel_name in channels:
            channel = self._output_channels.get(channel_name)
            if not channel:
                logger.warning(f"Output channel not found: {channel_name}")
                continue

            output = await self._send_to_channel(result, channel, routing_metadata)
            outputs.append(output)

        return outputs

    async def _send_to_channel(
        self,
        result: Any,
        channel: OutputChannel,
        routing_metadata: dict[str, Any] | None = None,
    ) -> OutputResult:
        """
        Send result to a specific channel.

        Supports routing_metadata for "reply to original thread" functionality.
        """
        try:
            if channel.type == "slack":
                from harness.connectors.slack import SlackConnector

                connector = self._find_connector(ConnectorType.SLACK)
                if connector and isinstance(connector, SlackConnector):
                    # Use routing_metadata for thread reply
                    thread_ts = None
                    if routing_metadata:
                        thread_ts = routing_metadata.get(RoutingKeys.SLACK_THREAD_TS)

                    success = await connector.send_message(
                        channel=channel.config.get("channel", "#general"),
                        text=getattr(result, "final_response", None) or "Task completed",
                        thread_ts=thread_ts,
                    )
                    return OutputResult(
                        channel_name=channel.name,
                        success=success,
                    )

            elif channel.type == "github":
                from harness.connectors.github import GitHubConnector

                connector = self._find_connector(ConnectorType.GITHUB)
                if connector and isinstance(connector, GitHubConnector):
                    # Use routing_metadata for PR/Issue context
                    pr_number = None
                    repo = channel.config.get("repo", "")

                    if routing_metadata:
                        pr_number = routing_metadata.get(RoutingKeys.GITHUB_PR_NUMBER)
                        if not repo:
                            repo = routing_metadata.get(RoutingKeys.GITHUB_REPO, "")

                    if pr_number and repo:
                        success = await connector.create_pr_comment(
                            repo=repo,
                            pr_number=pr_number,
                            body=getattr(result, "final_response", None) or "Task completed",
                        )
                        return OutputResult(
                            channel_name=channel.name,
                            success=success,
                        )

            elif channel.type == "webhook":
                # Send to external webhook
                try:
                    import aiohttp

                    async with aiohttp.ClientSession() as session:
                        payload = {
                            "result": getattr(result, "final_response", None),
                            "status": getattr(result, "status", "unknown"),
                        }
                        if routing_metadata:
                            payload["routing"] = routing_metadata

                        await session.post(
                            channel.config.get("url"),
                            json=payload,
                            headers=channel.config.get("headers", {}),
                        )
                    return OutputResult(channel_name=channel.name, success=True)

                except ImportError:
                    logger.warning("aiohttp not installed for webhook output")
                    return OutputResult(
                        channel_name=channel.name,
                        success=False,
                        error="aiohttp not installed",
                    )

            elif channel.type == "file":
                # Write to file
                import os

                path = channel.config.get("path", "output.txt")
                os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

                with open(path, "a") as f:
                    f.write(f"\n---\n{getattr(result, 'final_response', 'Task completed')}\n")

                return OutputResult(channel_name=channel.name, success=True)

            else:
                return OutputResult(
                    channel_name=channel.name,
                    success=False,
                    error=f"Unknown channel type: {channel.type}",
                )

        except Exception as e:
            logger.error(f"Failed to send to channel {channel.name}: {e}")
            return OutputResult(
                channel_name=channel.name,
                success=False,
                error=str(e),
            )

    def _find_connector(self, connector_type: ConnectorType) -> Connector | None:
        """Find a connector by type."""
        for connector in self._connectors.values():
            if connector.connector_type == connector_type:
                return connector
        return None

    def list_connectors(self) -> list[dict[str, Any]]:
        """List all connectors with their status."""
        return [
            {
                "id": connector.id,
                "type": connector.connector_type.value,
                "state": connector.state.value,
            }
            for connector in self._connectors.values()
        ]

    def list_output_channels(self) -> list[str]:
        """List all output channel names."""
        return list(self._output_channels.keys())

    @property
    def connector_count(self) -> int:
        """Get number of registered connectors."""
        return len(self._connectors)

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running
