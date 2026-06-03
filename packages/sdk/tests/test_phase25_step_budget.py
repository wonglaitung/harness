"""
Tests for Phase 25: Step Budget Controller
"""

import pytest

from harness.core.step_budget import (
    BudgetCheckResult,
    BudgetLevel,
    StepBudgetConfig,
    StepBudgetController,
    StepUsage,
)


class TestStepBudgetConfig:
    """Tests for StepBudgetConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = StepBudgetConfig()
        assert config.max_iterations_per_task == 50
        assert config.max_tool_calls_per_step == 10
        assert config.max_tool_calls_per_task == 200
        assert config.warning_threshold == 0.8
        assert config.critical_threshold == 0.95
        assert config.action_on_exceed == "stop"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = StepBudgetConfig(
            max_iterations_per_task=100,
            max_tool_calls_per_step=5,
            max_tool_calls_per_task=50,
            action_on_exceed="throttle",
        )
        assert config.max_iterations_per_task == 100
        assert config.max_tool_calls_per_step == 5
        assert config.max_tool_calls_per_task == 50
        assert config.action_on_exceed == "throttle"

    def test_invalid_iterations(self):
        """Test invalid iterations raises error."""
        with pytest.raises(ValueError, match="max_iterations_per_task must be at least 1"):
            StepBudgetConfig(max_iterations_per_task=0)

    def test_invalid_tool_calls_step(self):
        """Test invalid tool calls per step raises error."""
        with pytest.raises(ValueError, match="max_tool_calls_per_step must be at least 1"):
            StepBudgetConfig(max_tool_calls_per_step=0)

    def test_tool_calls_task_less_than_step(self):
        """Test tool calls per task must be >= tool calls per step."""
        with pytest.raises(ValueError, match="max_tool_calls_per_task must be >= max_tool_calls_per_step"):
            StepBudgetConfig(max_tool_calls_per_step=20, max_tool_calls_per_task=10)

    def test_invalid_warning_threshold(self):
        """Test invalid warning threshold raises error."""
        with pytest.raises(ValueError, match="warning_threshold must be between 0 and 1"):
            StepBudgetConfig(warning_threshold=1.0)

        with pytest.raises(ValueError, match="warning_threshold must be between 0 and 1"):
            StepBudgetConfig(warning_threshold=0)

    def test_invalid_critical_threshold(self):
        """Test invalid critical threshold raises error."""
        with pytest.raises(ValueError, match="critical_threshold must be between 0 and 1"):
            StepBudgetConfig(critical_threshold=1.5)

    def test_warning_greater_than_critical(self):
        """Test warning threshold must be < critical threshold."""
        with pytest.raises(ValueError, match="warning_threshold must be < critical_threshold"):
            StepBudgetConfig(warning_threshold=0.9, critical_threshold=0.8)

    def test_invalid_action_on_exceed(self):
        """Test invalid action_on_exceed raises error."""
        with pytest.raises(ValueError, match="Invalid action_on_exceed"):
            StepBudgetConfig(action_on_exceed="invalid")

    def test_invalid_throttle_ratio(self):
        """Test invalid throttle ratio raises error."""
        with pytest.raises(ValueError, match="throttle_ratio must be between 0 and 1"):
            StepBudgetConfig(throttle_ratio=0)


class TestStepUsage:
    """Tests for StepUsage."""

    def test_default_usage(self):
        """Test default usage values."""
        usage = StepUsage()
        assert usage.iterations == 0
        assert usage.tool_calls_total == 0
        assert usage.tool_calls_this_step == 0
        assert usage.tool_calls_by_tool == {}

    def test_reset_step(self):
        """Test step reset."""
        usage = StepUsage(
            iterations=5,
            tool_calls_total=10,
            tool_calls_this_step=3,
        )
        usage.reset_step()

        assert usage.iterations == 5  # Not reset
        assert usage.tool_calls_total == 10  # Not reset
        assert usage.tool_calls_this_step == 0  # Reset

    def test_serialization(self):
        """Test serialization to dictionary."""
        usage = StepUsage(
            iterations=5,
            tool_calls_total=20,
            tool_calls_this_step=3,
            tool_calls_by_tool={"read": 10, "write": 10},
        )
        data = usage.to_dict()

        assert data["iterations"] == 5
        assert data["tool_calls_total"] == 20
        assert data["tool_calls_this_step"] == 3
        assert data["tool_calls_by_tool"]["read"] == 10


class TestStepBudgetController:
    """Tests for StepBudgetController."""

    def test_start_and_end_task(self):
        """Test task lifecycle."""
        controller = StepBudgetController()

        controller.start_task()
        assert controller._task_active is True

        usage = controller.end_task()
        assert controller._task_active is False
        assert isinstance(usage, StepUsage)

    def test_advance_iteration(self):
        """Test iteration advancement."""
        controller = StepBudgetController()
        controller.start_task()

        result = controller.advance_iteration()
        assert result.level == BudgetLevel.NORMAL
        assert controller._usage.iterations == 1

        result = controller.advance_iteration()
        assert controller._usage.iterations == 2

    def test_record_tool_call(self):
        """Test tool call recording."""
        controller = StepBudgetController()
        controller.start_task()

        result = controller.record_tool_call("read")
        assert result.level == BudgetLevel.NORMAL
        assert controller._usage.tool_calls_total == 1
        assert controller._usage.tool_calls_this_step == 1
        assert controller._usage.tool_calls_by_tool["read"] == 1

        result = controller.record_tool_call("write")
        assert controller._usage.tool_calls_total == 2
        assert controller._usage.tool_calls_by_tool["write"] == 1

    def test_check_before_tool_call(self):
        """Test pre-call budget check."""
        controller = StepBudgetController(StepBudgetConfig(
            max_tool_calls_per_step=2,
            max_tool_calls_per_task=100,
        ))
        controller.start_task()

        # First check should pass
        result = controller.check_before_tool_call("read")
        assert result.is_within_budget is True

        # Record call
        controller.record_tool_call("read")

        # Second check should pass
        result = controller.check_before_tool_call("read")
        assert result.is_within_budget is True

        # Record call
        controller.record_tool_call("read")

        # Third check should fail (step limit exceeded)
        result = controller.check_before_tool_call("read")
        assert result.is_within_budget is False
        assert result.level == BudgetLevel.EXCEEDED

    def test_iteration_limit_exceeded(self):
        """Test iteration limit."""
        config = StepBudgetConfig(max_iterations_per_task=3)
        controller = StepBudgetController(config)
        controller.start_task()

        # First 3 iterations should be OK
        for _ in range(3):
            result = controller.advance_iteration()
            # At exactly 100%, we're at critical threshold
            # The iteration count is compared to limit, so 3/3 = 100% >= 1.0

        # At 3/3 = 100% usage, check should indicate exceeded
        result = controller._check_budget()
        assert result.level == BudgetLevel.EXCEEDED

    def test_tool_calls_limit_exceeded(self):
        """Test tool calls limit."""
        config = StepBudgetConfig(
            max_tool_calls_per_step=5,
            max_tool_calls_per_task=5
        )
        controller = StepBudgetController(config)
        controller.start_task()

        # Record 5 tool calls
        for i in range(5):
            result = controller.record_tool_call(f"tool_{i}")
            # First 4 should be normal, 5th hits 100%
            if i < 4:
                assert result.is_within_budget is True

        # 5th call reaches 100% which equals threshold
        result = controller._check_budget()
        assert result.level == BudgetLevel.EXCEEDED

    def test_warning_threshold(self):
        """Test warning threshold."""
        config = StepBudgetConfig(
            max_tool_calls_per_task=10,
            warning_threshold=0.8,
            critical_threshold=0.95,
        )
        controller = StepBudgetController(config)
        controller.start_task()

        # 7 calls = 70% - normal
        for i in range(7):
            controller.record_tool_call(f"tool_{i}")
        result = controller._check_budget()
        assert result.level == BudgetLevel.NORMAL

        # 8 calls = 80% - warning
        controller.record_tool_call("tool_8")
        result = controller._check_budget()
        assert result.level == BudgetLevel.WARNING

    def test_critical_threshold(self):
        """Test critical threshold."""
        config = StepBudgetConfig(
            max_tool_calls_per_step=100,
            max_tool_calls_per_task=100,
            warning_threshold=0.8,
            critical_threshold=0.95,
        )
        controller = StepBudgetController(config)
        controller.start_task()

        # 95 calls = 95% - critical
        for i in range(95):
            controller.record_tool_call(f"tool_{i}")
        result = controller._check_budget()
        assert result.level == BudgetLevel.CRITICAL

    def test_action_stop(self):
        """Test stop action on exceed."""
        config = StepBudgetConfig(
            max_tool_calls_per_step=2,
            max_tool_calls_per_task=2,
            action_on_exceed="stop",
        )
        controller = StepBudgetController(config)
        controller.start_task()

        controller.record_tool_call("tool_1")
        controller.record_tool_call("tool_2")

        result = controller._check_budget()
        assert result.should_stop is True
        assert result.is_within_budget is False

    def test_action_warn(self):
        """Test warn action on exceed."""
        config = StepBudgetConfig(
            max_tool_calls_per_step=2,
            max_tool_calls_per_task=2,
            action_on_exceed="warn",
        )
        controller = StepBudgetController(config)
        controller.start_task()

        controller.record_tool_call("tool_1")
        controller.record_tool_call("tool_2")

        result = controller._check_budget()
        assert result.should_stop is False
        assert result.is_within_budget is True  # warn doesn't stop

    def test_action_throttle(self):
        """Test throttle action on exceed."""
        config = StepBudgetConfig(
            max_tool_calls_per_task=10,
            action_on_exceed="throttle",
            throttle_ratio=0.5,
        )
        controller = StepBudgetController(config)
        controller.start_task()

        # Exhaust budget
        for i in range(10):
            controller.record_tool_call(f"tool_{i}")

        result = controller._check_budget()
        assert result.should_stop is False
        assert result.throttle_limit is not None
        assert result.throttle_limit >= 1

    def test_get_usage_report(self):
        """Test usage report."""
        controller = StepBudgetController()
        controller.start_task()

        controller.advance_iteration()
        controller.record_tool_call("read")
        controller.record_tool_call("write")

        report = controller.get_usage_report()

        assert report["iterations"]["used"] == 1
        assert report["iterations"]["limit"] == 50
        assert report["tool_calls"]["used"] == 2
        assert report["tool_calls"]["limit"] == 200
        assert report["tool_calls"]["this_step"] == 2
        assert report["by_tool"]["read"] == 1
        assert report["by_tool"]["write"] == 1
        assert report["task_active"] is True

    def test_no_active_task(self):
        """Test operations without active task."""
        controller = StepBudgetController()

        # Should not crash, just return safe result
        result = controller.advance_iteration()
        assert result.message == "No active task"

        result = controller.record_tool_call("tool")
        assert result.message == "No active task"

    def test_projected_check(self):
        """Test projected budget check."""
        config = StepBudgetConfig(
            max_tool_calls_per_step=10,
            max_tool_calls_per_task=10
        )
        controller = StepBudgetController(config)
        controller.start_task()

        # Record 8 calls (80% = warning level)
        for i in range(8):
            controller.record_tool_call(f"tool_{i}")

        # Project 9th call - should pass (at 90%, still warning level)
        result = controller.check_before_tool_call("tool_8")
        assert result.is_within_budget is True
        assert result.level == BudgetLevel.WARNING  # 9/10 = 90% >= 0.8

        # Record 9th call
        controller.record_tool_call("tool_8")

        # Project 10th call - at 100% exactly, ratio = 1.0 triggers EXCEEDED
        result = controller.check_before_tool_call("tool_9")
        assert result.level == BudgetLevel.EXCEEDED  # 10/10 = 100% >= 1.0
        assert result.is_within_budget is False

        # Test that we can still add more calls when using 'warn' action
        controller2 = StepBudgetController(
            StepBudgetConfig(
                max_tool_calls_per_step=10,
                max_tool_calls_per_task=10,
                action_on_exceed="warn"
            )
        )
        controller2.start_task()
        for i in range(10):
            controller2.record_tool_call(f"tool_{i}")

        # With 'warn' action, should still be within budget
        result = controller2._check_budget()
        assert result.is_within_budget is True


class TestBudgetCheckResult:
    """Tests for BudgetCheckResult."""

    def test_default_result(self):
        """Test default result values."""
        result = BudgetCheckResult(
            level=BudgetLevel.NORMAL,
            is_within_budget=True,
            message="OK",
        )
        assert result.level == BudgetLevel.NORMAL
        assert result.is_within_budget is True
        assert result.message == "OK"
        assert result.should_stop is False
        assert result.throttle_limit is None
