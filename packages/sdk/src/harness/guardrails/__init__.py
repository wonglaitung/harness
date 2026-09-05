"""
Guardrails 模块 - PII 检测和内容安全

支持：
- Layer 1: PII 规则检测（手机号、身份证、银行卡等）- 快速，<1ms
- Layer 2: LLM Judge 语义检测（可选）- 约100ms

使用方法：
    from harness.guardrails import GuardrailConfig, GuardrailHook
    from harness import AgentHarness

    # 只启用 Layer 1（PII 过滤）
    agent = AgentHarness(
        model="claude-sonnet-4-6",
        guardrails=GuardrailConfig(
            enabled=True,
            layer1_enabled=True,
            layer2_enabled=False,
        ),
    )

    # 同时启用 Layer 1 和 Layer 2
    agent = AgentHarness(
        model="claude-sonnet-4-6",
        guardrails=GuardrailConfig(
            enabled=True,
            layer1_enabled=True,
            layer2_enabled=True,
            judge_endpoint="http://localhost:8001/v1/chat/completions",
        ),
    )

依赖安装：
    # 方式一：安装可选依赖（推荐）
    uv sync --extra guardrails

    # 方式二：手动安装
    pip install presidio-analyzer>=2.2.0
    pip install presidio-anonymizer>=2.2.0

    # Layer 2 (Judge) - 如果启用
    pip install httpx>=0.24.0
    pip install cachetools>=5.3.0  # 可选，用于结果缓存

注意：不需要安装 zh_core_web_sm 或其他 spaCy 中文模型。
      中文 PII 使用正则表达式 + 姓氏库实现，更精准且无额外依赖。
"""

# 配置类
# PII 过滤核心类
from harness.guardrails.chinese_guardrail import (
    ChinesePIIGuardrail,
    PIIEntity,
    UniversalPIIGuardrail,
    check_pii,
    create_guardrail,
    create_universal_guardrail,
    mask_pii,
    redact_pii,
    redact_pii_traditional,
    scan_pii,
)

# 中文姓名识别器
from harness.guardrails.chinese_name_recognizer import (
    COMMON_SURNAMES,
    COMPOUND_SURNAMES,
    ChineseNameRecognizer,
    NameMatch,
    create_name_recognizer,
    extract_chinese_names,
)

# PII 识别器
from harness.guardrails.chinese_pii_recognizers import (
    CHINA_PII_RECOGNIZERS,
    ChinaBankCardRecognizer,
    ChinaIDCardRecognizer,
    ChinaLicensePlateRecognizer,
    ChinaMobilePhoneRecognizer,
    ChinaPassportRecognizer,
    ChinaSocialCreditCodeRecognizer,
    EmailRecognizerCN,
    HongKongIDCardRecognizer,
    HongKongNameRecognizer,
    HongKongPhoneRecognizer,
    IpRecognizerCN,
)
from harness.guardrails.config import (
    GuardrailConfig,
    JudgeConfig,
    StreamInterceptConfig,
)

# 异常
from harness.guardrails.exceptions import (
    ContentRiskException,
    JudgeResult,
    JudgeTimeoutException,
    JudgeUnavailableException,
    StreamInterruptException,
)

# Hook
from harness.guardrails.hook import GuardrailHook

# Judge (Layer 2)
from harness.guardrails.judge import (
    ComplianceJudge,
    RiskLevel,
)

# 流式拦截器
from harness.guardrails.stream_interceptor import (
    InterceptResult,
    StreamInterceptor,
)

__all__ = [
    # 配置
    "GuardrailConfig",
    "JudgeConfig",
    "StreamInterceptConfig",
    # Hook
    "GuardrailHook",
    # PII 过滤
    "PIIEntity",
    "ChinesePIIGuardrail",
    "UniversalPIIGuardrail",
    "create_guardrail",
    "create_universal_guardrail",
    "check_pii",
    "redact_pii",
    "redact_pii_traditional",
    "scan_pii",
    "mask_pii",
    # PII 识别器
    "ChinaMobilePhoneRecognizer",
    "ChinaIDCardRecognizer",
    "ChinaBankCardRecognizer",
    "ChinaPassportRecognizer",
    "ChinaSocialCreditCodeRecognizer",
    "ChinaLicensePlateRecognizer",
    "EmailRecognizerCN",
    "IpRecognizerCN",
    "HongKongPhoneRecognizer",
    "HongKongIDCardRecognizer",
    "HongKongNameRecognizer",
    "CHINA_PII_RECOGNIZERS",
    # 中文姓名识别器
    "NameMatch",
    "ChineseNameRecognizer",
    "create_name_recognizer",
    "extract_chinese_names",
    "COMMON_SURNAMES",
    "COMPOUND_SURNAMES",
    # Judge
    "RiskLevel",
    "ComplianceJudge",
    # 流式拦截器
    "InterceptResult",
    "StreamInterceptor",
    # 异常
    "JudgeResult",
    "ContentRiskException",
    "JudgeTimeoutException",
    "JudgeUnavailableException",
    "StreamInterruptException",
]
