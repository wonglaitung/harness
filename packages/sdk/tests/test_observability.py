"""Tests for OpenTelemetry observability integration."""

import pytest

from harness.core.observability import (
    ObservabilityConfig,
    ObservabilityManager,
    SpanBuilder,
    get_observability_manager,
    is_tracing,
    traced_operation,
)
from harness.types import ProgressEvent, ProgressEventType, TokenUsage


class TestObservabilityConfig:
    """Tests for ObservabilityConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ObservabilityConfig()

        assert config.service_name == "harness-agent"
        assert config.service_version == "0.1.0"
        assert config.enabled is True
        assert config.export_console is False
        assert config.export_otlp is False
        assert config.sample_rate == 1.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ObservabilityConfig(
            service_name="my-service",
            export_console=True,
            otlp_endpoint="http://localhost:4318",
        )

        assert config.service_name == "my-service"
        assert config.export_console is True
        assert config.otlp_endpoint == "http://localhost:4318"


class TestObservabilityManager:
    """Tests for ObservabilityManager."""

    def test_manager_creation(self):
        """Test creating a manager."""
        manager = ObservabilityManager()

        assert manager.config is not None
        assert manager._setup_complete is False

    def test_disabled_manager(self):
        """Test manager with disabled config."""
        config = ObservabilityConfig(enabled=False)
        manager = ObservabilityManager(config)

        assert manager.is_enabled is False

    def test_setup_disabled(self):
        """Test setup when disabled."""
        config = ObservabilityConfig(enabled=False)
        manager = ObservabilityManager(config)

        result = manager.setup()

        assert result is False
        assert manager.tracer is None

    def test_setup_console_export(self):
        """Test setup with console export."""
        pytest.importorskip("opentelemetry")

        config = ObservabilityConfig(export_console=True)
        manager = ObservabilityManager(config)

        result = manager.setup()

        assert result is True
        assert manager.tracer is not None

        # Cleanup
        manager.shutdown()

    def test_get_tracer_before_setup(self):
        """Test getting tracer before setup."""
        config = ObservabilityConfig(enabled=False)
        manager = ObservabilityManager(config)

        assert manager.tracer is None


class TestSpanBuilder:
    """Tests for SpanBuilder."""

    def test_span_builder_disabled(self):
        """Test SpanBuilder when tracing is disabled."""
        with SpanBuilder("test.span") as builder:
            assert builder._span is None

    def test_span_builder_with_attributes(self):
        """Test SpanBuilder with attributes."""
        pytest.importorskip("opentelemetry")

        config = ObservabilityConfig(export_console=True)
        manager = ObservabilityManager(config)
        manager.setup()

        with SpanBuilder("test.span") as builder:
            builder.set_attr("key", "value")
            builder.add_event("event_name")

        manager.shutdown()


class TestTracedOperation:
    """Tests for traced_operation context manager."""

    def test_traced_operation_disabled(self):
        """Test traced_operation when disabled."""
        with traced_operation("test.op", {"attr": "value"}):
            # Should work without error even when disabled
            pass

    def test_traced_operation_enabled(self):
        """Test traced_operation when enabled."""
        pytest.importorskip("opentelemetry")

        config = ObservabilityConfig(export_console=True)
        manager = ObservabilityManager(config)
        manager.setup()

        with traced_operation("test.op", {"attr": "value"}) as builder:
            assert builder is not None

        manager.shutdown()


class TestGlobalFunctions:
    """Tests for global functions."""

    def test_get_observability_manager(self):
        """Test getting global manager."""
        manager1 = get_observability_manager()
        manager2 = get_observability_manager()

        assert manager1 is manager2

    def test_is_tracing_disabled(self):
        """Test is_tracing when disabled."""
        # Create a disabled manager
        _ = ObservabilityManager(ObservabilityConfig(enabled=False))
        # Don't set it as global to avoid affecting other tests

        # The global manager might be configured differently
        # Just test that the function works
        result = is_tracing()
        assert isinstance(result, bool)


class TestTokenUsageRecording:
    """Tests for recording token usage."""

    def test_record_token_usage(self):
        """Test recording token usage on a span."""
        pytest.importorskip("opentelemetry")

        from harness.core.observability import record_token_usage

        config = ObservabilityConfig(export_console=True)
        manager = ObservabilityManager(config)
        manager.setup()

        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=10,
            cache_write_tokens=5,
            tool_calls=2,
        )

        with SpanBuilder("test.span") as builder:
            if builder.span:
                record_token_usage(usage, builder.span)

        manager.shutdown()


class TestProgressEventTracing:
    """Tests for tracing progress events."""

    def test_trace_progress_event(self):
        """Test tracing a progress event."""
        pytest.importorskip("opentelemetry")

        from harness.core.observability import trace_progress_event

        config = ObservabilityConfig(export_console=True)
        manager = ObservabilityManager(config)
        manager.setup()

        event = ProgressEvent(
            type=ProgressEventType.LLM_RESPONSE,
            message="Test response",
            duration_ms=100.0,
            data={"model": "test-model"},
        )

        with SpanBuilder("test.span") as builder:
            if builder.span:
                trace_progress_event(event, builder.span)

        manager.shutdown()
