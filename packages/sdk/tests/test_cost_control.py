"""
Tests for Cost Control system.
"""


import pytest

from harness.core import BudgetStatus, CostConfig, CostController
from harness.types import BudgetExceededError, TokenUsage


class TestCostConfig:
    """Tests for CostConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CostConfig()

        assert config.max_tokens_per_session == 1_000_000
        assert config.max_tool_calls_per_session == 500
        assert config.max_iterations_per_request == 20
        assert config.warning_threshold == 0.8
        assert config.action_on_exceed == "stop"

    def test_custom_config(self):
        """Test custom configuration."""
        config = CostConfig(
            max_tokens_per_session=100_000,
            max_tool_calls_per_session=100,
            warning_threshold=0.9,
            action_on_exceed="compress",
        )

        assert config.max_tokens_per_session == 100_000
        assert config.max_tool_calls_per_session == 100
        assert config.warning_threshold == 0.9
        assert config.action_on_exceed == "compress"

    def test_invalid_action_on_exceed(self):
        """Test that invalid action raises error."""
        with pytest.raises(ValueError):
            CostConfig(action_on_exceed="invalid")


class TestTokenUsage:
    """Tests for TokenUsage with budget checking."""

    def test_total_tokens(self):
        """Test total tokens calculation."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)

        assert usage.total_tokens == 150

    def test_check_budget_within_limit(self):
        """Test budget check when within limit."""
        usage = TokenUsage(input_tokens=500, output_tokens=100)
        config = CostConfig(max_tokens_per_session=1_000_000)

        is_within, warning = usage.check_budget(config)

        assert is_within is True
        assert warning is None

    def test_check_budget_exceeded(self):
        """Test budget check when exceeded."""
        usage = TokenUsage(input_tokens=1_500_000, output_tokens=100)
        config = CostConfig(max_tokens_per_session=1_000_000)

        is_within, warning = usage.check_budget(config)

        assert is_within is False
        assert "Token limit exceeded" in warning

    def test_check_budget_warning(self):
        """Test budget warning at threshold."""
        usage = TokenUsage(input_tokens=850_000, output_tokens=0)
        config = CostConfig(
            max_tokens_per_session=1_000_000,
            warning_threshold=0.8,
        )

        is_within, warning = usage.check_budget(config)

        assert is_within is True
        assert "Budget warning" in warning

    def test_check_tool_call_limit(self):
        """Test tool call limit check."""
        usage = TokenUsage(tool_calls=600)
        config = CostConfig(max_tool_calls_per_session=500)

        is_within, warning = usage.check_budget(config)

        assert is_within is False
        assert "Tool call limit exceeded" in warning


class TestBudgetStatus:
    """Tests for BudgetStatus."""

    def test_is_warning(self):
        """Test warning state detection."""
        status = BudgetStatus(
            is_within_budget=True,
            usage=TokenUsage(),
            config=CostConfig(),
            warning_message="Budget warning",
        )

        assert status.is_warning is True

    def test_is_not_warning_when_exceeded(self):
        """Test that exceeded is not a warning."""
        status = BudgetStatus(
            is_within_budget=False,
            usage=TokenUsage(),
            config=CostConfig(),
            warning_message="Budget exceeded",
        )

        assert status.is_warning is False

    def test_remaining_tokens(self):
        """Test remaining tokens calculation."""
        status = BudgetStatus(
            is_within_budget=True,
            usage=TokenUsage(input_tokens=300, output_tokens=200),
            config=CostConfig(max_tokens_per_session=1_000_000),
        )

        assert status.remaining_tokens == 999_500

    def test_remaining_tool_calls(self):
        """Test remaining tool calls calculation."""
        status = BudgetStatus(
            is_within_budget=True,
            usage=TokenUsage(tool_calls=50),
            config=CostConfig(max_tool_calls_per_session=500),
        )

        assert status.remaining_tool_calls == 450


