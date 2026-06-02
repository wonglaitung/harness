"""
Sub-Agent Management.

Sub-agents allow the main agent to delegate sub-tasks to specialized child agents.
This is useful for:
- Task decomposition: Break large tasks into smaller, manageable pieces
- Parallel processing: Run multiple sub-agents concurrently
- Isolation: Each sub-agent has its own context window

Usage:
    from harness.core import SubAgentManager, SubAgentConfig

    # Create manager
    manager = SubAgentManager(parent_agent)

    # Spawn a sub-agent
    config = SubAgentConfig(
        name="code_analyzer",
        task="Analyze the codebase structure",
        max_iterations=20,
    )
    agent_id = await manager.spawn(config)

    # Run the sub-agent
    result = await manager.run(agent_id)

    # Collect results
    all_results = await manager.collect_all()
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from harness.sdk.harness import AgentHarness

logger = logging.getLogger(__name__)


class SubAgentStatus(Enum):
    """Status of a sub-agent."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubAgentConfig:
    """Configuration for a sub-agent."""

    # Unique name for this sub-agent
    name: str

    # Task description for the sub-agent
    task: str

    # Tools available to the sub-agent (None = inherit from parent)
    tools: list[str] | None = None

    # Maximum iterations for the sub-agent
    max_iterations: int = 20

    # Whether to inherit parent's context
    inherit_context: bool = False

    # How to report results back
    report_format: Literal["summary", "full", "structured"] = "summary"

    # Custom system prompt (overrides default)
    system_prompt: str | None = None

    # Working directory for the sub-agent
    working_directory: Path | None = None

    # Timeout in seconds (0 = no timeout)
    timeout: float = 0.0


@dataclass
class SubAgentResult:
    """Result from a sub-agent execution."""

    # Name of the sub-agent
    name: str

    # Whether the sub-agent completed successfully
    success: bool

    # Status of the sub-agent
    status: SubAgentStatus

    # Summary of the result (for summary format)
    summary: str | None = None

    # Full response (for full format)
    full_response: str | None = None

    # Structured result (for structured format)
    structured_result: dict[str, Any] | None = None

    # Number of iterations used
    iterations: int = 0

    # Token usage
    token_usage: dict[str, int] = field(default_factory=dict)

    # Error message if failed
    error: str | None = None


