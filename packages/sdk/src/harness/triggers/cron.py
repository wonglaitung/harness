"""
CronTrigger - Schedule-based trigger using cron expressions.

This module implements Trigger for cron-based scheduling.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

try:
    import croniter
except ImportError:
    croniter = None  # type: ignore

from harness.triggers.base import Trigger
from harness.triggers.types import TriggerAction, TriggerEvent, TriggerType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CronTrigger(Trigger):
    """
    Cron-based trigger for scheduled execution.

    Uses cron expressions to determine when to fire events.
    Supports standard 5-field cron format: minute hour day month weekday

    Attributes:
        schedule: Cron expression (e.g., "0 9 * * *" for daily at 9:00)
        timezone: Timezone for schedule interpretation (default: local)
        jitter_seconds: Random delay to add (avoid thundering herd)

    Example:
        ```python
        # Daily at 9:00 AM
        trigger = CronTrigger(
            schedule="0 9 * * *",
            action=TriggerAction(goal="Generate daily report"),
        )

        # Every hour with 5-minute jitter
        trigger = CronTrigger(
            schedule="0 * * * *",
            action=TriggerAction(goal="Health check"),
            jitter_seconds=300,
        )

        # Start the trigger
        await trigger.start(my_callback)
        ```
    """

    trigger_type = TriggerType.CRON

    def __init__(
        self,
        schedule: str,
        action: TriggerAction,
        timezone: str = "local",
        jitter_seconds: int = 0,
        trigger_id: str = "",
    ):
        """
        Initialize cron trigger.

        Args:
            schedule: Cron expression (5 fields: minute hour day month weekday)
            action: Action to execute when triggered
            timezone: Timezone for schedule ("local", "UTC", or timezone name)
            jitter_seconds: Maximum random delay in seconds (0 = no jitter)
            trigger_id: Optional unique identifier

        Raises:
            ImportError: If croniter is not installed
            ValueError: If cron expression is invalid
        """
        if croniter is None:
            raise ImportError(
                "croniter is required for CronTrigger. "
                "Install with: pip install harness-sdk[cron] or pip install croniter"
            )

        self.schedule = schedule
        self.action = action
        self.timezone = timezone
        self.jitter_seconds = jitter_seconds

        # Parse cron expression to validate
        try:
            self._cron = croniter.croniter(schedule)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid cron expression '{schedule}': {e}") from e

        self.id = trigger_id or self._generate_id()
        self._running = False
        self._task: asyncio.Task | None = None
        self._callback: Callable[[TriggerEvent], None] | None = None

    def _generate_id(self) -> str:
        """Generate a unique trigger ID."""
        import uuid

        return f"cron_{uuid.uuid4().hex[:8]}"

    async def start(self, callback: Callable[[TriggerEvent], None]) -> None:
        """
        Start the cron trigger.

        Args:
            callback: Function to call when trigger fires
        """
        if self._running:
            logger.warning(f"CronTrigger {self.id} is already running")
            return

        self._callback = callback
        self._running = True
        self._set_running()

        # Start the background task
        self._task = asyncio.create_task(self._run_loop())

        logger.info(
            f"CronTrigger {self.id} started with schedule '{self.schedule}', "
            f"next run at {self.get_next_run()}"
        )

    async def stop(self) -> None:
        """Stop the cron trigger."""
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
        logger.info(f"CronTrigger {self.id} stopped")

    def create_event(self, payload: dict[str, any] | None = None) -> TriggerEvent:
        """Create a trigger event."""
        return TriggerEvent(
            trigger_type=self.trigger_type,
            trigger_id=self.id,
            payload={
                "schedule": self.schedule,
                "timezone": self.timezone,
                **(payload or {}),
            },
        )

    async def _run_loop(self) -> None:
        """Main loop that waits for scheduled times and fires events."""
        while self._running:
            try:
                # Calculate wait time until next scheduled run
                now = datetime.now()
                next_run = self.get_next_run()
                wait_seconds = (next_run - now).total_seconds()

                # Add jitter if configured
                if self.jitter_seconds > 0:
                    jitter = random.uniform(0, self.jitter_seconds)
                    wait_seconds += jitter
                    logger.debug(f"Added {jitter:.1f}s jitter to wait time")

                # Wait until next run
                if wait_seconds > 0:
                    logger.debug(
                        f"CronTrigger {self.id} waiting {wait_seconds:.1f}s "
                        f"until next run at {next_run}"
                    )
                    await asyncio.sleep(wait_seconds)

                # Fire event if still running
                if self._running and self._callback:
                    event = self.create_event(
                        payload={"scheduled_time": next_run.isoformat()}
                    )
                    logger.info(f"CronTrigger {self.id} firing event")
                    self._callback(event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"CronTrigger {self.id} error: {e}")
                self._set_error(str(e))
                # Continue running on error (don't crash the loop)
                await asyncio.sleep(60)  # Wait before retrying

    def get_next_run(self, base_time: datetime | None = None) -> datetime:
        """
        Get the next scheduled run time.

        Args:
            base_time: Base time to calculate from (default: now)

        Returns:
            Next scheduled datetime
        """
        if base_time is None:
            base_time = datetime.now()

        # Reset the croniter to base time and get next
        self._cron = croniter.croniter(self.schedule, base_time)
        return self._cron.get_next(datetime)

    def get_next_runs(self, n: int = 5) -> list[datetime]:
        """
        Get the next N scheduled run times.

        Args:
            n: Number of future runs to return

        Returns:
            List of scheduled datetimes
        """
        self._cron = croniter.croniter(self.schedule, datetime.now())
        return [self._cron.get_next(datetime) for _ in range(n)]

    def __repr__(self) -> str:
        return f"CronTrigger(id={self.id!r}, schedule={self.schedule!r}, state={self.state.value})"