class TestCostController:
    """Tests for CostController."""

    def test_init_default(self):
        """Test default initialization."""
        controller = CostController()

        assert controller.config.max_tokens_per_session == 1_000_000

    def test_init_custom_config(self):
        """Test with custom configuration."""
        config = CostConfig(max_tokens_per_session=100_000)
        controller = CostController(config)

        assert controller.config.max_tokens_per_session == 100_000

    def test_check_within_budget(self):
        """Test check when within budget."""
        controller = CostController()
        usage = TokenUsage(input_tokens=100, output_tokens=50)

        status = controller.check(usage)

        assert status.is_within_budget is True
        assert status.warning_message is None

    def test_check_exceeded_budget(self):
        """Test check when budget exceeded."""
        config = CostConfig(max_tokens_per_session=100)
        controller = CostController(config)
        usage = TokenUsage(input_tokens=150, output_tokens=0)

        status = controller.check(usage)

        assert status.is_within_budget is False
        assert "Token limit exceeded" in status.warning_message

    def test_check_with_compress_action(self):
        """Test check with compress action on exceed."""
        config = CostConfig(
            max_tokens_per_session=100,
            action_on_exceed="compress",
        )
        controller = CostController(config)
        usage = TokenUsage(input_tokens=150, output_tokens=0)

        status = controller.check(usage)

        # With compress action, should continue but flag compression
        assert status.is_within_budget is True
        assert status.should_compress is True

    def test_check_iteration_within_limit(self):
        """Test iteration check within limit."""
        controller = CostController()

        assert controller.check_iteration(10) is True

    def test_check_iteration_exceeded(self):
        """Test iteration check exceeded."""
        config = CostConfig(max_iterations_per_request=20)
        controller = CostController(config)

        assert controller.check_iteration(20) is False

    def test_record_usage(self):
        """Test usage recording."""
        controller = CostController()

        usage = controller.record_usage(
            session_id="test-session",
            input_tokens=100,
            output_tokens=50,
            tool_call=True,
        )

        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.tool_calls == 1

    def test_record_usage_accumulates(self):
        """Test that usage recording accumulates."""
        controller = CostController()

        controller.record_usage("test", input_tokens=100, output_tokens=50)
        controller.record_usage("test", input_tokens=50, output_tokens=25, tool_call=True)

        usage = controller.get_session_usage("test")

        assert usage.input_tokens == 150
        assert usage.output_tokens == 75
        assert usage.tool_calls == 1

    def test_get_session_usage_unknown(self):
        """Test getting usage for unknown session."""
        controller = CostController()

        usage = controller.get_session_usage("unknown")

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_reset_session(self):
        """Test resetting session usage."""
        controller = CostController()

        controller.record_usage("test", input_tokens=100)
        controller.reset_session("test")

        usage = controller.get_session_usage("test")

        assert usage.input_tokens == 0

    def test_should_stop(self):
        """Test should_stop method."""
        config = CostConfig(max_tokens_per_session=100, action_on_exceed="stop")
        controller = CostController(config)
        usage = TokenUsage(input_tokens=150)

        assert controller.should_stop(usage) is True

    def test_should_stop_with_compress(self):
        """Test should_stop with compress action."""
        config = CostConfig(max_tokens_per_session=100, action_on_exceed="compress")
        controller = CostController(config)
        usage = TokenUsage(input_tokens=150)

        # With compress, should not stop
        assert controller.should_stop(usage) is False

    def test_should_compress(self):
        """Test should_compress method."""
        config = CostConfig(max_tokens_per_session=100, action_on_exceed="compress")
        controller = CostController(config)
        usage = TokenUsage(input_tokens=150)

        assert controller.should_compress(usage) is True

    def test_stats(self):
        """Test stats property."""
        controller = CostController()
        controller.record_usage("test", input_tokens=100)

        stats = controller.stats

        assert "config" in stats
        assert "sessions_tracked" in stats
        assert stats["sessions_tracked"] == 1


class TestBudgetExceededError:
    """Tests for BudgetExceededError."""

    def test_init(self):
        """Test error initialization."""
        usage = TokenUsage(input_tokens=100)
        error = BudgetExceededError("Budget exceeded", usage=usage, limit=50)

        assert str(error) == "Budget exceeded"
        assert error.usage == usage
        assert error.limit == 50

    def test_is_exception(self):
        """Test that it is an exception."""
        error = BudgetExceededError("Test")

        assert isinstance(error, Exception)
