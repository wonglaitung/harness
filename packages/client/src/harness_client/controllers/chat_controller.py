"""
Chat controller - manages conversation with AgentHarness.
"""

import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# SDK imports
from harness import (
    AgentHarness,
    ConfirmationResult,
    HarnessConfig,
    ProgressEvent,
    ProgressEventType,
)
from harness.core import ConfirmationHook
from harness.loop.types import GoalStatus
from harness.tools.builtins import (
    BashTool,
    GlobTool,
    GrepTool,
    ReadTool,
    UpdateCoreMemoryTool,
    WebFetchTool,
    WebSearchTool,
    WebToMarkdownTool,
    WriteTool,
)

from harness_client.controllers.session_manager import SessionManager
from harness_client.utils.settings import get_config_dir

logger = logging.getLogger(__name__)


@dataclass
class ChatConfig:
    """Chat configuration."""

    provider: str = "anthropic"
    api_key: str = ""
    base_url: str = ""
    model: str = "claude-sonnet-4-6"
    context_window: str = "auto"
    max_iterations: int = 10  # 业界标准默认值（与 SDK 一致）
    temperature: float = 0.3  # Lower = more deterministic
    tool_result_role: str = "tool"  # "tool" (native) or "user" (compatibility mode)
    auto_update_memory: bool = True  # Allow agent to autonomously update Core Memory

    # Routing configuration (智能路由，根据请求复杂度选择模型)
    enable_routing: bool = False  # 是否启用路由
    high_model: str = ""  # 高能力模型（如 gpt-4o）
    low_model: str = ""  # 低成本模型（如 gpt-4o-mini）
    router_model_path: str = ""  # 路由器模型路径（GGUF 文件）
    router_url: str = ""  # HTTP 路由服务 URL

    system_prompt: str = """你是一个有帮助的 AI 助手。

## 核心规则

**一次完成任务**：只做用户明确要求的事，完成后立即给出最终回答。不要延伸任务，不要做额外操作。

## 必须立即停止并回答的情况

当满足以下任一条件时，**立即停止调用工具，直接回答用户**：

1. **信息已足够**：你已经有了回答用户问题所需的全部信息
2. **任务已完成**：用户请求的操作已经执行完毕
3. **工具失败两次**：同一个工具调用失败两次，停止并报告错误
4. **收到停止信号**：收到系统提示要求你立即回答

## 禁止的行为

- ❌ 任务完成后"顺便"做其他事
- ❌ 获取信息后"继续探索"
- ❌ 用相同参数重复调用同一个工具
- ❌ 在已经有足够信息时继续调用工具

## 正确示例

- 用户："列出 Python 文件" → 执行 glob，列出文件，**立即回答**
- 用户："读取 main.py 前 20 行" → 执行 read(limit=20)，展示内容，**立即回答**
- 用户："项目结构是什么？" → 获取结构后，**立即回答**，不要继续读取更多文件
"""


