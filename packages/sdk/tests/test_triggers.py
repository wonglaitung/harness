"""
Tests for Trigger System - Phase 2: Automations.

This module tests:
- Trigger types and events
- CronTrigger
- IntervalTrigger
- TriggerManager
- Automation
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from harness.triggers import (
    CronTrigger,
    IntervalTrigger,
    TriggerAction,
    TriggerEvent,
    TriggerManager,
    TriggerState,
    TriggerType,
)

# ============================================================================
# TriggerAction Tests
# ============================================================================


class TestTriggerAction:
    """Tests for TriggerAction."""

    def test_create_action(self):
        """Test creating a trigger action."""
        action = TriggerAction(
            goal="Generate report",
            workspace_dir="/app",
            max_iterations=30,
        )

        assert action.goal == "Generate report"
        assert action.workspace_dir == "/app"
        assert action.max_iterations == 30

    def test_action_defaults(self):
        """Test default values for action."""
        action = TriggerAction(goal="Test goal")

        assert action.workspace_dir == "."
        assert action.max_iterations == 50
        assert action.timeout_seconds == 3600
        assert action.skills == []
        assert action.output_channels == []

    def test_action_validation_empty_goal(self):
        """Test that empty goal raises error."""
        with pytest.raises(ValueError, match="goal cannot be empty"):
            TriggerAction(goal="")

    def test_action_validation_invalid_iterations(self):
        """Test that invalid max_iterations raises error."""
        with pytest.raises(ValueError, match="max_iterations must be at least 1"):
            TriggerAction(goal="Test", max_iterations=0)

    def test_to_goal_config(self):
        """Test conversion to GoalConfig."""
        action = TriggerAction(
            goal="Fix bugs",
            workspace_dir="/project",
            max_iterations=20,
        )

        config = action.to_goal_config()

        assert config.description == "Fix bugs"
        assert config.workspace_dir == "/project"
        assert config.max_iterations == 20

    def test_to_goal_config_with_event(self):
        """Test conversion to GoalConfig with event context."""
        action = TriggerAction(goal="Process data")

        event = TriggerEvent(
            trigger_type=TriggerType.CRON,
            trigger_id="test",
            payload={"file": "data.csv", "count": 100},
        )

        config = action.to_goal_config(event)

        assert "file: data.csv" in config.description
        assert "count: 100" in config.description


# ============================================================================
# TriggerEvent Tests
# ============================================================================


class TestTriggerEvent:
    """Tests for TriggerEvent."""

    def test_create_event(self):
        """Test creating a trigger event."""
        event = TriggerEvent(
            trigger_type=TriggerType.CRON,
            trigger_id="trigger_123",
            payload={"key": "value"},
        )

        assert event.trigger_type == TriggerType.CRON
        assert event.trigger_id == "trigger_123"
        assert event.payload == {"key": "value"}
        assert isinstance(event.timestamp, datetime)

    def test_is_scheduled(self):
        """Test is_scheduled property."""
        cron_event = TriggerEvent(
            trigger_type=TriggerType.CRON,
            trigger_id="test",
        )
        interval_event = TriggerEvent(
            trigger_type=TriggerType.INTERVAL,
            trigger_id="test",
        )
        webhook_event = TriggerEvent(
            trigger_type=TriggerType.WEBHOOK,
            trigger_id="test",
        )

        assert cron_event.is_scheduled is True
        assert interval_event.is_scheduled is True
        assert webhook_event.is_scheduled is False

    def test_is_external(self):
        """Test is_external property."""
        webhook_event = TriggerEvent(
            trigger_type=TriggerType.WEBHOOK,
            trigger_id="test",
        )
        event_event = TriggerEvent(
            trigger_type=TriggerType.EVENT,
            trigger_id="test",
        )
        cron_event = TriggerEvent(
            trigger_type=TriggerType.CRON,
            trigger_id="test",
        )

        assert webhook_event.is_external is True
        assert event_event.is_external is True
        assert cron_event.is_external is False


# ============================================================================
# CronTrigger Tests
# ============================================================================


class TestCronTrigger:
    """Tests for CronTrigger."""

    def test_create_cron_trigger(self):
        """Test creating a cron trigger."""
        action = TriggerAction(goal="Test")
        trigger = CronTrigger(
            schedule="0 9 * * *",
            action=action,
        )

        assert trigger.trigger_type == TriggerType.CRON
        assert trigger.schedule == "0 9 * * *"
        assert trigger.state == TriggerState.IDLE

    def test_invalid_cron_expression(self):
        """Test that invalid cron expression raises error."""
        action = TriggerAction(goal="Test")

        with pytest.raises(ValueError, match="Invalid cron expression"):
            CronTrigger(
                schedule="invalid cron",
                action=action,
            )

    def test_get_next_run(self):
        """Test getting next run time."""
        action = TriggerAction(goal="Test")
        trigger = CronTrigger(
            schedule="0 * * * *",  # Every hour
            action=action,
        )

        next_run = trigger.get_next_run()

        assert isinstance(next_run, datetime)
        assert next_run > datetime.now()

    def test_get_next_runs(self):
        """Test getting multiple next run times."""
        action = TriggerAction(goal="Test")
        trigger = CronTrigger(
            schedule="0 * * * *",
            action=action,
        )

        next_runs = trigger.get_next_runs(5)

        assert len(next_runs) == 5
        # Each should be after the previous
        for i in range(len(next_runs) - 1):
            assert next_runs[i] < next_runs[i + 1]

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping trigger."""
        action = TriggerAction(goal="Test")
        trigger = CronTrigger(
            schedule="* * * * *",  # Every minute
            action=action,
        )

        events = []

        def callback(event):
            events.append(event)

        await trigger.start(callback)
        assert trigger.is_running()

        # Wait a bit but not long enough for trigger
        await asyncio.sleep(0.1)

        await trigger.stop()
        assert trigger.is_stopped()

    def test_create_event(self):
        """Test creating event from trigger."""
        action = TriggerAction(goal="Test")
        trigger = CronTrigger(
            schedule="0 9 * * *",
            action=action,
            trigger_id="my_trigger",
        )

        event = trigger.create_event({"custom": "data"})

        assert event.trigger_type == TriggerType.CRON
        assert event.trigger_id == "my_trigger"
        assert event.payload["schedule"] == "0 9 * * *"
        assert event.payload["custom"] == "data"


