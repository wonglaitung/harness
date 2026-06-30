# 03 - 工具系统详解

## 概述

工具系统让 LLM 能够"动手操作"——读取文件、执行命令、搜索代码、访问网络。工具系统是 Agent 能力的核心扩展机制。

## 架构

```
┌─────────────────────────────────────────────────┐
│                 Tool System                      │
│                                                  │
│  ┌─────────────┐  ┌──────────────┐              │
│  │  Tool Base  │  │Tool Registry │              │
│  │  (抽象类)    │  │  (注册管理)   │              │
│  └──────┬──────┘  └──────┬───────┘              │
│         │                │                       │
│         ↓                ↓                       │
│  ┌─────────────────────────────────────────┐    │
│  │           Tool Executor                  │    │
│  │  ┌──────────┐  ┌───────────────────┐    │    │
│  │  │ Sequential│  │ Batch (Parallel)  │    │    │
│  │  │ Execute  │  │ Execute           │    │    │
│  │  └──────────┘  └───────────────────┘    │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │          Built-in Tools (9)              │    │
│  │  Read │ Write │ Edit │ Glob │ Grep      │    │
│  │  Bash │ WebSearch │ WebFetch            │    │
│  │  WebToMarkdown                           │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │        Custom + MCP Tools                │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

## Tool 基类

```python
from harness.tools.base import Tool, ToolResult, ToolContext

class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（LLM 可见）"""

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（LLM 可见）"""

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """参数 JSON Schema"""

    @property
    def permission_level(self) -> PermissionLevel:
        """权限级别，默认 READ"""
        return PermissionLevel.READ

    @abstractmethod
    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        """执行工具并返回结果"""
```

### ToolResult

```python
@dataclass
class ToolResult:
    tool_call_id: str              # 工具调用ID（用于匹配LLM调用）
    success: bool                  # 是否成功执行
    content: str                   # 工具输出内容
    error: str | None = None       # 错误信息
    metadata: dict[str, Any] = field(default_factory=dict)  # 附加元数据

    def to_api_format(self) -> dict[str, Any]:
        """转换为API格式供LLM使用"""
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_call_id,
            "content": self.content if self.success else f"Error: {self.error}",
            "is_error": not self.success,
        }
```

### ToolContext

```python
@dataclass
class ToolContext:
    session_id: str                # 会话 ID
    working_directory: Path        # 当前工作目录
    permissions: PermissionSet     # 权限集合
    logger: Any | None = None      # 日志记录器
    metadata: dict[str, Any] = field(default_factory=dict)  # 附加上下文
```

### PermissionLevel

```python
class PermissionLevel(Enum):
    READ = "read"           # 只读操作（默认）
    WRITE = "write"         # 写入操作
    EXECUTE = "execute"     # 执行操作（如 Bash）
    NETWORK = "network"     # 网络访问
    DANGEROUS = "dangerous" # 危险操作（需确认）
```

## 内置工具

### Read - 文件读取

```python
class ReadTool(Tool):
    name = "read"
    description = "读取文件内容"
    permission_level = PermissionLevel.READ

    # 参数:
    #   file_path: str - 文件路径（必需）
    #   offset: int | None - 起始行号
    #   limit: int | None - 读取行数
```

### Write - 文件写入

```python
class WriteTool(Tool):
    name = "write"
    description = "创建或覆盖文件"
    permission_level = PermissionLevel.WRITE

    # 参数:
    #   file_path: str - 文件路径（必需）
    #   content: str - 文件内容（必需）
```

### Edit - 文件编辑

```python
class EditTool(Tool):
    name = "edit"
    description = "精确替换文件中的字符串"
    permission_level = PermissionLevel.WRITE

    # 参数:
    #   file_path: str - 文件路径（必需）
    #   old_string: str - 要替换的字符串（必需）
    #   new_string: str - 替换后的字符串（必需）
    #   replace_all: bool - 是否替换所有匹配（默认 False）
```

### Glob - 文件搜索

```python
class GlobTool(Tool):
    name = "glob"
    description = "按模式搜索文件名"
    permission_level = PermissionLevel.READ

    # 参数:
    #   pattern: str - glob 模式（必需）
    #   path: str | None - 搜索目录
```

### Grep - 内容搜索

```python
class GrepTool(Tool):
    name = "grep"
    description = "搜索文件内容（支持正则表达式）"
    permission_level = PermissionLevel.READ

    # 参数:
    #   pattern: str - 正则表达式（必需）
    #   path: str | None - 搜索路径
    #   include: str | None - 文件名过滤（如 "*.py"）
    #   output_mode: str - "content" | "files_with_matches" | "count"
```

### Bash - 命令执行

```python
class BashTool(Tool):
    name = "bash"
    description = "在沙箱中执行 shell 命令"
    permission_level = PermissionLevel.EXECUTE

    # 参数:
    #   command: str - 要执行的命令（必需）
    #   timeout: int | None - 超时时间（毫秒，默认 30000）
    #   working_dir: str | None - 工作目录