class SubAgentManager:
    """
    Manages sub-agents for task delegation.

    The manager creates, runs, and collects results from sub-agents.
    Each sub-agent is an independent AgentHarness with its own context.

    Example:
        parent = AgentHarness(model="claude-sonnet-4-6")
        manager = SubAgentManager(parent)

        # Create sub-agents for parallel analysis
        await manager.spawn(SubAgentConfig(
            name="core_analyzer",
            task="Analyze src/core directory",
        ))
        await manager.spawn(SubAgentConfig(
            name="tools_analyzer",
            task="Analyze src/tools directory",
        ))

        # Run all sub-agents in parallel
        results = await manager.run_all()

        # Aggregate results
        for name, result in results.items():
            print(f"{name}: {result.summary}")
    """

    def __init__(self, parent_agent: "AgentHarness"):
        """
        Initialize the sub-agent manager.

        Args:
            parent_agent: The parent agent that owns this manager
        """
        self.parent = parent_agent
        self._sub_agents: dict[str, "AgentHarness"] = {}
        self._configs: dict[str, SubAgentConfig] = {}
        self._results: dict[str, SubAgentResult] = {}
        self._statuses: dict[str, SubAgentStatus] = {}

    async def spawn(self, config: SubAgentConfig, llm_client: Any = None) -> str:
        """
        Create a new sub-agent.

        Args:
            config: Configuration for the sub-agent
            llm_client: Optional LLM client to use (for testing)

        Returns:
            The name of the created sub-agent
        """
        from harness.sdk.harness import AgentHarness
        from harness.sdk.config import HarnessConfig

        # Create sub-agent configuration
        # Inherit API settings from parent
        parent_config = getattr(self.parent, 'config', None)
        sub_config = HarnessConfig(
            model=getattr(parent_config, 'model', "claude-sonnet-4-6") if parent_config else "claude-sonnet-4-6",
            api_key=getattr(parent_config, 'api_key', None) if parent_config else None,
            provider=getattr(parent_config, 'provider', "anthropic") if parent_config else "anthropic",
            base_url=getattr(parent_config, 'base_url', None) if parent_config else None,
            max_iterations=config.max_iterations,
            system_prompt=config.system_prompt or self._build_default_prompt(config),
        )

        # Inherit tools from parent, filtered by config.tools if specified
        inherited_tools = None
        if hasattr(self.parent, '_tool_registry'):
            all_tools = self.parent._tool_registry.get_all()
            if config.tools is not None:
                # Filter tools by name - support both exact names and common aliases
                tool_aliases = {
                    "read": "read",
                    "write": "write_file",
                    "edit": "edit_file",
                    "glob": "glob",
                    "grep": "grep",
                    "bash": "bash",
                    "websearch": "web_search",
                    "webfetch": "web_fetch",
                }
                allowed_names = set()
                for name in config.tools:
                    # Add the name as-is
                    allowed_names.add(name)
                    # Add any alias for the name
                    if name in tool_aliases:
                        allowed_names.add(tool_aliases[name])
                    # Check if name is an alias value
                    for alias, target in tool_aliases.items():
                        if target == name:
                            allowed_names.add(alias)

                inherited_tools = [
                    tool for tool in all_tools
                    if tool.name in allowed_names
                ]
            else:
                # Inherit all tools if not specified
                inherited_tools = all_tools

        # Create the sub-agent with inherited tools
        if llm_client:
            sub_agent = AgentHarness(
                llm_client=llm_client,
                config=sub_config,
                tools=inherited_tools,
            )
        else:
            sub_agent = AgentHarness(
                config=sub_config,
                tools=inherited_tools,
            )

        # Store references
        self._sub_agents[config.name] = sub_agent
        self._configs[config.name] = config
        self._statuses[config.name] = SubAgentStatus.PENDING

        logger.info(f"Spawned sub-agent: {config.name}")
        return config.name

    async def run(self, name: str, input_message: str | None = None) -> SubAgentResult:
        """
        Run a specific sub-agent.

        Args:
            name: Name of the sub-agent to run
            input_message: Optional input message (uses task if None)

        Returns:
            Result from the sub-agent execution
        """
        sub_agent = self._sub_agents.get(name)
        config = self._configs.get(name)

        if not sub_agent or not config:
            raise ValueError(f"Sub-agent '{name}' not found")

        self._statuses[name] = SubAgentStatus.RUNNING
        logger.info(f"Running sub-agent: {name}")

        try:
            # Run the sub-agent
            input_text = input_message or config.task
            result = await sub_agent.run(input_text)

            # Build result based on report format
            sub_result = self._build_result(name, config, result)
            self._results[name] = sub_result
            self._statuses[name] = SubAgentStatus.COMPLETED

            logger.info(f"Sub-agent {name} completed: success={sub_result.success}")
            return sub_result

        except asyncio.TimeoutError:
            logger.warning(f"Sub-agent {name} timed out")
            result = SubAgentResult(
                name=name,
                success=False,
                status=SubAgentStatus.FAILED,
                error="Timeout",
            )
            self._results[name] = result
            self._statuses[name] = SubAgentStatus.FAILED
            return result

        except Exception as e:
            logger.exception(f"Sub-agent {name} failed: {e}")
            result = SubAgentResult(
                name=name,
                success=False,
                status=SubAgentStatus.FAILED,
                error=str(e),
            )
            self._results[name] = result
            self._statuses[name] = SubAgentStatus.FAILED
            return result

    async def run_all(self) -> dict[str, SubAgentResult]:
        """
        Run all pending sub-agents in parallel.

        Returns:
            Dict mapping sub-agent names to their results
        """
        pending = [
            name for name, status in self._statuses.items()
            if status == SubAgentStatus.PENDING
        ]

        # Run all in parallel
        tasks = [self.run(name) for name in pending]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        return {
            name: result if isinstance(result, SubAgentResult) else SubAgentResult(
                name=name,
                success=False,
                status=SubAgentStatus.FAILED,
                error=str(result),
            )
            for name, result in zip(pending, results)
        }

    def get_result(self, name: str) -> SubAgentResult | None:
        """Get the result of a specific sub-agent."""
        return self._results.get(name)

    def get_status(self, name: str) -> SubAgentStatus | None:
        """Get the status of a specific sub-agent."""
        return self._statuses.get(name)

    def get_all_results(self) -> dict[str, SubAgentResult]:
        """Get all collected results."""
        return self._results.copy()

    def list_sub_agents(self) -> list[str]:
        """List all sub-agent names."""
        return list(self._sub_agents.keys())

    async def cancel(self, name: str) -> bool:
        """
        Cancel a running sub-agent.

        Args:
            name: Name of the sub-agent to cancel

        Returns:
            True if cancelled, False if not running
        """
        if self._statuses.get(name) != SubAgentStatus.RUNNING:
            return False

        # Mark as cancelled
        self._statuses[name] = SubAgentStatus.CANCELLED
        self._results[name] = SubAgentResult(
            name=name,
            success=False,
            status=SubAgentStatus.CANCELLED,
            error="Cancelled by user",
        )
        logger.info(f"Cancelled sub-agent: {name}")
        return True

    def clear(self) -> None:
        """Clear all sub-agents and results."""
        self._sub_agents.clear()
        self._configs.clear()
        self._results.clear()
        self._statuses.clear()

    def _build_default_prompt(self, config: SubAgentConfig) -> str:
        """Build the default system prompt for a sub-agent."""
        return f"""You are a specialized sub-agent tasked with: {config.task}

You are part of a larger task and should focus only on your assigned work.
Complete your task thoroughly and report your findings clearly.

When finished, provide a concise summary of what you accomplished."""

    def _build_result(
        self,
        name: str,
        config: SubAgentConfig,
        loop_result: Any,
    ) -> SubAgentResult:
        """Build a SubAgentResult from the loop result."""
        from harness.types import LoopState

        success = loop_result.status == LoopState.COMPLETED

        if config.report_format == "summary":
            # Truncate to summary
            response = loop_result.final_response or ""
            summary = response[:500] if len(response) > 500 else response
            return SubAgentResult(
                name=name,
                success=success,
                status=SubAgentStatus.COMPLETED if success else SubAgentStatus.FAILED,
                summary=summary,
                iterations=loop_result.iterations,
                token_usage={
                    "input": loop_result.token_usage.input_tokens if loop_result.token_usage else 0,
                    "output": loop_result.token_usage.output_tokens if loop_result.token_usage else 0,
                },
            )

        elif config.report_format == "full":
            return SubAgentResult(
                name=name,
                success=success,
                status=SubAgentStatus.COMPLETED if success else SubAgentStatus.FAILED,
                full_response=loop_result.final_response,
                iterations=loop_result.iterations,
                token_usage={
                    "input": loop_result.token_usage.input_tokens if loop_result.token_usage else 0,
                    "output": loop_result.token_usage.output_tokens if loop_result.token_usage else 0,
                },
            )

        else:  # structured
            return SubAgentResult(
                name=name,
                success=success,
                status=SubAgentStatus.COMPLETED if success else SubAgentStatus.FAILED,
                structured_result={
                    "response": loop_result.final_response,
                    "iterations": loop_result.iterations,
                    "messages": [m.to_api_format() for m in loop_result.messages] if loop_result.messages else [],
                },
                iterations=loop_result.iterations,
                token_usage={
                    "input": loop_result.token_usage.input_tokens if loop_result.token_usage else 0,
                    "output": loop_result.token_usage.output_tokens if loop_result.token_usage else 0,
                },
            )
