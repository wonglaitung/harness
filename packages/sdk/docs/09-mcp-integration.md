# 09 - MCP 集成详解

## 概述

MCP (Model Context Protocol) 允许 Harness 连接外部工具服务器，扩展 Agent 的能力边界。通过 MCP，Agent 可以使用 GitHub、Slack、数据库等第三方服务提供的工具。

## 安装依赖

使用 MCP 功能需要安装 `mcp` 包：

```bash
# 作为 SDK 依赖自动安装
uv sync --all-packages

# 或手动安装
pip install mcp>=1.0.0
```

SDK 的 `pyproject.toml` 已包含 `mcp>=1.0.0` 依赖。

## 架构

```
┌─────────────────────────────────────────────────┐
│              MCP Integration                     │
│                                                  │
│  ┌───────────────┐  ┌───────────────────┐       │
│  │  MCPManager   │  │  MCP Transport    │       │
│  │ (服务器管理)   │  │ (通信传输)         │       │
│  └───────┬───────┘  └───────┬───────────┘       │
│          │                  │                    │
│          ↓                  ↓                    │
│  ┌─────────────────────────────────────────┐    │
│  │           MCP Servers                    │    │
│  │  GitHub │ Slack │ Database │ Custom     │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  MCP 工具自动注册到 ToolExecutor                  │
│  与内置工具统一调度                               │
└─────────────────────────────────────────────────┘
```

## MCPManager

MCPManager 管理所有 MCP 服务器的连接、工具发现和生命周期。

```python
from harness.mcp.manager import MCPManager, MCPServerConfig

class MCPManager:
    def __init__(
        self,
        tool_registry: Optional["ToolRegistry"] = None,  # 工具注册表
        auto_load_configs: bool = True,                  # 自动加载配置文件
    )
    
    def add_server(self, config: MCPServerConfig) -> None:
        """添加 MCP 服务器配置"""
    
    def remove_server(self, name: str) -> bool:
        """移除 MCP 服务器配置，返回是否成功"""
    
    def get_server_config(self, name: str) -> Optional[MCPServerConfig]:
        """获取服务器配置"""
    
    def list_server_configs(self) -> List[MCPServerConfig]:
        """列出所有服务器配置"""
    
    async def connect_server(self, name: str) -> MCPClient:
        """连接特定 MCP 服务器"""
    
    async def connect_all(self) -> Dict[str, MCPServerInfo]:
        """连接所有启用的 MCP 服务器"""
    
    async def disconnect_server(self, name: str) -> bool:
        """断开特定 MCP 服务器连接"""
    
    async def disconnect_all(self) -> None:
        """断开所有 MCP 服务器连接"""
```

### MCPServerConfig

```python
@dataclass
class MCPServerConfig:
    name: str                          # 服务器名称
    transport: str                     # 传输方式: "stdio" 或 "http"
    command: Optional[str] = None      # Stdio 传输命令
    args: List[str] = field(default_factory=list)  # 命令参数
    url: Optional[str] = None          # HTTP 传输 URL
    env: Dict[str, str] = field(default_factory=dict)  # 环境变量
    headers: Dict[str, str] = field(default_factory=dict)  # HTTP 头
    enabled: bool = True               # 是否启用
    timeout: float = 30.0              # 超时时间（秒）
```

## MCP Transport

MCP 支持两种传输方式：

### Stdio 传输

通过子进程标准输入/输出通信，适用于本地安装的 MCP 服务器：

```python
from harness.mcp.manager import MCPManager, MCPServerConfig

# 创建 MCP 管理器
mcp_manager = MCPManager()

# 添加 Stdio 服务器
config = MCPServerConfig(
    name="github",
    transport="stdio",
    command="mcp-github",
    args=["--token", "$GITHUB_TOKEN"],  # 参数作为列表传递
    env={"GITHUB_TOKEN": "your-token-here"},  # 环境变量
)

mcp_manager.add_server(config)

# 连接服务器
await mcp_manager.connect_server("github")
```

### HTTP 传输

通过 HTTP/SSE 通信，适用于远程 MCP 服务器。HTTPTransport 支持三种 MCP HTTP 协议，自动检测服务器类型：

#### 支持的协议

| 协议 | 标准 | 发送消息 | 接收消息 | 说明 |
|------|------|----------|----------|------|
| **Streamable HTTP** | 2025-11-25 (最新) | POST `/mcp` | POST 响应 (JSON/SSE) + GET `/mcp` SSE | 单一端点，推荐 |
| **HTTP+SSE** | 2024-11-05 (已弃用) | POST `/message` | GET `/sse` | 分开两个端点 |
| **FastMCP SSE** | FastMCP 变种 | POST `/messages/?session_id=xxx` | GET `/sse` | 动态 session 发现 |