```

### WebSearch - 网络搜索

```python
class WebSearchTool(Tool):
    name = "web_search"
    description = "搜索互联网获取信息"
    permission_level = PermissionLevel.NETWORK

    # 参数:
    #   query: str - 搜索查询（必需）
    #   max_results: int - 最大结果数（默认 5）
```

### WebFetch - 网页获取

```python
class WebFetchTool(Tool):
    name = "web_fetch"
    description = "获取网页内容"
    permission_level = PermissionLevel.NETWORK

    # 参数:
    #   url: str - URL（必需）
    #   format: str - "text" | "markdown" | "html"
```

### WebToMarkdown - 网页转 Markdown

```python
class WebToMarkdownTool(Tool):
    name = "web_to_markdown"
    description = "获取网页并转换为干净的 Markdown 格式"
    permission_level = PermissionLevel.NETWORK

    # 参数:
    #   url: str - 网页 URL（必需）
    #   selector: str | None - CSS 选择器提取特定内容
    #   max_length: int - 最大内容长度（默认 50000）
    #   include_links: bool - 是否保留链接（默认 True）
    #   include_images: bool - 是否包含图片引用（默认 False）

    # 特性:
    #   - 提取主要内容（article, main, body）
    #   - 保留代码块、表格、列表、标题
    #   - 自动移除广告、导航、页脚
    #   - 支持 BeautifulSoup 解析
```

## ToolExecutor

ToolExecutor 负责工具的调度和执行，支持串行和并行模式。

```python
from harness.tools.executor import ToolExecutor

class ToolExecutor:
    def __init__(
        self,
        tools: dict[str, Tool],   # 工具注册表
        sandbox: Sandbox,          # 沙箱实例
        permissions: PermissionSet,# 权限集合
    )

    async def execute(
        self,
        tool_name: str,
        args: dict,
        ctx: ToolContext,
    ) -> ToolResult:
        """执行单个工具"""

    async def execute_batch(
        self,
        calls: list[dict],   # [{"name": ..., "arguments": ...}]
        ctx: ToolContext,
    ) -> list[ToolResult]:
        """并行执行多个独立工具调用"""

    async def execute_sequential(
        self,
        calls: list[dict],
        ctx: ToolContext,
    ) -> list[ToolResult]:
        """串行执行多个工具调用（有依赖时使用）"""
```

### 执行流程

```
Tool Call(s)
    │
    ↓
┌─────────────┐
│ 权限检查     │ → 拒绝 → 返回 ToolResult(error="Permission denied")
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ 参数验证     │ → 失败 → 返回 ToolResult(error="Invalid arguments")
└──────┬──────┘
       │
       ↓
┌─────────────────────┐
│ 单个调用 → execute  │
│ 多个调用 → batch   │  （并行执行独立调用）
└──────┬──────────────┘
       │
       ↓
┌─────────────┐
│ 沙箱执行     │ → 超时 → 返回 ToolResult(error="Timeout")
└──────┬──────┘
       │
       ↓
   ToolResult
```

## 自定义工具

### 方式 1：继承 Tool 类

```python
from harness.tools.base import Tool, ToolResult, ToolContext, PermissionLevel

class DatabaseQueryTool(Tool):
    @property
    def name(self) -> str:
        return "db_query"

    @property
    def description(self) -> str:
        return "执行数据库查询"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL 查询"},
                "database": {"type": "string", "description": "数据库名"},
            },
            "required": ["query"],
        }

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.DANGEROUS

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        query = args["query"]
        db = args.get("database", "default")
        try:
            result = await execute_sql(db, query)
            return ToolResult(output=str(result))
        except Exception as e:
            return ToolResult(output="", error=str(e))

# 注册
agent = AgentHarness()
agent.register_tool(DatabaseQueryTool())
```

### 方式 2：装饰器

```python
agent = AgentHarness()

@agent.tool(description="计算两个数的和")
def add(a: int, b: int) -> int:
    return a + b

@agent.tool(
    description="发送 HTTP 请求",
    permission_level="network",
)
async def http_request(url: str, method: str = "GET") -> str:
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url) as resp:
            return await resp.text()
```

## 工具与 MCP 的关系

内置工具和 MCP 工具统一通过 ToolExecutor 调度：

| 工具来源 | 注册方式 | 权限控制 |
|----------|----------|----------|
| 内置工具 | 自动注册 | 按 PermissionLevel |
| 自定义工具 | `register_tool()` | 按 PermissionLevel |
| MCP 工具 | MCP 服务器自动注册 | 按 MCP 配置 |

```python
# MCP 工具和内置工具统一使用
agent = AgentHarness()
agent.add_mcp_server("github", command="mcp-github")

# LLM 可以同时调用内置工具和 MCP 工具
result = await agent.run("搜索代码中的 TODO 并在 GitHub 创建 issue")
```

## 下一步

- [04-memory-system.md](./04-memory-system.md) - 了解记忆系统
- [05-skills-system.md](./05-skills-system.md) - 了解技能系统
- [09-mcp-integration.md](./09-mcp-integration.md) - MCP 协议集成
