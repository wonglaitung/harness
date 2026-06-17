# 10 - Python SDK 对比分析

## 概述

本文档对比 Python SDK 和 Java SDK 的设计差异，帮助理解两个版本的特点。

## 架构对比

| 层级 | Python SDK | Java SDK |
|------|-----------|----------|
| 入口类 | `AgentHarness` | `Harness` |
| 配置类 | `HarnessConfig` (pydantic) | `HarnessConfig` (record) |
| 循环引擎 | `AgentLoop` (async) | `AgentLoop` (CompletableFuture) |
| 工具接口 | `Tool` (abstract class) | `Tool` (interface) |
| LLM 客户端 | `LLMClient` (ABC) | `LLMClient` (interface) |
| MCP 客户端 | `McpClient` (mcp lib) | `HarnessMcpClient` (mcp-java-sdk) |

## 异步模型对比

### Python asyncio

```python
# Python SDK
async def run(self, prompt: str) -> LoopResult:
    while iteration < self.max_iterations:
        # 构建上下文
        context = await self.context_builder.build(self.session)

        # 调用 LLM
        response = await self.llm_client.call(context)

        # 执行工具
        results = await self.tool_executor.execute_all(response.tool_calls)

        iteration += 1
```

### Java CompletableFuture

```java
// Java SDK
public CompletableFuture<LoopResult> runAsync(String prompt) {
    return CompletableFuture.supplyAsync(() -> {
        while (iteration < config.maxIterations()) {
            // 构建上下文
            Context context = contextBuilder.build(session);

            // 调用 LLM
            LlmResponse response = llmClient.call(context);

            // 执行工具
            List<ToolResult> results = toolExecutor.executeAll(response.toolCalls());

            iteration++;
        }
        return LoopResult.completed(...);
    });
}
```

### 关键差异

| 特性 | Python | Java |
|------|--------|------|
| 异步关键字 | `async/await` | `CompletableFuture` |
| 并发模型 | 协程 | 线程池 |
| 流式处理 | `async for` | `subscribe` 回调 |
| 错误处理 | `try/except` | `exceptionally` |

## 数据模型对比

### Python pydantic

```python
# Python SDK
from pydantic import BaseModel, Field
from typing import List, Optional

class Message(BaseModel):
    role: str
    content: str
    metadata: dict = Field(default_factory=dict)

class LoopResult(BaseModel):
    state: LoopState
    session: Session
    content: Optional[str] = None
    iterations: int
    token_usage: TokenUsage
    error: Optional[str] = None
```

### Java Record

```java
// Java SDK
public record Message(
    String role,
    String content,
    Map<String, Object> metadata
) {
    public static Message user(String content) {
        return new Message("user", content, Map.of());
    }
}

public record LoopResult(
    LoopState state,
    Session session,
    String content,
    int iterations,
    TokenUsage tokenUsage,
    String error
) {
    public boolean isCompleted() {
        return state == LoopState.COMPLETED;
    }
}
```

### 关键差异

| 特性 | Python | Java |
|------|--------|------|
| 定义方式 | `@dataclass` 或 `BaseModel` | `record` |
| 默认值 | `Field(default=...)` | 构造器参数 |
| 验证 | pydantic 自动验证 | 手动或 Jackson |
| 可变性 | 默认可变 | 不可变（需用 `with` 方法） |

## 工具系统对比

### Python 工具定义

```python
# Python SDK
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def input_schema(self) -> dict: ...

    @abstractmethod
    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult: ...

    def validate_arguments(self, args: dict) -> tuple[bool, str | None]:
        return True, None  # 默认使用 jsonschema

# 装饰器方式
@agent.tool(description="计算两个数的和")
def add(a: int, b: int) -> int:
    return a + b
```

### Java 工具定义

```java
// Java SDK
public interface Tool {
    String name();
    String description();
    Map<String, Object> inputSchema();
    CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context);

    default ValidationResult validate(Map<String, Object> args) {
        return ValidationResult.valid();
    }
}

// 类实现
public class AddTool implements Tool {
    @Override
    public String name() { return "add"; }

    @Override
    public String description() { return "计算两个数的和"; }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "a", Map.of("type", "integer"),
                "b", Map.of("type", "integer")
            ),
            "required", List.of("a", "b")
        );
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext ctx) {
        int a = ((Number) args.get("a")).intValue();
        int b = ((Number) args.get("b")).intValue();
        return CompletableFuture.completedFuture(ToolResult.success(String.valueOf(a + b)));
    }
}
```

### 关键差异

| 特性 | Python | Java |
|------|--------|------|
| 定义方式 | ABC 或装饰器 | interface 实现 |
| 参数类型推断 | 自动（签名） | 手动 Schema |
| 执行方式 | `async def` | `CompletableFuture` |
| 验证方式 | jsonschema 库 | JsonSchemaValidator |

## MCP 集成对比

### Python MCP

```python
# Python SDK
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="mcp-server-filesystem",
    args=["--root", "/workspace"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("read_file", {"path": "README.md"})
```

### Java MCP

