# Harness SDK Java

可内嵌的 AI Agent Harness 框架 - Java 实现

## 项目状态

✅ **Phase 3 完成** - MCP 集成已实现

## 模块结构

```
harness-sdk-java/
├── harness-sdk-core/      # 核心模块（类型定义、AgentLoop）
├── harness-sdk-llm/       # LLM 客户端（Anthropic、OpenAI）
├── harness-sdk-mcp/       # MCP 协议集成（STDIO、SSE）
├── harness-sdk-tools/     # 内置工具（Read, Write, Edit, Bash, Glob, Grep）
├── harness-sdk-memory/    # 记忆系统（MEMORY.md 管理）
├── harness-sdk-skills/    # 技能系统（Skill 加载）
├── harness-sdk-security/  # 安全模块（沙箱、验证、审计）
└── harness-sdk-all/       # 聚合模块（Shadow JAR）
```

## 核心组件

### harness-sdk-core
- **类型定义**: Message, Session, ToolCall, ToolResult, LLMResponse, LoopResult
- **AgentLoop**: ReAct 执行引擎，支持：
  - LLM 重试：配置化重试次数 + 指数退避 + 随机抖动
  - 工具超时：`timeoutPerTool` 强制超时保护
  - 智能错误处理：`ErrorHandler` 根据错误类型智能决策
  - 熔断器：`CircuitBreaker` 检测相同工具+参数重复调用
  - 步骤预算：`StepBudgetController` 限制迭代和工具调用次数
  - 成本控制：`CostController` 多级预算管理（Session/User/Global）
  - 停滞检测：`StuckDetector` 语义相似度检测重复输出
  - 中断支持：可中断正在执行的循环
- **生命周期钩子**:
  - `HookPoint`: 钩子触发点（LLM 调用前后、工具执行前后等）
  - `HookAction`: 钩子动作（CONTINUE、ABORT、RETRY、INJECT_MESSAGE 等）
  - `HookContext`: 钩子上下文
  - `HookResult`: 钩子返回结果
- **流式处理**:
  - `StreamingHandler`: 流式输出处理，支持背压控制
  - `Chunk`/`ChunkType`: 流式块类型定义
- **进度事件**: `ProgressEvent`, `ProgressEventType` 跟踪 Agent 执行进度
- **成本控制**: `CostConfig`, `BudgetStatus`, `UserBudgetStatus`, `GlobalBudgetStatus`
- **MetricsCollector**: Prometheus 指标收集器，支持迭代、工具调用、Token 使用追踪
- **TracingManager**: OpenTelemetry 追踪管理器，支持 W3C TraceContext 传播
- **TracingFilter**: HTTP 过滤器，支持 Spring Cloud Gateway 集成
- **RalphLoopHook**: 长任务循环续接，防止上下文焦虑导致的提前退出
- **LifecycleHook**: 生命周期钩子接口
- **OutputOffloader**: 大输出卸载到临时文件，保护上下文窗口
- **PermissionSet**: 细粒度权限控制（路径、命令、网络）
- **MockHarness**: 完整测试 Harness，支持预定义响应
- **Tool 接口**: 工具抽象类，支持验证和异步执行
- **TokenCounter**: 基于 jtokkit 的 Token 计数
- **LoopConfig**: 循环配置，支持 Builder 模式

### harness-sdk-llm
- **AnthropicClient**: Claude API 客户端，支持自定义 baseUrl
- **OpenAIClient**: OpenAI/兼容 API 客户端
- **MockLLMClient**: 测试用 Mock 客户端，支持预定义响应

### harness-sdk-mcp
- **McpManager**: MCP 服务器管理器，支持多服务器连接
- **McpServerConfig**: 服务器配置（STDIO/SSE 传输）
- **McpToolWrapper**: MCP 工具包装器，适配 Harness Tool 接口
- **McpToolInfo**: MCP 工具元数据

### harness-sdk-tools
- **ReadTool**: 文件读取，支持行号、图片
- **WriteTool**: 文件写入
- **EditTool**: 文本替换
- **BashTool**: Shell 命令执行
- **GlobTool**: 文件模式匹配
- **GrepTool**: 内容搜索
- **UpdateCoreMemoryTool**: Agent 自主更新 Core Memory，支持内容提炼和去重

### harness-sdk-memory
- **MemoryFileManager**: MEMORY.md 文件管理，支持字符级去重检测
- **MemoryCategory**: 记忆类别枚举，支持 `getValue()` / `fromValue()` 方法
- **MemoryEntry**: 记忆条目
- **SessionManager**: 会话持久化
- **ContextCompressor**: 上下文压缩器，支持消息摘要和保留最近消息
- **CompressionConfig**: 压缩配置
- **CompressionResult**: 压缩结果
- **SystemPromptBuilder**: 动态系统提示组装，支持 AGENTS.md/MEMORY.md
- **SystemPromptConfig**: 系统提示配置
- **SystemPromptSource**: 系统提示源

### harness-sdk-skills
- **SkillRegistry**: 技能文件加载和管理
- **Skill**: 技能定义
- **SkillMetadata**: 技能元数据（描述、版本、工具、触发器）
- **SkillLoader**: 技能文件加载器，支持多路径搜索和自动发现
- **SkillInjector**: 技能注入器，将匹配的技能注入系统提示
- **InjectionConfig**: 注入配置

### harness-sdk-security
- **InputValidator**: 输入验证，检测注入模式
- **PromptInjectionDetector**: Prompt 注入检测
- **FileInputValidator**: 文件路径验证
- **SandboxExecutor**: 沙箱执行器
- **LightweightSandbox**: 轻量级沙箱
- **AuditLogger**: 审计日志
- **ResultSanitizer**: 输出脱敏

## 构建

```bash
# 构建所有模块
./gradlew build

# 构建 Shadow JAR
./gradlew :harness-sdk-all:shadowJar
```

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| anthropic-java | 2.40.1 | Anthropic Claude API |
| openai-java | 4.39.1 | OpenAI 兼容 API |
| mcp-java-sdk | 0.5.0 | MCP 协议 |
| jtokkit | 1.0.0 | Token 计数 |
| jackson | 2.17.0 | JSON 处理 |
| slf4j | 2.0.0 | 日志接口 |

## 文档

详细设计文档请见 [docs/](docs/) 目录。