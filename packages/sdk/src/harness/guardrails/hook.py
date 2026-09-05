"""
Guardrail Hook - 在 LLM 调用前后执行安全检查

通过 Hook 系统集成到 AgentHarness，实现：
- Layer 1: PII 检测和脱敏（用户输入）
- Layer 2: LLM Judge 语义检测（用户输入和 LLM 输出）
"""

import logging

from harness.core.hooks import LifecycleHook
from harness.guardrails.config import GuardrailConfig
from harness.types import HookContext, HookPoint, HookResult, Message

logger = logging.getLogger(__name__)


class GuardrailHook(LifecycleHook):
    """
    Guardrails Hook - 在 LLM 调用前后执行安全检查

    功能：
    - BEFORE_LLM_CALL: 检查用户输入
        - Layer 1: PII 检测和脱敏
        - Layer 2: Judge 语义风险检测
    - AFTER_LLM_CALL: 检查 LLM 输出
        - Layer 2: 输出安全性检测

    使用方法:
        from harness.guardrails import GuardrailConfig, GuardrailHook

        config = GuardrailConfig(
            enabled=True,
            layer1_enabled=True,
            layer2_enabled=False,
        )
        hook = GuardrailHook(config)
        agent.add_hook(hook)
    """

    def __init__(self, config: GuardrailConfig):
        """
        初始化 Guardrail Hook

        Args:
            config: Guardrails 配置
        """
        self.config = config
        self._pii_guardrail = None
        self._judge = None
        self._init_components()

    def _init_components(self):
        """初始化 Layer 1 和 Layer 2 组件"""
        # Layer 1: PII Guardrail
        if self.config.layer1_enabled:
            try:
                from harness.guardrails.chinese_guardrail import UniversalPIIGuardrail

                self._pii_guardrail = UniversalPIIGuardrail(
                    min_score=self.config.min_score,
                    placeholders=self.config.placeholders,
                )
                logger.info("Layer 1 (PII Guardrail) initialized")
            except ImportError as e:
                logger.warning(f"Layer 1 not available (missing dependencies): {e}")
                self._pii_guardrail = None

        # Layer 2: Judge
        if self.config.layer2_enabled and self.config.judge_endpoint:
            try:
                from harness.guardrails.judge import ComplianceJudge

                judge_config = self.config.get_judge_config()
                self._judge = ComplianceJudge(judge_config)
                logger.info(f"Layer 2 (Judge) initialized, endpoint: {self.config.judge_endpoint}")
            except ImportError as e:
                logger.warning(f"Layer 2 not available (missing dependencies): {e}")
                self._judge = None

    @property
    def hook_points(self) -> list[HookPoint]:
        """Hook 订阅的点"""
        points = []
        if self.config.layer1_enabled or self.config.layer2_enabled:
            points.append(HookPoint.BEFORE_LLM_CALL)
        if self.config.layer2_enabled:
            points.append(HookPoint.AFTER_LLM_CALL)
        return points

    async def execute(self, context: HookContext) -> HookResult:
        """
        执行 Hook 逻辑

        Args:
            context: Hook 上下文

        Returns:
            HookResult: 控制后续行为
        """
        if context.hook_point == HookPoint.BEFORE_LLM_CALL:
            return await self._handle_before_llm_call(context)
        elif context.hook_point == HookPoint.AFTER_LLM_CALL:
            return await self._handle_after_llm_call(context)
        return HookResult.continue_()

    async def _handle_before_llm_call(self, context: HookContext) -> HookResult:
        """
        LLM 调用前处理

        - Layer 1: PII 检测和脱敏
        - Layer 2: Judge 语义风险检测
        """
        if not context.messages:
            return HookResult.continue_()

        # 获取最后一条用户消息
        user_message = self._extract_last_user_message(context.messages)
        if not user_message:
            return HookResult.continue_()

        original_content = user_message
        modified_content = original_content

        # Layer 1: PII 检测和脱敏
        if self._pii_guardrail:
            try:
                entities = self._pii_guardrail.detect(original_content)
                if entities:
                    modified_content = self._pii_guardrail.redact(original_content)
                    logger.info(
                        f"Layer 1: Detected {len(entities)} PII entities, "
                        f"redacted: {original_content[:50]}... -> {modified_content[:50]}..."
                    )
            except Exception as e:
                logger.warning(f"Layer 1 PII detection failed: {e}")

        # Layer 2: Judge 语义风险检测
        if self._judge:
            try:
                result = await self._judge.judge(modified_content)
                logger.info(
                    f"Layer 2: Judge result - is_safe={result.is_safe}, "
                    f"risk_level={result.risk_level}, confidence={result.confidence}"
                )

                if result.risk_level in ("high", "critical"):
                    logger.warning(f"Layer 2: High risk content detected: {result.reason}")
                    return HookResult.abort(
                        f"内容安全风险：{result.reason} (风险等级: {result.risk_level})"
                    )
            except Exception as e:
                logger.warning(f"Layer 2 Judge check failed: {e}")
                # Judge 失败时继续，不阻止请求

        # 如果内容被修改（PII 脱敏），注入修改后的消息
        if modified_content != original_content:
            return HookResult.inject_message(Message(role="user", content=modified_content))

        return HookResult.continue_()

    async def _handle_after_llm_call(self, context: HookContext) -> HookResult:
        """
        LLM 调用后处理

        - Layer 2: 检查 LLM 输出是否安全
        """
        if not self._judge:
            return HookResult.continue_()

        # 获取 LLM 响应内容
        llm_content = self._extract_llm_response(context)
        if not llm_content:
            return HookResult.continue_()

        try:
            result = await self._judge.judge(llm_content)
            logger.info(
                f"Layer 2 (output): Judge result - is_safe={result.is_safe}, "
                f"risk_level={result.risk_level}"
            )

            if result.risk_level in ("high", "critical"):
                logger.warning(f"Layer 2: Unsafe LLM output detected: {result.reason}")
                return HookResult.abort(
                    f"输出安全风险：{result.reason} (风险等级: {result.risk_level})"
                )
        except Exception as e:
            logger.warning(f"Layer 2 output check failed: {e}")

        return HookResult.continue_()

    def _extract_last_user_message(self, messages: list) -> str | None:
        """提取最后一条用户消息"""
        for message in reversed(messages):
            if message.role == "user":
                if isinstance(message.content, str):
                    return message.content
                elif isinstance(message.content, list):
                    # 处理多模态消息
                    text_parts = []
                    for part in message.content:
                        if isinstance(part, dict) and "text" in part:
                            text_parts.append(part["text"])
                        elif isinstance(part, str):
                            text_parts.append(part)
                    return " ".join(text_parts) if text_parts else None
        return None

    def _extract_llm_response(self, context: HookContext) -> str | None:
        """从上下文提取 LLM 响应内容"""
        # 尝试从不同位置获取响应
        if hasattr(context, "llm_response") and context.llm_response:
            if isinstance(context.llm_response, str):
                return context.llm_response
            elif hasattr(context.llm_response, "content"):
                return context.llm_response.content

        # 从消息历史中获取最后一条助手消息
        if context.messages:
            for message in reversed(context.messages):
                if message.role == "assistant" and isinstance(message.content, str):
                    return message.content

        return None