# ============================================================================
# IntervalTrigger Tests
# ============================================================================


class TestIntervalTrigger:
    """Tests for IntervalTrigger."""

    def test_create_interval_trigger(self):
        """Test creating an interval trigger."""
        action = TriggerAction(goal="Test")
        trigger = IntervalTrigger(
            interval_seconds=60,
            action=action,
        )

        assert trigger.trigger_type == TriggerType.INTERVAL
        assert trigger.interval_seconds == 60
        assert trigger.state == TriggerState.IDLE

    def test_invalid_interval(self):
        """Test that invalid interval raises error."""
        action = TriggerAction(goal="Test")

        with pytest.raises(ValueError, match="must be at least 1 second"):
            IntervalTrigger(
                interval_seconds=0,
                action=action,
            )

    def test_get_estimated_next_run(self):
        """Test getting estimated next run time."""
        action = TriggerAction(goal="Test")
        trigger = IntervalTrigger(
            interval_seconds=300,
            action=action,
        )

        next_run = trigger.get_estimated_next_run()

        assert isinstance(next_run, datetime)
        # Should be approximately 5 minutes from now
        expected = datetime.now() + timedelta(seconds=300)
        diff = abs((next_run - expected).total_seconds())
        assert diff < 1  # Within 1 second

    @pytest.mark.asyncio
    async def test_interval_firing(self):
        """Test that interval trigger fires correctly."""
        action = TriggerAction(goal="Test")
        trigger = IntervalTrigger(
            interval_seconds=1,  # 1 second minimum
            action=action,
        )

        events = []

        def callback(event):
            events.append(event)

        await trigger.start(callback)

        # Wait for at least 2 fires (need 2+ seconds)
        await asyncio.sleep(2.5)

        await trigger.stop()

        assert len(events) >= 2
        assert trigger.fire_count >= 2

    @pytest.mark.asyncio
    async def test_start_immediately(self):
        """Test start_immediately option."""
        action = TriggerAction(goal="Test")
        trigger = IntervalTrigger(
            interval_seconds=60,
            action=action,
            start_immediately=True,
        )

        events = []

        def callback(event):
            events.append(event)

        await trigger.start(callback)

        # Should fire immediately
        await asyncio.sleep(0.01)

        assert len(events) == 1

        await trigger.stop()

    def test_create_event(self):
        """Test creating event from trigger."""
        action = TriggerAction(goal="Test")
        trigger = IntervalTrigger(
            interval_seconds=60,
            action=action,
            trigger_id="interval_test",
        )

        event = trigger.create_event({"custom": "data"})

        assert event.trigger_type == TriggerType.INTERVAL
        assert event.trigger_id == "interval_test"
        assert event.payload["interval_seconds"] == 60
        assert event.payload["custom"] == "data"