#### 协议自动检测

HTTPTransport 在连接时自动检测服务器协议类型：

1. POST `initialize` 请求到 `/mcp`
2. 如果返回 200 OK → **Streamable HTTP**
3. 如果返回 400/404/405 → GET `/sse` 进一步检测
4. 解析 SSE 首个事件区分 **FastMCP** 或 **HTTP+SSE**

#### 使用示例

```python
from harness.mcp.manager import MCPManager, MCPServerConfig

# 创建 MCP 管理器
mcp_manager = MCPManager()

# 添加 HTTP 服务器（自动检测协议）
config = MCPServerConfig(
    name="remote-tools",
    transport="http",
    url="https://mcp.example.com",  # 基础 URL，自动检测协议
    headers={"Authorization": "Bearer your-token"},  # 可选：认证头
)

mcp_manager.add_server(config)

# 连接服务器
await mcp_manager.connect_server("remote-tools")
```

#### 强制指定协议

如需跳过自动检测，可强制指定协议类型：

```python
from harness.mcp.transport import HTTPTransport

# 强制使用 Streamable HTTP
transport = HTTPTransport(
    url="https://mcp.example.com",
    protocol="streamable-http",  # 强制协议类型
)

# 可选值:
# - "streamable-http"  (Streamable HTTP 2025-11-25)
# - "http-sse"         (HTTP+SSE 2024-11-05, 已弃用)
# - "fastmcp-sse"      (FastMCP SSE)
```

#### Streamable HTTP 特性

Streamable HTTP (2025-11-25) 是最新的 MCP 标准，特性包括：

- **单一端点**：所有通信通过 `/mcp`
- **POST 请求**：发送 JSON-RPC 消息
- **灵活响应**：响应可能是 JSON 对象或 SSE 流
- **会话管理**：支持 `Mcp-Session-Id` 头
- **服务器推送**：GET `/mcp` 可开 SSE 流接收服务器主动消息

```python
# Streamable HTTP 配置示例
config = MCPServerConfig(
    name="streamable-server",
    transport="http",
    url="https://api.example.com/mcp",
)
```

#### FastMCP SSE 特性

FastMCP 是常用的 MCP 服务器实现，使用变种 SSE 协议：

- 连接 GET `/sse` 获取动态消息端点
- SSE 首个事件：`event: endpoint\ndata: /messages/?session_id=xxx`
- POST 到动态端点发送消息
- 持续监听 GET `/sse` 接收响应

```python
# FastMCP 配置示例
config = MCPServerConfig(
    name="fastmcp-server",
    transport="http",
    url="http://localhost:8500",
)
```

#### Session 自动重连

FastMCP SSE session 在约 90 秒不活动后会过期。HTTPTransport 自动处理这种情况：

1. POST 请求返回 404 时检测到 session 已过期
2. 自动重新连接 `/sse` 获取新的 `session_id`
3. 用新端点重试失败的请求

用户无需手动处理 session 过期问题，SDK 会自动重连。这是 SSE 的正常行为——SSE 协议本身没有内置的 keep-alive 机制（不像 WebSocket 的 ping/pong），服务器端 session 有 TTL 限制。

## 工具发现与注册

MCP 服务器连接后，自动发现其提供的工具并注册到 ToolExecutor：

```
1. 连接 MCP 服务器
2. 获取工具列表 (tools/list)
3. 为每个工具创建 MCPTool 包装器
4. 注册到 ToolExecutor
5. LLM 可调用 MCP 工具
```

### MCPToolWrapper 包装器

MCP 工具通过 `MCPToolWrapper` 包装为标准 Tool 接口，与内置工具统一调度：

```python
class MCPToolWrapper:
    """将 MCP 工具包装为 Harness Tool"""
    
    @property
    def name(self) -> str:
        """工具名称，格式: mcp_{server}_{tool}"""
    
    @property
    def input_schema(self) -> dict:
        """工具输入 Schema (JSON Schema 格式)"""
    
    def validate_arguments(self, arguments: dict) -> tuple[bool, str | None]:
        """验证参数，返回 (是否有效, 错误信息)"""
    
    async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
        """执行 MCP 工具调用"""
```

MCP 工具与内置工具使用方式完全相同，LLM 看到的是统一的工具列表：

