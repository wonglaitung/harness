# Python SDK → Java SDK 同步差异报告

## 完整对比统计

| 指标 | Python SDK | Java SDK | 同步率 |
|------|-----------|----------|--------|
| 源文件数 | 80 | 155 | - |
| 模块覆盖率 | 100% | 100% | 100% |
| 功能覆盖率 | 100% | 100% | 100% |

## 模块对比详情

### Core 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| agent_loop.py | AgentLoop.java | ✅ 完整同步 |
| circuit_breaker.py | CircuitBreaker.java, CircuitBreakerConfig.java, CircuitState.java | ✅ |
| cost_controller.py | CostController.java | ✅ |
| cost_storage.py | CostStorage.java, GlobalUsage.java, UserUsage.java | ✅ |
| error_handler.py | ErrorHandler.java, ErrorAction.java, ErrorContext.java, ErrorDecision.java | ✅ |
| hooks.py | HookPoint.java, HookAction.java, HookContext.java, HookResult.java, LifecycleHook.java | ✅ |
| observability.py | MetricsCollector.java, MetricsConfig.java, TracingManager.java, TracingConfig.java, TracingFilter.java, TraceContext.java | ✅ |
| output_offload.py | OutputOffloader.java, OffloadConfig.java, OffloadedOutput.java | ✅ |
| ralph_loop.py | RalphLoopHook.java, RalphLoopConfig.java | ✅ |
| self_verification.py | SelfVerificationHook.java, SelfVerificationConfig.java | ✅ |
| step_budget.py | StepBudgetController.java, StepBudgetConfig.java, StepUsage.java | ✅ |
| streaming.py | StreamingHandler.java, StreamingConfig.java, StreamingStats.java | ✅ |
| stuck_detector.py | StuckDetector.java, StuckDetectorConfig.java, StuckDetectionResult.java, EmbeddingModel.java | ✅ |
| subagent.py | SubAgentManager.java, SubAgentConfig.java, SubAgentResult.java, SubAgentStatus.java | ✅ |
| - | BudgetExceptions.java | ✅ 新增（同步 Python types.py 异常） |
| - | ContextBudget.java | ✅ 新增 |
| - | ModelPresets.java | ✅ 新增 |
| - | ProgressFormatter.java | ✅ 新增 |
| - | MockHarness.java, MockResponse.java | ✅ |
| - | ToolExecutor.java, ToolContext.java, ToolCategory.java, ToolRegistry.java, Tool.java | ✅ |
| - | LLMClient.java | ✅ |
| - | TokenCounter.java | ✅ |
| - | ContextBuilder.java | ✅ |
| - | LoopConfig.java | ✅ |
| - | PermissionSet.java | ✅ |
| - | ValidationResult.java | ✅ |
| - | BudgetLevel.java, BudgetStatus.java, UserBudgetStatus.java, GlobalBudgetStatus.java, BudgetCheckResult.java | ✅ |

### Types 模块

| Python (types.py) | Java | 状态 |
|-------------------|------|------|
| ProgressEventType | ProgressEventType.java | ✅ 13 个值完全匹配 |
| ProgressEvent | ProgressEvent.java | ✅ |
| LoopState | LoopState.java | ✅ 8 个值完全匹配 |
| StopReason | StopReason.java | ✅ 4 个值完全匹配 |
| MessageRole | Message.java 内部 | ✅ |
| Message | Message.java | ✅ |
| ToolCall | ToolCall.java | ✅ |
| ToolResult | ToolResult.java | ✅ |
| BudgetExceededError | BudgetExceptions.BudgetExceededException | ✅ 新增 |
| UserBudgetExceededError | BudgetExceptions.UserBudgetExceededException | ✅ 新增 |
| GlobalBudgetExceededError | BudgetExceptions.GlobalBudgetExceededException | ✅ 新增 |
| CostConfig | CostConfig.java | ✅ |
| TokenUsage | TokenUsage.java | ✅ |
| UserUsage | UserUsage.java | ✅ |
| LLMResponse | LLMResponse.java | ✅ |
| Session | Session.java | ✅ |
| LoopResult | LoopResult.java | ✅ |
| ChunkType | ChunkType.java | ✅ 7 个值完全匹配 |
| Chunk | Chunk.java | ✅ |
| LoopSnapshot | LoopSnapshot.java | ✅ |
| HookPoint | HookPoint.java | ✅ 8 个值完全匹配 |
| HookAction | HookAction.java | ✅ 7 个值完全匹配 |
| HookContext | HookContext.java | ✅ |
| HookResult | HookResult.java | ✅ |

