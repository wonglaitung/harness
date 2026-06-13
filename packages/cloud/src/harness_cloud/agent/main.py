"""
Container Agent - FastAPI service running inside Docker sandbox.

This module provides:
1. WebSocket endpoint for agent communication
2. Authentication with API credentials
3. Heartbeat detection
4. Memory soft limit configuration

Protocol (方案 A - 首次认证模式):
1. Client sends auth message with API credentials
2. Agent validates and responds auth_success or auth_failed
3. Client sends run_request messages (no API key needed)
4. Agent streams progress events and returns run_result

Reference: packages/cloud/docs/02-agent.md
"""

from __future__ import annotations

import asyncio
import logging
import resource
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from harness_cloud.agent.config import AgentConfig
from harness_cloud.agent.sdk_bridge import SDKBridge
from harness_cloud.common.messages import (
    AuthFailed,
    AuthRequest,
    AuthSuccess,
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

    Protocol (方案 A - 首次认证模式):
    1. Client sends auth message
    2. Agent validates credentials, responds auth_success/auth_failed
    3. Only after auth_success, client can send run_request
    4. Agent streams progress events, returns run_result

    Heartbeat:
    - Client sends ping
    - Agent responds pong
    - Detect timeout disconnection
    """
    await websocket.accept()
    bridge = SDKBridge(config)
    session_id = None
    authenticated = False
    auth_config: AuthRequest | None = None

    # Heartbeat detection
    last_ping = asyncio.get_event_loop().time()
    _closed = False  # Prevent double close

    async def heartbeat_monitor():
        """Monitor heartbeat timeout."""
        nonlocal _closed
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
            if envelope.type == MessageType.PING:
                last_ping = asyncio.get_event_loop().time()
                await websocket.send_json({"type": "pong"})
                continue

            # Handle authentication
            if envelope.type == MessageType.AUTH:
                if authenticated:
                    # Already authenticated, ignore
                    logger.warning("Received auth while already authenticated")
                    continue

                try:
                    auth_request = AuthRequest.model_validate(envelope.payload)
                    # Validate credentials
                    if not auth_request.api_key:
                        await websocket.send_json(
                            create_message(
                                MessageType.AUTH_FAILED,
                                AuthFailed(
                                    error="API key is required",
                                    error_code="INVALID_API_KEY",
                                ),
                            )
                        )
                        continue

                    # Store auth config
                    auth_config = auth_request
                    authenticated = True

                    await websocket.send_json(
                        create_message(
                            MessageType.AUTH_SUCCESS,
                            AuthSuccess(
                                provider=auth_config.provider,
                                model=auth_config.model,
                            ),
                        )
                    )
                    logger.info(f"Authenticated: provider={auth_config.provider}, model={auth_config.model}")

                except Exception as e:
                    logger.error(f"Auth validation error: {e}")
                    await websocket.send_json(
                        create_message(
                            MessageType.AUTH_FAILED,
                            AuthFailed(
                                error=str(e),
                                error_code="INVALID_AUTH_PAYLOAD",
                            ),
                        )
                    )
                continue

            # Handle run request (requires authentication)
            if envelope.type == MessageType.RUN_REQUEST:
                if not authenticated or not auth_config:
                    await websocket.send_json(
                        create_message(
                            MessageType.ERROR,
                            {"error": "Not authenticated. Send auth message first.", "error_code": "NOT_AUTHENTICATED"},
                        )
                    )
                    continue

                try:
                    request = RunRequest.model_validate(envelope.payload)
                    session_id = request.session_id

                    # Merge request with auth config (request can override)
                    merged_request = auth_config.merge_with_request(request)

                    # Send ACK
                    await websocket.send_json(
                        create_message(MessageType.ACK, {"session_id": session_id})
                    )

                    # Stream execution
                    async for event in bridge.run_stream(merged_request):
                        await websocket.send_json(event)

                except Exception as e:
                    logger.error(f"Run request error: {e}")
                    await websocket.send_json(
                        create_message(
                            MessageType.ERROR,
                            {"error": str(e), "error_code": "INVALID_RUN_REQUEST"},
                        )
                    )
                continue

            # Handle interrupt
            if envelope.type == MessageType.INTERRUPT:
                bridge.interrupt()
                await websocket.send_json(create_message(MessageType.INTERRUPTED, {}))
                continue

            # Unknown message type
            logger.warning(f"Unknown message type: {envelope.type}")
            await websocket.send_json(
                create_message(
                    MessageType.ERROR,
                    {"error": f"Unknown message type: {envelope.type}", "error_code": "UNKNOWN_MESSAGE_TYPE"},
                )
            )

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