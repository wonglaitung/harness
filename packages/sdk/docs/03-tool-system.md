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
│  │          Built-in Tools (17)             │    │
│  │  Read │ Write │ Edit │ Glob │ Grep      │    │
│  │  Bash │ WebSearch │ WebFetch            │    │
│  │  WebToMarkdown │ UpdateCoreMemory       │    │
│  │  BrowserNavigate │ BrowserClick         │    │
│  │  BrowserType │ BrowserExtract           │    │
│  │  BrowserScreenshot │ BrowserWait        │    │
│  │  BrowserClose                            │    │
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

### UpdateCoreMemoryTool - 长期记忆更新

更新 MEMORY.md 中的结构化条目，将用户偏好、项目约定等持久化到长期记忆。

```python
from harness.tools.builtins import UpdateCoreMemoryTool

tool = UpdateCoreMemoryTool()

# 添加记忆
result = await tool.execute({
    "category": "user_profile",
    "content": "Shell：使用 cmd（不使用 PowerShell）",
    "action": "add",
}, context)

# 移除记忆
result = await tool.execute({
    "category": "learned_patterns",
    "content": "回复风格：简洁",
    "action": "remove",
}, context)
```

#### 输入参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `category` | enum | 是 | 记忆类别：`user_profile`、`key_decisions`、`learned_patterns`、`project_context` |
| `content` | string | 是 | 记忆内容（应为提炼后的简洁陈述） |
| `action` | enum | 是 | 操作：`add`（添加）或 `remove`（移除） |

#### 记忆类别

| 类别 | 用途 | 示例 |
|------|------|------|
| `user_profile` | 用户偏好和环境信息 | "操作系统：Windows"、"主题偏好：深色" |
| `key_decisions` | 重要决策记录 | "框架选择：Next.js"、"数据库：PostgreSQL" |
| `learned_patterns` | 交互习惯 | "回复风格：简洁"、"语言：中文" |
| `project_context` | 项目约定 | "分支策略：GitFlow"、"部署方式：Docker" |

#### 内容提炼规则

- 不要存储用户原话，要提炼成简洁陈述
- 用户说「使用 cmd，不要用 powershell」→ 存储「Shell：使用 cmd（不使用 PowerShell）」
- 用户说「我使用 Windows」→ 存储「操作系统：Windows」
- 添加前先检查是否已有类似记忆，避免重复

#### 与 MemoryFileManager 集成

工具内部通过 `MemoryFileManager` 管理 MEMORY.md 文件：

```python
# 工具自动处理路径解析
# 优先级：context.metadata["memory_md_path"] → ~/.harness/
from harness.memory.memory_file import MemoryFileManager, MemoryEntry, MemoryCategory

manager = MemoryFileManager(project_root=Path("~/.harness"))
entry = MemoryEntry(
    category=MemoryCategory.USER_PROFILE,
    content="主题偏好：深色",
    source=MemorySource.USER_INPUT,
)
manager.add_entry(entry)  # 自动去重
```

添加成功后返回 `metadata={"refresh_memory": True}`，UI 可据此刷新记忆显示。

> **下一步**：了解记忆系统的完整架构，参见 [04-memory-system.md](./04-memory-system.md)。

## 浏览器自动化工具

基于 Playwright 的确定性浏览器自动化工具集，专为需要精确控制的场景设计（如金融/银行操作）。

### 特性

- **内网/离线支持**: 使用系统 Edge/Chrome，无需下载 Playwright 浏览器
- **XPath + CSS 选择器**: 支持两种选择器语法
- **自动等待**: 工具自动等待元素可见/可点击
- **重试机制**: 点击操作支持自动重试
- **截图审计**: 可选的每步操作自动截图

### BrowserManager 单例管理器

管理 Playwright 浏览器实例的生命周期，确保所有工具共享同一浏览器。

