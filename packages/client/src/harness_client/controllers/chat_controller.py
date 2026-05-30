"""
Chat controller - manages conversation with AgentHarness.
"""

import asyncio
import logging
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

logger = logging.getLogger(__name__)


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
        self._session_cache: dict[str, list] = {}  # session_id -> messages
        self._on_progress: Callable | None = None
        self._on_stream: Callable | None = None
        self._on_tool_call: Callable | None = None
        self._on_tool_result: Callable | None = None
        self._on_thinking: Callable | None = None
        self._on_text_chunk: Callable | None = None  # For streaming text

    def set_progress_callback(self, callback: Callable[[ProgressEvent], None]):
        """Set callback for progress events."""
        self._on_progress = callback

    def set_stream_callback(self, callback: Callable[[str], None]):
        """Set callback for streaming text."""
        self._on_stream = callback

    def set_tool_call_callback(self, callback: Callable[[str, dict], None]):
        """Set callback for tool call events."""
        self._on_tool_call = callback

    def set_tool_result_callback(self, callback: Callable[[str, str, bool], None]):
        """Set callback for tool result events."""
        self._on_tool_result = callback

    def set_thinking_callback(self, callback: Callable[[str], None]):
        """Set callback for thinking/progress messages."""
        self._on_thinking = callback

    def set_text_chunk_callback(self, callback: Callable[[str], None]):
        """Set callback for streaming text chunks."""
        self._on_text_chunk = callback

    def configure(self, config: ChatConfig):
        """Update chat configuration and reset agent."""
        self.config = config
        # Reset agent so it will be re-initialized with new config
        self.agent = None

    async def initialize(self, mcp_tools: list = None):
        """Initialize the AgentHarness with current configuration."""
        logger.info(f"Initializing agent with provider={self.config.provider}, model={self.config.model}")

        # Check if API key is configured
        if not self.config.api_key:
            raise ValueError(
                "未配置 API Key。请在设置中配置 API Key。\n\n"
                "或设置环境变量：\n"
                "- Anthropic: ANTHROPIC_API_KEY\n"
                "- OpenAI: OPENAI_API_KEY"
            )

        # Build SDK config
        sdk_config = HarnessConfig(
            model=self.config.model,
            api_key=self.config.api_key or None,
            provider=self.config.provider,
            base_url=self.config.base_url or None,
            max_iterations=self.config.max_iterations,
            system_prompt=self.config.system_prompt,
        )

        logger.info(f"SDK config: provider={sdk_config.provider}, base_url={sdk_config.base_url}")

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
        logger.info("Creating AgentHarness...")
        self.agent = AgentHarness(
            config=sdk_config,
            tools=tools,
        )
        logger.info("AgentHarness created successfully")

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """
        Send a message and yield streaming response chunks.

        Args:
            message: User message

        Yields:
            Response text chunks
        """
        logger.info(f"send_message called with: {message[:50]}...")

        if not self.agent:
            logger.info("Agent not initialized, initializing now...")
            await self.initialize()

        self.state.is_running = True
        full_response = ""

        try:
            # Run agent with progress tracking
            def on_progress(event: ProgressEvent):
                if self._on_progress:
                    self._on_progress(event)

                # Handle different event types
                if event.type == ProgressEventType.TOOL_CALL:
                    # Tool call started
                    if self._on_tool_call and event.data:
                        tool_name = event.data.get("tool", "unknown")
                        arguments = event.data.get("arguments", {})
                        self._on_tool_call(tool_name, arguments)

                elif event.type == ProgressEventType.TOOL_RESULT:
                    # Tool call completed
                    if self._on_tool_result and event.data:
                        tool_name = event.data.get("tool", "unknown")
                        result = event.data.get("result", "")
                        success = event.data.get("success", True)
                        self._on_tool_result(tool_name, result, success)

                elif event.type == ProgressEventType.ITERATION:
                    # Iteration started
                    if self._on_thinking:
                        iteration = event.data.get("iteration", 0)
                        self._on_thinking(f"思考中... (第 {iteration} 步)")

                elif event.type == ProgressEventType.LLM_CALL:
                    # LLM call started
                    if self._on_thinking:
                        self._on_thinking("正在生成回复...")

                elif event.type == ProgressEventType.TEXT_CHUNK:
                    # Streaming text chunk
                    if self._on_text_chunk and event.data:
                        chunk = event.data.get("text", "")
                        if chunk:
                            self._on_text_chunk(chunk)

            # Execute
            logger.info("Calling agent.run()...")
            result = await self.agent.run(
                message,
                session_id=self.state.session_id,
                on_progress=on_progress,
            )
            logger.info(f"agent.run() returned, iterations={result.iterations}")

            # Update state
            self.state.iterations = result.iterations
            if result.token_usage:
                self.state.token_usage["input"] += result.token_usage.input_tokens
                self.state.token_usage["output"] += result.token_usage.output_tokens

            # Cache session messages for later retrieval
            if result.session:
                self._session_cache[self.state.session_id] = result.session.messages

            # Yield response
            full_response = result.content
            logger.info(f"Response length: {len(full_response)} chars")
            yield full_response

        except ValueError as e:
            logger.error(f"ValueError: {e}")
            yield f"⚠️ 配置错误: {str(e)}"
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            yield f"❌ 错误: {type(e).__name__}: {str(e)}"
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
        return self._session_cache.get(self.state.session_id, [])

    def get_session_messages(self, session_id: str) -> list:
        """Get messages for a specific session."""
        return self._session_cache.get(session_id, [])

    def is_busy(self) -> bool:
        """Check if agent is processing."""
        return self.state.is_running

    def get_token_usage(self) -> dict:
        """Get total token usage."""
        return self.state.token_usage.copy()
