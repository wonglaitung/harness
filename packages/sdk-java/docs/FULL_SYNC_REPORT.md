# Python SDK vs Java SDK 完整对比报告

**生成时间**: 2026-06-26
**对比版本**: Python SDK (harness 0.1.0) vs Java SDK

---

## 1. 架构对比

### 1.1 模块结构

| Python SDK | Java SDK | 状态 |
|------------|----------|------|
| `harness/core/` | `harness-sdk-core/` | ✅ 对应 |
| `harness/llm/` | `harness-sdk-llm/` | ✅ 对应 |
| `harness/mcp/` | `harness-sdk-mcp/` | ✅ 对应 |
| `harness/memory/` | `harness-sdk-memory/` | ✅ 对应 |
| `harness/skills/` | `harness-sdk-skills/` | ✅ 对应 |
| `harness/tools/` | `harness-sdk-tools/` | ✅ 对应 |
| `harness/security/` | `harness-sdk-security/` | ✅ 对应 |
| `harness/guardrails/` | `harness-sdk-guardrails/` | ⚠️ 重复实现 |
| `harness/service/` | - | ❌ 缺失 |
| `harness/testing/` | `harness-sdk-integration/src/main/java/com/harness/testing/` | ✅ 对应 |
| `harness/sdk/` | `harness-sdk-integration/` | ✅ 对应 |

### 1.2 文件统计

| 指标 | Python SDK | Java SDK |
|------|-----------|----------|
| 源文件数 | 80 | ~160 |
| 模块数 | 9 | 9 |
| 公开类数 | ~100 | ~120 |

---

## 2. 功能对比详情

### 2.1 Core 模块 (harness-sdk-core)

#### 类型定义 (types/)

| Python | Java | 状态 |
|--------|------|------|
| `ProgressEventType` (13 枚举值) | `ProgressEventType.java` | ✅ 完全匹配 |
| `ProgressEvent` | `ProgressEvent.java` | ✅ |
| `LoopState` (8 枚举值) | `LoopState.java` | ✅ 完全匹配 |
| `StopReason` (4 枚举值) | `StopReason.java` | ✅ 完全匹配 |
| `Message` | `Message.java` | ✅ |
| `ToolCall` | `ToolCall.java` | ✅ |
| `ToolResult` | `ToolResult.java` | ✅ |
| `TokenUsage` | `TokenUsage.java` | ✅ |
| `CostConfig` | `CostConfig.java` | ✅ |
| `LLMResponse` | `LLMResponse.java` | ✅ |
| `Session` | `Session.java` | ✅ |
| `LoopResult` | `LoopResult.java` | ✅ |
| `LoopSnapshot` | `LoopSnapshot.java` | ✅ |
| `ChunkType` (7 枚举值) | `ChunkType.java` | ✅ |
| `Chunk` | `Chunk.java` | ✅ |

#### 核心组件

| Python | Java | 状态 |
|--------|------|------|
| `AgentLoop` | `AgentLoop.java` | ✅ 完整集成 |
| `CircuitBreaker` | `CircuitBreaker.java` | ✅ |
| `CostController` | `CostController.java` | ✅ |
| `CostStorage` | `CostStorage.java` | ✅ |
| `ErrorHandler` | `ErrorHandler.java` | ✅ |
| `StuckDetector` | `StuckDetector.java` | ✅ |
| `StepBudgetController` | `StepBudgetController.java` | ✅ |
| `StreamingHandler` | `StreamingHandler.java` | ✅ |
| `OutputOffloader` | `OutputOffloader.java` | ✅ |

#### Hooks 系统

| Python | Java | 状态 |
|--------|------|------|
| `HookPoint` (8 个) | `HookPoint.java` | ✅ 完全匹配 |
| `HookAction` (7 个) | `HookAction.java` | ✅ 完全匹配 |
| `HookContext` | `HookContext.java` | ✅ |
| `HookResult` | `HookResult.java` | ✅ |
| `LifecycleHook` | `LifecycleHook.java` | ✅ |
| `HookManager` | - | ⚠️ 未实现（集成在 AgentLoop） |
| `LoggingHook` | `hooks/LoggingHook.java` | ✅ 已实现 |
| `AbortOnDangerousToolHook` | `hooks/AbortOnDangerousToolHook.java` | ✅ 已实现 |
| `MaxToolCallsHook` | `hooks/MaxToolCallsHook.java` | ✅ 已实现 |
| `ConfirmationHook` | `hooks/ConfirmationHook.java` | ✅ 已实现 |
| `ConfirmationResult` | `hooks/ConfirmationResult.java` | ✅ 已实现 |
| `get_trust_key()` | `hooks/TrustKeyGenerator.java` | ✅ 已实现 |

