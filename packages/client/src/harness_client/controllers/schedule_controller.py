"""
Schedule Controller for Harness Client.

Manages triggers and automations using the SDK's TriggerManager.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScheduleConfig:
    """Configuration for a scheduled task."""
    id: str
    name: str
    goal: str
    trigger_type: str  # "cron" or "interval"
    trigger_value: str  # cron expression or interval seconds
    enabled: bool = True
    max_iterations: int = 50
    timeout_seconds: int = 3600
    skills: list[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    status: str = "idle"  # idle, running, paused, error
    error_message: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "trigger_type": self.trigger_type,
            "trigger_value": self.trigger_value,
            "enabled": self.enabled,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "skills": self.skills,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "status": self.status,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleConfig":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            goal=data.get("goal", ""),
            trigger_type=data.get("trigger_type", "cron"),
            trigger_value=data.get("trigger_value", ""),
            enabled=data.get("enabled", True),
            max_iterations=data.get("max_iterations", 50),
            timeout_seconds=data.get("timeout_seconds", 3600),
            skills=data.get("skills", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            next_run=datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None,
            run_count=data.get("run_count", 0),
            status=data.get("status", "idle"),
            error_message=data.get("error_message", ""),
        )


class ScheduleController:
    """
    Controller for managing scheduled tasks.

    Uses the SDK's TriggerManager for actual scheduling.
    """

    def __init__(self):
        self._schedules: dict[str, ScheduleConfig] = {}
        self._change_callback: Optional[Callable[[], None]] = None
        self._config_path: Optional[Path] = None
        self._trigger_manager = None
        self._agent = None
        self._running = False

    def set_change_callback(self, callback: Callable[[], None]):
        """Set callback to be called when schedule list changes."""
        self._change_callback = callback

    def set_agent(self, agent):
        """Set the agent to use for running tasks."""
        self._agent = agent

    def _notify_change(self):
        """Notify listeners of a change."""
        if self._change_callback:
            self._change_callback()

    def get_schedule_list(self) -> list[ScheduleConfig]:
        """Get list of all schedules."""
        return list(self._schedules.values())

    def get_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """Get a specific schedule by ID."""
        return self._schedules.get(schedule_id)

    def add_schedule(self, config: ScheduleConfig) -> bool:
        """Add a new schedule."""
        if config.id in self._schedules:
            logger.warning(f"Schedule {config.id} already exists")
            return False

        config.created_at = datetime.now()
        self._schedules[config.id] = config
        self._save_config()
        self._notify_change()

        # If enabled, register with trigger manager
        if config.enabled and self._trigger_manager:
            self._register_trigger(config)
            logger.info(f"Registered trigger for schedule: {config.name}")

        logger.info(f"Added schedule: {config.name}")
        return True

    def update_schedule(self, schedule_id: str, updates: dict) -> bool:
        """Update an existing schedule."""
        if schedule_id not in self._schedules:
            logger.warning(f"Schedule {schedule_id} not found")
            return False

        config = self._schedules[schedule_id]

        # Update fields
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        self._save_config()
        self._notify_change()

        # Re-register trigger if needed
        if self._trigger_manager:
            self._unregister_trigger(schedule_id)
            if config.enabled:
                self._register_trigger(config)

        logger.info(f"Updated schedule: {config.name}")
        return True

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if schedule_id not in self._schedules:
            return False

        # Unregister trigger
        if self._trigger_manager:
            self._unregister_trigger(schedule_id)

        del self._schedules[schedule_id]
        self._save_config()
        self._notify_change()

        logger.info(f"Deleted schedule: {schedule_id}")
        return True

    def toggle_schedule(self, schedule_id: str) -> bool:
        """Toggle a schedule's enabled state."""
        config = self._schedules.get(schedule_id)
        if not config:
            return False

        config.enabled = not config.enabled
        config.status = "idle" if config.enabled else "paused"

        self._save_config()
        self._notify_change()

        # Register/unregister trigger
        if self._trigger_manager:
            if config.enabled:
                self._register_trigger(config)
            else:
                self._unregister_trigger(schedule_id)

        logger.info(f"Toggled schedule {config.name}: enabled={config.enabled}")
        return True

    def _register_trigger(self, config: ScheduleConfig):
        """Register a trigger with the SDK's TriggerManager.

        If the manager is already running, the trigger will be started asynchronously.
        """
        if not self._trigger_manager:
            return

        try:
            from harness import TriggerAction

            action = TriggerAction(
                goal=config.goal,
                max_iterations=config.max_iterations,
                timeout_seconds=config.timeout_seconds,
                skills=config.skills,
            )

            if config.trigger_type == "cron":
                from harness import CronTrigger
                trigger = CronTrigger(
                    schedule=config.trigger_value,
                    action=action,
                    trigger_id=config.id,
                )
            else:  # interval
                from harness import IntervalTrigger
                interval_seconds = int(config.trigger_value)
                trigger = IntervalTrigger(
                    interval_seconds=interval_seconds,
                    action=action,
                    trigger_id=config.id,
                )

            self._trigger_manager.register(trigger)

            # If manager is already running, start the trigger asynchronously
            if self._trigger_manager.is_running:
                asyncio.create_task(trigger.start(self._trigger_manager._enqueue_event))

            config.status = "running"
            logger.info(f"Registered trigger for {config.name}")

        except Exception as e:
            logger.error(f"Failed to register trigger: {e}")
            config.status = "error"
            config.error_message = str(e)

    def _unregister_trigger(self, schedule_id: str):
        """Unregister a trigger from the SDK's TriggerManager."""
        if not self._trigger_manager:
            return

        try:
            self._trigger_manager.unregister(schedule_id)
            logger.info(f"Unregistered trigger {schedule_id}")
        except Exception as e:
            logger.error(f"Failed to unregister trigger: {e}")

    async def start(self):
        """Start the trigger manager."""
        if self._running:
            return

        if not self._agent:
            logger.warning("No agent set, ScheduleController will not execute tasks")
            return

        try:
            from harness import TriggerManager

            self._trigger_manager = TriggerManager(self._agent)

            # Register all enabled schedules BEFORE starting the manager
            for config in self._schedules.values():
                if config.enabled:
                    self._register_trigger(config)

            # Now start the manager (will start all registered triggers)
            await self._trigger_manager.start()

            self._running = True
            logger.info("ScheduleController started")

        except Exception as e:
            logger.error(f"Failed to start ScheduleController: {e}")

    async def stop(self):
        """Stop the trigger manager."""
        if not self._running or not self._trigger_manager:
            return

        try:
            await self._trigger_manager.stop()
            self._running = False
            logger.info("ScheduleController stopped")
        except Exception as e:
            logger.error(f"Failed to stop ScheduleController: {e}")

    def load_from_file(self, path: Path):
        """Load schedules from a JSON file."""
        self._config_path = path

        if not path.exists():
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._schedules.clear()
            for item in data.get("schedules", []):
                config = ScheduleConfig.from_dict(item)
                self._schedules[config.id] = config

            logger.info(f"Loaded {len(self._schedules)} schedules from {path}")
            self._notify_change()

        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")

    def _save_config(self):
        """Save schedules to the config file."""
        if not self._config_path:
            return

        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "schedules": [s.to_dict() for s in self._schedules.values()]
            }

            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved schedules to {self._config_path}")

        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")

    def save_to_file(self, path: Path):
        """Save schedules to a specific file path.

        Args:
            path: Path to save the schedule configuration
        """
        self._config_path = path
        self._save_config()

    def validate_cron(self, expression: str) -> tuple[bool, str]:
        """Validate a cron expression.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            from croniter import croniter
            croniter(expression)
            return True, ""
        except ImportError:
            # croniter not installed, do basic validation
            parts = expression.split()
            if len(parts) != 5:
                return False, "Cron 表达式必须包含 5 个字段"
            return True, ""
        except Exception as e:
            return False, f"无效的 Cron 表达式: {str(e)}"

    def get_next_run_times(self, expression: str, count: int = 5) -> list[datetime]:
        """Get the next run times for a cron expression."""
        try:
            from croniter import croniter
            cron = croniter(expression, datetime.now())
            return [cron.get_next(datetime) for _ in range(count)]
        except ImportError:
            return []
        except Exception:
            return []
