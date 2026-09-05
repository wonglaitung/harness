"""
Harness Agent Service - FastAPI wrapper for Spring Cloud integration.

This module provides a production-ready HTTP/WebSocket service wrapper
for AgentHarness, enabling integration with Spring Cloud ecosystem.

Features:
- Health check endpoint (/health)
- Metrics endpoint (/metrics) for Prometheus
- WebSocket streaming for long-running tasks
- TraceID propagation from Spring Cloud Gateway
- Unified error response format

Example:
    ```bash
    # Run with uvicorn
    uvicorn harness.service:app --host 0.0.0.0 --port 8000

    # Run with gunicorn (production)
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker harness.service:app
    ```
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from harness import AgentHarness, HarnessConfig, ProgressEvent
from harness.service.error_handler import (
    ErrorCode,
    create_error_response,
)
from harness.service.metrics import (
    PROMETHEUS_AVAILABLE,
    get_metrics_collector,
)
from harness.service.tracing import TracingMiddleware

# Redis session store (optional)
try:
    from harness.service.store_redis import (
        REDIS_AVAILABLE,
        RedisDistributedLock,
        RedisSessionConfig,
        RedisSessionStore,
    )
except ImportError:
    RedisSessionStore = None
    RedisSessionConfig = None
    RedisDistributedLock = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================


class RunRequest(BaseModel):
    """Request for running agent."""

    prompt: str
    session_id: str | None = None
    model: str | None = None
    max_iterations: int | None = None
    system_prompt: str | None = None


class RunResponse(BaseModel):
    """Response from agent execution."""

    status: str
    content: str
    session_id: str
    iterations: int
    token_usage: dict[str, int]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    checks: dict[str, bool]
    timestamp: str


# =============================================================================
# Application State
# =============================================================================


class AppState:
    """Application state for agent service."""

    def __init__(self):
        self.default_config: HarnessConfig | None = None
        self._agents: dict[str, AgentHarness] = {}

    def get_agent(self, request: RunRequest) -> AgentHarness:
        """Get or create agent for request."""
        # Use default config if available
        config = self.default_config or HarnessConfig()

        # Override with request-specific settings
        if request.model:
            config = HarnessConfig(
                model=request.model,
                max_iterations=request.max_iterations or config.max_iterations,
                system_prompt=request.system_prompt or config.system_prompt,
            )
        elif request.max_iterations:
            config.max_iterations = request.max_iterations
        elif request.system_prompt:
            config.system_prompt = request.system_prompt

        return AgentHarness(config=config)


app_state = AppState()


# =============================================================================
# Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup services."""
    logger.info("Harness Agent Service starting up...")

    # Initialize default config from environment
    app_state.default_config = HarnessConfig.from_env()

    # Initialize metrics collector
    if PROMETHEUS_AVAILABLE:
        get_metrics_collector().setup()
        logger.info("Prometheus metrics enabled")

    yield

    logger.info("Harness Agent Service shutting down...")


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="Harness Agent Service",
    description="AI Agent service for Spring Cloud integration",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tracing middleware for TraceID propagation
app.add_middleware(TracingMiddleware)


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Health check endpoint.

    Returns 503 if any critical dependency is unhealthy.
    This allows Nacos/K8s to automatically remove unhealthy instances.
    """
    checks = {
        "service": True,  # Service itself is running
        # Add more checks as needed:
        # "redis": await check_redis_connection(),
        # "llm": await check_llm_connection(),
    }

    all_healthy = all(checks.values())

    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content=HealthResponse(
            status="healthy" if all_healthy else "unhealthy",
            checks=checks,
            timestamp=datetime.now().isoformat(),
        ).model_dump(),
    )


# =============================================================================
# Prometheus Metrics
# =============================================================================


@app.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Exposes metrics for monitoring Agent execution:
    - harness_loop_iterations_total: Total loop iterations
    - harness_tool_calls_total: Tool calls by name and status
    - harness_llm_tokens_total: Token usage by type
    - harness_session_duration_seconds: Session duration histogram

    Requires: pip install prometheus-client
    """
    if not PROMETHEUS_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Prometheus client not available",
                "message": "Install with: pip install prometheus-client",
            },
        )

    from harness.service.metrics import get_metrics_collector

    collector = get_metrics_collector()
    metrics_data = collector.export()

    return Response(
        content=metrics_data,
        media_type=collector.get_content_type(),
    )


# =============================================================================
# REST API Endpoints
# =============================================================================


@app.post("/api/run", response_model=RunResponse)
async def run_agent(request: Request, body: RunRequest):
    """
    Run agent synchronously.

    Note: For long-running tasks, use WebSocket endpoint instead.
    """
    try:
        agent = app_state.get_agent(body)

        # Run agent
        result = await agent.run(
            prompt=body.prompt,
            session_id=body.session_id,
        )

        return RunResponse(
            status=result.status.value,
            content=result.content,
            session_id=result.session.id,
            iterations=result.iterations,
            token_usage={
                "input": result.token_usage.input_tokens,
                "output": result.token_usage.output_tokens,
            },
        )

    except Exception as e:
        logger.exception(f"Agent execution failed: {e}")
        raise


@app.get("/api/sessions/{session_id}")
async def get_session(request: Request, session_id: str):
    """Get session info."""
    agent = AgentHarness(config=app_state.default_config)
    session = agent.get_session(session_id)

    if session is None:
        return JSONResponse(
            status_code=404,
            content=create_error_response(
                ErrorCode.NOT_FOUND,
                f"Session not found: {session_id}",
                request.headers.get("X-Trace-Id"),
            ).model_dump(),
        )

    return {
        "session_id": session.id,
        "message_count": len(session.messages),
        "created_at": session.created_at.isoformat(),
    }


@app.delete("/api/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear session."""
    agent = AgentHarness(config=app_state.default_config)
    agent.clear_session(session_id)
    return {"status": "cleared"}


# =============================================================================
# WebSocket Endpoint (Long-running Tasks)
# =============================================================================


@app.websocket("/ws/run")
async def run_agent_ws(websocket: WebSocket):
    """
    WebSocket endpoint for streaming agent execution.

    Protocol:
    1. Client sends: {"prompt": "...", "session_id": "optional"}
    2. Server streams: ProgressEvent objects
    3. Server sends: {"type": "done", "result": {...}}

    This is the recommended mode for Spring Cloud integration
    to avoid Gateway timeout issues.
    """
    await websocket.accept()

    try:
        # Receive initial request
        data = await websocket.receive_json()
        request = RunRequest(**data)

        agent = app_state.get_agent(request)

        # Progress callback
        async def on_progress(event: ProgressEvent):
            await websocket.send_json(
                {
                    "type": "progress",
                    "event_type": event.type.value,
                    "message": event.message,
                    "data": event.data,
                    "duration_ms": event.duration_ms,
                }
            )

        # Run agent
        result = await agent.run(
            prompt=request.prompt,
            session_id=request.session_id,
            on_progress=on_progress,
        )

        # Send final result
        await websocket.send_json(
            {
                "type": "done",
                "result": {
                    "status": result.status.value,
                    "content": result.content,
                    "session_id": result.session.id,
                    "iterations": result.iterations,
                    "token_usage": {
                        "input": result.token_usage.input_tokens,
                        "output": result.token_usage.output_tokens,
                    },
                },
            }
        )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        await websocket.send_json(
            {
                "type": "error",
                "error": str(e),
            }
        )


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content=create_error_response(
            ErrorCode.INVALID_INPUT,
            str(exc),
            request.headers.get("X-Trace-Id"),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Internal server error",
            request.headers.get("X-Trace-Id"),
        ).model_dump(),
    )
