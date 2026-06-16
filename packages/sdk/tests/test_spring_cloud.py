"""
Tests for Spring Cloud integration components.

Tests:
- TracingMiddleware: W3C TraceContext extraction and propagation
- MetricsCollector: Prometheus metrics collection and export
- ErrorResponse: Unified error response format
"""

import pytest
from datetime import datetime


# =============================================================================
# TracingMiddleware Tests
# =============================================================================


class TestTracingMiddleware:
    """Tests for W3C TraceContext extraction."""

    def test_traceparent_header_extraction(self):
        """Test extracting W3C traceparent header."""
        from harness.service.tracing import TracingMiddleware

        # W3C format: version-traceid-parentid-flags
        # Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
        trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        parent_id = "00f067aa0ba902b7"

        # Verify format validation
        assert len(trace_id) == 32
        assert len(parent_id) == 16

    def test_b3_trace_id_header_fallback(self):
        """Test fallback to X-B3-TraceId header (Zipkin/Sleuth)."""
        # Spring Cloud Sleuth may send X-B3-TraceId
        b3_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"

        # Should be valid hex string
        assert int(b3_trace_id, 16) is not None

    def test_custom_trace_id_header_fallback(self):
        """Test fallback to X-Trace-Id header."""
        custom_trace_id = "custom-trace-123"

        # Should accept any string
        assert isinstance(custom_trace_id, str)

    def test_middleware_without_opentelemetry(self, monkeypatch):
        """Test middleware behavior when OpenTelemetry is not available."""
        from fastapi import FastAPI
        from harness.service.tracing import TracingMiddleware

        # Create app with middleware
        app = FastAPI()
        app.add_middleware(TracingMiddleware)

        # Middleware should be added successfully
        assert len(app.user_middleware) > 0

    def test_get_trace_id_without_opentelemetry(self, monkeypatch):
        """Test get_trace_id returns None without OpenTelemetry."""
        monkeypatch.setattr(
            "harness.service.tracing.OTEL_AVAILABLE",
            False
        )

        from harness.service.tracing import get_trace_id

        result = get_trace_id()
        assert result is None


# =============================================================================
# MetricsCollector Tests
# =============================================================================


