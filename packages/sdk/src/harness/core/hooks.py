"""
Lifecycle Hooks for Agent Loop.

Hooks allow custom logic to be injected at key points in the agent loop.
This is the foundation for advanced features like:
- Ralph Loop (long-horizon task continuation)
- Self-verification (auto-run tests after code changes)
- Audit logging
- Custom retry logic
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING

from harness.types import HookAction, HookContext, HookPoint, HookResult, Message

if TYPE_CHECKING:
    from harness.core.agent_loop import AgentLoop

logger = logging.getLogger(__name__)


class LifecycleHook(ABC):
    """
    Base class for lifecycle hooks.

    Hooks are called at specific points in the agent loop.
    Subclasses implement execute() to define custom behavior.

    Example:
        class MyHook(LifecycleHook):
            @property
            def hook_points(self) -> list[HookPoint]:
                return [HookPoint.BEFORE_TOOL_EXECUTE]

            async def execute(self, context: HookContext) -> HookResult:
                if context.tool_name == "dangerous_tool":
                    return HookResult.abort("Dangerous tool blocked")
                return HookResult.continue_()

        # Register with agent
        agent.add_hook(MyHook())
    """

    @property
    def hook_points(self) -> list[HookPoint]:
        """
        Which hook points this hook subscribes to.

        Override to specify which points to hook into.
        """
        return []

    @abstractmethod
    async def execute(self, context: HookContext) -> HookResult:
        """
        Execute the hook logic.

        Args:
            context: Context about the current state

        Returns:
            HookResult controlling what happens next
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} hook_points={self.hook_points}>"


class HookManager:
    """
    Manages registration and execution of lifecycle hooks.

    Used internally by AgentLoop to invoke hooks at appropriate points.

    Example:
        manager = HookManager()
        manager.register(MyHook())

        # Execute hooks at a point
        result = await manager.execute_hooks(
            HookPoint.BEFORE_TOOL_EXECUTE,
            HookContext(...)
        )
    """

    def __init__(self):
        self._hooks: dict[HookPoint, list[LifecycleHook]] = defaultdict(list)

    def register(
        self,
        hook: LifecycleHook,
        points: list[HookPoint] | None = None,
    ) -> None:
        """
        Register a hook for specific points.

        Args:
            hook: The hook to register
            points: Specific points to register for (uses hook.hook_points if None)
        """
        points = points or hook.hook_points
        for point in points:
            self._hooks[point].append(hook)
            logger.debug(f"Registered hook {hook} for point {point}")

    def unregister(self, hook: LifecycleHook) -> None:
        """
        Unregister a hook from all points.

        Args:
            hook: The hook to unregister
        """
        for point in list(self._hooks.keys()):
            if hook in self._hooks[point]:
                self._hooks[point].remove(hook)
                logger.debug(f"Unregistered hook {hook} from point {point}")

    def has_hooks(self, point: HookPoint) -> bool:
        """Check if there are hooks registered for a point."""
        return len(self._hooks[point]) > 0

    async def execute_hooks(
        self,
        point: HookPoint,
        context: HookContext,
    ) -> HookResult:
        """
        Execute all hooks for a point in sequence.

        Hooks are executed in registration order.
        If any hook returns a non-CONTINUE action, execution stops
        and that result is returned.

        Args:
            point: The hook point being triggered
            context: Context for the hook execution

        Returns:
            The final HookResult (CONTINUE if all hooks continue)
        """
        hooks = self._hooks[point]

        if not hooks:
            return HookResult.continue_()

        for hook in hooks:
            try:
                result = await hook.execute(context)

                if result.action != HookAction.CONTINUE:
                    logger.debug(
                        f"Hook {hook} returned action {result.action} at {point}"
                    )
                    return result

            except Exception as e:
                logger.exception(f"Hook {hook} raised exception at {point}: {e}")
                # Continue with other hooks on error
                continue

        return HookResult.continue_()

    def clear(self) -> None:
        """Remove all registered hooks."""
        self._hooks.clear()


# =============================================================================
# Built-in Hooks
# =============================================================================

class LoggingHook(LifecycleHook):
    """
    A hook that logs all hook point events.

    Useful for debugging and monitoring.
    """

    @property
    def hook_points(self) -> list[HookPoint]:
        return list(HookPoint)

    async def execute(self, context: HookContext) -> HookResult:
        """Log the hook event."""
        logger.info(
            f"[Hook] {context.hook_point.value} "
            f"session={context.session_id} iteration={context.iteration}"
        )
        return HookResult.continue_()


