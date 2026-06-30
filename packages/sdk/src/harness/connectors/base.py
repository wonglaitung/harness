"""
Connector abstract base class for external system integration.

This module provides the Connector ABC that all external system
integrations must implement.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any, Callable

from harness.connectors.types import ConnectorEvent, ConnectorState, ConnectorType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Type alias for async event callback
EventCallback = Callable[[ConnectorEvent], Coroutine[Any, Any, None]]


class Connector(ABC):
    """
    Connector abstract base class.

    All external system integrations must inherit from this class.

    Key requirements:
    - Event callback must be async (to avoid blocking event loops)
    - Connector should be stateless regarding event context
    - Support health_check for monitoring

    Example:
        ```python
        class MyConnector(Connector):
            connector_type = ConnectorType.CUSTOM

            async def start(self, event_callback: EventCallback) -> None:
                self._callback = event_callback
                self.state = ConnectorState.RUNNING
                # Start listening for events...

            async def stop(self) -> None:
                self.state = ConnectorState.STOPPED

            def create_event(
                self,
                event_type: str,
                payload: dict[str, Any],
                source: str = "",
                routing_metadata: dict[str, Any] | None = None,
            ) -> ConnectorEvent:
                return ConnectorEvent(
                    connector_type=self.connector_type,
                    connector_id=self.id,
                    event_type=event_type,
                    source=source,
                    payload=payload,
                    routing_metadata=routing_metadata or {},
                )
        ```
    """

    connector_type: ConnectorType
    id: str = ""
    state: ConnectorState = ConnectorState.IDLE

    @abstractmethod
    async def start(self, event_callback: EventCallback) -> None:
        """
        Start the connector.

        Args:
            event_callback: Async callback function to send events to ConnectorManager

        Note:
            The callback MUST be an async function to avoid blocking
            async event loops (e.g., Slack Socket Mode).
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the connector."""
        pass

    @abstractmethod
    def create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "",
        routing_metadata: dict[str, Any] | None = None,
    ) -> ConnectorEvent:
        """
        Create a standardized connector event.

        Args:
            event_type: Event type identifier
            payload: Event-specific data
            source: Source identifier (e.g., username, repository)
            routing_metadata: Metadata for routing responses back to source

        Returns:
            Standardized ConnectorEvent
        """
        pass

    def is_running(self) -> bool:
        """Check if connector is running."""
        return self.state == ConnectorState.RUNNING

    async def health_check(self) -> bool:
        """
        Perform health check.

        Returns:
            True if connector is healthy
        """
        return self.is_running()

    def _generate_id(self) -> str:
        """Generate a unique connector ID."""
        return f"{self.connector_type.value}_{uuid.uuid4().hex[:8]}"

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(id='{self.id}', state={self.state.value})"