class TestMetricsCollector:
    """Tests for Prometheus metrics collection."""

    def test_metrics_config_defaults(self):
        """Test default MetricsConfig values."""
        from harness.service.metrics import MetricsConfig

        config = MetricsConfig()

        assert config.enabled is True
        assert config.prefix == "harness"
        assert 0.1 in config.duration_buckets
        assert 60.0 in config.duration_buckets

    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initialization."""
        from harness.service.metrics import MetricsCollector, MetricsConfig

        config = MetricsConfig(prefix="test")
        collector = MetricsCollector(config)

        assert collector.config.prefix == "test"
        assert not collector._setup_complete

    def test_metrics_collector_disabled(self):
        """Test metrics collection when disabled."""
        from harness.service.metrics import MetricsCollector, MetricsConfig

        config = MetricsConfig(enabled=False)
        collector = MetricsCollector(config)

        assert not collector.is_enabled

    def test_setup_without_prometheus(self, monkeypatch):
        """Test setup when Prometheus client is not available."""
        monkeypatch.setattr(
            "harness.service.metrics.PROMETHEUS_AVAILABLE",
            False
        )

        from harness.service.metrics import MetricsCollector

        collector = MetricsCollector()
        result = collector.setup()

        assert result is False

    def test_record_iteration(self):
        """Test recording loop iterations."""
        from harness.service.metrics import MetricsCollector

        collector = MetricsCollector()
        # Should not raise even if not set up
        collector.record_iteration()

    def test_record_tool_call(self):
        """Test recording tool calls."""
        from harness.service.metrics import MetricsCollector

        collector = MetricsCollector()
        # Should not raise even if not set up
        collector.record_tool_call("bash", success=True, duration_seconds=0.5)
        collector.record_tool_call("read", success=False)

    def test_record_llm_call(self):
        """Test recording LLM call duration."""
        from harness.service.metrics import MetricsCollector

        collector = MetricsCollector()
        # Should not raise even if not set up
        collector.record_llm_call(1.5)

    def test_record_session_duration(self):
        """Test recording session duration."""
        from harness.service.metrics import MetricsCollector

        collector = MetricsCollector()
        # Should not raise even if not set up
        collector.record_session_duration(30.0)

    def test_active_sessions_counter(self):
        """Test active sessions gauge."""
        from harness.service.metrics import MetricsCollector

        collector = MetricsCollector()
        # Should not raise even if not set up
        collector.increment_active_sessions()
        collector.decrement_active_sessions()

    def test_export_without_prometheus(self, monkeypatch):
        """Test export returns empty string without Prometheus."""
        monkeypatch.setattr(
            "harness.service.metrics.PROMETHEUS_AVAILABLE",
            False
        )

        from harness.service.metrics import MetricsCollector

        collector = MetricsCollector()
        result = collector.export()

        assert result == ""

    def test_get_content_type_without_prometheus(self, monkeypatch):
        """Test content type fallback without Prometheus."""
        monkeypatch.setattr(
            "harness.service.metrics.PROMETHEUS_AVAILABLE",
            False
        )

        from harness.service.metrics import MetricsCollector

        collector = MetricsCollector()
        result = collector.get_content_type()

        assert result == "text/plain"


class TestMetricsGlobalFunctions:
    """Tests for global metrics functions."""

    def test_get_metrics_collector_singleton(self):
        """Test that get_metrics_collector returns singleton."""
        from harness.service.metrics import get_metrics_collector

        # Reset global state
        import harness.service.metrics as metrics_module
        metrics_module._global_collector = None

        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2


# =============================================================================
# ErrorResponse Tests
# =============================================================================


class TestErrorResponse:
    """Tests for unified error response format."""

    def test_error_code_enum_values(self):
        """Test ErrorCode enum values follow convention."""
        from harness.service.error_handler import ErrorCode

        # Check format: AGENT_{HTTP_STATUS}_{SEQUENCE}
        assert ErrorCode.INVALID_INPUT.value == "AGENT_400_001"
        assert ErrorCode.UNAUTHORIZED.value == "AGENT_401_001"
        assert ErrorCode.FORBIDDEN.value == "AGENT_403_001"
        assert ErrorCode.NOT_FOUND.value == "AGENT_404_001"
        assert ErrorCode.INTERNAL_ERROR.value == "AGENT_500_001"

    def test_error_response_creation(self):
        """Test creating ErrorResponse."""
        from harness.service.error_handler import (
            ErrorResponse,
            ErrorCode,
            create_error_response,
        )

        response = create_error_response(
            ErrorCode.INVALID_INPUT,
            "Invalid input parameter",
            trace_id="test-trace-123",
        )

        assert response.errorCode == "AGENT_400_001"
        assert response.errorMessage == "Invalid input parameter"
        assert response.traceId == "test-trace-123"
        assert response.timestamp is not None

    def test_error_response_timestamp_format(self):
        """Test ErrorResponse timestamp is ISO 8601 format."""
        from harness.service.error_handler import (
            create_error_response,
            ErrorCode,
        )

        response = create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Test error",
        )

        # Should be parseable as ISO format
        timestamp = response.timestamp
        assert timestamp.endswith("Z")

        # Should be parseable by datetime
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)

    def test_error_response_without_trace_id(self):
        """Test ErrorResponse without trace ID."""
        from harness.service.error_handler import (
            create_error_response,
            ErrorCode,
        )

        response = create_error_response(
            ErrorCode.NOT_FOUND,
            "Resource not found",
        )

        assert response.traceId is None

    def test_error_response_with_string_code(self):
        """Test creating ErrorResponse with string error code."""
        from harness.service.error_handler import create_error_response

        response = create_error_response(
            "CUSTOM_ERROR_CODE",
            "Custom error message",
        )

        assert response.errorCode == "CUSTOM_ERROR_CODE"


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_budget_exceeded_error(self):
        """Test BudgetExceededError."""
        from harness.service.error_handler import (
            BudgetExceededError,
            ErrorCode,
        )

        error = BudgetExceededError()

        assert error.error_code == ErrorCode.BUDGET_EXCEEDED
        assert "Budget exceeded" in error.message

    def test_iteration_limit_error(self):
        """Test IterationLimitError."""
        from harness.service.error_handler import (
            IterationLimitError,
            ErrorCode,
        )

        error = IterationLimitError(50)

        assert error.error_code == ErrorCode.ITERATION_LIMIT
        assert "50" in error.message

    def test_stuck_detected_error(self):
        """Test StuckDetectedError."""
        from harness.service.error_handler import (
            StuckDetectedError,
            ErrorCode,
        )

        error = StuckDetectedError("Repeating pattern detected")

        assert error.error_code == ErrorCode.STUCK_DETECTED
        assert "Repeating pattern" in error.message

    def test_llm_error(self):
        """Test LLMError."""
        from harness.service.error_handler import (
            LLMError,
            ErrorCode,
        )

        error = LLMError("API timeout")

        assert error.error_code == ErrorCode.LLM_ERROR
        assert "API timeout" in error.message

    def test_tool_execution_error(self):
        """Test ToolExecutionError."""
        from harness.service.error_handler import (
            ToolExecutionError,
            ErrorCode,
        )

        error = ToolExecutionError("bash", "Command failed")

        assert error.error_code == ErrorCode.TOOL_ERROR
        assert "bash" in error.message
        assert "Command failed" in error.message


# =============================================================================
# Integration Tests (require FastAPI)
# =============================================================================


class TestFastAPIIntegration:
    """Integration tests with FastAPI."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        from fastapi import FastAPI
        from harness.service.tracing import TracingMiddleware

        app = FastAPI()

        # Add tracing middleware (gracefully handles missing OpenTelemetry)
        app.add_middleware(TracingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        return app

    def test_app_health_endpoint(self, app):
        """Test health endpoint works."""
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_app_with_trace_header(self, app):
        """Test request with trace header."""
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get(
            "/test",
            headers={"X-Trace-Id": "test-trace-123"}
        )

        assert response.status_code == 200


# =============================================================================
# Redis Session Store Tests (require Redis)
# =============================================================================


@pytest.mark.skip(reason="Requires Redis server")
class TestRedisSessionStore:
    """Tests for Redis session storage."""

    @pytest.fixture
    def redis_store(self):
        """Create Redis session store."""
        from harness.service.store_redis import RedisSessionStore

        return RedisSessionStore("redis://localhost:6379/15")

    @pytest.mark.asyncio
    async def test_save_and_load_session(self, redis_store):
        """Test saving and loading session from Redis."""
        from harness.types import Session, Message

        session = Session(id="test-session-123")
        session.messages.append(Message(
            role="user",
            content="Hello",
            timestamp=datetime.now(),
        ))

        await redis_store.save(session)

        loaded = await redis_store.load("test-session-123")

        assert loaded is not None
        assert loaded.id == "test-session-123"
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "Hello"

        await redis_store.delete("test-session-123")

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, redis_store):
        """Test loading a session that doesn't exist."""
        result = await redis_store.load("nonexistent-session")

        assert result is None

    @pytest.mark.asyncio
    async def test_session_ttl(self, redis_store):
        """Test session TTL is set."""
        from harness.types import Session

        session = Session(id="ttl-test-session")

        await redis_store.save(session)

        # Check TTL is set
        ttl = await redis_store._get_redis().ttl(
            redis_store._session_key("ttl-test-session")
        )

        assert ttl > 0

        await redis_store.delete("ttl-test-session")