class AbortOnDangerousToolHook(LifecycleHook):
    """
    A hook that blocks dangerous tool calls.

    Prevents execution of tools that match a blocklist.
    """

    def __init__(self, blocked_tools: list[str] | None = None):
        self.blocked_tools = blocked_tools or [
            "rm",
            "sudo",
            "chmod",
            "chown",
            "dd",
            "mkfs",
            "fdisk",
        ]

    @property
    def hook_points(self) -> list[HookPoint]:
        return [HookPoint.BEFORE_TOOL_EXECUTE]

    async def execute(self, context: HookContext) -> HookResult:
        """Check if tool is blocked."""
        if context.tool_name in self.blocked_tools:
            logger.warning(f"Blocked dangerous tool: {context.tool_name}")
            return HookResult.abort(f"Tool '{context.tool_name}' is blocked for safety")

        # Also check bash commands
        if context.tool_name == "bash" and context.tool_args:
            command = context.tool_args.get("command", "")
            for blocked in self.blocked_tools:
                if blocked in command.split():
                    logger.warning(f"Blocked dangerous command: {blocked}")
                    return HookResult.abort(
                        f"Command contains blocked tool '{blocked}'"
                    )

        return HookResult.continue_()


class MaxToolCallsHook(LifecycleHook):
    """
    A hook that limits the number of calls to a specific tool.

    Useful to prevent infinite loops with a single tool.
    """

    def __init__(self, tool_name: str, max_calls: int = 5):
        self.tool_name = tool_name
        self.max_calls = max_calls
        self._call_counts: dict[str, int] = defaultdict(int)

    @property
    def hook_points(self) -> list[HookPoint]:
        return [HookPoint.BEFORE_TOOL_EXECUTE]

    async def execute(self, context: HookContext) -> HookResult:
        """Check if tool call limit is reached."""
        if context.tool_name != self.tool_name:
            return HookResult.continue_()

        key = f"{context.session_id}:{self.tool_name}"
        self._call_counts[key] += 1

        if self._call_counts[key] > self.max_calls:
            logger.warning(
                f"Tool {self.tool_name} called {self._call_counts[key]} times, "
                f"exceeds limit of {self.max_calls}"
            )
            return HookResult.abort(
                f"Tool '{self.tool_name}' exceeded max calls ({self.max_calls})"
            )

        return HookResult.continue_()

    def reset(self, session_id: str | None = None) -> None:
        """Reset call counts."""
        if session_id:
            keys_to_remove = [k for k in self._call_counts if k.startswith(session_id)]
            for key in keys_to_remove:
                del self._call_counts[key]
        else:
            self._call_counts.clear()