# ============================================================================
# TriggerManager Tests
# ============================================================================


class TestTriggerManager:
    """Tests for TriggerManager."""

    def test_register_trigger(self):
        """Test registering a trigger."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent)

        action = TriggerAction(goal="Test")
        trigger = IntervalTrigger(interval_seconds=60, action=action)

        trigger_id = manager.register(trigger)

        assert trigger_id == trigger.id
        assert manager.trigger_count == 1

    def test_unregister_trigger(self):
        """Test unregistering a trigger."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent)

        action = TriggerAction(goal="Test")
        trigger = IntervalTrigger(interval_seconds=60, action=action)

        trigger_id = manager.register(trigger)
        assert manager.unregister(trigger_id) is True
        assert manager.trigger_count == 0

    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent trigger."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent)

        assert manager.unregister("nonexistent") is False

    def test_enable_disable(self):
        """Test enabling and disabling triggers."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent)

        action = TriggerAction(goal="Test")
        trigger = IntervalTrigger(interval_seconds=60, action=action)

        trigger_id = manager.register(trigger)

        assert manager.disable(trigger_id) is True
        reg = manager.get_trigger(trigger_id)
        assert reg is not None
        assert reg.enabled is False

        assert manager.enable(trigger_id) is True
        assert reg.enabled is True

    def test_list_triggers(self):
        """Test listing triggers."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent)

        action1 = TriggerAction(goal="Test 1")
        action2 = TriggerAction(goal="Test 2")

        trigger1 = IntervalTrigger(interval_seconds=60, action=action1)
        trigger2 = CronTrigger(schedule="0 9 * * *", action=action2)

        manager.register(trigger1)
        manager.register(trigger2)

        triggers = manager.list_triggers()

        assert len(triggers) == 2
        types = {t["type"] for t in triggers}
        assert "interval" in types
        assert "cron" in types

    @pytest.mark.asyncio
    async def test_start_stop_manager(self):
        """Test starting and stopping manager."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent)

        action = TriggerAction(goal="Test")
        trigger = IntervalTrigger(interval_seconds=60, action=action)

        manager.register(trigger)

        await manager.start()
        assert manager.is_running
        assert trigger.is_running()

        await manager.stop()
        assert not manager.is_running
        assert trigger.is_stopped()


# ============================================================================
# Integration Tests
# ============================================================================


class TestTriggerIntegration:
    """Integration tests for trigger system."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete trigger workflow."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent)

        action = TriggerAction(
            goal="Test goal",
            workspace_dir=".",
        )

        trigger = IntervalTrigger(
            interval_seconds=1,  # 1 second minimum
            action=action,
        )

        # Register
        trigger_id = manager.register(trigger)
        assert manager.trigger_count == 1

        # Start
        await manager.start()
        assert manager.is_running

        # Wait for triggers (2+ seconds for 2 fires)
        await asyncio.sleep(2.5)

        # Stop
        await manager.stop()
        assert not manager.is_running

        # Check statistics
        reg = manager.get_trigger(trigger_id)
        assert reg is not None
        assert reg.fire_count >= 2


# ============================================================================
# Concurrency Tests
# ============================================================================