```python
from harness.tools.browser import BrowserManager

# 配置浏览器
BrowserManager.configure(
    headless=True,
    browser_type="msedge",  # 使用系统 Edge（内网友好）
    auto_screenshot=True,
)

# 检测系统可用浏览器
browser = BrowserManager.detect_available_browser()
# 返回: "msedge" | "chrome" | "chromium" | None

# 一键配置系统浏览器（内网环境推荐）
if BrowserManager.use_system_browser():
    print("已配置系统浏览器，无需下载")

# 获取页面实例
page = await BrowserManager.get_page()

# 关闭浏览器
await BrowserManager.close()
```

#### 浏览器类型

| 类型 | 说明 | 需要下载 |
|------|------|----------|
| `chromium` | Playwright 内置 Chromium | 是 (`playwright install`) |
| `firefox` | Playwright 内置 Firefox | 是 |
| `webkit` | Playwright 内置 WebKit | 是 |
| `msedge` | 系统 Microsoft Edge | **否**（内网推荐） |
| `chrome` | 系统 Google Chrome | **否** |

### BrowserNavigateTool

导航到 URL 并等待页面加载。

```python
from harness.tools.browser import BrowserNavigateTool

tool = BrowserNavigateTool()

result = await tool.execute({
    "url": "https://example.com",
    "wait_until": "load",  # load | domcontentloaded | networkidle
    "timeout": 30000,
}, context)
```

### BrowserClickTool

点击页面元素，支持自动等待和重试。

```python
from harness.tools.browser import BrowserClickTool

tool = BrowserClickTool()

# CSS 选择器
result = await tool.execute({
    "selector": "#submit-btn",
    "timeout": 10000,
    "retry_count": 2,
}, context)

# XPath 选择器
result = await tool.execute({
    "selector": "//button[text()='Submit']",
}, context)
```

### BrowserTypeTool

在输入框中输入文本。

```python
from harness.tools.browser import BrowserTypeTool

tool = BrowserTypeTool()

result = await tool.execute({
    "selector": "#username",
    "text": "myusername",
    "clear_first": True,  # 先清空
    "delay": 50,  # 每个字符延迟（毫秒）
}, context)
```

### BrowserExtractTool

提取页面数据（文本或属性）。

```python
from harness.tools.browser import BrowserExtractTool

tool = BrowserExtractTool()

# 提取文本
result = await tool.execute({
    "selector": ".article-content",
}, context)

# 提取属性
result = await tool.execute({
    "selector": "a.download-link",
    "attribute": "href",
}, context)

# 提取多个元素
result = await tool.execute({
    "selector": "li.item",
    "multiple": True,
}, context)
```

### BrowserScreenshotTool

截取页面或元素的截图。

```python
from harness.tools.browser import BrowserScreenshotTool

tool = BrowserScreenshotTool()

# 整页截图
result = await tool.execute({
    "full_page": True,
}, context)

# 元素截图
result = await tool.execute({
    "selector": "#chart",
}, context)

# 返回 base64
result = await tool.execute({
    "return_base64": True,
}, context)
```

### BrowserWaitTool

等待页面条件（元素、URL、超时）。

```python
from harness.tools.browser import BrowserWaitTool

tool = BrowserWaitTool()

# 等待元素出现
result = await tool.execute({
    "wait_type": "selector",
    "selector": "#loading",
    "state": "hidden",  # visible | hidden | attached | detached
}, context)

# 等待 URL 变化
result = await tool.execute({
    "wait_type": "url",
    "url_pattern": "**/success",
}, context)

# 等待超时
result = await tool.execute({
    "wait_type": "timeout",
    "timeout_ms": 1000,
}, context)
```

### BrowserCloseTool

关闭浏览器实例。

```python
from harness.tools.browser import BrowserCloseTool

tool = BrowserCloseTool()
result = await tool.execute({}, context)
```

### get_browser_tools() 工厂函数

返回所有浏览器工具的列表，方便一次性注册：

