"""
Routing LLM client for cost optimization.

Routes requests to different downstream models based on complexity,
using a lightweight CPU model (e.g., Qwen2.5-1.5B) as the router.

Architecture:
    User Request → Router (CPU) → high/low label → Downstream LLM
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Callable

from harness.llm.base import LLMClient, LLMConfig, ToolDefinition
from harness.types import (
    Chunk,
    ChunkType,
    LLMResponse,
    ProgressEvent,
    ProgressEventType,
    StopReason,
    TokenUsage,
)

if TYPE_CHECKING:
    from harness.sdk.config import RoutingConfig

logger = logging.getLogger(__name__)

# Default routing prompt template
DEFAULT_ROUTE_PROMPT = """你是一个请求路由器。根据用户请求的复杂度，决定应该使用哪个模型处理。

可用模型：
- high: {high_description}
- low: {low_description}

判断标准：
1. 需要多步推理 → high
2. 需要调用多个工具 → high
3. 需要代码生成或修改 → high
4. 需要深度分析或报告 → high
5. 简单问答、查询、翻译 → low

**重要**：当不确定时，选择 high。宁可浪费也不要牺牲质量。

历史对话：
{conversation_history}

当前用户请求：
{user_message}

请输出路由决策（仅输出一个标签：high 或 low）："""


class RoutingLLMClient(LLMClient):
    """
    LLM client that routes requests to different downstream models.

    Uses a lightweight CPU model to classify request complexity,
    then forwards to the appropriate downstream model.

    Usage:
        from harness.llm.routing import RoutingLLMClient
        from harness.sdk.config import RoutingConfig

        config = RoutingConfig(
            high_model="gpt-4o",
            low_model="gpt-4o-mini",
            router_model_path="models/qwen2.5-1.5b.gguf",
        )

        client = RoutingLLMClient(
            config=config,
            high_client=OpenAIClient(model="gpt-4o"),
            low_client=OpenAIClient(model="gpt-4o-mini"),
        )

        response = await client.call(messages)
    """

    def __init__(
        self,
        config: RoutingConfig,
        high_client: LLMClient,
        low_client: LLMClient,
        on_progress: Callable[[ProgressEvent], None] | None = None,
    ):
        """
        Initialize the routing client.

        Args:
            config: Routing configuration
            high_client: LLM client for complex requests
            low_client: LLM client for simple requests
            on_progress: Optional callback for progress events
        """
        super().__init__(LLMConfig(model="routing-client"))
        self.routing_config = config
        self.high_client = high_client
        self.low_client = low_client
        self._on_progress = on_progress

        # Router client (initialized lazily)
        self._router_client: LLMClient | None = None

        # Track last routing decision for observability
        self._last_route: str = ""
        self._last_router_latency_ms: float = 0.0

    @property
    def model_name(self) -> str:
        """Return a descriptive model name."""
        return f"routing(high={self.routing_config.high_model}, low={self.routing_config.low_model})"

    def _init_router_client(self) -> LLMClient:
        """Initialize the router client (embedded or HTTP)."""
        if self._router_client is not None:
            return self._router_client

        if self.routing_config.router_model_path:
            # Embedded mode (default)
            from harness.llm.llama_cpp import EmbeddedLlamaClient

            self._router_client = EmbeddedLlamaClient(
                model_path=self.routing_config.router_model_path,
                context_window=self.routing_config.router_context_window,
            )
            logger.info(f"Router initialized (embedded): {self.routing_config.router_model_path}")

        elif self.routing_config.router_url:
            # HTTP mode
            from harness.llm.openai import OpenAIClient

            self._router_client = OpenAIClient(
                base_url=self.routing_config.router_url,
                model="router",
                api_key="local",
            )
            logger.info(f"Router initialized (HTTP): {self.routing_config.router_url}")

        else:
            raise ValueError("Router not configured: need router_model_path or router_url")

        return self._router_client

    def _build_route_prompt(
        self,
        user_message: str,
        conversation_history: str = "",
    ) -> str:
        """Build the routing prompt."""
        template = self.routing_config.route_prompt_template or DEFAULT_ROUTE_PROMPT

        return template.format(
            high_description=self.routing_config.high_description,
            low_description=self.routing_config.low_description,
            conversation_history=conversation_history or "(无历史对话)",
            user_message=user_message,
        )

    def _extract_route_input(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[str, str]:
        """
        Extract user message and conversation history for routing.

        Returns:
            (user_message, conversation_history)
        """
        # Get the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    user_message = content
                elif isinstance(content, list):
                    # Handle multimodal content
                    user_message = " ".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict) and part.get("type") == "text"
                    )
                break

        # Build conversation history (last N messages)
        history_messages = messages[-self.routing_config.history_window:]
        history_parts = []

        for msg in history_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if isinstance(content, str):
                preview = content[:200] + "..." if len(content) > 200 else content
                history_parts.append(f"[{role}]: {preview}")

        conversation_history = "\n".join(history_parts)

        return user_message, conversation_history

    async def _get_route_decision(self, prompt: str) -> str:
        """
        Get routing decision from the router model.

        Returns:
            "high" or "low"
        """
        router = self._init_router_client()

        try:
            response = await asyncio.wait_for(
                router.call([{"role": "user", "content": prompt}]),
                timeout=self.routing_config.router_timeout,
            )

            return self._parse_route_label(response.content)

        except asyncio.TimeoutError:
            logger.warning(f"Router timeout ({self.routing_config.router_timeout}s), using default: high")
            return self.routing_config.default_route

        except Exception as e:
            logger.error(f"Router error: {e}, using default: high")
            return self.routing_config.default_route

    def _parse_route_label(self, content: str) -> str:
        """
        Parse the route label from router response.

        Returns:
            "high" or "low"
        """
        content = content.strip().lower()

        # Check for explicit labels
        if "high" in content:
            return "high"
        elif "low" in content:
            return "low"

        # Default to high (conservative)
        logger.warning(f"Could not parse route label from: {content[:50]}, defaulting to high")
        return "high"

    def _emit_progress(self, event: ProgressEvent) -> None:
        """Emit a progress event if callback is set."""
        if self._on_progress:
            self._on_progress(event)

    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Route the request and call the appropriate downstream model.
        """
        # 1. Extract routing input
        user_message, conversation_history = self._extract_route_input(messages)

        if not user_message:
            # No user message found, default to high
            logger.warning("No user message found, defaulting to high")
            route = "high"
            router_latency_ms = 0.0
        else:
            # 2. Build routing prompt
            route_prompt = self._build_route_prompt(user_message, conversation_history)

            # 3. Get routing decision
            router_start = time.time()
            route = await self._get_route_decision(route_prompt)
            router_latency_ms = (time.time() - router_start) * 1000

        # 4. Store for observability
        self._last_route = route
        self._last_router_latency_ms = router_latency_ms

        # 5. Emit progress event
        self._emit_progress(ProgressEvent(
            type=ProgressEventType.ROUTER_DECISION,
            message=f"Routed to: {route}",
            data={
                "route": route,
                "target_model": self.routing_config.high_model if route == "high" else self.routing_config.low_model,
                "router_latency_ms": router_latency_ms,
            },
        ))

        # 6. Select downstream client
        client = self.high_client if route == "high" else self.low_client

        logger.info(f"Routing decision: {route} (latency: {router_latency_ms:.1f}ms)")

        # 7. Call downstream
        return await client.call(messages, tools, system, **kwargs)

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        **kwargs,
    ):
        """
        Stream response from the routed downstream model.

        Note: Routing decision is made first, then streaming happens.
        """
        # Make routing decision (non-streaming)
        response = await self.call(messages, tools, system, **kwargs)

        # Yield the response as a single chunk
        if response.content:
            if on_chunk:
                on_chunk(response.content)
            yield response.content