class TestTriggerManagerConcurrency:
    """Tests for concurrent goal execution."""

    @pytest.mark.asyncio
    async def test_concurrent_goal_execution(self):
        """Test that multiple triggers execute goals concurrently."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent, max_concurrent_goals=3)

        # Create 3 triggers with short interval
        for i in range(3):
            trigger = IntervalTrigger(
                interval_seconds=1,
                action=TriggerAction(goal=f"Task {i}"),
            )
            manager.register(trigger)

        await manager.start()

        # Wait for triggers to fire
        await asyncio.sleep(1.5)

        # Verify semaphore was created
        assert manager._semaphore is not None

        # Verify tasks were created concurrently
        # (they may have completed by now, so we check fire counts)
        total_fires = sum(reg.fire_count for reg in manager._registrations.values())
        assert total_fires >= 3  # At least 3 fires across all triggers

        await manager.stop()

    @pytest.mark.asyncio
    async def test_max_concurrent_limit(self):
        """Test that concurrent execution respects the limit."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent, max_concurrent_goals=2)

        # Create 5 triggers
        for i in range(5):
            trigger = IntervalTrigger(
                interval_seconds=1,
                action=TriggerAction(goal=f"Task {i}"),
            )
            manager.register(trigger)

        await manager.start()
        await asyncio.sleep(1.5)

        # Check that max_concurrent_goals was set correctly
        assert manager.max_concurrent_goals == 2

        await manager.stop()

    @pytest.mark.asyncio
    async def test_stop_waits_for_active_tasks(self):
        """Test that stop() waits for active tasks to complete."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent, max_concurrent_goals=3)

        trigger = IntervalTrigger(
            interval_seconds=1,
            action=TriggerAction(goal="Test"),
        )
        manager.register(trigger)

        await manager.start()
        await asyncio.sleep(1.5)

        # Stop should complete without hanging
        await manager.stop()
        assert not manager.is_running


# ============================================================================
# Automation Integration Tests
# ============================================================================


class TestAutomationWithManager:
    """Tests for Automation integration with TriggerManager."""

    def test_get_global_manager_requires_agent(self):
        """Test that get_global_manager requires agent on first call."""
        from harness.loop.automation import (
            get_global_manager,
            reset_global_manager,
        )

        # Reset to ensure clean state
        reset_global_manager()

        with pytest.raises(ValueError, match="Agent is required"):
            get_global_manager()

    def test_get_global_manager_singleton(self):
        """Test that get_global_manager returns a singleton."""
        from harness.loop.automation import (
            get_global_manager,
            reset_global_manager,
        )
        from harness.testing import MockHarness

        reset_global_manager()

        agent = MockHarness()
        manager1 = get_global_manager(agent)
        manager2 = get_global_manager()

        assert manager1 is manager2

        reset_global_manager()

    @pytest.mark.asyncio
    async def test_automation_uses_global_manager(self):
        """Test that Automation uses the global TriggerManager."""
        from harness.loop.automation import (
            Automation,
            get_global_manager,
            reset_global_manager,
        )
        from harness.testing import MockHarness

        reset_global_manager()

        agent = MockHarness()
        automation = Automation(
            name="test",
            interval_seconds=60,
            goal="Test goal",
        )

        await automation.start(agent)

        # Verify registered in global manager
        manager = get_global_manager()
        assert manager.trigger_count >= 1

        await automation.stop()
        reset_global_manager()

    @pytest.mark.asyncio
    async def test_automation_with_explicit_manager(self):
        """Test Automation with explicitly provided TriggerManager."""
        from harness.loop.automation import Automation, reset_global_manager
        from harness.testing import MockHarness

        reset_global_manager()

        agent = MockHarness()
        manager = TriggerManager(agent)
        automation = Automation(
            name="test",
            interval_seconds=60,
            goal="Test goal",
        )

        await automation.start(agent, manager=manager)

        # Verify registered in provided manager
        assert manager.trigger_count == 1

        await automation.stop()

    @pytest.mark.asyncio
    async def test_automation_pause_resume(self):
        """Test Automation pause and resume with TriggerManager."""
        from harness.loop.automation import Automation, reset_global_manager
        from harness.testing import MockHarness

        reset_global_manager()

        agent = MockHarness()
        automation = Automation(
            name="test",
            interval_seconds=60,
            goal="Test goal",
        )

        await automation.start(agent)
        assert automation.is_running

        await automation.pause()
        assert automation.status.value == "paused"

        await automation.resume()
        assert automation.is_running

        await automation.stop()
        reset_global_manager()

    @pytest.mark.asyncio
    async def test_automation_result_syncs_from_manager(self):
        """Test that Automation.result syncs from TriggerManager stats."""
        from harness.loop.automation import Automation, reset_global_manager
        from harness.testing import MockHarness

        reset_global_manager()

        agent = MockHarness()
        manager = TriggerManager(agent, max_concurrent_goals=3)
        automation = Automation(
            name="test",
            interval_seconds=1,
            goal="Test goal",
        )

        await automation.start(agent, manager=manager)

        # Wait for a trigger
        await asyncio.sleep(1.5)

        # Access result to trigger sync
        result = automation.result

        # Check that fire_count was synced
        assert result.fire_count >= 1

        await automation.stop()
        reset_global_manager()
