# Python SDK vs Java SDK 对比报告

生成日期: 2026-06-27
**更新日期: 2026-06-27 (同步后)**

## 同步完成状态

| 任务 | 优先级 | 状态 |
|------|--------|------|
| Memory Scoring + Archive | P0 | ✅ 已同步 |
| model_presets | P0 | ✅ 已存在（无需修改） |
| tool_result_role 兼容模式 | P0 | ✅ 已同步 |
| Tracing 集成到 AgentLoop | P1 | ✅ 已同步 |
| Error Handler 完整策略 | P1 | ✅ 已存在（补充 previousErrors） |
| 功能演示测试用例 | P1 | ✅ 已完成 (27个测试用例) |

---

## 测试用例验证

Java SDK 已创建完整的功能演示示例 `SdkFeatureDemo.java`（位于 `examples/` 目录），包含 27 个演示：

1. **基础对话功能** - MockLLMClient 测试
2. **工具系统 - 文件操作** - ReadTool, GlobTool, GrepTool
3. **多轮对话 - 会话管理** - Session 隔离测试
4. **成本控制** - maxIterations 配置
5. **进度追踪** - Consumer<Object> 回调
6. **自定义工具** - SimpleTool 实现
7. **Mock 测试** - MockHarness 模式
8. **Skills 技能系统** - SkillRegistry + triggers 匹配
9. **Skill 注入** - 多技能匹配
10. **MCP 服务器** - McpManager
11. **Security 安全系统** - SecurityConfig
12. **Observability 可观测性** - TracingManager + TracingConfig
13. **多级成本控制** - CostControlConfig
14. **中断与恢复** - 会话状态管理
15. **配置管理** - HarnessConfig 全配置
16. **完整工作流** - 多工具 + 进度追踪
17. **Lifecycle Hooks** - LoggingHook 实现
18. **动态系统提示** - SystemPromptBuilder
19. **Ralph Loop** - 长任务循环
20. **Sub-Agent 管理** - 子代理模式
21. **自验证钩子** - 代码修改验证
22. **渐进式技能加载** - L1/L2/L3 三级加载
23. **MEMORY.md 标准** - MemoryFileManager
24. **向量检索** - VectorMemoryStore
25. **语义卡住检测** - StuckDetection
26. **Guardrails PII 检测** - PIIDetector
27. **CPU Router** - 成本优化路由

---

## 1. 模块结构对比

### Python SDK 结构
```
packages/sdk/src/harness/
├── sdk/           (harness.py, config.py)
├── core/          (agent_loop.py, cost_controller.py, hooks.py, circuit_breaker.py, ...)
├── llm/           (base.py, anthropic.py, openai.py, mock.py, routing.py, llama_cpp.py)
├── memory/        (context_builder.py, session.py, store.py, memory_file.py, compressor.py, ...)
├── tools/         (base.py, builtins.py, executor.py, registry.py, permissions.py)
├── mcp/           (manager.py, client.py, transport.py, tool_wrapper.py)
├── skills/        (base.py, registry.py, injector.py, loader.py, progressive.py)
├── security/      (sandbox.py, validation.py, sanitizer.py, audit.py)
├── guardrails/    (hook.py, judge.py, chinese_pii_recognizers.py, ...)
├── service/       (metrics.py, discovery.py, tracing.py, store_redis.py)
├── testing/       (mock_harness.py, recording.py, pytest_plugin.py)
├── progress.py
├── model_presets.py
├── types.py
```

### Java SDK 结构
```
packages/sdk-java/
├── harness-sdk-core/        (types, Hook, CircuitBreaker, StepBudget, Streaming, ...)
├── harness-sdk-llm/         (LLMClient interface, MockResponse)
├── harness-sdk-memory/      (MemoryEntry, SessionManager, ContextBuilder, ContextCompressor, ...)
├── harness-sdk-tools/       (ReadTool, WriteTool, EditTool, BashTool, GrepTool, GlobTool)
├── harness-sdk-security/    (InputValidator, ResultSanitizer, SandboxExecutor, AuditLogger, ...)
├── harness-sdk-mcp/         (McpManager, McpClient, McpToolWrapper, Transport)
├── harness-sdk-skills/      (SkillLoader, SkillInjector, SkillRegistry)
├── harness-sdk-guardrails/  (GuardrailHook, PIIDetector, ChinesePIIRecognizers, ...)
├── harness-sdk-integration/ (AgentHarness, AgentLoop - 组合所有模块)
├── harness-sdk-all/         (聚合包)
```