```java
// Java SDK
McpConfig config = McpConfig.builder()
    .transport(McpTransport.STDIO)
    .command("mcp-server-filesystem")
    .args(List.of("--root", "/workspace"))
    .build();

HarnessMcpClient client = new HarnessMcpClient("filesystem", config);
client.connect().join();

List<McpToolInfo> tools = client.listTools().join();
McpToolResult result = client.callTool("read_file", Map.of("path", "README.md")).join();

client.disconnect().join();
```

### 关键差异

| 特性 | Python | Java |
|------|--------|------|
| SDK 来源 | `mcp` Python 包 | `mcp-java-sdk` |
| 连接管理 | `async with` 上下文 | 手动 `connect/disconnect` |
| 调用方式 | `await` | `.join()` 或回调 |
| 工具包装 | `MCPToolWrapper` | `McpToolWrapper` |

## 记忆系统对比

### Python 记忆系统

```python
# Python SDK
from harness.memory import MemoryManager, Memory

memory_manager = MemoryManager(
    memory_dir=Path.home() / ".harness",
    memory_md_path=Path.home() / ".harness" / "MEMORY.md"
)

# 添加记忆
memory_manager.add_user_memory(
    name="user_role",
    description="用户角色",
    content="用户是高级 Python 开发者"
)

# Token 计数
from tiktoken import encoding_for_model
encoding = encoding_for_model("gpt-4")
token_count = len(encoding.encode(text))
```

### Java 记忆系统

```java
// Java SDK
Path memoryDir = Path.of(System.getProperty("user.home"), ".harness");
MemoryManager memoryManager = new MemoryManager(memoryDir, memoryDir.resolve("MEMORY.md"));

// 添加记忆
memoryManager.addUserMemory(
    "user_role",
    "用户角色",
    "USER",
    "用户是高级 Java 开发者"
);

// Token 计数
import com.knuddelsgmbh.jtokkit.api.EncodingType;
Encoding encoding = registry.getEncoding(EncodingType.CL100K_BASE);
int tokenCount = encoding.encode(text).size();
```

### 关键差异

| 特性 | Python | Java |
|------|--------|------|
| Token 计数库 | `tiktoken` | `jtokkit` |
| 编码类型 | 动态（按模型） | 固定（cl100k_base） |
| 精度 | 高精度 | 可能有细微差异 |
| 记忆存储 | 同步 | 可异步 |

## 安全模块对比

### Python 安全

```python
# Python SDK
from harness.security import SandboxExecutor, InputValidator

class SandboxExecutor:
    def __init__(self, work_dir, read_only_paths, read_write_paths):
        ...

    async def execute(self, command: str) -> CommandResult:
        ...

class InputValidator:
    def validate(self, input: str) -> ValidationResult:
        ...
```

### Java 安全

```java
// Java SDK
SandboxExecutor sandbox = new SandboxExecutor(
    workDir,
    readOnlyPaths,
    readWritePaths,
    deniedPaths,
    defaultTimeout
);

CompletableFuture<CommandResult> result = sandbox.execute(command);

InputValidator validator = new DefaultInputValidator(config);
ValidationResult validation = validator.validate(input);
```

### 关键差异

| 特性 | Python | Java |
|------|--------|------|
| 执行方式 | `async` | `CompletableFuture` |
| 沙箱实现 | Python 层限制 | JVM 层限制 |
| 验证模式 | 类继承 | 接口实现 |

## 性能对比

| 指标 | Python | Java |
|------|--------|------|
| 启动时间 | 快 | 较慢（JVM 启动） |
| 执行速度 | 中 | 高 |
| 内存占用 | 低 | 较高 |
| 并发能力 | 协程（高） | 线程池（中） |
| GC 影响 | 无 | 有 |

## 适用场景对比

| 场景 | 推荐 | 原因 |
|------|------|------|
| 快速原型开发 | Python | 简洁、动态类型 |
| 生产环境部署 | Java | 稳定、高性能 |
| 银行系统集成 | Java | 企业级支持 |
| 跨平台桌面应用 | Python | PyQt6 生态 |
| 大规模并发 | Python | asyncio 协程 |

## API 命名对比

| Python | Java |
|--------|------|
| `AgentHarness` | `Harness` |
| `run()` | `run()` / `runAsync()` |
| `stream()` | `stream()` |
| `add_tool()` | `registerTool()` |
| `add_hook()` | `addHook()` |
| `interrupt()` | `interrupt()` |

## 维护策略

### Python 主导

- **新功能**: 先在 Python SDK 实现
- **API 设计**: Python API 作为参考
- **文档**: Python 文档为主

### Java 同步

- **核心功能**: 与 Python 保持一致
- **Java 特性**: 利用 Java 生态优势
- **版本同步**: 大版本号保持一致

### 版本对照

| Python 版本 | Java 版本 | 状态 |
|-------------|----------|------|
| 1.0.0 | 1.0.0 | 开发中 |

## 下一步

- [11-testing.md](./11-testing.md) - 测试策略
- [13-production-readiness.md](./13-production-readiness.md) - 生产就绪检查