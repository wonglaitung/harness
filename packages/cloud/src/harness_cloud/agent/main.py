"""
Container Agent - FastAPI service running inside Docker sandbox.

This module provides:
1. WebSocket endpoint for agent communication
2. Heartbeat detection
3. Memory soft limit configuration

Reference: packages/cloud/docs/02-agent.md
"""

from __future__ import annotations

import asyncio
import json
import logging
import resource
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from harness_cloud.agent.config import AgentConfig
from harness_cloud.agent.sdk_bridge import SDKBridge
from harness_cloud.common.messages import (
    MessageEnvelope,
    MessageType,
    RunRequest,
    create_message,
)

logger = logging.getLogger(__name__)

# Global config
config = AgentConfig()


def setup_memory_limit() -> None:
    """
    Set process memory soft limit.

    When memory exceeds 3.8GB, Python raises MemoryError instead of
    being killed by Linux OOM Killer (SIGKILL). This allows SDKBridge
    to catch and convert to a friendly WebSocket error message.

    Limitations:
    1. C extensions (numpy) may not catch MemoryError correctly
    2. Child processes (BashTool) are not limited
    3. Process can still be killed by Linux OOM Killer

    Solution:
    - Keep this soft limit as first defense
    - Rely on Docker/K8s mem_limit as fallback
    - Gateway's _cleanup_loop handles OOM-killed container cleanup
    """
    try:
        soft_limit = config.memory_soft_limit
        hard_limit = config.memory_hard_limit
        resource.setrlimit(resource.RLIMIT_AS, (soft_limit, hard_limit))
        logger.info(f"Memory limit set: soft={soft_limit}, hard={hard_limit}")
    except Exception as e:
        logger.warning(f"Failed to set memory limit: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup initialization."""
    setup_memory_limit()
    yield


app = FastAPI(title="Harness Container Agent", lifespan=lifespan)


@app.websocket("/ws/run")
async def websocket_run(websocket: WebSocket):
    """
    Main WebSocket endpoint.

    Protocol:
    1. Client sends RunRequest
    2. Agent sends ACK
    3. Agent streams ProgressEvents
    4. Agent sends RunResult

    Heartbeat:
    - Client sends ping
    - Agent responds pong
    - Detect timeout disconnection
    """
    await websocket.accept()
    bridge = SDKBridge(config)
    session_id = None

    # Heartbeat detection
    last_ping = asyncio.get_event_loop().time()
    _closed = False  # Prevent double close

    async def heartbeat_monitor():
        """Monitor heartbeat timeout."""
        while True:
            await asyncio.sleep(30)
            if _closed:
                return
            elapsed = asyncio.get_event_loop().time() - last_ping
            if elapsed > config.heartbeat_timeout:
                logger.warning("Heartbeat timeout, closing connection")
                _closed = True
                try:
                    await websocket.close(code=1001, reason="Heartbeat timeout")
                except Exception:
                    pass  # Ignore double close errors
                return

    heartbeat_task = asyncio.create_task(heartbeat_monitor())

    try:
        while True:
            raw_data = await websocket.receive_text()
            envelope = MessageEnvelope.model_validate_json(raw_data)

            # Handle heartbeat
            if envelope.type == "ping":
                last_ping = asyncio.get_event_loop().time()
                await websocket.send_json({"type": "pong"})
                continue

            if envelope.type == MessageType.RUN_REQUEST:
                request = RunRequest.model_validate(envelope.payload)
                session_id = request.session_id

                # Send ACK
                await websocket.send_json(
                    create_message(MessageType.ACK, {"session_id": session_id})
                )

                # Stream execution
                async for event in bridge.run_stream(request):
                    await websocket.send_json(event)

            elif envelope.type == MessageType.INTERRUPT:
                bridge.interrupt()
                await websocket.send_json(create_message(MessageType.INTERRUPTED, {}))

    except WebSocketDisconnect:
        logger.info(f"Client disconnected, session: {session_id}")
    except Exception as e:
        logger.error(f"Unexpected error in websocket: {e}")
    finally:
        _closed = True
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


@app.get("/health")
async def health_check():
    """Container health check endpoint."""
    return {"status": "healthy"}