---

## 2. 功能差异详细分析

### 2.1 AgentLoop 核心循环

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| ReAct 循环 | ✅ 完整 | ✅ 完整 | 同步 |
| Circuit Breaker | ✅ 完整 | ✅ 完整 | 同步 |
| Stuck Detection | ✅ 完整（语义相似度+空/错误检测） | ✅ 完整 | 同步 |
| Step Budget | ✅ 完整 | ✅ 完整 | 同步 |
| Output Offload | ✅ 完整 | ✅ 完整 | 同步 |
| Lifecycle Hooks | ✅ 8个HookPoint | ✅ 8个HookPoint | 同步 |
| Error Handler | ✅ 完整（RETRY/COMPRESS_CONTEXT/ABORT） | ⚠️ 仅基础重试 | **Python 更完善** |
| Progress Events | ✅ 完整 | ✅ 完整 | 同步 |
| Tracing (OpenTelemetry) | ✅ SpanBuilder | ⚠️ TracingManager 存在但未集成到 AgentLoop | **Python 更完善** |
| Cost Controller | ✅ 完整 | ✅ 存在 | 同步 |
| Memory MD Path | ✅ memory_md_path 配置 | ✅ 存在 | 同步 |

### 2.2 LLM 客户端

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| Anthropic Client | ✅ 完整 | ⚠️ 仅接口定义 | **Python 更完善** |
| OpenAI Client | ✅ 完整（支持第三方兼容API） | ⚠️ 仅接口定义 | **Python 更完善** |
| Mock Client | ✅ MockHarness | ✅ MockHarness | 同步 |
| CPU Router | ✅ RoutingLLMClient + llama_cpp | ❌ 不存在 | **Python 独有** |
| model_presets | ✅ 完整（自动检测 provider、context_window） | ✅ ModelPresets 类 | 同步 |
| tool_result_role | ✅ 支持 "tool"/"user" 兼容模式 | ✅ 支持 "tool"/"user" 兼容模式 | 同步 |

### 2.3 配置系统

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| HarnessConfig | ✅ dataclass | ✅ record class | 同步 |
| RoutingConfig | ✅ 完整 | ❌ 不存在 | **Python 独有** |
| SecurityConfig | ✅ 完整 | ✅ 存在 | 同步 |
| CostControlConfig | ✅ 完整 | ✅ CostConfig | 同步 |
| ObservabilityConfig | ✅ OpenTelemetry | ✅ TracingConfig | 同步 |
| OffloadConfig | ✅ 完整 | ✅ 存在 | 同步 |
| StorageConfig | ✅ file/sqlite | ✅ FileSessionStore/SQLiteSessionStore | 同步 |
| context_window 自动解析 | ✅ "auto"/"32k"/"64k"/... | ❌ 硬编码 | **Python 更完善** |

### 2.4 Memory 系统

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| MemoryFileManager | ✅ 完整 | ✅ 完整 | 同步 |
| MemoryEntry | ✅ dataclass | ✅ record | 同步 |
| MemoryScoringConfig | ✅ decay_lambda, min_retrieval_strength | ❌ 不存在 | **Python 独有** |
| Retrieval Strength 计算 | ✅ calculate_retrieval_strength() | ❌ 不存在 | **Python 独有** |
| Archive 归档 | ✅ archive_low_importance() + MEMORY_ARCHIVE.md | ❌ 不存在 | **Python 独有** |
| ContextCompressor | ✅ 完整 | ✅ 存在 | 同步 |
| SystemPromptBuilder | ✅ 多源动态构建 | ✅ 存在 | 同步 |
| VectorMemoryStore | ✅ 可选 | ✅ 存在 | 同步 |
| SessionManager | ✅ 完整 | ✅ 存在 | 同步 |
| TokenCounter | ✅ tiktoken | ✅ 简单估算 | Python 更精确 |
| memory_md_path 目录处理 | ✅ 修复 (43cb54c) | ❓ 需验证 | Python 已修复 |