class ConfirmationHook(LifecycleHook):
    """
    Hook that asks for user confirmation before dangerous operations.

    This hook intercepts tool calls that may have destructive effects
    (file modifications, command execution) and asks the user to confirm.

    Design principles (based on industry best practices):
    1. File modifications (write/edit) always require confirmation
    2. Bash commands only require confirmation for dangerous patterns
    3. Read-only operations (read/glob/grep) never require confirmation

    Example:
        async def my_confirm(tool_name: str, args: dict) -> bool:
            # Show dialog, return True if user confirms
            return show_confirmation_dialog(tool_name, args)

        hook = ConfirmationHook(on_confirm=my_confirm)
        agent.add_hook(hook)
    """

    # Tools that always require confirmation (modify files)
    DANGEROUS_TOOLS = {
        "write",
        "edit",
    }

    # Dangerous command patterns within bash
    # Based on: Claude Code security research, OWASP guidelines, and cross-platform considerations
    DANGEROUS_COMMANDS = {
        # === System-destructive commands ===
        "rm",           # Delete files
        "rmdir",        # Delete directories
        "del",          # Windows delete
        "erase",        # Windows erase
        "format",       # Format disk (Windows)
        "diskpart",     # Windows disk management
        "dd",           # Disk duplicator (can wipe disks)
        "mkfs",         # Make filesystem
        "fdisk",        # Disk partitioning
        "shred",        # Secure delete
        "wipefs",       # Wipe filesystem signature

        # === Privilege escalation ===
        "sudo",         # Run as superuser (Linux/macOS)
        "su",           # Switch user
        "runas",        # Windows run as administrator
        "doas",         # OpenBSD alternative to sudo
        "pkexec",       # PolicyKit execute

        # === Permission changes ===
        "chmod",        # Change mode
        "chown",        # Change owner
        "chgrp",        # Change group
        "icacls",       # Windows ACL management
        "attrib",       # Windows file attributes

        # === Git destructive operations ===
        "git push --force",
        "git push -f",
        "git reset --hard",
        "git clean -fd",
        "git checkout --",  # Discard changes

        # === Package publishing ===
        "npm publish",
        "yarn publish",
        "pip upload",
        "twine upload",
        "cargo publish",
        "gem push",
        "mvn deploy",

        # === Network/data exfiltration ===
        "curl | bash",      # Dangerous pipe pattern
        "curl | sh",        # Dangerous pipe pattern
        "wget | bash",      # Dangerous pipe pattern
        "wget | sh",        # Dangerous pipe pattern
        "nc -l",            # Netcat listen (potential backdoor)
        "ncat -l",          # Ncat listen

        # === Process/job control ===
        "kill",         # Terminate processes
        "killall",      # Kill all processes by name
        "pkill",        # Kill by pattern
        "taskkill",     # Windows kill process

        # === Environment/shell manipulation ===
        "export",       # Set environment variable (can poison)
        "setenv",       # Set environment
        "source",       # Execute shell script
        "eval",         # Evaluate expression (code execution)

        # === Python dangerous patterns ===
        "python -c",    # Execute Python code
        "python3 -c",   # Execute Python code
        "pip install --force",
        "pip uninstall",

        # === Node.js dangerous patterns ===
        "node -e",      # Execute Node.js code
        "node -p",      # Execute and print
        "npm install -g",  # Global install

        # === Database operations ===
        "DROP TABLE",
        "DROP DATABASE",
        "TRUNCATE",
        "DELETE FROM",

        # === Service management ===
        "systemctl stop",
        "systemctl disable",
        "systemctl restart",
        "service stop",
        "net stop",     # Windows service
    }

    def __init__(
        self,
        on_confirm: "Callable[[str, dict], Coroutine[Any, Any, bool]]",
        dangerous_tools: set[str] | None = None,
        dangerous_commands: set[str] | None = None,
    ):
        """
        Initialize the confirmation hook.

        Args:
            on_confirm: Async callback that returns True if user confirms
            dangerous_tools: Set of tool names that require confirmation
            dangerous_commands: Set of command patterns that require confirmation
        """
        self.on_confirm = on_confirm
        self.dangerous_tools = dangerous_tools or self.DANGEROUS_TOOLS
        self.dangerous_commands = dangerous_commands or self.DANGEROUS_COMMANDS

    @property
    def hook_points(self) -> list[HookPoint]:
        from harness.types import HookPoint
        return [HookPoint.BEFORE_TOOL_EXECUTE]

    async def execute(self, context: "HookContext") -> "HookResult":
        """Check if tool requires confirmation and ask user."""
        from harness.types import HookPoint

        if not self._is_dangerous(context.tool_name, context.tool_args):
            return HookResult.continue_()

        try:
            confirmed = await self.on_confirm(context.tool_name, context.tool_args or {})
            if confirmed:
                logger.info(f"User confirmed operation: {context.tool_name}")
                return HookResult.continue_()
            else:
                logger.info(f"User rejected operation: {context.tool_name}")
                return HookResult.abort("User rejected the operation")

        except Exception as e:
            logger.error(f"Confirmation callback error: {e}")
            return HookResult.abort(f"Confirmation failed: {e}")

    def _is_dangerous(self, tool_name: str, args: dict | None) -> bool:
        """Check if the tool call is potentially dangerous.

        Rules:
        - write/edit: Always require confirmation
        - bash: Only if command matches dangerous patterns
        - read/glob/grep: Never require confirmation
        """
        # File modification tools always require confirmation
        if tool_name in self.dangerous_tools:
            return True

        # Bash: check command content for dangerous patterns
        if tool_name == "bash" and args:
            command = args.get("command", "")
            # Check for dangerous command patterns
            for dangerous in self.dangerous_commands:
                if dangerous in command:
                    return True

        return False
