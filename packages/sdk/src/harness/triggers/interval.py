"""
IntervalTrigger - Fixed interval trigger for periodic execution.

This module implements Trigger for interval-based scheduling.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from harness.triggers.base import Trigger
from harness.triggers.types import TriggerAction, TriggerEvent, TriggerType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class IntervalTrigger(Trigger):
    """
    Interval-based trigger for periodic execution.

    Fires events at a fixed interval. Simpler than cron for
    regular periodic tasks.

    Attributes:
        interval_seconds: Time between firings in seconds
        start_immediately: Whether to fire immediately on start
        action: Action to execute when triggered

    Example:
        ```python
        # Every 5 minutes
        trigger = IntervalTrigger(
            interval_seconds=300,
            action=TriggerAction(goal="Health check"),
        )

        # Every hour, fire immediately on start
        trigger = IntervalTrigger(
            interval_seconds=3600,
            action=TriggerAction(goal="Hourly sync"),
            start_immediately=True,
        )

        # Start the trigger
        await trigger.start(my_callback)
        ```
    """

    trigger_type = TriggerType.INTERVAL

    def __init__(
        self,
        interval_seconds: int | float,
        action: TriggerAction,
        start_immediately: bool = False,
        trigger_id: str = "",
    ):
        """
        Initialize interval trigger.

        Args:
            interval_seconds: Time between firings (minimum 1 second)
            action: Action to execute when triggered
            start_immediately: Fire immediately when started (default: False)
            trigger_id: Optional unique identifier

        Raises:
            ValueError: If interval_seconds is less than 1
        """
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be at least 1 second")

        self.interval_seconds = float(interval_seconds)
        self.action = action
        self.start_immediately = start_immediately

        self.id = trigger_id or self._generate_id()
        self._running = False
        self._task: asyncio.Task | None = None
        self._callback: Callable[[TriggerEvent], None] | None = None
        self._fire_count = 0

    def _generate_id(self) -> str:
        """Generate a unique trigger ID."""
        import uuid

        return f"interval_{uuid.uuid4().hex[:8]}"

    async def start(self, callback: Callable[[TriggerEvent], None]) -> None:
        """
        Start the interval trigger.

        Args:
            callback: Function to call when trigger fires
        """
        if self._running:
            logger.warning(f"IntervalTrigger {self.id} is already running")
            return

        self._callback = callback
        self._running = True
        self._set_running()

        # Start the background task
        self._task = asyncio.create_task(self._run_loop())

        logger.info(
            f"IntervalTrigger {self.id} started with interval {self.interval_seconds}s"
        )

    async def stop(self) -> None:
        """Stop the interval trigger."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._set_stopped()
        logger.info(f"IntervalTrigger {self.id} stopped after {self._fire_count} fires")

    def create_event(self, payload: dict[str, any] | None = None) -> TriggerEvent:
        """Create a trigger event."""
        return TriggerEvent(
            trigger_type=self.trigger_type,
            trigger_id=self.id,
            payload={
                "interval_seconds": self.interval_seconds,
                "fire_count": self._fire_count,
                **(payload or {}),
            },
        )

    async def _run_loop(self) -> None:
        """Main loop that fires at regular intervals."""
        # Fire immediately if configured
        if self.start_immediately and self._running and self._callback:
            await self._fire_event()

        while self._running:
            try:
                # Wait for interval
                await asyncio.sleep(self.interval_seconds)

                # Fire event if still running
                if self._running and self._callback:
                    await self._fire_event()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"IntervalTrigger {self.id} error: {e}")
                self._set_error(str(e))
                # Continue running on error
                await asyncio.sleep(60)  # Wait before retrying

    async def _fire_event(self) -> None:
        """Fire a trigger event."""
        self._fire_count += 1
        event = self.create_event(
            payload={"fire_number": self._fire_count}
        )
        logger.debug(
            f"IntervalTrigger {self.id} firing event #{self._fire_count}"
        )
        self._callback(event)

    @property
    def fire_count(self) -> int:
        """Number of times this trigger has fired."""
        return self._fire_count

    def get_estimated_next_run(self) -> datetime:
        """
        Get estimated next run time.

        Note: This is an estimate based on current time,
        not the actual scheduled time which depends on
        when the loop is in its cycle.

        Returns:
            Estimated next datetime
        """
        from datetime import timedelta

        return datetime.now() + timedelta(seconds=self.interval_seconds)

    def __repr__(self) -> str:
        return (
            f"IntervalTrigger(id={self.id!r}, interval={self.interval_seconds}s, "
            f"state={self.state.value}, fires={self._fire_count})"
        )