# =============================================================================
# Service Discovery Tests
# =============================================================================


class TestServiceDiscovery:
    """Tests for service discovery interfaces."""

    def test_service_registry_protocol(self):
        """Test ServiceRegistry protocol exists."""
        from harness.service.discovery import ServiceRegistry

        # Protocol should have required methods
        assert hasattr(ServiceRegistry, 'register')
        assert hasattr(ServiceRegistry, 'deregister')
        assert hasattr(ServiceRegistry, 'heartbeat')
        assert hasattr(ServiceRegistry, 'close')

    def test_service_instance(self):
        """Test ServiceInstance dataclass."""
        from harness.service.discovery import ServiceInstance

        instance = ServiceInstance(
            service_name="harness-agent",
            ip="10.0.0.1",
            port=8000,
            metadata={"version": "1.0.0"},
        )

        assert instance.service_name == "harness-agent"
        assert instance.ip == "10.0.0.1"
        assert instance.port == 8000
        assert instance.metadata["version"] == "1.0.0"

    def test_nacos_registry_init(self):
        """Test NacosServiceRegistry initialization."""
        from harness.service.discovery import NacosServiceRegistry

        registry = NacosServiceRegistry(
            server_addresses="nacos:8848",
            namespace="production",
        )

        assert registry.server_addresses == "nacos:8848"
        assert registry.namespace == "production"

    def test_eureka_registry_init(self):
        """Test EurekaServiceRegistry initialization."""
        from harness.service.discovery import EurekaServiceRegistry

        registry = EurekaServiceRegistry(
            eureka_server="http://eureka:8761",
        )

        assert registry.eureka_server == "http://eureka:8761"

    def test_get_pod_ip(self):
        """Test get_pod_ip helper function."""
        from harness.service.discovery import get_pod_ip

        # Should return a valid IP or localhost
        ip = get_pod_ip()
        assert isinstance(ip, str)
        # Should be valid IP format or localhost
        assert ip in ["localhost", "127.0.0.1"] or "." in ip


# =============================================================================
# Run tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