```python
from harness.tools.browser import get_browser_tools

# 返回 7 个工具实例:
# [
#   BrowserNavigateTool(),
#   BrowserClickTool(),
#   BrowserTypeTool(),
#   BrowserExtractTool(),
#   BrowserScreenshotTool(),
#   BrowserWaitTool(),
#   BrowserCloseTool(),
# ]
tools = get_browser_tools()

# 直接用于 AgentHarness
from harness import AgentHarness

agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=get_browser_tools(),
)

result = await agent.run("""
1. 打开 https://example.com/login
2. 输入用户名和密码
3. 点击登录
4. 截取结果页面
""")
```

### 安装

```bash
# 安装 Playwright 库
pip install harness-sdk[browser]

# 下载浏览器（如使用内置 Chromium/Firefox/WebKit）
playwright install

# 使用系统浏览器则无需 playwright install
# BrowserManager.use_system_browser() 会自动检测
```

### 内网环境部署

```python
# 方式 1：自动检测系统浏览器
BrowserManager.use_system_browser()

# 方式 2：手动指定 Edge
BrowserManager.configure(browser_type="msedge")

# 方式 3：手动指定 Chrome
BrowserManager.configure(browser_type="chrome")
```

**注意**: 使用系统浏览器需要安装 Playwright 库，但不需要 `playwright install` 下载浏览器。

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
| MCP 工具 | `add_mcp_server()` 自动注册 | 按 MCP 配置 |

```python
# MCP 工具和内置工具统一使用
from harness import AgentHarness, ReadTool

agent = AgentHarness(tools=[ReadTool()])

# 添加 MCP 服务器（异步方法，自动连接并注册工具）
info = await agent.add_mcp_server("github", command="mcp-github")

# 查看所有工具（内置 + MCP）
all_tools = agent._tool_registry.list_tools()
print(f"可用工具: {[t.name for t in all_tools]}")

# LLM 可以同时调用内置工具和 MCP 工具
result = await agent.run("搜索代码中的 TODO 并在 GitHub 创建 issue")
```

### MCP 工具管理方法

```python
# 列出已连接的 MCP 服务器
servers = agent.list_connected_mcp_servers()

# 获取指定服务器的工具
github_tools = agent.get_mcp_server_tools("github")

# 获取所有 MCP 工具
all_mcp_tools = agent.get_all_mcp_tools()

# 断开服务器
await agent.disconnect_mcp_server("github")
```

详见 [07-sdk-api.md](./07-sdk-api.md) 的 MCP 方法章节。

### MCP 操作日志

SDK 提供详细的 MCP 操作日志，便于调试连接问题和跟踪工具可用性：

#### 日志位置

| 组件 | 文件 | 日志内容 |
|------|------|----------|
| MCP Client | `harness/mcp/client.py` | 工具发现、工具调用、断开连接 |
| MCP Manager | `harness/mcp/manager.py` | 服务器连接/断开、工具注册/注销 |
| MCP Controller | `harness_client/controllers/mcp_controller.py` | 客户端连接/断开操作 |

#### 日志示例

```
# 服务器连接
INFO - MCP server 'github' connected with 5 tools: ['search_repos', 'create_issue', ...]

# 工具发现
DEBUG - MCP tool discovered: mcp_github_search_repos

# 工具调用
DEBUG - MCP tool call: mcp_github_search_repos(args={'query': 'todo'})

# 服务器断开
INFO - MCP server 'github' disconnected
```

#### 启用详细日志

```python
import logging

# 启用 MCP 模块详细日志
logging.getLogger("harness.mcp").setLevel(logging.DEBUG)
logging.getLogger("harness_client.mcp_controller").setLevel(logging.DEBUG)
```

#### 日志用途

- **调试连接问题**：查看服务器是否成功连接、工具是否正确发现
- **跟踪工具可用性**：监控工具的注册和注销
- **性能分析**：分析工具调用耗时

## 下一步

- [04-memory-system.md](./04-memory-system.md) - 了解记忆系统
- [05-skills-system.md](./05-skills-system.md) - 了解技能系统
- [08-security.md](./08-security.md) - 浏览器工具安全注意事项
- [09-mcp-integration.md](./09-mcp-integration.md) - MCP 协议集成
