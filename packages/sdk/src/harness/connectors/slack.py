"""
Slack connector for Slack App integration.

This module provides SlackConnector for receiving Slack events
and sending messages to Slack channels.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from harness.connectors.base import Connector, EventCallback
from harness.connectors.types import (
    ConnectorEvent,
    ConnectorState,
    ConnectorType,
    RoutingKeys,
    SlackConfig,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SlackConnector(Connector):
    """
    Slack connector for Slack App integration.

    Features:
    - Receive Slack messages and commands
    - Send messages to channels
    - Socket Mode support (no public IP required)
    - Thread reply support via routing_metadata

    Usage:
        ```python
        slack = SlackConnector(
            config=SlackConfig(
                bot_token="xoxb-...",
                app_token="xapp-...",  # For Socket Mode
            )
        )
        await slack.start(event_callback)

        # Send message
        await slack.send_message(
            channel="#general",
            text="Hello!",
            thread_ts="17123456.0001",  # Reply to thread
        )
        ```
    """

    connector_type = ConnectorType.SLACK

    def __init__(
        self,
        config: SlackConfig,
        connector_id: str = "",
    ):
        """
        Initialize SlackConnector.

        Args:
            config: Slack configuration
            connector_id: Optional connector ID
        """
        self.config = config
        self.id = connector_id or self._generate_id()
        self._callback: EventCallback | None = None
        self._client: Any = None  # Slack WebClient
        self._socket_client: Any = None  # Socket Mode client
        self.state = ConnectorState.IDLE

    async def start(self, event_callback: EventCallback) -> None:
        """
        Start the Slack connector.

        If app_token is configured, starts Socket Mode client.

        Args:
            event_callback: Async callback for events
        """
        self._callback = event_callback

        try:
            from slack_sdk.web.async_client import AsyncWebClient

            self._client = AsyncWebClient(token=self.config.bot_token)

            # Start Socket Mode if app_token is provided
            if self.config.app_token:
                await self._start_socket_mode()

            self.state = ConnectorState.RUNNING
            logger.info(f"SlackConnector started: {self.id}")

        except ImportError:
            logger.error("slack_sdk not installed. Install with: pip install slack_sdk")
            self.state = ConnectorState.ERROR
            raise

    async def _start_socket_mode(self) -> None:
        """Start Socket Mode client for receiving events."""
        try:
            from slack_sdk.socket_mode.aiohttp import SocketModeClient

            self._socket_client = SocketModeClient(
                app_token=self.config.app_token,
            )

            # Register event handler
            @self._socket_client.event
            async def handle_event(event: dict) -> None:
                connector_event = self._parse_slack_event(event)
                if connector_event and self._callback:
                    await self._callback(connector_event)

            await self._socket_client.connect()
            logger.info("Slack Socket Mode connected")

        except ImportError:
            logger.warning(
                "slack_sdk[socket_mode] not installed. "
                "Install with: pip install slack_sdk[socket_mode]"
            )
        except Exception as e:
            logger.error(f"Failed to start Socket Mode: {e}")

    def _parse_slack_event(self, event: dict) -> ConnectorEvent | None:
        """
        Parse Slack event into ConnectorEvent.

        Extracts routing_metadata for thread replies.

        Args:
            event: Raw Slack event dict

        Returns:
            ConnectorEvent or None if not applicable
        """
        event_type = event.get("type")

        # Handle message events
        if event_type == "message":
            # Skip bot messages and channel join messages
            if event.get("bot_id") or event.get("subtype") == "channel_join":
                return None

            # Extract routing metadata for thread replies
            routing_metadata = {}

            # Use thread_ts if available, otherwise use message ts
            if event.get("thread_ts"):
                routing_metadata[RoutingKeys.SLACK_THREAD_TS] = event.get("thread_ts")
            elif event.get("ts"):
                routing_metadata[RoutingKeys.SLACK_THREAD_TS] = event.get("ts")

            if event.get("channel"):
                routing_metadata[RoutingKeys.SLACK_CHANNEL_ID] = event.get("channel")

            return self.create_event(
                event_type="slack.message",
                payload={
                    "text": event.get("text"),
                    "user": event.get("user"),
                    "channel": event.get("channel"),
                    "ts": event.get("ts"),
                    "thread_ts": event.get("thread_ts"),
                },
                source=event.get("user", "unknown"),
                routing_metadata=routing_metadata,
            )

        # Handle slash commands
        elif event_type == "slash_command":
            routing_metadata = {
                RoutingKeys.SLACK_CHANNEL_ID: event.get("channel_id"),
            }

            return self.create_event(
                event_type="slack.command",
                payload={
                    "command": event.get("command"),
                    "text": event.get("text"),
                    "user_id": event.get("user_id"),
                    "channel_id": event.get("channel_id"),
                    "trigger_id": event.get("trigger_id"),
                },
                source=event.get("user_id", "unknown"),
                routing_metadata=routing_metadata,
            )

        # Handle app mentions
        elif event_type == "app_mention":
            routing_metadata = {}

            if event.get("thread_ts"):
                routing_metadata[RoutingKeys.SLACK_THREAD_TS] = event.get("thread_ts")
            elif event.get("ts"):
                routing_metadata[RoutingKeys.SLACK_THREAD_TS] = event.get("ts")

            if event.get("channel"):
                routing_metadata[RoutingKeys.SLACK_CHANNEL_ID] = event.get("channel")

            return self.create_event(
                event_type="slack.mention",
                payload={
                    "text": event.get("text"),
                    "user": event.get("user"),
                    "channel": event.get("channel"),
                    "ts": event.get("ts"),
                    "thread_ts": event.get("thread_ts"),
                },
                source=event.get("user", "unknown"),
                routing_metadata=routing_metadata,
            )

        return None

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict] | None = None,
        thread_ts: str | None = None,
    ) -> bool:
        """
        Send a message to a Slack channel.

        Args:
            channel: Channel ID or name
            text: Message text
            blocks: Optional Slack Block Kit blocks
            thread_ts: Thread timestamp to reply to a specific thread

        Returns:
            True if successful
        """
        if not self._client:
            logger.warning("Slack client not initialized")
            return False

        try:
            await self._client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
                thread_ts=thread_ts,
            )
            logger.debug(f"Sent Slack message to {channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False

    async def send_ephemeral(
        self,
        channel: str,
        user: str,
        text: str,
        blocks: list[dict] | None = None,
    ) -> bool:
        """
        Send an ephemeral message (visible only to a specific user).

        Args:
            channel: Channel ID
            user: User ID
            text: Message text
            blocks: Optional Slack Block Kit blocks

        Returns:
            True if successful
        """
        if not self._client:
            return False

        try:
            await self._client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=text,
                blocks=blocks,
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send ephemeral message: {e}")
            return False

    async def stop(self) -> None:
        """Stop the Slack connector."""
        if self._socket_client:
            await self._socket_client.disconnect()
            self._socket_client = None

        self._client = None
        self._callback = None
        self.state = ConnectorState.STOPPED
        logger.info(f"SlackConnector stopped: {self.id}")

    def create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "",
        routing_metadata: dict[str, Any] | None = None,
    ) -> ConnectorEvent:
        """Create a standardized Slack event."""
        return ConnectorEvent(
            connector_type=self.connector_type,
            connector_id=self.id,
            event_type=event_type,
            source=source,
            payload=payload,
            user_id=payload.get("user_id"),
            channel_id=payload.get("channel_id"),
            routing_metadata=routing_metadata or {},
        )