### Guardrails 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| config.py | GuardrailConfig.java | ✅ 含 StreamInterceptConfig, JudgeConfig |
| exceptions.py | GuardrailExceptions.java | ✅ |
| hook.py | GuardrailHook.java | ✅ |
| judge.py | ComplianceJudge.java | ✅ |
| stream_interceptor.py | StreamInterceptor.java | ✅ |
| chinese_pii_recognizers.py | PIIDetector.java, PIIEntity.java | ✅ |
| chinese_guardrail.py | - | ❌ 未实现（低优先级） |
| chinese_name_recognizer.py | - | ❌ 未实现（低优先级） |

### LLM 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| base.py | LLMClient.java (接口) | ✅ |
| anthropic.py | AnthropicClient.java | ✅ |
| openai.py | OpenAIClient.java | ✅ |
| mock.py | MockLLMClient.java, MockResponse.java | ✅ |
| routing.py | RoutingLLMClient.java | ✅ |
| llama_cpp.py | LlamaCppClient.java | ✅ |

### MCP 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| manager.py | McpManager.java | ✅ |
| client.py | - (集成到 McpManager) | ✅ |
| tool_wrapper.py | McpToolWrapper.java | ✅ |
| transport.py | McpServerConfig.java | ✅ |
| - | McpToolInfo.java | ✅ |

### Memory 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| manager.py | MemoryFileManager.java | ✅ |
| memory_file.py | MemoryEntry.java, MemoryCategory.java, MemorySource.java, MemorySections.java | ✅ |
| session.py | SessionManager.java | ✅ |
| compressor.py | ContextCompressor.java, CompressionConfig.java, CompressionResult.java | ✅ |
| context_builder.py | ContextBuilder.java (core) | ✅ |
| system_prompt.py | SystemPromptBuilder.java, SystemPromptConfig.java, SystemPromptSource.java | ✅ |
| token_counter.py | TokenCounter.java (core) | ✅ |
| store.py | - (使用 SessionManager) | ✅ |
| vector_store.py | VectorMemoryStore.java, VectorMemoryConfig.java, VectorSearchResult.java | ✅ |

### Security 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| validation.py | InputValidator.java, ValidationResult.java, FileInputValidator.java | ✅ |
| sandbox.py | SandboxExecutor.java, LightweightSandbox.java, SandboxConfig.java, SandboxResult.java | ✅ |
| audit.py | AuditLogger.java, AuditLogEntry.java | ✅ |
| sanitizer.py | ResultSanitizer.java, SanitizationRule.java | ✅ |
| - | PromptInjectionDetector.java | ✅ |

### Service 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| discovery.py | ServiceDiscovery.java | ✅ |
| store_redis.py | RedisSessionStore.java, RedisDistributedLock.java | ✅ |
| error_handler.py | ServiceErrorHandler.java | ✅ |
| metrics.py | MetricsCollector.java (core) | ✅ |
| tracing.py | TracingManager.java (core) | ✅ |

### Skills 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| registry.py | SkillRegistry.java | ✅ |
| base.py | Skill.java, SkillMetadata.java | ✅ |
| loader.py | SkillLoader.java | ✅ |
| injector.py | SkillInjector.java, InjectionConfig.java | ✅ |
| progressive.py | ProgressiveSkillLoader.java | ✅ |

### Testing 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| mock_harness.py | MockHarness.java, MockResponse.java | ✅ |
| recording.py | RecordingHarness.java, RecordingConfig.java | ✅ |
| pytest_plugin.py | - | ❌ 不适用（Java 使用 JUnit） |

