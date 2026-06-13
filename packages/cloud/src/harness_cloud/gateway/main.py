"""
Gateway main entry point.

Provides:
- REST API endpoints
- WebSocket endpoint with authentication
- CORS configuration
- Lifespan management

Reference: packages/cloud/docs/03-gateway.md
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from harness_cloud.gateway.auth import User, verify_token
from harness_cloud.gateway.config import GatewayConfig, Settings
from harness_cloud.gateway.container_manager import ContainerManager
from harness_cloud.gateway.docker_manager import DockerManager
from harness_cloud.gateway.rate_limiter import RedisRateLimiter
from harness_cloud.gateway.tunnel import WebSocketTunnel

logger = logging.getLogger(__name__)

# Configuration
settings = Settings.from_env()
config = GatewayConfig(
    jwt_secret=settings.jwt_secret or config.jwt_secret,
    redis_url=settings.redis_url or config.redis_url,
    environment=settings.environment or config.environment,
)

# Global instances
container_manager: ContainerManager
rate_limiter: RedisRateLimiter


class SessionCreateResponse(BaseModel):
    """Response for session creation."""

    session_id: str
    container_id: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    containers: int = 0


# Lifespan
async def lifespan(app: FastAPI):
    """Initialize and cleanup services."""
    global container_manager, rate_limiter

    # Initialize container manager with gateway config
    container_manager = DockerManager(gateway_config=config)
    await container_manager.start()

    # Initialize rate limiter
    rate_limiter = RedisRateLimiter(
        redis_url=config.redis_url,
        max_requests=config.rate_limit_max_requests,
        window_seconds=config.rate_limit_window_seconds,
    )

    logger.info("Gateway started")

    yield

    # Cleanup
    await container_manager.stop()
    logger.info("Gateway stopped")


app = FastAPI(
    title="Harness Gateway",
    description="Harness Cloud Gateway - Container orchestration and message routing",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# REST API Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        containers=len(container_manager._containers),  # type: ignore[attr-defined]
    )


@app.post("/api/sessions", response_model=SessionCreateResponse)
async def create_session(user: User = Depends(lambda: None)):  # Placeholder auth
    """
    Create new session.

    1. Check rate limit
    2. Create sandbox container
    3. Return session ID
    """
    # TODO: Implement proper auth dependency
    # For MVP, accept requests without auth for testing
    user_id = user.id if user else "anonymous"

    # Rate limit check
    if user_id != "anonymous" and not rate_limiter.check(user_id):
        raise HTTPException(429, "Rate limit exceeded")

    # Generate session ID
    session_id = str(uuid.uuid4())[:8]

    # Create container
    try:
        info = await container_manager.create_container(
            session_id=session_id,
            user_id=user_id,
        )
        return SessionCreateResponse(
            session_id=session_id,
            container_id=info.container_id[:12],
        )
    except Exception as e:
        logger.error(f"Failed to create container: {e}")
        raise HTTPException(500, f"Failed to create session: {e}")


@app.delete("/api/sessions/{session_id}")
async def destroy_session(session_id: str, user: User = Depends(lambda: None)):
    """Destroy session and container."""
    user_id = user.id if user else "anonymous"

    info = container_manager.get_container(session_id)
    if not info:
        raise HTTPException(404, "Session not found")

    if info.user_id != user_id and user_id != "anonymous":
        raise HTTPException(403, "Not authorized")

    await container_manager.destroy_container(session_id)
    return {"status": "destroyed"}


# =============================================================================
# Static Files (Frontend)
# =============================================================================

# Mount frontend static files if built
# Check multiple possible locations (development and Docker)
FRONTEND_DIST = (
    Path(__file__).parent.parent.parent.parent.parent / "frontend" / "dist"  # Development
    or Path("/app/frontend/dist")  # Docker container
)
if not FRONTEND_DIST.exists():
    FRONTEND_DIST = Path("/app/frontend/dist")

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")
    logger.info(f"Frontend static files mounted from {FRONTEND_DIST}")


@app.get("/")
async def serve_index():
    """Serve frontend index.html."""
    if FRONTEND_DIST.exists():
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            from fastapi.responses import FileResponse
            return FileResponse(index_file)
    return {"message": "Harness Gateway - Frontend not built"}


@app.get("/icon.svg")
async def serve_icon():
    """Serve frontend icon.svg."""
    if FRONTEND_DIST.exists():
        icon_file = FRONTEND_DIST / "icon.svg"
        if icon_file.exists():
            from fastapi.responses import FileResponse
            return FileResponse(icon_file, media_type="image/svg+xml")
    raise HTTPException(404, "Icon not found")


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """
    Session WebSocket endpoint.

    Protocol:
    1. Accept connection
    2. Wait for auth message (token passed in first message)
    3. Verify container ownership
    4. Establish tunnel to container

    Security (ADR-005):
    - Token passed in first message, not URL
    - Prevents token leakage in logs/headers
    """
    logger.info(f"WebSocket connection request for session: {session_id}")
    await websocket.accept()
    logger.info("WebSocket accepted")

    # Wait for auth message (30 second timeout for manual testing)
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
        logger.info(f"Received auth message: {auth_msg[:100]}...")
        auth_data = json.loads(auth_msg)

        if auth_data.get("type") != "auth":
            logger.warning(f"Expected auth message, got: {auth_data.get('type')}")
            await websocket.close(code=4001, reason="Expected auth message")
            return

        token = auth_data.get("token", "")
        logger.info(f"Token received: {token[:20]}...")
    except asyncio.TimeoutError:
        logger.warning("Auth timeout")
        await websocket.close(code=4001, reason="Auth timeout")
        return
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid auth message: {e}")
        await websocket.close(code=4001, reason="Invalid auth message")
        return

    # Verify token
    try:
        user = verify_token(token, config)
        logger.info(f"Token verified, user: {user.id}")
    except ValueError as e:
        logger.warning(f"Token verification failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Get container
    info = container_manager.get_container(session_id)
    if not info:
        logger.warning(f"Session not found: {session_id}")
        await websocket.close(code=4004, reason="Session not found")
        return

    logger.info(f"Container found: {info.container_id[:12]}")

    # Verify ownership
    if info.user_id != user.id and user.id != "anonymous":
        logger.warning(f"Ownership mismatch: container user={info.user_id}, request user={user.id}")
        await websocket.close(code=4003, reason="Not authorized")
        return

    # Update activity timestamp
    info.last_activity = datetime.now()

    # Establish tunnel
    try:
        container_url = container_manager.get_container_url(session_id)
        logger.info(f"Establishing tunnel to: {container_url}")
        tunnel = WebSocketTunnel(container_url)
        await tunnel.connect(websocket)
    except Exception as e:
        logger.error(f"Tunnel error: {e}", exc_info=True)
    finally:
        # WebSocket disconnected - mark container as draining
        # Container will be cleaned up after graceful_shutdown_timeout
        logger.info(f"WebSocket closed, marking container {session_id} as draining")
        await container_manager.mark_draining(session_id)
