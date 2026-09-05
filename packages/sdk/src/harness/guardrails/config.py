"""
Guardrails 配置模块

定义 Layer 1 (PII 检测) 和 Layer 2 (LLM Judge) 的配置类。
"""

from dataclasses import dataclass, field


@dataclass
class StreamInterceptConfig:
    """流式拦截配置"""

    enabled: bool = False
    check_interval: int = 10  # 每 N 个 token 检测一次
    safety_threshold: float = 0.3  # 安全阈值（低于此值中断）
    min_tokens_before_check: int = 5  # 检测前最小 token 数


@dataclass
class JudgeConfig:
    """Layer 2 Judge 配置"""

    enabled: bool = False
    endpoint: str = ""  # Judge 服务端点
    model: str = ""  # 使用的模型名称
    timeout: float = 5.0  # 超时时间（秒）
    timeout_action: str = "pass"  # pass | block（超时时的行为）
    stream_intercept: StreamInterceptConfig | None = None


@dataclass
class GuardrailConfig:
    """Guardrails 完整配置"""

    enabled: bool = False  # 是否启用 Guardrails
    layer1_enabled: bool = True  # Layer 1: PII 规则检测
    layer2_enabled: bool = False  # Layer 2: LLM Judge
    judge_endpoint: str = ""  # Layer 2 服务端点
    judge_timeout: float = 5.0  # Judge 超时时间
    min_score: float = 0.5  # PII 检测最小置信度
    language: str = "auto"  # auto, zh, zh-tw, en
    placeholders: dict[str, str] = field(default_factory=dict)  # 自定义占位符

    def get_judge_config(self) -> JudgeConfig:
        """获取 Judge 配置"""
        return JudgeConfig(
            enabled=self.layer2_enabled,
            endpoint=self.judge_endpoint,
            timeout=self.judge_timeout,
        )