### 2.5 Tools 系统

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| Tool 基类 | ✅ 完整 | ✅ Tool interface | 同步 |
| ReadTool | ✅ 完整 | ✅ 完整 | 同步 |
| WriteTool | ✅ 完整 | ✅ 完整 | 同步 |
| EditTool | ✅ 完整 | ✅ 完整 | 同步 |
| BashTool | ✅ 完整 | ✅ 存在 | 同步 |
| GrepTool | ✅ 完整 | ✅ 完整 | 同步 |
| GlobTool | ❓ 需验证 | ✅ 完整 | 同步 |
| ToolExecutor | ✅ 完整 | ✅ Tool interface execute() | 同步 |
| ToolRegistry | ✅ 分类管理 | ✅ 存在 | 同步 |
| Permissions | ✅ PermissionSet | ❓ 需验证 | 同步 |
| Decorator 注册 | ✅ @agent.tool() | ❌ Java 不支持 | 语言差异 |

### 2.6 MCP 集成

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| McpManager | ✅ 完整 | ✅ 完整 | 同步 |
| McpClient | ✅ 完整 | ✅ 完整 | 同步 |
| StdioTransport | ✅ 完整 | ✅ 完整 | 同步 |
| HTTPTransport | ✅ 完整 | ✅ 完整 | 同步 |
| McpToolWrapper | ✅ 完整 | ✅ 完整 | 同步 |

### 2.7 Skills 系统

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| SkillLoader | ✅ 完整 | ✅ 完整 | 同步 |
| SkillRegistry | ✅ 完整 | ✅ 完整 | 同步 |
| SkillInjector | ✅ 完整 | ✅ 完整 | 同步 |
| ProgressiveSkill | ✅ 存在 | ❓ 需验证 | Python 可能更完善 |

### 2.8 Security 系统

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| InputValidator | ✅ 完整 | ✅ 完整 | 同步 |
| ResultSanitizer | ✅ 完整 | ✅ 完整 | 同步 |
| SandboxExecutor | ✅ 完整 | ✅ LightweightSandbox | 同步 |
| AuditLogger | ✅ 完整 | ✅ 完整 | 同步 |
| PromptInjectionDetector | ✅ 存在 | ✅ 完整 | 同步 |

### 2.9 Guardrails 系统

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| GuardrailHook | ✅ 完整 | ✅ 完整 | 同步 |
| PIIDetector | ✅ presidio-analyzer | ✅ 存在 | 同步 |
| ChinesePIIRecognizers | ✅ 完整 | ✅ 完整 | 同步 |
| ChineseNameRecognizer | ✅ 完整 | ✅ 完整 | 同步 |
| StreamInterceptor | ✅ 完整 | ✅ 存在 | 同步 |
| ComplianceJudge | ✅ 存在 | ✅ 存在 | 同步 |

### 2.10 Observability / Service

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| ObservabilityManager | ✅ 完整 | ⚠️ TracingManager 存在但未完全集成 | **Python 更完善** |
| MetricsCollector | ✅ Prometheus metrics | ✅ MetricsCollector | 同步 |
| Tracing | ✅ OpenTelemetry SpanBuilder | ✅ TraceContext | 同步 |
| Redis Session Store | ✅ AsyncSQLiteSessionStore | ⚠️ 存在但需验证 | 同步 |
| Spring Cloud 集成 | ✅ discovery.py, tracing.py | ❌ Java SDK 不含 Spring Cloud | Python 独有 |

### 2.11 Testing 系统

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| MockHarness | ✅ 完整 | ✅ MockHarness | 同步 |
| Recording | ✅ 完整 | ❓ 需验证 | 同步 |
| pytest_plugin | ✅ 完整 | ❌ JUnit 无插件 | 语言差异 |

### 2.12 Ralph Loop

| 功能 | Python SDK | Java SDK | 状态 |
|------|------------|----------|------|
| RalphLoopConfig | ✅ 内置 LoopConfig | ✅ 独立类 | 同步 |
| RalphLoopHook | ✅ hooks.py 中实现 | ✅ 独立类 | 同步 |
| ON_EXIT_ATTEMPT HookPoint | ✅ 完整 | ✅ 完整 | 同步 |

---

## 3. Python SDK 独有功能（需同步到 Java）

### 3.1 CPU Router (RoutingLLMClient)
**位置**: `packages/sdk/src/harness/llm/routing.py`

**功能**: 使用本地 CPU 模型（如 Qwen2.5-1.5B GGUF）作为路由器，根据任务复杂度分配到高级或基础模型，降低成本。