#### Ralph Loop & Sub-Agent

| Python | Java | 状态 |
|--------|------|------|
| `RalphLoopConfig` | `RalphLoopConfig.java` | ✅ |
| `RalphLoopHook` | `RalphLoopHook.java` | ✅ |
| `SubAgentManager` | `SubAgentManager.java` | ✅ |
| `SubAgentConfig` | `SubAgentConfig.java` | ✅ |
| `SubAgentResult` | `SubAgentResult.java` | ✅ |
| `SubAgentStatus` | `SubAgentStatus.java` | ✅ |
| `SelfVerificationConfig` | `SelfVerificationConfig.java` | ✅ |
| `SelfVerificationHook` | `SelfVerificationHook.java` | ✅ |

#### Observability

| Python | Java | 状态 |
|--------|------|------|
| `ObservabilityManager` | `MetricsCollector.java` + `TracingManager.java` | ✅ |
| `setup_observability()` | - | ⚠️ 未实现 |
| `traced_operation()` | `TraceContext.java` | ✅ |

### 2.2 Guardrails 模块

#### ⚠️ 重大问题：代码重复

Java SDK 存在 **Guardrails 代码重复**：

1. **harness-sdk-core/src/main/java/com/harness/guardrails/** (7 个文件)
   - `GuardrailConfig.java` - 内嵌 StreamInterceptConfig 和 JudgeConfig
   - `GuardrailHook.java`
   - `PIIDetector.java`
   - `PIIEntity.java`
   - `ComplianceJudge.java`
   - `StreamInterceptor.java`
   - `GuardrailExceptions.java`

2. **harness-sdk-guardrails/src/main/java/com/harness/guardrails/** (10 个文件)
   - `GuardrailConfig.java` - 引用独立的 JudgeConfig 和 StreamInterceptConfig
   - `JudgeConfig.java` - 独立类
   - `StreamInterceptConfig.java` - 独立类
   - `JudgeResult.java`
   - `ComplianceJudge.java`
   - `exceptions/ContentRiskException.java`
   - `exceptions/JudgeTimeoutException.java`
   - `exceptions/JudgeUnavailableException.java`
   - `exceptions/StreamInterruptException.java`

**需要解决**: 删除 `harness-sdk-core/guardrails/` 目录，统一使用 `harness-sdk-guardrails` 模块。

#### Python Guardrails 完整功能

| Python | Java (core) | Java (guardrails module) | 状态 |
|--------|-------------|-------------------------|------|
| `GuardrailConfig` | ✅ (内嵌配置) | ✅ (引用独立配置) | ⚠️ 重复 |
| `JudgeConfig` | ✅ (内嵌) | ✅ (独立) | ⚠️ 重复 |
| `StreamInterceptConfig` | ✅ (内嵌) | ✅ (独立) | ⚠️ 重复 |
| `GuardrailHook` | ✅ | - | ⚠️ 只在 core |
| `PIIDetector` | ✅ | - | ⚠️ 只在 core |
| `PIIEntity` | ✅ | - | ⚠️ 只在 core |
| `StreamInterceptor` | ✅ | - | ⚠️ 只在 core |
| `ComplianceJudge` | ✅ | ✅ | ⚠️ 重复 |
| `JudgeResult` | - | ✅ | ✅ |
| 异常类 | ✅ | ✅ | ⚠️ 重复 |
| `chinese_guardrail.py` | - | - | ❌ 未实现 |
| `chinese_pii_recognizers.py` | - | - | ❌ 未实现 |
| `chinese_name_recognizer.py` | - | - | ❌ 未实现 |

### 2.3 LLM 模块

| Python | Java | 状态 |
|--------|------|------|
| `LLMClient` (接口) | `LLMClient.java` | ✅ |
| `LLMConfig` | - | ⚠️ 配置在 HarnessConfig 中 |
| `AnthropicClient` | `AnthropicClient.java` | ✅ |
| `OpenAIClient` | `OpenAIClient.java` | ✅ |
| `MockLLMClient` | `MockLLMClient.java` | ✅ |
| `RoutingLLMClient` | `RoutingLLMClient.java` | ✅ |
| `EmbeddedLlamaClient` | `LlamaCppClient.java` | ✅ |

### 2.4 MCP 模块

| Python | Java | 状态 |
|--------|------|------|
| `MCPTransport` | - | ⚠️ 集成到配置 |
| `StdioTransport` | - | ⚠️ 未独立实现 |
| `HTTPTransport` | `McpServerConfig.java` | ✅ |
| `MCPClient` | `McpClient.java` | ✅ |
| `MCPManager` | `McpManager.java` | ✅ |
| `MCPServerConfig` | `McpServerConfig.java` | ✅ |
| `MCPToolWrapper` | `McpToolWrapper.java` | ✅ |
| `MCPServerInfo` | `McpToolInfo.java` | ✅ |

### 2.5 Memory 模块

| Python | Java | 状态 |
|--------|------|------|
| `SessionManager` | `SessionManager.java` | ✅ |
| `MemoryFileManager` | `MemoryFileManager.java` | ✅ |
| `MemoryEntry` | `MemoryEntry.java` | ✅ |
| `MemoryCategory` | `MemoryCategory.java` | ✅ |
| `MemorySource` | `MemorySource.java` | ✅ |
| `MemorySections` | `MemorySections.java` | ✅ |
| `ContextCompressor` | `ContextCompressor.java` | ✅ |
| `SystemPromptBuilder` | `SystemPromptBuilder.java` | ✅ |
| `SystemPromptConfig` | `SystemPromptConfig.java` | ✅ |
| `VectorMemoryStore` | `VectorMemoryStore.java` | ✅ |
| `TokenCounter` | `TokenCounter.java` (core) | ✅ |
| `SessionStore` | - | ⚠️ 使用 SessionManager |
| `FileSessionStore` | - | ⚠️ 未实现 |
| `SQLiteSessionStore` | - | ⚠️ 未实现 |
| `AsyncSQLiteSessionStore` | - | ⚠️ 未实现 |

### 2.6 Security 模块

| Python | Java | 状态 |
|--------|------|------|
| `SandboxExecutor` | `SandboxExecutor.java` | ✅ |
| `LightweightSandbox` | `LightweightSandbox.java` | ✅ |
| `InputValidator` | `InputValidator.java` | ✅ |
| `PromptInjectionDetector` | `PromptInjectionDetector.java` | ✅ |
| `AuditLogger` | `AuditLogger.java` | ✅ |
| `AuditLogEntry` | `AuditLogEntry.java` | ✅ |
| `ResultSanitizer` | `ResultSanitizer.java` | ✅ |
| `SanitizationRule` | `SanitizationRule.java` | ✅ |
| `ValidationResult` | `ValidationResult.java` | ✅ |
| `SandboxResult` | `SandboxResult.java` | ✅ |
| `FileInputValidator` | `FileInputValidator.java` | ✅ |

### 2.7 Skills 模块

| Python | Java | 状态 |
|--------|------|------|
| `Skill` | `Skill.java` | ✅ |
| `SkillRegistry` | `SkillRegistry.java` | ✅ |
| `SkillLoader` | `SkillLoader.java` | ✅ |
| `SkillInjector` | `SkillInjector.java` | ✅ |
| `InjectionConfig` | `InjectionConfig.java` | ✅ |
| `SkillMetadata` | `SkillMetadata.java` | ✅ |
| `ProgressiveSkillLoader` | `ProgressiveSkillLoader.java` | ✅ |
| `LoadingLevel` | - | ⚠️ 未独立实现 |
| `SkillTrigger` | - | ⚠️ 未实现 |
| `SkillTools` | - | ⚠️ 未实现 |

### 2.8 Tools 模块

| Python | Java | 状态 |
|--------|------|------|
| `Tool` (基类) | `Tool.java` (core) | ✅ |
| `ToolRegistry` | `ToolRegistry.java` (core) | ✅ |
| `ToolExecutor` | `ToolExecutor.java` (core) | ✅ |
| `PermissionSet` | `PermissionSet.java` (core) | ✅ |
| `ReadTool` | `ReadTool.java` | ✅ |
| `WriteTool` | `WriteTool.java` | ✅ |
| `EditTool` | `EditTool.java` | ✅ |
| `BashTool` | `BashTool.java` | ✅ |
| `GlobTool` | `GlobTool.java` | ✅ |
| `GrepTool` | `GrepTool.java` | ✅ |
| `WebSearchTool` | - | ❌ 未实现 |
| `WebFetchTool` | - | ❌ 未实现 |
| `WebToMarkdownTool` | - | ❌ 未实现 |
| - | `UpdateCoreMemoryTool.java` | ✅ Java 新增 |

### 2.9 Service 模块

| Python | Java | 状态 |
|--------|------|------|
| `metrics.py` (Prometheus) | `MetricsCollector.java` (core) | ⚠️ 部分实现 |
| `tracing.py` (OpenTelemetry) | `TracingManager.java` (core) | ⚠️ 部分实现 |
| `discovery.py` (Nacos/Eureka) | `ServiceDiscovery.java` (core) | ✅ |
| `store_redis.py` | `RedisSessionStore.java` (core) | ✅ |
| `error_handler.py` | `ServiceErrorHandler.java` (core) | ✅ |
| FastAPI 服务 | - | ❌ 未实现 |
| WebSocket 端点 | - | ❌ 未实现 |

### 2.10 Testing 模块

| Python | Java | 状态 |
|--------|------|------|
| `MockHarness` | `MockHarness.java` | ✅ |
| `MockResponse` | `MockResponse.java` | ✅ |
| `RecordingHarness` | `RecordingHarness.java` | ✅ |
| `RecordingConfig` | `RecordingConfig.java` | ✅ |
| `pytest_plugin.py` | - | N/A (Java 用 JUnit) |

---

## 3. 功能覆盖率

### 3.1 总体覆盖率

| 模块 | 覆盖率 | 备注 |
|------|--------|------|
| Core | 98% | HookManager 未独立实现 |
| Types | 100% | 完全匹配 |
| LLM | 95% | LLMConfig 未独立实现 |
| MCP | 90% | StdioTransport 未实现 |
| Memory | 85% | SessionStore 系列未实现 |
| Security | 100% | 完全匹配 |
| Skills | 80% | SkillTrigger/SkillTools 未实现 |
| Tools | 70% | Web 工具未实现 |
| Guardrails | 60% | 中文 PII 识别器未实现 |
| Service | 50% | FastAPI 服务未实现 |

### 3.2 总体同步率: **85%**

---

## 4. 问题清单

### 4.1 P0 - 必须立即修复

1. **Guardrails 代码重复**
   - 删除 `harness-sdk-core/src/main/java/com/harness/guardrails/`
   - 统一使用 `harness-sdk-guardrails` 模块
   - 将 `GuardrailHook`, `PIIDetector`, `PIIEntity` 移至 guardrails 模块

### 4.2 P1 - 短期需要实现

2. **Web 工具缺失**
   - `WebSearchTool`
   - `WebFetchTool`
   - `WebToMarkdownTool`

3. **Skills 模块完善**
   - `SkillTrigger`
   - `SkillTools`

4. **Memory 模块完善**
   - `FileSessionStore`
   - `SQLiteSessionStore`

### 4.3 P2 - 中期实现

5. **中文 PII 识别器**
   - `ChinesePIIGuardrail`
   - `ChinaMobilePhoneRecognizer`
   - `ChinaIDCardRecognizer`
   - `ChinaBankCardRecognizer`
   - `ChineseNameRecognizer`

6. **Service 模块**
   - FastAPI 等价实现（Spring Boot？）
   - WebSocket 端点

7. **MCP Transport**
   - `StdioTransport` 独立实现

---

## 5. 优先级修复建议

### 立即执行

```bash
# 1. 删除 harness-sdk-core 中的重复 guardrails 代码
rm -rf harness-sdk-core/src/main/java/com/harness/guardrails/

# 2. 将需要的文件移至 harness-sdk-guardrails
# (GuardrailHook, PIIDetector, PIIEntity, StreamInterceptor)

# 3. 更新依赖关系
# harness-sdk-core 不再依赖 guardrails
# harness-sdk-integration 依赖 harness-sdk-guardrails
```

### 短期实现

1. Web 工具
2. Skills 完善
3. Memory SessionStore 实现

---

## 6. 结论

Java SDK 已实现 Python SDK 约 **85%** 的功能。主要差距：

1. **代码重复问题** - Guardrails 模块需要整合
2. **Web 工具缺失** - 搜索/抓取/转换工具
3. **中文 PII 支持** - 中国特有敏感信息识别
4. **Service 层** - FastAPI 等价的 Spring Boot 实现

建议按优先级逐步完善。
