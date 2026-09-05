"""
End-to-end tests for Spring Cloud integration using Docker Compose.

These tests require Docker Compose environment:
    docker-compose -f packages/sdk/docker/docker-compose.test.yml up -d

Run tests:
    pytest packages/sdk/tests/integration/test_spring_cloud_e2e.py -v

Environment variables:
    TEST_API_URL: Base URL for the agent service (default: http://localhost:8000)
    ANTHROPIC_API_KEY or OPENAI_API_KEY: For live LLM tests
"""

import os

import pytest

# =============================================================================
# Configuration
# =============================================================================


TEST_API_URL = os.getenv("TEST_API_URL", "http://localhost:8000")


def is_service_available():
    """Check if the test service is available."""
    try:
        import httpx
        response = httpx.get(f"{TEST_API_URL}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests if service not available
pytestmark = pytest.mark.skipif(
    not is_service_available(),
    reason=(
        "Test service not available. Run: "
        "docker-compose -f packages/sdk/docker/docker-compose.test.yml up -d"
    ),
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def api_client():
    """Create HTTP client for API calls."""
    import httpx

    with httpx.Client(base_url=TEST_API_URL, timeout=60.0) as client:
        yield client


@pytest.fixture
def trace_id():
    """Generate a trace ID for testing."""
    import uuid
    return str(uuid.uuid4()).replace("-", "")[:32]


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheckE2E:
    """End-to-end health check tests."""

    def test_health_endpoint_returns_healthy(self, api_client):
        """Service should report healthy status."""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["service"] is True


# =============================================================================
# Tracing Tests
# =============================================================================


class TestTracingE2E:
    """End-to-end tracing tests."""

    def test_trace_id_propagation(self, api_client, trace_id):
        """Trace ID should be propagated through the request."""
        response = api_client.get(
            "/health",
            headers={"X-Trace-Id": trace_id}
        )

        assert response.status_code == 200
        assert response.headers.get("X-Trace-Id") == trace_id

    def test_w3c_traceparent_propagation(self, api_client, trace_id):
        """W3C traceparent header should be handled."""
        response = api_client.get(
            "/health",
            headers={"traceparent": f"00-{trace_id}-00f067aa0ba902b7-01"}
        )

        assert response.status_code == 200


# =============================================================================
# Metrics Tests
# =============================================================================


class TestMetricsE2E:
    """End-to-end Prometheus metrics tests."""

    def test_metrics_endpoint_returns_prometheus_format(self, api_client):
        """Metrics endpoint should return Prometheus format."""
        response = api_client.get("/metrics")

        # May return 503 if prometheus not installed
        if response.status_code == 503:
            pytest.skip("Prometheus not available")

        assert response.status_code == 200
        content = response.text

        # Check for Prometheus format
        assert "# HELP" in content or "# TYPE" in content or "harness_" in content


# =============================================================================
# Redis Integration Tests
# =============================================================================


class TestRedisIntegrationE2E:
    """End-to-end Redis integration tests."""

    def test_session_persistence_with_redis(self, api_client):
        """Session should be persisted in Redis."""
        # This test would require actual LLM API key
        pytest.skip("Requires LLM API key and actual agent execution")


# =============================================================================
# Agent Execution Tests (Requires LLM API Key)
# =============================================================================


@pytest.mark.skipif(
    not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")),
    reason="Requires ANTHROPIC_API_KEY or OPENAI_API_KEY"
)
class TestAgentExecutionE2E:
    """End-to-end agent execution tests."""

    def test_run_agent_sync(self, api_client, trace_id):
        """Test synchronous agent execution."""
        response = api_client.post(
            "/api/run",
            json={"prompt": "Say 'Hello, World!'"},
            headers={"X-Trace-Id": trace_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "content" in data
        assert "session_id" in data
        assert data["iterations"] >= 1

    def test_run_agent_with_session_continuation(self, api_client):
        """Test session continuation across requests."""
        # First request
        response1 = api_client.post(
            "/api/run",
            json={"prompt": "Remember the number 42"}
        )

        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Second request with same session
        response2 = api_client.post(
            "/api/run",
            json={
                "prompt": "What number did I ask you to remember?",
                "session_id": session_id
            }
        )

        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

    def test_websocket_streaming(self, api_client):
        """Test WebSocket streaming execution."""
        import asyncio
        import json

        import websockets

        async def run_websocket_test():
            uri = "ws://localhost:8000/ws/run"
            async with websockets.connect(uri) as websocket:
                # Send request
                await websocket.send(json.dumps({
                    "prompt": "Count from 1 to 3"
                }))

                # Receive messages
                messages = []
                while True:
                    data = await websocket.recv()
                    message = json.loads(data)
                    messages.append(message)

                    if message.get("type") == "done":
                        break
                    elif message.get("type") == "error":
                        raise Exception(message.get("error"))

                # Should have received some progress events
                assert len(messages) > 0
                assert messages[-1]["type"] == "done"

        asyncio.run(run_websocket_test())


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandlingE2E:
    """End-to-end error handling tests."""

    def test_invalid_request_returns_400(self, api_client):
        """Invalid request should return 400."""
        response = api_client.post("/api/run", json={})

        assert response.status_code == 422  # Validation error

    def test_error_includes_trace_id(self, api_client, trace_id):
        """Error response should include trace ID."""
        response = api_client.post(
            "/api/run",
            json={},
            headers={"X-Trace-Id": trace_id}
        )

        # Trace ID should be in response header
        assert response.headers.get("X-Trace-Id") == trace_id


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformanceE2E:
    """End-to-end performance tests."""

    def test_health_check_response_time(self, api_client):
        """Health check should respond quickly."""
        import time

        start = time.time()
        response = api_client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond within 1 second

    def test_concurrent_health_checks(self, api_client):
        """Service should handle concurrent requests."""
        import concurrent.futures

        def make_request():
            response = api_client.get("/health")
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]

        # All requests should succeed
        assert all(status == 200 for status in results)


# =============================================================================
# Run tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