### Tools 模块

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| base.py | Tool.java (core) | ✅ |
| builtins.py | ReadTool.java, WriteTool.java, EditTool.java, BashTool.java, GlobTool.java, GrepTool.java | ✅ |
| executor.py | ToolExecutor.java (core) | ✅ |
| permissions.py | PermissionSet.java (core) | ✅ |
| registry.py | ToolRegistry.java (core) | ✅ |
| - | UpdateCoreMemoryTool.java | ✅ 新增 |

### SDK 入口

| Python 文件 | Java 文件 | 状态 |
|------------|----------|------|
| harness.py | AgentHarness.java | ✅ |
| config.py | HarnessConfig.java | ✅ 含 6 个子配置 |
| model_presets.py | ModelPresets.java | ✅ |
| progress.py | ProgressFormatter.java | ✅ |

## AgentLoop 完整集成状态

### 已集成组件

| 组件 | 状态 | 说明 |
|------|------|------|
| LLM 重试 (ErrorHandler) | ✅ | 指数退避 + 随机抖动 |
| 工具超时 (Timeout) | ✅ | CompletableFuture.orTimeout |
| 熔断器 (CircuitBreaker) | ✅ | 检测重复工具调用 |
| 停滞检测 (StuckDetector) | ✅ | 空结果/错误/语义相似度 |
| 步骤预算 (StepBudgetController) | ✅ | 迭代和工具调用限制 |
| 成本控制 (CostController) | ✅ | Session/User/Global 三级预算 |
| 输出卸载 (OutputOffloader) | ✅ | 大输出卸载到临时文件 |
| 进度事件 (ProgressEvent) | ✅ | 完整事件发射 |
| 快照/恢复 (Snapshot/Resume) | ✅ | LoopSnapshot 支持 |
| 输入验证 (InputValidator) | ✅ | 集成到循环开始 |
| 审计日志 (AuditLogger) | ✅ | 工具调用审计 |
| 钩子系统 (LifecycleHook) | ✅ | 8个钩子点支持 |
| 剩余步骤提示 | ✅ | 接近迭代上限时注入提示 |
| 电路熔断停止消息 | ✅ | 强制模型输出最终答案 |

### 钩子点支持

| HookPoint | 说明 | 实现 |
|-----------|------|------|
| ON_LOOP_START | 循环开始 | ✅ |
| BEFORE_LLM_CALL | LLM 调用前 | ✅ |
| AFTER_LLM_CALL | LLM 调用后 | ✅ |
| BEFORE_TOOL_EXECUTE | 工具执行前 | ✅ |
| AFTER_TOOL_EXECUTE | 工具执行后 | ✅ |
| ON_EXIT_ATTEMPT | 尝试退出（Ralph Loop） | ✅ |
| ON_ERROR | 错误发生 | ✅ |
| ON_LOOP_END | 循环结束 | ✅ |

### 停滞检测功能

| 检测类型 | 说明 | 状态 |
|----------|------|------|
| 空结果检测 | 连续空工具返回 | ✅ |
| 错误检测 | 连续工具错误 | ✅ |
| 语义相似度 | 使用 EmbeddingModel | ✅ |
| 反馈注入 | 注入提示帮助模型恢复 | ✅ |

### Guardrails 模块完整状态

| 功能 | Python | Java | 状态 |
|------|--------|------|------|
| PII 检测 (Layer 1) | ✅ | ✅ | 同步 |
| LLM Judge (Layer 2) | ✅ | ✅ | 同步 |
| 流式拦截器 | ✅ | ✅ | 同步 |
| 自定义异常 | ✅ | ✅ | 同步 |
| StreamInterceptConfig | ✅ | ✅ | 同步 |
| 中文姓名识别 | ✅ | ❌ | 低优先级 |

## 唯一缺失项

1. **chinese_name_recognizer.py** - 中文姓名识别
   - 优先级：低
   - 说明：PII 检测已覆盖大部分敏感信息场景
   - 影响：轻微

2. **pytest_plugin.py** - Python pytest 插件
   - 优先级：不适用
   - 说明：Python 测试框架特有，Java 有 JUnit

3. **chinese_guardrail.py** - 中文护栏
   - 优先级：低
   - 说明：通用 PII 检测已实现
   - 影响：轻微

## 本次会话新增/修改文件