**关键代码**:
```python
class RoutingLLMClient(LLMClient):
    def __init__(self, config: RoutingConfig, high_client, low_client):
        self.router = self._create_router(config)
        self.high_client = high_client
        self.low_client = low_client

    async def call(self, messages, tools, system):
        complexity = await self.router.classify(messages)
        if complexity == "complex":
            return await self.high_client.call(...)
        else:
            return await self.low_client.call(...)
```

**Java SDK 需要**: 创建 `RoutingLLMClient` 类，支持 llama.cpp Java binding 或 HTTP 服务。

### 3.2 model_presets 自动检测
**位置**: `packages/sdk/src/harness/model_presets.py`

**功能**: 根据模型名称自动检测 provider、context_window、max_tokens。

**关键代码**:
```python
MODEL_PRESETS = {
    "claude-sonnet-4-6": ModelPreset(provider="anthropic", context_window=200000, max_tokens=16384),
    "gpt-4o": ModelPreset(provider="openai", context_window=128000, max_tokens=16384),
    ...
}
```

**Java SDK 已实现**: `ModelPresets` 类已创建，支持同样的自动检测逻辑。

### 3.3 tool_result_role 兼容模式
**位置**: `packages/sdk/src/harness/sdk/config.py` + `llm/anthropic.py`

**功能**: 某些代理 API（如 OpenAI-compatible）不支持 `tool` role，需要用 `user` role 发送 tool results。

**关键代码**:
```python
class HarnessConfig:
    tool_result_role: str = "tool"  # "tool" (native) or "user" (compatibility mode)
```

**Java SDK 已实现**: `HarnessConfig.toolResultRole` 已支持 "tool"/"user" 兼容模式。

### 3.4 Memory Scoring (Retrieval Strength)
**位置**: `packages/sdk/src/harness/memory/memory_file.py`

**功能**: 基于 Bjork's New Theory of Disuse 的记忆衰减和检索强度计算。

**关键代码**:
```python
class MemoryEntry:
    importance: float = 1.0           # Storage Strength
    last_accessed: datetime | None    # Last access time
    access_count: int = 0             # Access count

    def calculate_retrieval_strength(self, decay_lambda, min_strength):
        days_idle = (datetime.now() - self.last_accessed).days
        time_decay = min_strength + (1 - min_strength) * math.exp(-decay_lambda * days_idle)
        access_bonus = 1 + 0.5 * math.log(1 + self.access_count)
        return time_decay * access_bonus
```

**Java SDK 需要**: 在 `MemoryEntry` 中添加 importance、accessCount、lastAccessed 字段，并实现 retrieval strength 计算。

### 3.5 Archive 归档机制
**位置**: `packages/sdk/src/harness/memory/memory_file.py`

**功能**: 当 Core Memory 超过 token 限制时，自动归档低 importance 条目到 MEMORY_ARCHIVE.md 或 VectorStore。

**关键代码**:
```python
async def archive_low_importance(self, archive_callback=None):
    # Sort by importance (lowest first)
    all_entries.sort(key=lambda x: x["entry"].importance)

    # Archive to file or vector store
    for entry in all_entries:
        self._archive_to_file(entry)
        self.remove_entry(entry.category, entry.index)
```

**Java SDK 需要**: 在 `MemoryFileManager` 中实现 archive 逻辑和 MEMORY_ARCHIVE.md 文件处理。

### 3.6 Error Handler 完整策略
**位置**: `packages/sdk/src/harness/core/error_handler.py`

**功能**: 完整的错误处理策略（RETRY / COMPRESS_CONTEXT / ABORT），支持延迟、上下文压缩等。

**Java SDK 需要**: 完善 Java SDK 的 `ErrorHandler`，添加 COMPRESS_CONTEXT 等策略。

### 3.7 Tracing 集成到 AgentLoop
**位置**: `packages/sdk/src/harness/core/agent_loop.py`

**功能**: OpenTelemetry tracing 完整集成到 AgentLoop，支持 SpanBuilder、record_token_usage。

**关键代码**:
```python
if is_tracing():
    return await self._run_with_tracing(prompt, session, tools, on_chunk, on_progress)

with SpanBuilder("agent_loop.run") as span:
    span.set_attr("session.id", session.id)
    span.set_attr("model", self.llm.model_name)
    ...
```

**Java SDK 需要**: 在 `AgentLoop` 中集成 `TracingManager`。

### 3.8 Spring Cloud 集成
**位置**: `packages/sdk/src/harness/service/`

