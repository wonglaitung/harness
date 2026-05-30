"""
Chat controller - manages conversation with AgentHarness.
"""

import asyncio
from pathlib import Path
from typing import AsyncIterator, Callable
from dataclasses import dataclass, field

# SDK imports
from harness import (
    AgentHarness,
    HarnessConfig,
    Session,
    LoopResult,
    ProgressEvent,
    ProgressEventType,
)
from harness.tools.builtins import ReadTool, WriteTool, GlobTool, GrepTool, BashTool


@dataclass
class ChatConfig:
    """Chat configuration."""
    provider: str = "anthropic"
    api_key: str = ""
    base_url: str = ""
    model: str = "claude-sonnet-4-6"
    max_iterations: int = 20
    system_prompt: str = "你是一个有帮助的 AI 助手。"


@dataclass
class ChatState:
    """Current chat state."""
    is_running: bool = False
    session_id: str = "default"
    token_usage: dict = field(default_factory=lambda: {"input": 0, "output": 0})
    iterations: int = 0


class ChatController:
    """
    Controller for managing chat interactions with AgentHarness.

    Features:
    - Send messages and receive streaming responses
    - Manage session and history
    - Track token usage
    - Support progress callbacks
    """

    def __init__(self, work_dir: Path | None = None):
        self.work_dir = work_dir or Path.cwd()
        self.agent: AgentHarness | None = None
        self.config = ChatConfig()
        self.state = ChatState()
        self._on_progress: Callable | None = None
        self._on_stream: Callable | None = None

    def set_progress_callback(self, callback: Callable[[ProgressEvent], None]):
        """Set callback for progress events."""
        self._on_progress = callback

    def set_stream_callback(self, callback: Callable[[str], None]):
        """Set callback for streaming text."""
        self._on_stream = callback

    def configure(self, config: ChatConfig):
        """Update chat configuration and reset agent."""
        self.config = config
        # Reset agent so it will be re-initialized with new config
        self.agent = None

    async def initialize(self, mcp_tools: list = None):
        """Initialize the AgentHarness with current configuration."""
        # Build SDK config
        sdk_config = HarnessConfig(
            model=self.config.model,
            api_key=self.config.api_key or None,
            provider=self.config.provider,
            base_url=self.config.base_url or None,
            max_iterations=self.config.max_iterations,
            system_prompt=self.config.system_prompt,
        )

        # Default tools
        tools = [
            ReadTool(),
            WriteTool(),
            GlobTool(),
            GrepTool(),
        ]

        # Add MCP tools if provided
        if mcp_tools:
            tools.extend(mcp_tools)

        # Create agent
        self.agent = AgentHarness(
            config=sdk_config,
            tools=tools,
        )

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """
        Send a message and yield streaming response chunks.

        Args:
            message: User message

        Yields:
            Response text chunks
        """
        if not self.agent:
            await self.initialize()

        self.state.is_running = True
        full_response = ""

        try:
            # Run agent with progress tracking
            def on_progress(event: ProgressEvent):
                if self._on_progress:
                    self._on_progress(event)

            # Execute
            result = await self.agent.run(
                message,
                session_id=self.state.session_id,
                on_progress=on_progress,
            )

            # Update state
            self.state.iterations = result.iterations
            if result.token_usage:
                self.state.token_usage["input"] += result.token_usage.input_tokens
                self.state.token_usage["output"] += result.token_usage.output_tokens

            # Yield response
            full_response = result.content
            yield full_response

        except Exception as e:
            yield f"❌ 错误: {str(e)}"
        finally:
            self.state.is_running = False

    async def send_message_stream(self, message: str) -> AsyncIterator[str]:
        """
        Send a message and yield truly streaming response.

        Note: Requires SDK stream() support.
        """
        if not self.agent:
            await self.initialize()

        self.state.is_running = True

        try:
            # Check if agent supports streaming
            if hasattr(self.agent, 'stream'):
                async for chunk in self.agent.stream(message, session_id=self.state.session_id):
                    if chunk.content:
                        yield chunk.content
            else:
                # Fallback to regular run
                result = await self.agent.run(message, session_id=self.state.session_id)
                yield result.content

        except Exception as e:
            yield f"❌ 错误: {str(e)}"
        finally:
            self.state.is_running = False

    def new_session(self):
        """Start a new session."""
        import uuid
        self.state.session_id = str(uuid.uuid4())[:8]
        self.state.token_usage = {"input": 0, "output": 0}
        self.state.iterations = 0

    def get_session_history(self) -> list:
        """Get current session message history."""
        if not self.agent:
            return []
        # TODO: Implement session history retrieval
        return []

    def is_busy(self) -> bool:
        """Check if agent is processing."""
        return self.state.is_running

    def get_token_usage(self) -> dict:
        """Get total token usage."""
        return self.state.token_usage.copy()