```python
# MCP 工具自动注册，无需额外配置
result = await agent.run("搜索代码中的 TODO 并在 GitHub 创建 issue")
# LLM 可能调用: grep (内置) + mcp_github_create_issue (MCP)
```

## 常用 MCP 服务器

| 服务器 | 安装命令 | 提供工具 |
|--------|----------|----------|
| GitHub | `mcp-github` | PR、Issue、代码搜索 |
| Slack | `mcp-slack` | 发送消息、搜索 |
| Filesystem | `mcp-filesystem` | 文件操作（与内置工具互补） |
| Database | `mcp-database` | SQL 查询 |
| Browser | `mcp-browser` | 网页浏览 |

### 配置示例

```python
from harness import AgentHarness, MCPManager, MCPServerConfig

# 创建 Agent
agent = AgentHarness()

# 创建 MCP 管理器并连接到工具注册表
mcp_manager = MCPManager(tool_registry=agent._tool_registry)

# 添加多个 MCP 服务器
github_config = MCPServerConfig(
    name="github",
    transport="stdio",
    command="mcp-github",
    env={"GITHUB_TOKEN": "your-token-here"},
)
mcp_manager.add_server(github_config)

slack_config = MCPServerConfig(
    name="slack",
    transport="stdio",
    command="mcp-slack",
    args=["--token", "$SLACK_TOKEN"],
    env={"SLACK_TOKEN": "your-slack-token"},
)
mcp_manager.add_server(slack_config)

# 连接所有服务器
await mcp_manager.connect_all()
# MCP 工具自动注册到 agent 的工具注册表

# 使用
result = await agent.run("查看最近的 GitHub issue 并在 Slack 通知团队")
```

## 从配置文件自动加载

`MCPManager` 自动从以下路径搜索配置文件（按优先级顺序）：

1. `.agent/mcp.json`
2. `.agent/mcp.yaml` 
3. `.mcp.json`
4. `.mcp.yaml`
5. `~/.harness/mcp.json`
6. `~/.harness/mcp.yaml`
7. `~/.claude/mcp.json` (Claude Code 兼容格式)

### 配置文件格式

```yaml
# .mcp.yaml (YAML 格式)
mcpServers:
  github:
    command: mcp-github
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
  slack:
    command: mcp-slack
    env:
      SLACK_TOKEN: ${SLACK_TOKEN}
  remote:
    url: https://mcp.example.com/sse
    transport: http
```

```json
// .mcp.json (JSON 格式)
{
  "mcpServers": {
    "github": {
      "command": "mcp-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "slack": {
      "command": "mcp-slack",
      "env": {
        "SLACK_TOKEN": "${SLACK_TOKEN}"
      }
    }
  }
}
```

### 使用方式

```python
from harness import AgentHarness, MCPManager

# 创建 Agent
agent = AgentHarness()

# 创建 MCP 管理器（自动加载配置文件）
mcp_manager = MCPManager(tool_registry=agent._tool_registry)

# 连接所有服务器（从配置文件加载）
await mcp_manager.connect_all()
```

## MCP 工具权限

MCP 工具的权限通过 PermissionSet 控制：

```python
from harness.security.sandbox import PermissionSet, PermissionLevel

# 限制 MCP 工具权限
agent = AgentHarness(
    permissions=PermissionSet(
        max_permission=PermissionLevel.NETWORK,
        denied_tools={"mcp_github_delete_repo"},  # 禁止删除仓库
    ),
)
```

## 生命周期管理

MCP 服务器需要手动管理连接和断开：

```python
from harness import AgentHarness, MCPManager, MCPServerConfig

# 创建 Agent 和 MCP 管理器
agent = AgentHarness()
mcp_manager = MCPManager(tool_registry=agent._tool_registry)

# 运行时动态添加服务器
config = MCPServerConfig(
    name="github",
    transport="stdio",
    command="mcp-github",
    env={"GITHUB_TOKEN": "your-token-here"},
)
mcp_manager.add_server(config)

# 连接服务器
await mcp_manager.connect_server("github")

# 使用 MCP 工具
result = await agent.run("查看 GitHub issues")

# 断开服务器连接
await mcp_manager.disconnect_server("github")

# 断开所有服务器连接
await mcp_manager.disconnect_all()
```

## 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| 服务器启动失败 | 记录错误，跳过该服务器的工具 |
| 工具调用超时 | 返回 ToolResult(error="MCP timeout") |
| 服务器崩溃 | 自动重连（最多 3 次） |
| 工具不存在 | 返回 ToolResult(error="Tool not found") |
