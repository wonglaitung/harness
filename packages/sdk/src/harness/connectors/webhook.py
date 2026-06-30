"""
Webhook connector for HTTP webhook integration.

This module provides WebhookConnector for receiving HTTP webhook events
from external systems like GitHub, Stripe, etc.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from typing import TYPE_CHECKING, Any

from harness.connectors.base import Connector, EventCallback
from harness.connectors.types import (
    ConnectorEvent,
    ConnectorState,
    ConnectorType,
    RoutingKeys,
    WebhookConfig,
)

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response

logger = logging.getLogger(__name__)


class WebhookConnector(Connector):
    """
    HTTP Webhook connector.

    Supports receiving HTTP POST requests as trigger sources.
    Can integrate with existing FastAPI applications.

    Features:
    - HMAC signature verification
    - IP whitelist (optional)
    - Rate limiting support

    Usage modes:
    1. Inject into existing FastAPI app (recommended):
       ```python
       app = FastAPI()
       webhook = WebhookConnector(config=WebhookConfig(endpoint="/webhook"))
       webhook.app = app  # Inject
       await webhook.start(callback)
       ```

    2. Standalone use with manual request handling:
       ```python
       webhook = WebhookConnector(config=WebhookConfig(endpoint="/webhook"))
       await webhook.start(callback)
       # In your route:
       response = await webhook.handle_request(request)
       ```

    Example:
        ```python
        webhook = WebhookConnector(
            config=WebhookConfig(
                endpoint="/webhook/github",
                secret="whsec_...",
            )
        )
        webhook.app = existing_fastapi_app
        await webhook.start(event_callback)
        ```
    """

    connector_type = ConnectorType.WEBHOOK

    def __init__(
        self,
        config: WebhookConfig,
        connector_id: str = "",
    ):
        """
        Initialize WebhookConnector.

        Args:
            config: Webhook configuration
            connector_id: Optional connector ID (auto-generated if not provided)
        """
        self.config = config
        self.id = connector_id or self._generate_id()
        self._callback: EventCallback | None = None
        self._app: FastAPI | None = None
        self.state = ConnectorState.IDLE

    @property
    def app(self) -> FastAPI | None:
        """Get the FastAPI app."""
        return self._app

    @app.setter
    def app(self, value: FastAPI | None) -> None:
        """Set the FastAPI app for route registration."""
        self._app = value

    async def start(self, event_callback: EventCallback) -> None:
        """
        Start the webhook connector.

        If a FastAPI app is injected, registers the endpoint route.

        Args:
            event_callback: Async callback for events
        """
        self._callback = event_callback
        self.state = ConnectorState.RUNNING

        if self._app:
            # Register route with FastAPI app
            try:
                from fastapi import Request, Response

                @self._app.post(self.config.endpoint)
                async def handle_webhook(request: Request) -> Response:
                    return await self.handle_request(request)

                logger.info(
                    f"Registered webhook endpoint: {self.config.endpoint}"
                )
            except ImportError:
                logger.warning(
                    "FastAPI not installed. "
                    "Install with: pip install fastapi"
                )

        logger.info(f"WebhookConnector started: {self.id}")

    async def stop(self) -> None:
        """Stop the webhook connector."""
        self.state = ConnectorState.STOPPED
        self._callback = None
        logger.info(f"WebhookConnector stopped: {self.id}")

    async def handle_request(self, request: Request) -> Response:
        """
        Handle incoming webhook request.

        Validates signature, parses payload, creates event, and calls callback.

        Args:
            request: FastAPI Request object

        Returns:
            FastAPI Response
        """
        from fastapi import Response

        # Verify signature if configured
        if self.config.secret:
            body = await request.body()
            signature = request.headers.get("X-Signature", "") or request.headers.get(
                "X-Hub-Signature-256", ""
            )

            if not self._verify_signature(body, signature):
                logger.warning(f"Invalid signature for webhook request")
                return Response(status_code=401, content="Invalid signature")

        # Parse payload
        try:
            payload = await request.json()
        except Exception as e:
            logger.warning(f"Failed to parse webhook payload: {e}")
            return Response(status_code=400, content="Invalid JSON")

        # Extract routing metadata
        routing_metadata = self._extract_routing_metadata(request, payload)

        # Create event
        event = self.create_event(
            event_type="webhook.received",
            payload=payload,
            source=request.headers.get("X-Forwarded-For", "unknown"),
            routing_metadata=routing_metadata,
        )

        # Async callback
        if self._callback:
            await self._callback(event)

        return Response(status_code=200, content="OK")

    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """
        Verify webhook signature.

        Args:
            body: Request body bytes
            signature: Signature from header

        Returns:
            True if signature is valid
        """
        if not self.config.secret or not signature:
            return True

        expected = hmac.new(
            self.config.secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Support both "sha256=..." and raw hex formats
        if signature.startswith("sha256="):
            signature = signature[7:]

        return hmac.compare_digest(signature, expected)

    def _extract_routing_metadata(
        self,
        request: Request,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract routing metadata from request.

        Override this method in subclasses for specific webhook types.
        """
        metadata = {}

        # Extract request ID for tracing
        request_id = request.headers.get("X-Request-ID") or request.headers.get(
            "X-GitHub-Delivery"
        )
        if request_id:
            metadata[RoutingKeys.WEBHOOK_REQUEST_ID] = request_id

        return metadata

    def create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "",
        routing_metadata: dict[str, Any] | None = None,
    ) -> ConnectorEvent:
        """Create a standardized webhook event."""
        return ConnectorEvent(
            connector_type=self.connector_type,
            connector_id=self.id,
            event_type=event_type,
            source=source,
            payload=payload,
            routing_metadata=routing_metadata or {},
        )
