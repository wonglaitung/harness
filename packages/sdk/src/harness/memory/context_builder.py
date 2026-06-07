"""
Context builder for assembling messages for LLM calls.

Handles system prompt injection, message windowing, and token budget management.
Includes automatic compression when context exceeds budget.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from harness.memory.compressor import CompressionConfig, CompressionResult, ContextCompressor
from harness.memory.system_prompt import SystemPromptBuilder, SystemPromptConfig
from harness.memory.token_counter import TokenCounter
from harness.types import Message, Session

if TYPE_CHECKING:
    from harness.llm.base import ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class ContextBudget:
    """
    Token budget allocation for context components.

    Priority order: system_prompt > recent_messages > skills > memory

    Attributes:
        max_tokens: Maximum context window size
        response_reserve: Tokens reserved for LLM response
        system_prompt: Tokens allocated for system prompt
        tools: Tokens allocated for tool definitions
        recent_messages: Tokens allocated for recent messages
        skills: Tokens allocated for skill prompts
        memory: Tokens allocated for memory/context
    """
    max_tokens: int = 200000
    response_reserve: int = 4096
    system_prompt: int = 0
    tools: int = 0
    recent_messages: int = 0
    skills: int = 0
    memory: int = 0

    @property
    def available_for_input(self) -> int:
        """Tokens available for all input components."""
        return self.max_tokens - self.response_reserve

    @property
    def used(self) -> int:
        """Total tokens allocated."""
        return (
            self.system_prompt +
            self.tools +
            self.recent_messages +
            self.skills +
            self.memory
        )

    @property
    def remaining(self) -> int:
        """Tokens remaining unallocated."""
        return self.available_for_input - self.used

    @property
    def needs_compression(self) -> bool:
        """Check if context exceeds budget and needs compression."""
        return self.used > self.available_for_input

    @classmethod
    def allocate(
        cls,
        max_tokens: int,
        system_prompt_tokens: int = 0,
        tool_tokens: int = 0,
        message_ratio: float = 0.7,
        skills_ratio: float = 0.2,
        memory_ratio: float = 0.1,
    ) -> "ContextBudget":
        """
        Create a budget with automatic allocation.

        Args:
            max_tokens: Maximum context window
            system_prompt_tokens: Actual system prompt tokens
            tool_tokens: Actual tool definition tokens
            message_ratio: Ratio for messages (default 70%)
            skills_ratio: Ratio for skills (default 20%)
            memory_ratio: Ratio for memory (default 10%)

        Returns:
            Allocated ContextBudget
        """
        response_reserve = 4096
        available = max_tokens - response_reserve

        # Fixed allocations first (high priority)
        actual_system = min(system_prompt_tokens, available)
        remaining_after_system = available - actual_system

        actual_tools = min(tool_tokens, remaining_after_system)
        remaining = remaining_after_system - actual_tools

        # Proportional allocation for remaining
        total_ratio = message_ratio + skills_ratio + memory_ratio
        if total_ratio > 0:
            messages_alloc = int(remaining * message_ratio / total_ratio)
            skills_alloc = int(remaining * skills_ratio / total_ratio)
            memory_alloc = remaining - messages_alloc - skills_alloc
        else:
            messages_alloc = remaining
            skills_alloc = 0
            memory_alloc = 0

        return cls(
            max_tokens=max_tokens,
            response_reserve=response_reserve,
            system_prompt=actual_system,
            tools=actual_tools,
            recent_messages=messages_alloc,
            skills=skills_alloc,
            memory=memory_alloc,
        )


@dataclass
class ContextConfig:
    """Configuration for context building."""
    max_tokens: int = 200000
    system_prompt: str = ""
    window_size: int = 100  # Max number of recent messages
    compression_threshold: float = 0.9  # Compress when usage > 90%
    enable_compression: bool = True  # Enable automatic compression
    compression_config: CompressionConfig | None = None  # Compression settings

    # Dynamic system prompt configuration
    system_prompt_config: SystemPromptConfig | None = None  # Advanced prompt assembly
    project_root: Path | None = None  # Project root for AGENTS.md/MEMORY.md discovery
    memory_md_path: Path | None = None  # Optional path to global MEMORY.md file


@dataclass
class BuiltContext:
    """Result of context building."""
    messages: list[dict[str, Any]]
    system_prompt: str
    estimated_tokens: int
    budget: ContextBudget | None = None
    compression_needed: bool = False
    compression_result: CompressionResult | None = None


class ContextBuilder:
    """
    Builds context for LLM calls.

    Handles:
    - System prompt injection (static and dynamic)
    - Message windowing with token budget
    - Automatic compression detection and execution
    - Integration with TokenCounter for accurate counting
    - AGENTS.md / MEMORY.md discovery and loading
    """

    def __init__(
        self,
        config: ContextConfig | None = None,
        token_counter: TokenCounter | None = None,
        compressor: ContextCompressor | None = None,
    ):
        self.config = config or ContextConfig()
        self._token_counter = token_counter or TokenCounter()

        # Initialize compressor
        if compressor:
            self._compressor = compressor
        elif self.config.enable_compression:
            compression_config = self.config.compression_config or CompressionConfig()
            self._compressor = ContextCompressor(
                token_counter=self._token_counter,
                config=compression_config,
            )
        else:
            self._compressor = None

        # Initialize system prompt builder
        self._init_system_prompt_builder()

    def _init_system_prompt_builder(self) -> None:
        """Initialize the system prompt builder based on config."""
        logger.debug(
            f"_init_system_prompt_builder: system_prompt_config={self.config.system_prompt_config is not None}, "
            f"project_root={self.config.project_root}, system_prompt={bool(self.config.system_prompt)}, "
            f"memory_md_path={self.config.memory_md_path}"
        )
        if self.config.system_prompt_config:
            # Use provided config
            self._prompt_builder = SystemPromptBuilder(self.config.system_prompt_config)
        elif self.config.project_root or self.config.system_prompt or self.config.memory_md_path:
            # Create config from simple settings
            prompt_config = SystemPromptConfig(
                base_prompt=self.config.system_prompt,
                project_root=self.config.project_root,
                auto_discover=True,
            )
            self._prompt_builder = SystemPromptBuilder(prompt_config)

            # Add global memory source if specified
            if self.config.memory_md_path:
                logger.info(f"Adding GlobalMemory source: {self.config.memory_md_path}")
                from harness.memory.system_prompt import SystemPromptSource
                self._prompt_builder.add_source(SystemPromptSource(
                    name="GlobalMemory",
                    priority=40,
                    file_path=self.config.memory_md_path,
                ))
            else:
                logger.debug("No memory_md_path specified, skipping GlobalMemory source")
        else:
            # No dynamic prompt building
            self._prompt_builder = None

    def build(
        self,
        session: Session,
        new_prompt: str | None = None,
        tools: list[ToolDefinition] | None = None,
    ) -> BuiltContext:
        """
        Build context for LLM call with budget management.

        Automatically compresses context if it exceeds budget.

        Args:
            session: Current session
            new_prompt: Optional new user prompt
            tools: Available tools for budget estimation

        Returns:
            BuiltContext: Prepared messages for LLM
        """
        # Calculate budget
        budget = self._calculate_budget(tools)

        # Get messages from session
        session_messages = session.messages.copy()

        # Apply sliding window
        windowed_messages = self._apply_window(session_messages)

        # Add new prompt if provided
        if new_prompt:
            windowed_messages.append(Message(role="user", content=new_prompt))

        # Estimate current tokens
        estimated = self._estimate_tokens(windowed_messages)

        # Check if compression is needed
        compression_needed = estimated > budget.available_for_input * self.config.compression_threshold
        compression_result = None

        if compression_needed and self._compressor:
            logger.info(
                f"Context compression needed: {estimated} tokens > "
                f"{int(budget.available_for_input * self.config.compression_threshold)} threshold"
            )

            # Perform compression
            target_tokens = int(budget.available_for_input * 0.7)  # Aim for 70% utilization
            compression_result = self._compressor.compress(
                messages=windowed_messages,
                target_tokens=target_tokens,
            )

            # Use compressed messages
            windowed_messages = compression_result.compressed_messages
            estimated = compression_result.tokens_after

            logger.info(
                f"Compression complete: {compression_result.tokens_before} -> "
                f"{compression_result.tokens_after} tokens "
                f"(saved {compression_result.compression_saved})"
            )

        # Convert to API format
        messages = [msg.to_api_format() for msg in windowed_messages]

        return BuiltContext(
            messages=messages,
            system_prompt=self._get_system_prompt(),
            estimated_tokens=estimated,
            budget=budget,
            compression_needed=compression_needed,
            compression_result=compression_result,
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt, using dynamic builder if available."""
        if self._prompt_builder:
            return self._prompt_builder.build()
        return self.config.system_prompt

    def _calculate_budget(self, tools: list[ToolDefinition] | None = None) -> ContextBudget:
        """Calculate token budget allocation."""
        system_tokens = self._token_counter.count(self._get_system_prompt())
        tool_tokens = self._token_counter.estimate_tool_overhead(tools or [])

        return ContextBudget.allocate(
            max_tokens=self.config.max_tokens,
            system_prompt_tokens=system_tokens,
            tool_tokens=tool_tokens,
        )

    def _apply_window(self, messages: list[Message]) -> list[Message]:
        """
        Apply sliding window to messages.

        Args:
            messages: All messages

        Returns:
            Messages within window size
        """
        if len(messages) <= self.config.window_size:
            return messages

        return messages[-self.config.window_size:]

    def _estimate_tokens(self, messages: list[Message]) -> int:
        """
        Estimate total tokens in messages.

        Args:
            messages: Messages to estimate

        Returns:
            Estimated token count
        """
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else ""
            total += self._token_counter.count(content)
            total += 4  # Message format overhead
        return total

    def _build_messages(
        self,
        session: Session,
        new_prompt: str | None,
        token_budget: int,
    ) -> list[dict[str, Any]]:
        """
        Build message list within token budget.

        Uses sliding window to fit messages within budget.
        """
        messages = []

        # Start with window size limit
        recent = session.messages[-self.config.window_size:]

        # Add messages from newest to oldest until budget exhausted
        current_tokens = 0
        included_messages = []

        for msg in reversed(recent):
            msg_tokens = self._token_counter.count(msg.content if isinstance(msg.content, str) else "")

            if current_tokens + msg_tokens <= token_budget:
                included_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                # Budget exhausted, stop adding older messages
                break

        # Convert to API format
        for msg in included_messages:
            messages.append(msg.to_api_format())

        # Add new prompt if provided
        if new_prompt:
            messages.append({
                "role": "user",
                "content": new_prompt,
            })

        return messages

    def _dict_to_message(self, msg_dict: dict[str, Any]) -> Message:
        """Convert dict to Message for token counting."""
        return Message(
            role=msg_dict.get("role", "user"),
            content=msg_dict.get("content", ""),
        )

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt."""
        self.config.system_prompt = prompt
        # Update prompt builder if exists
        if self._prompt_builder:
            # Update base prompt in config
            self._prompt_builder.config.base_prompt = prompt
            # Re-setup sources to pick up the new base prompt
            self._prompt_builder._setup_default_sources()

    def set_project_root(self, project_root: Path) -> None:
        """
        Set the project root for AGENTS.md / MEMORY.md discovery.

        Args:
            project_root: Path to project root directory
        """
        self.config.project_root = project_root
        # Re-initialize prompt builder with new project root
        self._init_system_prompt_builder()

    def add_prompt_source(self, source: "SystemPromptSource") -> None:
        """
        Add a custom system prompt source.

        Args:
            source: SystemPromptSource to add
        """
        if self._prompt_builder is None:
            # Initialize builder if not exists
            self._init_system_prompt_builder()
        self._prompt_builder.add_source(source)

    def get_available_prompt_sources(self) -> list[str]:
        """Get list of prompt sources that have content."""
        if self._prompt_builder:
            return self._prompt_builder.get_available_sources()
        return ["base"] if self.config.system_prompt else []

    def estimate_tokens(self, content: str) -> int:
        """Estimate token count for content using tiktoken."""
        return self._token_counter.count(content)

    def get_message_window(self, session: Session, max_tokens: int) -> list[Message]:
        """
        Get messages that fit within token budget.

        Args:
            session: Current session
            max_tokens: Maximum tokens for messages

        Returns:
            List of messages fitting within budget
        """
        messages = []
        current_tokens = 0

        for msg in reversed(session.messages):
            msg_tokens = self._token_counter.count(
                msg.content if isinstance(msg.content, str) else ""
            )

            if current_tokens + msg_tokens <= max_tokens:
                messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break

        return messages
