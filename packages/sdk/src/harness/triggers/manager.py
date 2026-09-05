"""
TriggerManager - Manages trigger lifecycle and execution.

This module provides the central manager for all triggers,
handling registration, lifecycle, and goal execution.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING, Any

from harness.triggers.types import TriggerAction, TriggerEvent, TriggerRegistration

if TYPE_CHECKING:
    from harness.sdk.harness import AgentHarness
    from harness.triggers.base import Trigger

logger = logging.getLogger(__name__)


class EventQueue:
    """
    Thread-safe event queue that works across event loop switches.

    Unlike asyncio.Queue which is bound to a specific event loop,
    this implementation uses threading primitives for thread-safety
    and asyncio.Event for async waiting, making it resilient to
    qasync event loop switching issues.
    """

    def __init__(self):
        self._queue: deque[TriggerEvent] = deque()
        self._lock = threading.Lock()
        self._notifier: asyncio.Event | None = None

    def put_nowait(self, event: TriggerEvent) -> None:
        """Add event to queue (thread-safe, non-blocking)."""
        with self._lock:
            self._queue.append(event)
        # Notify waiter if exists
        if self._notifier is not None:
            with contextlib.suppress(Exception):
                self._notifier.set()  # Event might be bound to old loop

    async def get(self) -> TriggerEvent:
        """Get event from queue (async, waits if empty)."""
        # Create notifier in current event loop
        if self._notifier is None:
            self._notifier = asyncio.Event()

        while True:
            with self._lock:
                if self._queue:
                    return self._queue.popleft()

            # Wait for notification
            self._notifier.clear()
            try:
                await self._notifier.wait()
            except Exception:
                # Event loop might have switched, create new notifier
                self._notifier = asyncio.Event()

    def qsize(self) -> int:
        """Get queue size (thread-safe)."""
        with self._lock:
            return len(self._queue)


class TriggerManager:
    """
    Central manager for triggers.

    Handles:
    - Registration and unregistration of triggers
    - Starting and stopping all triggers
    - Executing goals when triggers fire
    - Error handling and retries
    - Concurrent goal execution with configurable limits

    Example:
        ```python
        from harness import AgentHarness
        from harness.triggers import TriggerManager, CronTrigger, TriggerAction

        agent = AgentHarness()
        manager = TriggerManager(agent, max_concurrent_goals=3)

        # Register a trigger
        trigger = CronTrigger(
            schedule="0 9 * * *",
            action=TriggerAction(goal="Generate daily report"),
        )
        trigger_id = manager.register(trigger)

        # Start all triggers
        await manager.start()

        # Later, stop all triggers
        await manager.stop()
        ```
    """

    def __init__(
        self,
        agent: AgentHarness,
        max_concurrent_goals: int = 5,
    ):
        """
        Initialize trigger manager.

        Args:
            agent: AgentHarness instance to use for goal execution
            max_concurrent_goals: Maximum number of goals to execute concurrently.
                This prevents API rate limiting when multiple triggers fire at once.
        """
        self.agent = agent
        self.max_concurrent_goals = max_concurrent_goals
        self._registrations: dict[str, TriggerRegistration] = {}
        self._running = False
        # Use EventQueue instead of asyncio.Queue to avoid qasync event loop binding issues
        self._event_queue: EventQueue = EventQueue()
        self._processor_task: asyncio.Task | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._running_tasks: set[asyncio.Task] = set()

    def register(
        self,
        trigger: Trigger,
        action: TriggerAction | None = None,
        enabled: bool = True,
    ) -> str:
        """
        Register a trigger.

        Args:
            trigger: Trigger instance to register
            action: Action to execute (optional if trigger has action)
            enabled: Whether to enable the trigger immediately

        Returns:
            Trigger ID

        Raises:
            ValueError: If no action is provided and trigger has none
        """
        # Use trigger's action if not provided
        action = action or trigger.action
        if action is None:
            raise ValueError(
                f"No action provided for trigger {trigger.id}. "
                "Either pass an action or set trigger.action."
            )

        # Generate ID if not set
        if not trigger.id:
            import uuid

            trigger.id = f"trigger_{uuid.uuid4().hex[:8]}"

        # Create registration
        self._registrations[trigger.id] = TriggerRegistration(
            trigger=trigger,
            action=action,
            enabled=enabled,
        )

        logger.info(f"Registered trigger {trigger.id} of type {trigger.trigger_type.value}")
        return trigger.id

    def unregister(self, trigger_id: str) -> bool:
        """
        Unregister a trigger.

        Will stop the trigger if it's running.

        Args:
            trigger_id: ID of trigger to unregister

        Returns:
            True if trigger was found and removed
        """
        if trigger_id not in self._registrations:
            return False

        reg = self._registrations[trigger_id]

        # Stop trigger if running
        if reg.trigger.is_running():
            asyncio.create_task(reg.trigger.stop())

        del self._registrations[trigger_id]
        logger.info(f"Unregistered trigger {trigger_id}")
        return True

    def enable(self, trigger_id: str) -> bool:
        """
        Enable a registered trigger.

        Args:
            trigger_id: ID of trigger to enable

        Returns:
            True if trigger was found and enabled
        """
        if trigger_id not in self._registrations:
            return False

        self._registrations[trigger_id].enabled = True
        logger.debug(f"Enabled trigger {trigger_id}")
        return True

    def disable(self, trigger_id: str) -> bool:
        """
        Disable a registered trigger.

        The trigger will not fire while disabled, but remains registered.

        Args:
            trigger_id: ID of trigger to disable

        Returns:
            True if trigger was found and disabled
        """
        if trigger_id not in self._registrations:
            return False

        self._registrations[trigger_id].enabled = False
        logger.debug(f"Disabled trigger {trigger_id}")
        return True

    async def start(self) -> None:
        """
        Start all registered and enabled triggers.

        Also starts the event processor task.
        """
        if self._running:
            logger.warning("TriggerManager is already running")
            return

        self._running = True

        # Start event processor
        self._processor_task = asyncio.create_task(self._process_events())

        # Start all enabled triggers
        for reg in self._registrations.values():
            if reg.enabled:
                try:
                    await reg.trigger.start(self._enqueue_event)
                except Exception as e:
                    logger.error(f"Failed to start trigger {reg.trigger.id}: {e}")
                    reg.last_error = str(e)

        logger.info(f"TriggerManager started with {len(self._registrations)} triggers")

    async def stop(self) -> None:
        """
        Stop all triggers and the event processor.

        Waits for active goal executions to complete (with timeout)
        before shutting down.
        """
        if not self._running:
            return

        self._running = False

        # Stop event processor FIRST to avoid queue access on wrong event loop
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            except RuntimeError as e:
                # qasync may raise RuntimeError about event loop binding
                logger.debug(f"Event processor stopped (caught RuntimeError: {e})")
            self._processor_task = None

        # Wait for active tasks to complete (with timeout)
        if self._running_tasks:
            logger.info(f"Waiting for {len(self._running_tasks)} active tasks to complete...")
            try:
                done, pending = await asyncio.wait(
                    self._running_tasks,
                    timeout=30.0,  # Maximum wait time
                )
                if pending:
                    logger.warning(f"Cancelling {len(pending)} pending tasks")
                    for task in pending:
                        task.cancel()
            except RuntimeError as e:
                # qasync event loop binding issue
                logger.debug(f"Task wait interrupted (RuntimeError: {e})")

        # Stop all triggers
        for reg in self._registrations.values():
            try:
                await reg.trigger.stop()
            except Exception as e:
                logger.error(f"Error stopping trigger {reg.trigger.id}: {e}")

        logger.info("TriggerManager stopped")

    def _enqueue_event(self, event: TriggerEvent) -> None:
        """
        Enqueue an event for processing.

        Called by triggers when they fire.

        Args:
            event: Event to enqueue
        """
        self._event_queue.put_nowait(event)
        logger.debug(
            f"Event enqueued for trigger {event.trigger_id}, "
            f"queue size: {self._event_queue.qsize()}"
        )

    async def enqueue_event(self, event: TriggerEvent) -> None:
        """
        Async enqueue an event for processing.

        Called by ConnectorManager for external events.
        This async version is required for non-blocking operation
        in async event loops (e.g., Slack Socket Mode).

        Args:
            event: Event to enqueue
        """
        self._event_queue.put_nowait(event)
        logger.debug(f"Event async enqueued for trigger {event.trigger_id}")

    async def _process_events(self) -> None:
        """
        Process events from the queue.

        This is the main loop that handles trigger events
        and executes goals concurrently.
        """
        self._semaphore = asyncio.Semaphore(self.max_concurrent_goals)

        logger.info("Event processor started, waiting for events...")

        loop_count = 0
        while self._running:
            loop_count += 1
            try:
                # EventQueue is resilient to event loop switching
                event = await self._event_queue.get()

                logger.debug(
                    f"Processing event from trigger {event.trigger_id}, "
                    f"queue size: {self._event_queue.qsize()}"
                )
                # Execute concurrently, not blocking queue consumption
                task = asyncio.create_task(self._handle_event_concurrent(event))
                self._running_tasks.add(task)
                task.add_done_callback(self._running_tasks.discard)

            except asyncio.CancelledError:
                logger.info("Event processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)

        logger.info(f"Event processor stopped, _running={self._running}, loops={loop_count}")

    async def _handle_event_concurrent(self, event: TriggerEvent) -> None:
        """
        Handle a trigger event concurrently with semaphore protection.

        Args:
            event: Event to handle
        """
        trigger_id = event.trigger_id
        logger.debug(f"Waiting for semaphore to handle event from {trigger_id}")

        if self._semaphore is None:
            # Fallback for edge cases
            await self._handle_event(event)
            return

        async with self._semaphore:
            logger.debug(f"Semaphore acquired, handling event from {trigger_id}")
            await self._handle_event(event)
            logger.debug(f"Event handling completed for {trigger_id}")

    async def _handle_event(self, event: TriggerEvent) -> None:
        """
        Handle a trigger event by executing the associated goal.

        Args:
            event: Event to handle
        """
        trigger_id = event.trigger_id

        if trigger_id not in self._registrations:
            logger.warning(f"Received event for unknown trigger {trigger_id}")
            return

        reg = self._registrations[trigger_id]

        if not reg.enabled:
            logger.debug(f"Ignoring event for disabled trigger {trigger_id}")
            return

        logger.info(f"Executing goal for trigger {trigger_id}")

        try:
            # Activate skills if configured
            for skill_name in reg.action.skills:
                try:
                    self.agent.activate_skill(skill_name)
                    logger.debug(f"Activated skill {skill_name}")
                except Exception as e:
                    logger.warning(f"Failed to activate skill {skill_name}: {e}")

            # Build goal config
            goal_config = reg.action.to_goal_config(event)

            # Execute goal (run_goal expects goal string as first arg)
            result = await self.agent.run_goal(
                goal=goal_config.description,
                success_criteria=goal_config.success_criteria,
                workspace_dir=goal_config.workspace_dir,
                max_iterations=goal_config.max_iterations,
                max_context_resets=goal_config.max_context_resets,
                timeout_seconds=goal_config.timeout_seconds,
                custom_verifier=goal_config.custom_verifier,
            )

            # Update statistics
            reg.last_fired = datetime.now()
            reg.fire_count += 1

            if result.achieved:
                logger.info(
                    f"Trigger {trigger_id} goal achieved in {result.total_iterations} iterations"
                )
            else:
                logger.warning(f"Trigger {trigger_id} goal not achieved: {result.status.value}")

        except Exception as e:
            reg.error_count += 1
            reg.last_error = str(e)
            logger.error(f"Error executing trigger {trigger_id}: {e}")

            # Retry if configured
            if reg.action.max_retries > 0:
                await self._retry(reg, event)

    async def _retry(
        self,
        reg: TriggerRegistration,
        event: TriggerEvent,
    ) -> None:
        """
        Retry a failed trigger execution.

        Args:
            reg: Trigger registration
            event: Original event
        """
        for attempt in range(reg.action.max_retries):
            await asyncio.sleep(reg.action.retry_delay_seconds * (attempt + 1))

            try:
                logger.info(f"Retrying trigger {reg.trigger.id}, attempt {attempt + 1}")
                await self._handle_event(event)
                break
            except Exception as e:
                logger.error(f"Retry {attempt + 1} failed: {e}")

    def list_triggers(self) -> list[dict[str, Any]]:
        """
        List all registered triggers with their status.

        Returns:
            List of trigger info dictionaries
        """
        return [
            {
                "id": trigger_id,
                "type": reg.trigger.trigger_type.value,
                "state": reg.trigger.state.value,
                "enabled": reg.enabled,
                "last_fired": reg.last_fired.isoformat() if reg.last_fired else None,
                "fire_count": reg.fire_count,
                "error_count": reg.error_count,
                "last_error": reg.last_error,
            }
            for trigger_id, reg in self._registrations.items()
        ]

    def get_trigger(self, trigger_id: str) -> TriggerRegistration | None:
        """
        Get a trigger registration by ID.

        Args:
            trigger_id: Trigger ID

        Returns:
            TriggerRegistration or None if not found
        """
        return self._registrations.get(trigger_id)

    @property
    def is_running(self) -> bool:
        """Check if the manager is running."""
        return self._running

    @property
    def trigger_count(self) -> int:
        """Number of registered triggers."""
        return len(self._registrations)