class ChatController:
    """
    Controller for managing chat interactions with AgentHarness.

    Features:
    - Send messages and receive streaming responses
    - Session management via SessionManager
    - Track token usage
    - Support progress callbacks
    - Dangerous operation confirmation
    """

    def __init__(self, work_dir: Path | None = None):
        self.work_dir = work_dir or Path.cwd()
        self.agent: AgentHarness | None = None
        self.config = ChatConfig()
        self.session_manager = SessionManager()
        self._is_running = False
        self._mcp_tools: list = []  # MCP tools from connected servers
        self._on_progress: Callable | None = None
        self._on_stream: Callable | None = None
        self._on_tool_call: Callable | None = None
        self._on_tool_result: Callable | None = None
        self._on_thinking: Callable | None = None
        self._on_text_chunk: Callable | None = None
        self._confirm_callback: Callable[[str, dict], ConfirmationResult] | None = None
        self._on_agent_ready: Callable | None = None  # Callback when agent is initialized

    def set_mcp_tools(self, tools: list):
        """Set MCP tools from connected servers.

        Args:
            tools: List of MCP tool wrappers
        """
        self._mcp_tools = tools
        # Reset agent to force re-initialization with new tools
        # Only reset if agent was already initialized (not during initialization)
        if self.agent is not None:
            self.agent = None

    def set_progress_callback(self, callback: Callable[[ProgressEvent], None]):
        """Set callback for progress events."""
        self._on_progress = callback

    def set_stream_callback(self, callback: Callable[[str], None]):
        """Set callback for streaming text."""
        self._on_stream = callback

    def set_tool_call_callback(self, callback: Callable[[str, dict], None]):
        """Set callback for tool call events."""
        self._on_tool_call = callback

    def set_tool_result_callback(self, callback: Callable[[str, str, bool, dict], None]):
        """Set callback for tool result events.

        Callback signature: (tool_name, result, success, metadata)
        """
        self._on_tool_result = callback

    def set_thinking_callback(self, callback: Callable[[str], None]):
        """Set callback for thinking/progress messages."""
        self._on_thinking = callback

    def set_text_chunk_callback(self, callback: Callable[[str], None]):
        """Set callback for streaming text chunks."""
        self._on_text_chunk = callback

    def set_confirm_callback(self, callback: Callable[[str, dict], ConfirmationResult]):
        """Set callback for dangerous operation confirmation.

        Args:
            callback: Function that takes (tool_name, args) and returns ConfirmationResult
        """
        self._confirm_callback = callback

    def configure(self, config: ChatConfig):
        """Update chat configuration and reset agent."""
        self.config = config
        self.agent = None

    async def initialize(self, mcp_tools: list = None):
        """Initialize the AgentHarness with current configuration.

        Args:
            mcp_tools: Optional list of MCP tools to add to the agent
        """
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
            temperature=self.config.temperature,
            tool_result_role=self.config.tool_result_role,
            system_prompt=self.config.system_prompt,
            sandbox_workspace=str(self.work_dir),
            memory_md_path=get_config_dir() / "MEMORY.md",
        )

        logger.info(
            f"SDK config: provider={sdk_config.provider}, "
            f"base_url={sdk_config.base_url}, temperature={sdk_config.temperature}"
        )

        tools = [
            ReadTool(),
            WriteTool(),
            GlobTool(),
            GrepTool(),
            BashTool(),
            WebSearchTool(),
            WebFetchTool(),
            WebToMarkdownTool(),
        ]

        # Add MCP tools if provided
        if mcp_tools:
            tools.extend(mcp_tools)
            logger.info(f"Added {len(mcp_tools)} MCP tools")

        # Add stored MCP tools
        if self._mcp_tools:
            tools.extend(self._mcp_tools)
            logger.info(f"Added {len(self._mcp_tools)} stored MCP tools")

        # Add UpdateCoreMemoryTool if auto_update_memory is enabled
        if self.config.auto_update_memory:
            tools.append(UpdateCoreMemoryTool())
            logger.info("Added UpdateCoreMemoryTool (auto_update_memory enabled)")

        logger.info("Creating AgentHarness...")

        # Check if routing is enabled
        if self.config.enable_routing:
            self.agent = await self._create_routing_agent(sdk_config, tools)
        else:
            self.agent = AgentHarness(
                config=sdk_config,
                tools=tools,
            )

        # Add confirmation hook if callback is set
        if self._confirm_callback:
            async def async_confirm(tool_name: str, args: dict) -> ConfirmationResult:
                """Wrap sync callback for async hook."""
                return self._confirm_callback(tool_name, args)

            def is_trusted(trust_key: str) -> bool:
                """Check if command is trusted for current session."""
                session = self.session_manager.get_current()
                return session.is_command_trusted(trust_key) if session else False

            def on_trust(trust_key: str) -> None:
                """Mark command as trusted for current session."""
                session = self.session_manager.get_current()
                if session:
                    session.trust_command(trust_key)

            self.agent.add_hook(ConfirmationHook(
                on_confirm=async_confirm,
                is_trusted=is_trusted,
                on_trust=on_trust,
            ))
            logger.info("ConfirmationHook registered with session trust support")

        logger.info("AgentHarness created successfully")

        # Notify that agent is ready
        if self._on_agent_ready:
            self._on_agent_ready(self.agent)

    async def _create_routing_agent(self, sdk_config: HarnessConfig, tools: list):
        """Create AgentHarness with RoutingLLMClient."""
        from harness.llm.routing import RoutingLLMClient
        from harness.sdk.config import RoutingConfig

        # Validate routing configuration
        if not self.config.high_model:
            raise ValueError("启用路由时，必须配置高级模型")
        if not self.config.low_model:
            raise ValueError("启用路由时，必须配置基础模型")
        if not self.config.router_model_path and not self.config.router_url:
            raise ValueError("启用路由时，必须配置路由器模型路径或服务 URL")

        routing_config = RoutingConfig(
            high_model=self.config.high_model,
            low_model=self.config.low_model,
            router_model_path=self.config.router_model_path or None,
            router_url=self.config.router_url or None,
        )

        # Create downstream clients
        high_client = self._create_llm_client(self.config.high_model)
        low_client = self._create_llm_client(self.config.low_model)

        logger.info(
            f"Creating RoutingLLMClient: high={self.config.high_model}, "
            f"low={self.config.low_model}"
        )

        routing_client = RoutingLLMClient(
            config=routing_config,
            high_client=high_client,
            low_client=low_client,
            on_progress=self._on_progress,
        )

        return AgentHarness(
            llm_client=routing_client,
            config=sdk_config,
            tools=tools,
        )

    def _create_llm_client(self, model: str):
        """Create LLM client for the specified model."""
        from harness.llm.anthropic import AnthropicClient
        from harness.llm.openai import OpenAIClient

        if self.config.provider == "anthropic":
            return AnthropicClient(
                model=model,
                api_key=self.config.api_key,
                base_url=self.config.base_url or None,
            )
        else:
            return OpenAIClient(
                model=model,
                api_key=self.config.api_key,
                base_url=self.config.base_url or None,
            )

    async def send_message(
        self,
        message: str | list[dict[str, Any]],
        goal_mode: bool = False
    ) -> AsyncIterator[str]:
        """
        Send a message and yield the response.

        Args:
            message: User message - can be text (str) or multimodal content (list of dicts)
                     Multimodal format: [{"type": "text", "text": "..."}, {"type": "image", ...}]
            goal_mode: If True, use run_goal() for multi-iteration autonomous execution

        Yields:
            Response text
        """
        # Convert to string for logging
        if isinstance(message, list):
            log_msg = "[多模态消息]"
            for block in message:
                if block.get("type") == "text":
                    log_msg = block.get("text", "")[:50]
                    break
        else:
            log_msg = message[:50]
        logger.info(f"send_message called with: {log_msg}..., goal_mode={goal_mode}")

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
                        metadata = event.data.get("metadata", {})
                        self._on_tool_result(tool_name, result, success, metadata)

                elif event.type == ProgressEventType.ITERATION:
                    if self._on_thinking:
                        iteration = event.data.get("iteration", 0)
                        if goal_mode:
                            self._on_thinking(f"执行中... (第 {iteration} 步)")
                        else:
                            self._on_thinking(f"思考中... (第 {iteration} 步)")

                elif event.type == ProgressEventType.LLM_CALL:
                    if self._on_thinking:
                        self._on_thinking("正在生成回复...")

                elif event.type == ProgressEventType.TEXT_CHUNK:  # noqa: SIM102
                    if self._on_text_chunk and event.data and (chunk := event.data.get("text", "")):
                        self._on_text_chunk(chunk)

            current_session = self.session_manager.get_current()
            session_id = current_session.id if current_session else None

            # Extract text from multimodal message for skill matching
            prompt_text: str
            if isinstance(message, list):
                # Multimodal: extract text block
                prompt_text = ""
                for block in message:
                    if block.get("type") == "text":
                        prompt_text = block.get("text", "")
                        break
            else:
                prompt_text = message

            # Log matching skills (only check text portion)
            if prompt_text and self.agent:
                matching_skills = self.agent.get_matching_skills(prompt_text)
                if matching_skills:
                    logger.info(f"Matching skills: {[s.name for s in matching_skills]}")

            if goal_mode:
                # Task mode: Multi-iteration autonomous execution
                logger.info("Calling agent.run_goal()...")
                result = await self.agent.run_goal(
                    goal=prompt_text,  # Use extracted text for goal mode
                    session_id=session_id,
                    max_iterations=50,
                    on_progress=on_progress,
                )
                logger.info(f"agent.run_goal() returned, status={result.status.value}, iterations={result.total_iterations}")

                # Update token usage
                if result.total_tokens:
                    self.session_manager.update_token_usage(
                        result.total_tokens.get("input", 0),
                        result.total_tokens.get("output", 0),
                    )

                # Format response with status
                response = result.final_response
                if result.achieved:
                    response = f"✅ 目标达成 ({result.total_iterations} 步)\n\n{response}"
                else:
                    # Map status to user-friendly text
                    status_map = {
                        GoalStatus.TIMEOUT: "⏱️ 超时",
                        GoalStatus.MAX_ITERATIONS: "🔄 达到最大迭代",
                        GoalStatus.MAX_RESETS: "📋 达到最大重置",
                        GoalStatus.ERROR: "❌ 错误",
                        GoalStatus.VERIFIER_FAULT: "⚠️ 验证器故障",
                        GoalStatus.CANCELLED: "🚫 已取消",
                    }
                    status_text = status_map.get(result.status, result.status.value)
                    response = f"{status_text}\n\n{response}"

                # Cache assistant response AFTER receiving
                if response:
                    self.session_manager.add_message_to_current("assistant", response)

                logger.info(f"Response length: {len(response)} chars")
                yield response
            else:
                # Chat mode: Single-turn conversation
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

    def clear_context(self) -> bool:
        """Clear current session messages without creating new session."""
        success = self.session_manager.clear_current_messages()
        if success:
            # Reset agent to force re-initialization
            self.agent = None
        return success

    def get_current_session_id(self) -> str | None:
        """Get the current session ID."""
        return self.session_manager.current_id

    def get_current_session(self):
        """Get the current session object."""
        return self.session_manager.get_current()

    def is_busy(self) -> bool:
        """Check if agent is processing."""
        return self._is_running

    def stop(self) -> bool:
        """Stop the current agent execution.

        Returns:
            True if stop was requested, False if not running
        """
        if self._is_running and self.agent:
            self.agent.interrupt()
            logger.info("Stop requested for current task")
            return True
        return False

    def get_token_usage(self) -> dict:
        """Get current session token usage."""
        current = self.session_manager.get_current()
        if current:
            return current.token_usage.copy()
        return {"input": 0, "output": 0}