**功能**: 支持 Spring Cloud 微服务环境（Nacos/Eureka 发现、TraceContext传播、Prometheus指标）。

**Java SDK 需要**: 创建 `harness-sdk-spring` 模块，提供 Spring Cloud Starter。

---

## 4. Java SDK 独有功能（Python 可能需要）

暂无明显 Java SDK 独有功能需要同步到 Python。

---

## 5. 代码质量对比

| 维度 | Python SDK | Java SDK |
|------|------------|----------|
| 文档注释 | ✅ 完整 docstring | ✅ 完整 Javadoc |
| 类型系统 | ✅ dataclass + TYPE_CHECKING | ✅ record + interface |
| 测试覆盖 | ✅ pytest 完整 | ✅ JUnit 测试 |
| 模块化 | ✅ 单一 sdk 包 | ✅ 多模块 Gradle 项目 |
| 异步支持 | ✅ asyncio async/await | ✅ CompletableFuture |
| 错误处理 | ✅ 完整 Error Handler | ⚠️ 基础 |
| 可扩展性 | ✅ Hook 系统 | ✅ Hook 系统 |

---

## 6. 同步优先级

### P0 - 立即同步
1. **Memory Scoring + Archive** - 核心功能差异
2. **model_presets** - 配置便捷性
3. **tool_result_role** - 兼容性支持

### P1 - 近期同步
4. **Error Handler 完整策略** - 生产可靠性
5. **Tracing 集成到 AgentLoop** - Observability
6. **CPU Router** - 成本优化（可选）

### P2 - 长期规划
7. **Spring Cloud Starter** - Java SDK 专属模块
8. **Streaming backpressure** - 高级流控

---

## 7. 最近 Python SDK 更新（需关注）

| Commit | 说明 | Java 状态 |
|--------|------|-----------|
| 43cb54c | Fix: treat memory_md_path as directory in ContextBuilder | ❓ 需验证 |
| 6c9cf0c | Fix: support memory_md_path in UpdateCoreMemoryTool | ❓ 需验证 |
| e38791b | improve memory quality with content refinement and deduplication | ❌ 需同步 |
| 010cabd | add memory scoring and decay mechanism | ❌ 需同步 |
| 9db3695 | add CPU router for cost-optimized LLM routing | ❌ 需同步 |
| 82c7366 | add Guardrails module for PII detection | ✅ 已同步 |
| 4d3f26b | add Spring Cloud integration service module | ❌ Java SDK 需专属模块 |

---

## 8. 建议行动

1. **创建 Java SDK 同步任务清单**
2. **优先实现 Memory Scoring + Archive**
3. **创建 model_presets Java 类**
4. **添加 tool_result_role 支持**
5. **完善 Error Handler 策略**
6. **集成 Tracing 到 AgentLoop**
7. **考虑 RoutingLLMClient Java 实现**

---

## 附录: 文件对照表

| Python 文件 | Java 对应 | 同步状态 |
|-------------|----------|----------|
| `sdk/harness.py` | `integration/AgentHarness.java` | ✅ 同步 |
| `core/agent_loop.py` | `integration/AgentLoop.java` | ⚠️ 需完善 |
| `sdk/config.py` | `core/HarnessConfig.java` | ⚠️ 需完善 |
| `llm/base.py` | `core/LLMClient.java` | ✅ 同步 |
| `llm/anthropic.py` | ❌ 无实现 | ❌ 需创建 |
| `llm/openai.py` | ❌ 无实现 | ❌ 需创建 |
| `llm/routing.py` | ❌ 无 | ❌ 需创建 |
| `model_presets.py` | ❌ 无 | ❌ 需创建 |
| `memory/memory_file.py` | `memory/MemoryFileManager.java` | ⚠️ 需完善 |
| `memory/context_builder.py` | `core/ContextBuilder.java` | ⚠️ 需完善 |
| `tools/builtins.py` | `tools/*.java` | ✅ 同步 |
| `mcp/manager.py` | `mcp/McpManager.java` | ✅ 同步 |
| `skills/*.py` | `skills/*.java` | ✅ 同步 |
| `security/*.py` | `security/*.java` | ✅ 同步 |
| `guardrails/*.py` | `guardrails/*.java` | ✅ 同步 |
| `service/*.py` | ❌ 无 Spring Cloud 模块 | ❌ 需创建专属模块 |