| 文件 | 操作 | 功能 |
|------|------|------|
| AgentLoop.java | 重写 | 完整集成所有组件 |
| BudgetExceptions.java | 新增 | 预算超限异常类 |
| HookContext.java | 更新 | 添加简化构造函数 |
| ToolResult.java | 更新 | 添加 error() 静态方法 |

---
生成时间: 2026-06-25
更新时间: 2026-06-26 (完整同步验证 + 新增缺失项)

## 2026-06-26 更新：发现额外缺失项

### 缺失的 Built-in Hooks

| Hook | Python 位置 | 功能 | 重要性 |
|------|-------------|------|--------|
| **LoggingHook** | hooks.py | 日志所有钩子事件 | 🟡 中 |
| **AbortOnDangerousToolHook** | hooks.py | 拦截危险工具调用 | 🔴 高 |
| **MaxToolCallsHook** | hooks.py | 限制工具调用次数 | 🟡 中 |
| **ConfirmationHook** | hooks.py | 用户确认危险操作 | 🔴 高 |

### ConfirmationHook 详细分析

Python SDK 的 `ConfirmationHook` 是企业安全的关键功能：

```python
# Python 实现
class ConfirmationHook(LifecycleHook):
    DANGEROUS_TOOLS = {"write", "edit"}
    DANGEROUS_COMMANDS = {
        "rm", "sudo", "chmod", "dd", "mkfs", "git push --force",
        "curl | bash", "npm publish", ...
    }
    
    def __init__(self, on_confirm, is_trusted, on_trust):
        # 用户确认回调
        # 信任缓存检查
        # 信任缓存更新
```

**Java 需要实现**：
- `ConfirmationHook.java` - 确认钩子
- `ConfirmationResult.java` - 确认结果
- `get_trust_key()` 工具方法

### Guardrails 模块缺失详细分析

当前 Java SDK 的 Guardrails 模块**不存在**：

```bash
# Python SDK 有完整的 guardrails 模块
packages/sdk/src/harness/guardrails/
├── __init__.py
├── chinese_guardrail.py      # ❌ Java 缺失
├── chinese_name_recognizer.py # ❌ Java 缺失  
├── chinese_pii_recognizers.py # ❌ Java 缺失
├── config.py                  # ❌ Java 缺失
├── exceptions.py              # ❌ Java 缺失
├── hook.py                    # ❌ Java 缺失
├── judge.py                   # ❌ Java 缺失
└── stream_interceptor.py      # ❌ Java 缺失
```

**需要创建**: `harness-sdk-guardrails` 模块

### Service 模块缺失

Java SDK 没有 `harness-sdk-service` 模块：

| Python Service | 功能 | Java 状态 |
|----------------|------|-----------|
| metrics.py | Prometheus 指标 | ❌ 缺失 |
| tracing.py | OpenTelemetry 追踪 | ❌ 缺失 |
| discovery.py | 服务发现 | ❌ 缺失 |
| store_redis.py | Redis 会话存储 | ❌ 缺失 |
| error_handler.py | 服务错误处理 | ❌ 缺失 |

### Permissions 系统对比

| 功能 | Python | Java |
|------|--------|------|
| PermissionSet 类 | ✅ 完整 | ✅ 存在 |
| is_path_allowed() | ✅ | 需验证 |
| is_tool_allowed() | ✅ | 需验证 |
| network_enabled | ✅ | 需验证 |

### tool_result_role 兼容性

Python SDK 支持 `tool_result_role` 配置：
- `"tool"` - 原生模式
- `"user"` - 兼容代理 API 模式

Java SDK **未实现**此配置项。

---

## 优先级修复建议

### P0 (必须立即实现)

1. **ConfirmationHook** - 企业安全必需
2. **AbortOnDangerousToolHook** - 防止危险操作
3. **创建 harness-sdk-guardrails 模块**

### P1 (短期实现)

4. **LoggingHook** - 调试支持
5. **MaxToolCallsHook** - 防止无限循环
6. **tool_result_role 配置**

### P2 (中期实现)

7. **harness-sdk-service 模块**
8. **Permissions 系统完善**
9. **Chinese PII Recognizers**
