"""
TriggerManager - Manages trigger lifecycle and execution.

This module provides the central manager for all triggers,
handling registration, lifecycle, and goal execution.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from harness.triggers.types import TriggerAction, TriggerEvent, TriggerRegistration

if TYPE_CHECKING:
    from harness.sdk.harness import AgentHarness
    from harness.triggers.base import Trigger

logger = logging.getLogger(__name__)


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
        agent: "AgentHarness",
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
        # Queue will be created in start() to bind to correct event loop
        self._event_queue: asyncio.Queue[TriggerEvent] | None = None
        self._processor_task: asyncio.Task | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._running_tasks: set[asyncio.Task] = set()

    def register(
        self,
        trigger: "Trigger",
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

        # Create queue in the current event loop (fixes qasync event loop binding issue)
        self._event_queue = asyncio.Queue()
        logger.debug("Created event queue in current event loop")

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

        logger.info(
            f"TriggerManager started with {len(self._registrations)} triggers"
        )

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
            logger.info(
                f"Waiting for {len(self._running_tasks)} active tasks to complete..."
            )
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
        if self._event_queue is None:
            logger.warning(f"Event queue not initialized, dropping event from {event.trigger_id}")
            return
        self._event_queue.put_nowait(event)
        logger.debug(f"Event enqueued for trigger {event.trigger_id}, queue size: {self._event_queue.qsize()}")

    async def enqueue_event(self, event: TriggerEvent) -> None:
        """
        Async enqueue an event for processing.

        Called by ConnectorManager for external events.
        This async version is required for non-blocking operation
        in async event loops (e.g., Slack Socket Mode).

        Args:
            event: Event to enqueue
        """
        if self._event_queue is None:
            logger.warning(f"Event queue not initialized, dropping event from {event.trigger_id}")
            return
        await self._event_queue.put(event)

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
                # Re-create queue if it's bound to a different event loop (qasync issue)
                queue = self._ensure_queue_for_current_loop()
                if queue is None:
                    logger.warning("Could not get/create event queue, waiting...")
                    await asyncio.sleep(0.1)
                    continue

                event = await queue.get()

                logger.debug(f"Processing event from trigger {event.trigger_id}, queue size: {queue.qsize()}")
                # Execute concurrently, not blocking queue consumption
                task = asyncio.create_task(self._handle_event_concurrent(event))
                self._running_tasks.add(task)
                task.add_done_callback(self._running_tasks.discard)

            except asyncio.CancelledError:
                logger.info("Event processor cancelled")
                break
            except RuntimeError as e:
                # qasync may switch event loops, causing queue access issues
                if "bound to a different event loop" in str(e):
                    logger.debug(f"Event loop changed, will recreate queue: {e}")
                    self._event_queue = None  # Force recreation on next iteration
                    await asyncio.sleep(0.01)  # Small delay before retry
                else:
                    logger.error(f"RuntimeError processing event: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)

        logger.info(f"Event processor stopped, _running={self._running}, loops={loop_count}")

    def _ensure_queue_for_current_loop(self) -> asyncio.Queue[TriggerEvent] | None:
        """
        Ensure we have a queue bound to the current event loop.

        qasync may switch event loops during execution, causing the original
        queue to become inaccessible. This method checks if the current queue
        works, and creates a new one if needed.
        """
        if self._event_queue is None:
            # Create new queue in current event loop
            try:
                self._event_queue = asyncio.Queue()
                logger.debug("Created new event queue in current event loop")
                return self._event_queue
            except Exception as e:
                logger.error(f"Failed to create event queue: {e}")
                return None

        # Test if existing queue works with current event loop
        try:
            # Try a non-blocking check - qsize() doesn't require event loop
            _ = self._event_queue.qsize()
            return self._event_queue
        except RuntimeError as e:
            if "bound to a different event loop" in str(e):
                logger.debug("Queue bound to different event loop, creating new one")
                try:
                    self._event_queue = asyncio.Queue()
                    logger.debug("Created new event queue after event loop change")
                    return self._event_queue
                except Exception as create_error:
                    logger.error(f"Failed to create new event queue: {create_error}")
                    return None
            else:
                logger.error(f"Unexpected error accessing queue: {e}")
                return None

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
                    f"Trigger {trigger_id} goal achieved in "
                    f"{result.total_iterations} iterations"
                )
            else:
                logger.warning(
                    f"Trigger {trigger_id} goal not achieved: {result.status.value}"
                )

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
                logger.info(
                    f"Retrying trigger {reg.trigger.id}, attempt {attempt + 1}"
                )
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
