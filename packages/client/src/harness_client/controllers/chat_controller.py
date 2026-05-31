"""
Chat controller - manages conversation with AgentHarness.
"""

import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path

# SDK imports
from harness import (
    AgentHarness,
    HarnessConfig,
    ProgressEvent,
    ProgressEventType,
)
from harness.tools.builtins import GlobTool, GrepTool, ReadTool, WriteTool

from harness_client.controllers.session_manager import SessionManager

logger = logging.getLogger(__name__)


@dataclass
class ChatConfig:
    """Chat configuration."""

    provider: str = "anthropic"
    api_key: str = ""
    base_url: str = ""
    model: str = "claude-sonnet-4-6"
    context_window: str = "auto"
    max_iterations: int = 20
    system_prompt: str = "你是一个有帮助的 AI 助手。"


class ChatController:
    """
    Controller for managing chat interactions with AgentHarness.

    Features:
    - Send messages and receive streaming responses
    - Session management via SessionManager
    - Track token usage
    - Support progress callbacks
    """

    def __init__(self, work_dir: Path | None = None):
        self.work_dir = work_dir or Path.cwd()
        self.agent: AgentHarness | None = None
        self.config = ChatConfig()
        self.session_manager = SessionManager()
        self._is_running = False
        self._on_progress: Callable | None = None
        self._on_stream: Callable | None = None
        self._on_tool_call: Callable | None = None
        self._on_tool_result: Callable | None = None
        self._on_thinking: Callable | None = None
        self._on_text_chunk: Callable | None = None

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
        self.agent = None

    async def initialize(self, mcp_tools: list = None):
        """Initialize the AgentHarness with current configuration."""
        logger.info(
            f"Initializing agent with provider={self.config.provider}, model={self.config.model}"
        )

        if not self.config.api_key:
            raise ValueError(
                "未配置 API Key。请在设置中配置 API Key。\n\n"
                "或设置环境变量：\n"
                "- Anthropic: ANTHROPIC_API_KEY\n"
                "- OpenAI: OPENAI_API_KEY"
            )

        sdk_config = HarnessConfig(
            model=self.config.model,
            api_key=self.config.api_key or None,
            provider=self.config.provider,
            base_url=self.config.base_url or None,
            context_window=self.config.context_window,
            max_iterations=self.config.max_iterations,
            system_prompt=self.config.system_prompt,
        )

        logger.info(f"SDK config: provider={sdk_config.provider}, base_url={sdk_config.base_url}")

        tools = [
            ReadTool(),
            WriteTool(),
            GlobTool(),
            GrepTool(),
        ]

        if mcp_tools:
            tools.extend(mcp_tools)

        logger.info("Creating AgentHarness...")
        self.agent = AgentHarness(
            config=sdk_config,
            tools=tools,
        )
        logger.info("AgentHarness created successfully")

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """
        Send a message and yield the response.

        Args:
            message: User message

        Yields:
            Response text
        """
        logger.info(f"send_message called with: {message[:50]}...")

        if not self.agent:
            logger.info("Agent not initialized, initializing now...")
            await self.initialize()

        self._is_running = True

        # Cache user message BEFORE sending
        self.session_manager.add_message_to_current("user", message)

        try:

            def on_progress(event: ProgressEvent):
                if self._on_progress:
                    self._on_progress(event)

                if event.type == ProgressEventType.TOOL_CALL:
                    if self._on_tool_call and event.data:
                        tool_name = event.data.get("tool", "unknown")
                        arguments = event.data.get("arguments", {})
                        self._on_tool_call(tool_name, arguments)

                elif event.type == ProgressEventType.TOOL_RESULT:
                    if self._on_tool_result and event.data:
                        tool_name = event.data.get("tool", "unknown")
                        result = event.data.get("result", "")
                        success = event.data.get("success", True)
                        self._on_tool_result(tool_name, result, success)

                elif event.type == ProgressEventType.ITERATION:
                    if self._on_thinking:
                        iteration = event.data.get("iteration", 0)
                        self._on_thinking(f"思考中... (第 {iteration} 步)")

                elif event.type == ProgressEventType.LLM_CALL:
                    if self._on_thinking:
                        self._on_thinking("正在生成回复...")

                elif event.type == ProgressEventType.TEXT_CHUNK:  # noqa: SIM102
                    if self._on_text_chunk and event.data and (chunk := event.data.get("text", "")):
                        self._on_text_chunk(chunk)

            current_session = self.session_manager.get_current()
            session_id = current_session.id if current_session else None

            logger.info("Calling agent.run()...")
            result = await self.agent.run(
                message,
                session_id=session_id,
                on_progress=on_progress,
            )
            logger.info(f"agent.run() returned, iterations={result.iterations}")

            # Update token usage
            if result.token_usage:
                self.session_manager.update_token_usage(
                    result.token_usage.input_tokens, result.token_usage.output_tokens
                )

            # Cache assistant response AFTER receiving
            response = result.content
            if response:
                self.session_manager.add_message_to_current("assistant", response)

            logger.info(f"Response length: {len(response)} chars")
            yield response

        except ValueError as e:
            logger.error(f"ValueError: {e}")
            yield f"⚠️ 配置错误: {str(e)}"
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            yield f"❌ 错误: {type(e).__name__}: {str(e)}"
        finally:
            self._is_running = False

    def new_session(self) -> str:
        """Create a new session and return its ID."""
        # Archive current session first
        self.session_manager.archive_current()
        # Create new session
        session = self.session_manager.create()
        # Reset agent to force re-initialization with new session
        self.agent = None
        return session.id

    def switch_session(self, session_id: str) -> bool:
        """Switch to a different session."""
        if self.session_manager.switch_to(session_id):
            self.agent = None  # Force re-initialization
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self.session_manager.delete(session_id)

    def get_current_session_id(self) -> str | None:
        """Get the current session ID."""
        return self.session_manager.current_id

    def get_current_session(self):
        """Get the current session object."""
        return self.session_manager.get_current()

    def is_busy(self) -> bool:
        """Check if agent is processing."""
        return self._is_running

    def get_token_usage(self) -> dict:
        """Get current session token usage."""
        current = self.session_manager.get_current()
        if current:
            return current.token_usage.copy()
        return {"input": 0, "output": 0}
