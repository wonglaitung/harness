"""
WebSocket tunnel for bidirectional message forwarding.

Provides tunneling between:
Frontend WebSocket <-> Gateway <-> Container WebSocket

Reference: packages/cloud/docs/03-gateway.md (Tunnel section)
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import websockets
from websockets.client import WebSocketClientProtocol

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketTunnel:
    """
    Bidirectional WebSocket tunnel.

    Forwards messages between frontend and container:
    - Frontend messages -> Container
    - Container messages -> Frontend
    """

    def __init__(self, container_url: str):
        """
        Initialize tunnel.

        Args:
            container_url: WebSocket URL for container agent
                          (e.g., ws://172.18.0.2:8000/ws/run)
        """
        self.container_url = container_url
        self._frontend_ws: WebSocket | None = None
        self._container_ws: WebSocketClientProtocol | None = None
        self._running = False

    async def connect(self, frontend_ws: WebSocket) -> None:
        """
        Establish bidirectional tunnel.

        1. Connect to container agent
        2. Start bidirectional forwarding tasks

        Args:
            frontend_ws: Frontend WebSocket connection
        """
        self._frontend_ws = frontend_ws
        self._running = True

        # Connect to container
        logger.info(f"Connecting to container: {self.container_url}")
        try:
            self._container_ws = await websockets.connect(self.container_url)
            logger.info("Container WebSocket connected")

            # Bidirectional forwarding
            await asyncio.gather(
                self._forward_to_container(),
                self._forward_to_frontend(),
            )
        except Exception as e:
            logger.error(f"Failed to connect to container: {e}")
            raise

    async def _forward_to_container(self) -> None:
        """
        Forward messages: Frontend -> Container.

        Handles:
        - Text messages from frontend
        - Connection close
        """
        try:
            while self._running:
                data = await self._frontend_ws.receive_text()  # type: ignore[misc]
                if self._container_ws:
                    await self._container_ws.send(data)
        except Exception as e:
            logger.debug(f"Frontend->Container forward ended: {e}")
            self._running = False

    async def _forward_to_frontend(self) -> None:
        """
        Forward messages: Container -> Frontend.

        Handles:
        - Text messages from container
        - Connection close
        """
        try:
            while self._running and self._container_ws:
                data = await self._container_ws.recv()
                if self._frontend_ws:
                    await self._frontend_ws.send_text(data)  # type: ignore[misc]
        except Exception as e:
            logger.debug(f"Container->Frontend forward ended: {e}")
            self._running = False

    def close(self) -> None:
        """Close tunnel connections."""
        self._running = False