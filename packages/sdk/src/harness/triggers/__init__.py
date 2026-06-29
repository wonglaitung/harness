"""
Trigger System - Automations and scheduled execution.

This module provides the Trigger System for Loop Engineering Phase 2.
Triggers enable automatic goal execution based on time, events, or
external conditions.

Main components:
- Trigger: Abstract base class for all triggers
- CronTrigger: Schedule-based trigger using cron expressions
- IntervalTrigger: Fixed interval trigger for periodic execution
- TriggerManager: Central manager for trigger lifecycle

Example:
    ```python
    from harness.triggers import CronTrigger, TriggerAction, TriggerManager
    from harness import AgentHarness

    agent = AgentHarness()
    manager = TriggerManager(agent)

    # Create a daily trigger
    trigger = CronTrigger(
        schedule="0 9 * * *",
        action=TriggerAction(goal="Generate daily report"),
    )

    # Register and start
    manager.register(trigger)
    await manager.start()
    ```
"""

from harness.triggers.base import Trigger
from harness.triggers.cron import CronTrigger
from harness.triggers.interval import IntervalTrigger
from harness.triggers.manager import TriggerManager
from harness.triggers.types import (
    TriggerAction,
    TriggerEvent,
    TriggerRegistration,
    TriggerState,
    TriggerType,
)

__all__ = [
    # Base classes
    "Trigger",
    # Trigger implementations
    "CronTrigger",
    "IntervalTrigger",
    # Manager
    "TriggerManager",
    # Types
    "TriggerType",
    "TriggerState",
    "TriggerEvent",
    "TriggerAction",
    "TriggerRegistration",
]
