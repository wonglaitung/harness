"""
Automation - Simplified API for Trigger + Goal execution.

This module provides the Automation class, which is the primary
user-facing API for Loop Engineering Phase 2.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

from harness.loop.types import GoalConfig, GoalResult
from harness.triggers import CronTrigger, IntervalTrigger, Trigger, TriggerAction

if TYPE_CHECKING:
    from harness.sdk.harness import AgentHarness

logger = logging.getLogger(__name__)


class AutomationStatus(Enum):
    """
    Status of an Automation.

    Automations transition through these states during their lifecycle.
    """

    PENDING = "pending"       # Not started yet
    RUNNING = "running"       # Active and monitoring
    PAUSED = "paused"         # Temporarily paused
    STOPPED = "stopped"       # Permanently stopped
    ERROR = "error"           # Error state


@dataclass
class AutomationConfig:
    """
    Configuration for an Automation.

    An Automation combines a trigger with a goal, providing a simple
    way to set up scheduled or periodic goal execution.

    Attributes:
        name: Human-readable name for this automation
        goal: Goal description to execute when triggered

        # Trigger configuration (one of schedule, interval_seconds, or trigger)
        schedule: Cron expression (e.g., "0 9 * * *" for daily at 9:00)
        interval_seconds: Fixed interval in seconds
        trigger: Custom Trigger instance

        # Goal configuration
        workspace_dir: Working directory
        max_iterations: Maximum iterations per execution
        timeout_seconds: Execution timeout
        custom_verifier: Optional verification function

        # Output configuration
        skills: Skills to activate
        output_channels: Channels for results

        # Execution control
        max_retries: Retry attempts on failure
        retry_delay_seconds: Delay between retries
    """

    # Identity
    name: str

    # Goal
    goal: str

    # Trigger (one required)
    schedule: str | None = None
    interval_seconds: int | None = None
    trigger: Trigger | None = None

    # Goal configuration
    workspace_dir: str = "."
    max_iterations: int = 50
    timeout_seconds: int = 3600
    custom_verifier: Callable | None = None

    # Skills and output
    skills: list[str] = field(default_factory=list)
    output_channels: list[str] = field(default_factory=list)

    # Retry
    max_retries: int = 3
    retry_delay_seconds: float = 5.0

    def __post_init__(self):
        """Validate configuration."""
        if not self.name:
            raise ValueError("name is required")

        if not self.goal:
            raise ValueError("goal is required")

        # Ensure exactly one trigger is specified
        triggers = [
            self.schedule is not None,
            self.interval_seconds is not None,
            self.trigger is not None,
        ]
        if sum(triggers) == 0:
            raise ValueError(
                "One of schedule, interval_seconds, or trigger is required"
            )
        if sum(triggers) > 1:
            raise ValueError(
                "Only one of schedule, interval_seconds, or trigger can be specified"
            )


@dataclass
class AutomationResult:
    """
    Result of an Automation execution.

    Tracks the status and statistics of an automation.

    Attributes:
        automation_name: Name of the automation
        status: Current status
        goal_result: Result from last goal execution
        last_run: When the automation last ran
        run_count: Total number of executions
        error_count: Number of failed executions
        error_message: Last error message
    """

    automation_name: str
    status: AutomationStatus = AutomationStatus.PENDING
    goal_result: GoalResult | None = None
    last_run: datetime | None = None
    run_count: int = 0
    error_count: int = 0
    error_message: str | None = None


class Automation:
    """
    Automation - Simplified API for Trigger + Goal.

    Automation is the primary user-facing API for Loop Engineering Phase 2.
    It combines a trigger with a goal configuration, providing a simple
    interface for scheduled and periodic task execution.

    Example:
        ```python
        from harness.loop import Automation

        # Create a daily automation
        automation = Automation(
            name="daily-report",
            schedule="0 9 * * *",
            goal="Generate daily report and send to Slack",
            skills=["report-generation"],
        )

        # Start it
        await automation.start(agent)

        # Check status
        print(automation.status)

        # Stop it
        await automation.stop()
        ```

        ```python
        # Interval-based automation
        automation = Automation(
            name="health-check",
            interval_seconds=300,  # Every 5 minutes
            goal="Check system health",
        )
        await automation.start(agent)
        ```
    """

    def __init__(
        self,
        name: str,
        goal: str,
        schedule: str | None = None,
        interval_seconds: int | None = None,
        trigger: Trigger | None = None,
        **kwargs,
    ):
        """
        Create an Automation.

        Args:
            name: Human-readable name
            goal: Goal description to execute
            schedule: Cron expression for scheduled execution
            interval_seconds: Interval for periodic execution
            trigger: Custom trigger instance
            **kwargs: Additional AutomationConfig options
        """
        self.config = AutomationConfig(
            name=name,
            goal=goal,
            schedule=schedule,
            interval_seconds=interval_seconds,
            trigger=trigger,
            **kwargs,
        )

        self._trigger: Trigger | None = None
        self._agent: AgentHarness | None = None
        self._status = AutomationStatus.PENDING
        self._result = AutomationResult(automation_name=name)

    @classmethod
    def create(
        cls,
        name: str,
        goal: str,
        schedule: str | None = None,
        interval_seconds: int | None = None,
        **kwargs,
    ) -> "Automation":
        """
        Convenience factory method.

        Args:
            name: Automation name
            goal: Goal description
            schedule: Cron expression (optional)
            interval_seconds: Interval in seconds (optional)
            **kwargs: Additional options

        Returns:
            Automation instance
        """
        return cls(
            name=name,
            goal=goal,
            schedule=schedule,
            interval_seconds=interval_seconds,
            **kwargs,
        )

    @property
    def name(self) -> str:
        """Automation name."""
        return self.config.name

    @property
    def status(self) -> AutomationStatus:
        """Current status."""
        return self._status

    @property
    def result(self) -> AutomationResult:
        """Execution result."""
        return self._result

    @property
    def is_running(self) -> bool:
        """Check if automation is running."""
        return self._status == AutomationStatus.RUNNING

    async def start(self, agent: "AgentHarness") -> None:
        """
        Start the automation.

        Args:
            agent: AgentHarness instance to use for execution

        Raises:
            ValueError: If no valid trigger configuration
        """
        if self._status == AutomationStatus.RUNNING:
            logger.warning(f"Automation {self.name} is already running")
            return

        self._agent = agent

        # Create the trigger
        action = self._create_action()

        if self.config.schedule:
            self._trigger = CronTrigger(
                schedule=self.config.schedule,
                action=action,
                trigger_id=f"auto_{self.name}",
            )
        elif self.config.interval_seconds:
            self._trigger = IntervalTrigger(
                interval_seconds=self.config.interval_seconds,
                action=action,
                trigger_id=f"auto_{self.name}",
            )
        elif self.config.trigger:
            self._trigger = self.config.trigger
            self._trigger.action = action
        else:
            raise ValueError("No valid trigger configuration")

        # Start the trigger
        await self._trigger.start(self._on_trigger)
        self._status = AutomationStatus.RUNNING

        logger.info(
            f"Automation {self.name} started "
            f"(trigger: {self._trigger.trigger_type.value})"
        )

    async def stop(self) -> None:
        """Stop the automation."""
        if self._trigger:
            await self._trigger.stop()
            self._trigger = None

        self._status = AutomationStatus.STOPPED
        logger.info(f"Automation {self.name} stopped after {self._result.run_count} runs")

    async def pause(self) -> None:
        """Pause the automation."""
        if self._trigger and self._trigger.is_running():
            await self._trigger.stop()

        self._status = AutomationStatus.PAUSED
        logger.info(f"Automation {self.name} paused")

    async def resume(self) -> None:
        """Resume a paused automation."""
        if self._status != AutomationStatus.PAUSED:
            logger.warning(f"Automation {self.name} is not paused")
            return

        if self._trigger and self._agent:
            await self._trigger.start(self._on_trigger)
            self._status = AutomationStatus.RUNNING
            logger.info(f"Automation {self.name} resumed")

    def _create_action(self) -> TriggerAction:
        """Create TriggerAction from configuration."""
        return TriggerAction(
            goal=self.config.goal,
            workspace_dir=self.config.workspace_dir,
            max_iterations=self.config.max_iterations,
            timeout_seconds=self.config.timeout_seconds,
            custom_verifier=self.config.custom_verifier,
            skills=self.config.skills,
            output_channels=self.config.output_channels,
            max_retries=self.config.max_retries,
            retry_delay_seconds=self.config.retry_delay_seconds,
        )

    def _on_trigger(self, event: Any) -> None:
        """
        Callback when trigger fires.

        Creates an async task to execute the goal.

        Args:
            event: TriggerEvent from the trigger
        """
        if self._status != AutomationStatus.RUNNING:
            return

        # Create async task for goal execution
        asyncio.create_task(self._execute_goal(event))

    async def _execute_goal(self, event: Any) -> None:
        """
        Execute the goal.

        Args:
            event: TriggerEvent that triggered execution
        """
        if not self._agent:
            logger.error(f"Automation {self.name} has no agent")
            return

        try:
            logger.info(f"Automation {self.name} executing goal")

            # Activate skills
            for skill_name in self.config.skills:
                try:
                    self._agent.activate_skill(skill_name)
                except Exception as e:
                    logger.warning(f"Failed to activate skill {skill_name}: {e}")

            # Build goal config
            goal_config = GoalConfig(
                description=self.config.goal,
                workspace_dir=self.config.workspace_dir,
                max_iterations=self.config.max_iterations,
                timeout_seconds=self.config.timeout_seconds,
                custom_verifier=self.config.custom_verifier,
            )

            # Execute
            result = await self._agent.run_goal(goal_config)

            # Update statistics
            self._result.goal_result = result
            self._result.last_run = datetime.now()
            self._result.run_count += 1

            if result.achieved:
                logger.info(
                    f"Automation {self.name} goal achieved in "
                    f"{result.total_iterations} iterations"
                )
            else:
                logger.warning(
                    f"Automation {self.name} goal not achieved: {result.status.value}"
                )

            # Handle output channels
            await self._handle_output(result)

        except Exception as e:
            self._result.error_count += 1
            self._result.error_message = str(e)
            self._status = AutomationStatus.ERROR
            logger.error(f"Automation {self.name} error: {e}")

    async def _handle_output(self, result: GoalResult) -> None:
        """
        Handle output to configured channels.

        Args:
            result: Goal execution result
        """
        for channel in self.config.output_channels:
            try:
                if channel == "console":
                    print(f"[{self.name}] {result.final_response}")
                elif channel == "log":
                    logger.info(f"[{self.name}] {result.final_response}")
                # Additional channels (slack, email) would be implemented here
            except Exception as e:
                logger.warning(f"Failed to output to {channel}: {e}")

    def __repr__(self) -> str:
        return (
            f"Automation(name={self.name!r}, status={self._status.value}, "
            f"runs={self._result.run_count})"
        )
