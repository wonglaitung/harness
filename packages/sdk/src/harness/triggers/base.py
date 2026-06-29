"""
Trigger base class - Abstract base class for all triggers.

This module defines the Trigger ABC that all trigger implementations must follow.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

from harness.triggers.types import TriggerEvent, TriggerState, TriggerType

if TYPE_CHECKING:
    from harness.triggers.types import TriggerAction


class Trigger(ABC):
    """
    Abstract base class for triggers.

    A Trigger monitors for a specific condition and fires events when
    that condition is met. Subclasses implement specific triggering
    mechanisms (cron, interval, webhook, etc.).

    Lifecycle:
        1. Create trigger with configuration
        2. Call start() with a callback function
        3. Trigger monitors for condition
        4. When condition met, creates TriggerEvent and calls callback
        5. Call stop() to cease monitoring

    Attributes:
        trigger_type: Type of this trigger
        id: Unique identifier for this trigger
        state: Current state of the trigger
        action: Action to take when trigger fires

    Example:
        ```python
        class MyTrigger(Trigger):
            trigger_type = TriggerType.CUSTOM

            async def start(self, callback):
                self._callback = callback
                # Start monitoring...

            async def stop(self):
                # Stop monitoring...

            def create_event(self, payload=None):
                return TriggerEvent(
                    trigger_type=self.trigger_type,
                    trigger_id=self.id,
                    payload=payload or {},
                )
        ```
    """

    trigger_type: TriggerType
    id: str = ""
    state: TriggerState = TriggerState.IDLE
    action: "TriggerAction | None" = None

    @abstractmethod
    async def start(self, callback: Callable[[TriggerEvent], None]) -> None:
        """
        Start the trigger.

        Args:
            callback: Function to call when trigger fires.
                     Receives a TriggerEvent as argument.

        Raises:
            RuntimeError: If trigger is already running
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the trigger.

        Should be safe to call multiple times.
        """
        pass

    @abstractmethod
    def create_event(self, payload: dict[str, any] | None = None) -> TriggerEvent:
        """
        Create a trigger event.

        Args:
            payload: Optional data to include in the event

        Returns:
            TriggerEvent instance
        """
        pass

    def is_running(self) -> bool:
        """Check if trigger is currently running."""
        return self.state == TriggerState.RUNNING

    def is_stopped(self) -> bool:
        """Check if trigger is stopped."""
        return self.state == TriggerState.STOPPED

    def _set_running(self) -> None:
        """Set state to running."""
        self.state = TriggerState.RUNNING

    def _set_stopped(self) -> None:
        """Set state to stopped."""
        self.state = TriggerState.STOPPED

    def _set_error(self, error: str | None = None) -> None:
        """Set state to error."""
        self.state = TriggerState.ERROR
        self._last_error = error

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, state={self.state.value})"
