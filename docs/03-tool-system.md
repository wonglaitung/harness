# 03 - Tool System 工具系统

## 概述

Tool System 是让 LLM 能够"动手操作"的能力层，定义了 Agent 可以执行的动作和约束。

## 核心设计

### 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                       Tool System                            │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Tool Registry                       │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │   │
│  │  │  File   │  │  Shell  │  │   Web   │  │   MCP   │ │   │
│  │  │  Tools  │  │  Tools  │  │  Tools  │  │  Tools  │ │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │   │
│  │              Built-in         Custom       External   │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 Permission Manager                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │   Path      │  │  Command    │  │   Rate      │  │   │
│  │  │   Filter    │  │  Blocklist  │  │   Limiter   │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Tool Executor                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │   Sandbox   │  │   Timeout   │  │   Result    │  │   │
│  │  │  Executor   │  │   Handler   │  │   Parser    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   MCP Manager                         │   │
│  │  连接外部 MCP 服务器，自动注册工具                      │   │
│  │  支持: Stdio / HTTP / WebSocket 传输                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Tool 接口设计

### 基础 Tool 类

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import jsonschema

class PermissionLevel(Enum):
    """权限级别"""
    SAFE = "safe"              # 安全操作，无需确认
    MODERATE = "moderate"      # 中等风险，可选确认
    DANGEROUS = "dangerous"    # 危险操作，必须确认
    RESTRICTED = "restricted"  # 受限操作，默认禁用

@dataclass
class ToolSchema:
    """工具 Schema"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    required: List[str] = field(default_factory=list)

    def to_anthropic_format(self) -> dict:
        """转换为 Anthropic 格式"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required
            }
        }

    def to_openai_format(self) -> dict:
        """转换为 OpenAI 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required
                }
            }
        }

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, content: str, **metadata) -> "ToolResult":
        return cls(success=True, content=content, metadata=metadata)

    @classmethod
    def error(cls, message: str) -> "ToolResult":
        return cls(success=False, content="", error=message)

@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: Dict[str, Any]

class Tool(ABC):
    """工具基类"""

    # 子类必须定义
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    required: List[str] = []
    permission_level: PermissionLevel = PermissionLevel.SAFE

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._validate_definition()

    def _validate_definition(self):
        """验证工具定义"""
        if not self.name:
            raise ValueError("Tool must have a name")
        if not self.description:
            raise ValueError("Tool must have a description")

    @property
    def schema(self) -> ToolSchema:
        """获取工具 Schema"""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            required=self.required
        )

    def validate_arguments(self, arguments: Dict[str, Any]) -> bool:
        """验证参数"""
        try:
            schema = {
                "type": "object",
                "properties": self.parameters,
                "required": self.required
            }
            jsonschema.validate(arguments, schema)
            return True
        except jsonschema.ValidationError as e:
            raise ValueError(f"Invalid arguments: {e.message}")

    @abstractmethod
    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        """执行工具"""
        pass

    def should_confirm(self, arguments: Dict[str, Any]) -> bool:
        """是否需要用户确认"""
        if self.permission_level == PermissionLevel.DANGEROUS:
            return True
        if self.permission_level == PermissionLevel.RESTRICTED:
            return True
        return False

    def get_confirmation_message(self, arguments: Dict[str, Any]) -> str:
        """获取确认消息"""
        return f"Execute {self.name} with arguments: {arguments}?"
```

### Tool Context

```python
@dataclass
class ToolContext:
    """工具执行上下文"""
    session_id: str
    working_directory: str
    environment: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    user_id: Optional[str] = None
    permissions: "PermissionSet" = None
    logger: Optional[Logger] = None

    # 回调
    on_progress: Optional[Callable[[str], None]] = None
```

## 内置工具

### 3.1 File Tools

```python
class ReadTool(Tool):
    """读取文件"""

    name = "read"
    description = "Read the contents of a file from the local filesystem."
    parameters = {
        "file_path": {
            "type": "string",
            "description": "The absolute path to the file to read"
        },
        "limit": {
            "type": "integer",
            "description": "Number of lines to read (optional)"
        },
        "offset": {
            "type": "integer",
            "description": "Starting line number (optional)"
        }
    }
    required = ["file_path"]
    permission_level = PermissionLevel.SAFE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        file_path = arguments["file_path"]

        # 权限检查
        if not context.permissions.is_path_allowed(file_path, "read"):
            return ToolResult.error(f"Access denied: {file_path}")

        try:
            with open(file_path, "r") as f:
                if "limit" in arguments or "offset" in arguments:
                    lines = f.readlines()
                    offset = arguments.get("offset", 0)
                    limit = arguments.get("limit", len(lines))
                    content = "".join(lines[offset:offset + limit])
                else:
                    content = f.read()

            return ToolResult.ok(content, path=file_path)

        except FileNotFoundError:
            return ToolResult.error(f"File not found: {file_path}")
        except PermissionError:
            return ToolResult.error(f"Permission denied: {file_path}")
        except Exception as e:
            return ToolResult.error(f"Error reading file: {e}")


class WriteTool(Tool):
    """写入文件"""

    name = "write"
    description = "Write content to a file on the local filesystem."
    parameters = {
        "file_path": {
            "type": "string",
            "description": "The absolute path to the file to write"
        },
        "content": {
            "type": "string",
            "description": "The content to write to the file"
        }
    }
    required = ["file_path", "content"]
    permission_level = PermissionLevel.MODERATE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        file_path = arguments["file_path"]
        content = arguments["content"]

        # 权限检查
        if not context.permissions.is_path_allowed(file_path, "write"):
            return ToolResult.error(f"Write access denied: {file_path}")

        try:
            # 确保目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                f.write(content)

            return ToolResult.ok(
                f"Successfully wrote {len(content)} characters to {file_path}",
                path=file_path,
                bytes_written=len(content)
            )

        except Exception as e:
            return ToolResult.error(f"Error writing file: {e}")


class EditTool(Tool):
    """编辑文件"""

    name = "edit"
    description = "Perform exact string replacement in a file."
    parameters = {
        "file_path": {
            "type": "string",
            "description": "The absolute path to the file to edit"
        },
        "old_string": {
            "type": "string",
            "description": "The text to replace"
        },
        "new_string": {
            "type": "string",
            "description": "The text to replace with"
        },
        "replace_all": {
            "type": "boolean",
            "description": "Replace all occurrences (default false)"
        }
    }
    required = ["file_path", "old_string", "new_string"]
    permission_level = PermissionLevel.MODERATE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        file_path = arguments["file_path"]
        old_string = arguments["old_string"]
        new_string = arguments["new_string"]
        replace_all = arguments.get("replace_all", False)

        if not context.permissions.is_path_allowed(file_path, "write"):
            return ToolResult.error(f"Write access denied: {file_path}")

        try:
            with open(file_path, "r") as f:
                content = f.read()

            if old_string not in content:
                return ToolResult.error(
                    f"String not found in file: {old_string[:50]}..."
                )

            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            with open(file_path, "w") as f:
                f.write(new_content)

            return ToolResult.ok(
                f"Successfully edited {file_path}",
                replacements=content.count(old_string) if replace_all else 1
            )

        except Exception as e:
            return ToolResult.error(f"Error editing file: {e}")


class GlobTool(Tool):
    """文件模式匹配"""

    name = "glob"
    description = "Find files matching a glob pattern."
    parameters = {
        "pattern": {
            "type": "string",
            "description": "The glob pattern to match (e.g., **/*.py)"
        },
        "path": {
            "type": "string",
            "description": "The directory to search in (optional)"
        }
    }
    required = ["pattern"]
    permission_level = PermissionLevel.SAFE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        import glob as glob_module

        pattern = arguments["pattern"]
        path = arguments.get("path", context.working_directory)

        matches = glob_module.glob(
            pattern,
            root_dir=path,
            recursive=True
        )

        return ToolResult.ok(
            "\n".join(sorted(matches)),
            count=len(matches)
        )


class GrepTool(Tool):
    """文件内容搜索"""

    name = "grep"
    description = "Search for patterns in file contents using regex."
    parameters = {
        "pattern": {
            "type": "string",
            "description": "The regex pattern to search for"
        },
        "path": {
            "type": "string",
            "description": "The directory to search in (optional)"
        },
        "file_pattern": {
            "type": "string",
            "description": "Glob pattern for files to search (e.g., *.py)"
        },
        "ignore_case": {
            "type": "boolean",
            "description": "Case insensitive search (default false)"
        }
    }
    required = ["pattern"]
    permission_level = PermissionLevel.SAFE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        import re
        from pathlib import Path

        pattern = arguments["pattern"]
        path = Path(arguments.get("path", context.working_directory))
        file_pattern = arguments.get("file_pattern", "*")
        ignore_case = arguments.get("ignore_case", False)

        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(pattern, flags)

        results = []
        for file_path in path.rglob(file_pattern):
            if not file_path.is_file():
                continue
            if not context.permissions.is_path_allowed(str(file_path), "read"):
                continue

            try:
                with open(file_path, "r") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"{file_path}:{i}: {line.rstrip()}")
            except (UnicodeDecodeError, PermissionError):
                continue

        return ToolResult.ok(
            "\n".join(results),
            matches=len(results)
        )
```

### 3.2 Shell Tools

```python
class BashTool(Tool):
    """执行 Shell 命令"""

    name = "bash"
    description = "Execute a shell command and return the output."
    parameters = {
        "command": {
            "type": "string",
            "description": "The command to execute"
        },
        "timeout": {
            "type": "number",
            "description": "Timeout in seconds (optional)"
        },
        "cwd": {
            "type": "string",
            "description": "Working directory (optional)"
        }
    }
    required = ["command"]
    permission_level = PermissionLevel.DANGEROUS

    # 危险命令黑名单
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "rm -rf ~",
        "mkfs",
        "dd if=",
        ":(){ :|:& };:",  # Fork bomb
        "> /dev/sda",
        "chmod -R 777 /",
        "chown -R",
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        command = arguments["command"]
        timeout = arguments.get("timeout", context.timeout)
        cwd = arguments.get("cwd", context.working_directory)

        # 检查危险命令
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command:
                return ToolResult.error(f"Blocked dangerous command: {blocked}")

        # 权限检查
        if not context.permissions.is_command_allowed(command):
            return ToolResult.error(f"Command not allowed: {command}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, **context.environment}
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult.error(f"Command timed out after {timeout}s")

            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    content=output,
                    error=f"Exit code {process.returncode}: {error}"
                )

            return ToolResult.ok(
                output,
                exit_code=process.returncode
            )

        except Exception as e:
            return ToolResult.error(f"Error executing command: {e}")
```

### 3.3 Web Tools

```python
class WebSearchTool(Tool):
    """Web 搜索"""

    name = "web_search"
    description = "Search the web for information."
    parameters = {
        "query": {
            "type": "string",
            "description": "The search query"
        },
        "num_results": {
            "type": "integer",
            "description": "Number of results to return (default 5)"
        }
    }
    required = ["query"]
    permission_level = PermissionLevel.MODERATE

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.api_key = config.get("api_key") if config else None
        self.search_engine = config.get("engine", "tavily")

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        query = arguments["query"]
        num_results = arguments.get("num_results", 5)

        # 使用搜索 API
        # 可以接入 Tavily, Serper, Google Custom Search 等
        results = await self._search(query, num_results)

        return ToolResult.ok(
            self._format_results(results),
            query=query,
            count=len(results)
        )


class WebFetchTool(Tool):
    """获取网页内容"""

    name = "web_fetch"
    description = "Fetch and extract content from a URL."
    parameters = {
        "url": {
            "type": "string",
            "description": "The URL to fetch"
        },
        "selector": {
            "type": "string",
            "description": "CSS selector to extract specific content (optional)"
        }
    }
    required = ["url"]
    permission_level = PermissionLevel.MODERATE

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        import aiohttp
        from bs4 import BeautifulSoup

        url = arguments["url"]
        selector = arguments.get("selector")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        return ToolResult.error(f"HTTP {response.status}")
                    html = await response.text()

            soup = BeautifulSoup(html, "html.parser")

            # 移除脚本和样式
            for element in soup(["script", "style", "nav", "footer"]):
                element.decompose()

            if selector:
                content = soup.select(selector)
                text = "\n".join(e.get_text() for e in content)
            else:
                text = soup.get_text(separator="\n", strip=True)

            return ToolResult.ok(text[:10000], url=url)  # 限制长度

        except Exception as e:
            return ToolResult.error(f"Error fetching URL: {e}")
```

## Tool Registry

```python
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)

    def register(self, tool: Tool, category: str = "general"):
        """注册工具"""
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool
        self._categories[category].append(tool.name)

    def unregister(self, name: str):
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            for tools in self._categories.values():
                if name in tools:
                    tools.remove(name)

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self, category: str = None) -> List[ToolSchema]:
        """列出工具"""
        if category:
            names = self._categories.get(category, [])
            return [self._tools[n].schema for n in names if n in self._tools]
        return [t.schema for t in self._tools.values()]

    def get_schemas_for_llm(self, provider: str = "anthropic") -> List[dict]:
        """获取 LLM 可用的工具 schemas"""
        schemas = []
        for tool in self._tools.values():
            if provider == "anthropic":
                schemas.append(tool.schema.to_anthropic_format())
            elif provider == "openai":
                schemas.append(tool.schema.to_openai_format())
        return schemas

    def register_defaults(self):
        """注册默认工具集"""
        # File tools
        self.register(ReadTool(), category="file")
        self.register(WriteTool(), category="file")
        self.register(EditTool(), category="file")
        self.register(GlobTool(), category="file")
        self.register(GrepTool(), category="file")

        # Shell tools
        self.register(BashTool(), category="shell")

        # Web tools
        self.register(WebSearchTool(), category="web")
        self.register(WebFetchTool(), category="web")
```

## Permission System

```python
@dataclass
class PermissionRule:
    """权限规则"""
    type: str  # "allow" or "deny"
    resource: str  # path pattern, command pattern, etc.
    action: str  # "read", "write", "execute"

@dataclass
class PermissionSet:
    """权限集合"""
    rules: List[PermissionRule] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    allowed_commands: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=list)
    default_deny: bool = True

    def is_path_allowed(self, path: str, action: str) -> bool:
        """检查路径权限"""
        from pathlib import Path

        abs_path = Path(path).resolve()

        # 检查黑名单
        for blocked in self.blocked_paths:
            if abs_path.is_relative_to(blocked):
                return False

        # 检查白名单
        if not self.allowed_paths:
            return not self.default_deny

        for allowed in self.allowed_paths:
            if abs_path.is_relative_to(allowed):
                return True

        return not self.default_deny

    def is_command_allowed(self, command: str) -> bool:
        """检查命令权限"""
        # 检查黑名单
        for blocked in self.blocked_commands:
            if blocked in command:
                return False

        # 如果有白名单，检查是否匹配
        if self.allowed_commands:
            for allowed in self.allowed_commands:
                if command.startswith(allowed):
                    return True
            return False

        return True

    @classmethod
    def sandbox(cls, workspace: str) -> "PermissionSet":
        """创建沙箱权限"""
        return cls(
            allowed_paths=[workspace],
            blocked_paths=["/etc", "/root", "~/.ssh"],
            blocked_commands=["rm -rf", "sudo", "chmod"],
            default_deny=True
        )

    @classmethod
    def full_access(cls) -> "PermissionSet":
        """完全访问权限"""
        return cls(
            default_deny=False,
            blocked_commands=["rm -rf /"]
        )
```

## Tool Executor

```python
class ToolExecutor:
    """工具执行器"""

    def __init__(
        self,
        registry: ToolRegistry,
        permissions: PermissionSet,
        default_timeout: float = 30.0,
        sandbox: bool = True
    ):
        self.registry = registry
        self.permissions = permissions
        self.default_timeout = default_timeout
        self.sandbox = sandbox
        self._pending_confirmations: Dict[str, ToolCall] = {}

    async def execute(
        self,
        call: ToolCall,
        context: ToolContext
    ) -> ToolResult:
        """执行工具调用"""

        # 获取工具
        tool = self.registry.get(call.name)
        if not tool:
            return ToolResult.error(f"Unknown tool: {call.name}")

        # 验证参数
        try:
            tool.validate_arguments(call.arguments)
        except ValueError as e:
            return ToolResult.error(str(e))

        # 检查是否需要确认
        if tool.should_confirm(call.arguments):
            # 可以实现确认流程
            confirmed = await self._request_confirmation(tool, call, context)
            if not confirmed:
                return ToolResult.error("User denied the operation")

        # 创建执行上下文
        exec_context = ToolContext(
            session_id=context.session_id,
            working_directory=context.working_directory,
            environment=context.environment,
            timeout=self.default_timeout,
            permissions=self.permissions,
            logger=context.logger
        )

        # 执行工具
        try:
            if self.sandbox:
                result = await self._execute_in_sandbox(tool, call.arguments, exec_context)
            else:
                result = await tool.execute(call.arguments, exec_context)

            return result

        except asyncio.TimeoutError:
            return ToolResult.error(f"Tool execution timed out")
        except Exception as e:
            return ToolResult.error(f"Tool execution error: {e}")

    async def _execute_in_sandbox(
        self,
        tool: Tool,
        arguments: Dict,
        context: ToolContext
    ) -> ToolResult:
        """在沙箱中执行工具"""
        # 可以使用 Docker, gVisor, nsjail 等
        # 这里是一个简化实现
        return await tool.execute(arguments, context)

    async def _request_confirmation(
        self,
        tool: Tool,
        call: ToolCall,
        context: ToolContext
    ) -> bool:
        """请求用户确认"""
        # 实现确认流程
        # 可以通过回调、消息队列等方式
        return True

    async def execute_parallel(
        self,
        calls: List[ToolCall],
        context: ToolContext
    ) -> List[ToolResult]:
        """并行执行多个工具"""
        tasks = [self.execute(call, context) for call in calls]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

## Custom Tools

### 函数装饰器方式

```python
def tool(
    name: str = None,
    description: str = None,
    permission: PermissionLevel = PermissionLevel.SAFE
):
    """将函数注册为工具的装饰器"""

    def decorator(func):
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or ""

        # 从函数签名推断参数
        import inspect
        sig = inspect.signature(func)
        parameters = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls", "context"]:
                continue

            param_type = "string"  # 默认类型
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object"
                }
                param_type = type_map.get(param.annotation, "string")

            parameters[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}"
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        class FunctionTool(Tool):
            name = tool_name
            description = tool_desc
            parameters = parameters
            required = required
            permission_level = permission

            async def execute(self, arguments, context):
                try:
                    result = func(**arguments)
                    if asyncio.iscoroutine(result):
                        result = await result
                    return ToolResult.ok(str(result))
                except Exception as e:
                    return ToolResult.error(str(e))

        return FunctionTool()

    return decorator


# 使用示例
@tool(description="Get current weather for a city")
async def get_weather(city: str, unit: str = "celsius") -> str:
    """Get weather information"""
    # 调用天气 API
    return f"Weather in {city}: 25°{unit[0].upper()}"


@tool(permission=PermissionLevel.MODERATE)
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email"""
    # 发送邮件逻辑
    return f"Email sent to {to}"
```

### 类方式

```python
class DatabaseQueryTool(Tool):
    """数据库查询工具"""

    name = "db_query"
    description = "Execute a SQL query on the database"
    parameters = {
        "query": {
            "type": "string",
            "description": "SQL query to execute"
        },
        "params": {
            "type": "array",
            "description": "Query parameters"
        }
    }
    required = ["query"]
    permission_level = PermissionLevel.DANGEROUS

    def __init__(self, connection_string: str):
        super().__init__()
        self.connection_string = connection_string

    async def execute(self, arguments: Dict, context: ToolContext) -> ToolResult:
        import asyncpg

        query = arguments["query"]
        params = arguments.get("params", [])

        # 只允许 SELECT 语句
        if not query.strip().upper().startswith("SELECT"):
            return ToolResult.error("Only SELECT queries are allowed")

        try:
            conn = await asyncpg.connect(self.connection_string)
            rows = await conn.fetch(query, *params)
            await conn.close()

            return ToolResult.ok(
                json.dumps([dict(r) for r in rows], indent=2),
                row_count=len(rows)
            )
        except Exception as e:
            return ToolResult.error(f"Query error: {e}")
```

## MCP (Model Context Protocol) 支持

MCP 是 Anthropic 提出的开放协议，用于连接 AI 模型与外部工具和资源。Harness 原生支持 MCP，可以将 MCP 服务器的工具无缝集成到工具系统中。

### MCP 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Harness                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Tool Registry                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │   │
│  │  │ Built-in │ │ Custom   │ │     MCP Tools        │ │   │
│  │  │ Tools    │ │ Tools    │ │  (mcp_server_tool)   │ │   │
│  │  └──────────┘ └──────────┘ └──────────────────────┘ │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                             │                               │
│                             ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   MCP Manager                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │   │
│  │  │ Transport│ │ Protocol │ │   Server Registry    │ │   │
│  │  │  Layer   │ │  Client  │ │                      │ │   │
│  │  └──────────┘ └──────────┘ └──────────────────────┘ │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                             │                               │
│                             ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   MCP Servers                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │   │
│  │  │Filesystem│ │  GitHub  │ │  Slack   │  ...        │   │
│  │  │  Server  │ │  Server  │ │  Server  │             │   │
│  │  └──────────┘ └──────────┘ └──────────┘             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 传输层实现

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any
import asyncio
import json

class MCPTransport(ABC):
    """MCP 传输层抽象"""

    @abstractmethod
    async def connect(self):
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    async def send(self, message: dict) -> None:
        """发送消息"""
        pass

    @abstractmethod
    async def receive(self) -> AsyncIterator[dict]:
        """接收消息流"""
        pass


class StdioTransport(MCPTransport):
    """标准输入输出传输（最常用）"""

    def __init__(self, command: str, args: list = None, env: dict = None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._process: Optional[asyncio.subprocess.Process] = None

    async def connect(self):
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **self.env}
        )

    async def disconnect(self):
        if self._process:
            self._process.terminate()
            await self._process.wait()

    async def send(self, message: dict) -> None:
        data = json.dumps(message) + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()

    async def receive(self) -> AsyncIterator[dict]:
        while True:
            line = await self._process.stdout.readline()
            if not line:
                break
            try:
                yield json.loads(line.decode())
            except json.JSONDecodeError:
                continue


class HTTPTransport(MCPTransport):
    """HTTP/SSE 传输"""

    def __init__(self, url: str, headers: dict = None):
        self.url = url
        self.headers = headers or {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self):
        self._session = aiohttp.ClientSession(headers=self.headers)

    async def disconnect(self):
        if self._session:
            await self._session.close()

    async def send(self, message: dict) -> None:
        async with self._session.post(f"{self.url}/message", json=message) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Send failed: {resp.status}")

    async def receive(self) -> AsyncIterator[dict]:
        async with self._session.get(f"{self.url}/sse") as resp:
            async for line in resp.content:
                if line.startswith(b"data: "):
                    yield json.loads(line[6:])
```

### MCP Client 实现

```python
import uuid
from dataclasses import dataclass, field

@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]

@dataclass
class MCPServerInfo:
    """服务器信息"""
    name: str
    version: str
    capabilities: List[str]


class MCPClient:
    """MCP 客户端"""

    def __init__(self, transport: MCPTransport, client_name: str = "harness"):
        self.transport = transport
        self.client_name = client_name
        self._server_info: Optional[MCPServerInfo] = None
        self._tools: List[MCPTool] = []
        self._request_handlers: Dict[str, asyncio.Future] = {}

    async def connect(self) -> MCPServerInfo:
        """连接并初始化"""
        await self.transport.connect()
        asyncio.create_task(self._message_loop())

        # 发送初始化请求
        response = await self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": self.client_name, "version": "1.0.0"},
            "capabilities": {"tools": {}, "resources": {}}
        })

        self._server_info = MCPServerInfo(
            name=response["serverInfo"]["name"],
            version=response["serverInfo"]["version"],
            capabilities=list(response.get("capabilities", {}).keys())
        )

        # 发送 initialized 通知
        await self._notify("notifications/initialized", {})

        # 获取工具列表
        await self._list_tools()

        return self._server_info

    async def disconnect(self):
        await self.transport.disconnect()

    async def _list_tools(self):
        response = await self._request("tools/list", {})
        self._tools = [
            MCPTool(
                name=tool["name"],
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {})
            )
            for tool in response.get("tools", [])
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用 MCP 工具"""
        response = await self._request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        content = response.get("content", [])
        is_error = response.get("isError", False)

        text_content = "\n".join(
            item.get("text", "")
            for item in content
            if item.get("type") == "text"
        )

        return {"content": text_content, "is_error": is_error}

    async def _request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        self._request_handlers[request_id] = future

        await self.transport.send({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        })

        return await future

    async def _notify(self, method: str, params: Dict[str, Any]):
        await self.transport.send({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        })

    async def _message_loop(self):
        async for message in self.transport.receive():
            if "id" in message and message["id"] in self._request_handlers:
                future = self._request_handlers.pop(message["id"])
                if "error" in message:
                    future.set_exception(Exception(message["error"]["message"]))
                else:
                    future.set_result(message.get("result", {}))

    @property
    def tools(self) -> List[MCPTool]:
        return self._tools
```

### MCP Manager

```python
@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    transport: str              # "stdio", "http"
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


class MCPManager:
    """MCP 管理器"""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self._clients: Dict[str, MCPClient] = {}
        self._configs: Dict[str, MCPServerConfig] = {}

    def add_server(self, config: MCPServerConfig):
        """添加 MCP 服务器配置"""
        self._configs[config.name] = config

    async def connect_server(self, name: str) -> MCPClient:
        """连接到指定服务器"""
        if name in self._clients:
            return self._clients[name]

        config = self._configs.get(name)
        if not config:
            raise ValueError(f"Unknown MCP server: {name}")

        # 创建传输层
        if config.transport == "stdio":
            transport = StdioTransport(config.command, config.args, config.env)
        elif config.transport == "http":
            transport = HTTPTransport(config.url)
        else:
            raise ValueError(f"Unknown transport: {config.transport}")

        # 连接
        client = MCPClient(transport)
        await client.connect()

        # 注册工具到 Harness
        for tool in client.tools:
            self._register_mcp_tool(name, tool, client)

        self._clients[name] = client
        return client

    async def connect_all(self):
        """连接所有已启用的服务器"""
        for name, config in self._configs.items():
            if config.enabled:
                try:
                    await self.connect_server(name)
                except Exception as e:
                    print(f"Failed to connect to {name}: {e}")

    async def disconnect_all(self):
        """断开所有连接"""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear()

    def _register_mcp_tool(self, server_name: str, mcp_tool: MCPTool, client: MCPClient):
        """将 MCP 工具注册到 Harness"""

        class MCPToolWrapper(Tool):
            name = f"mcp_{server_name}_{mcp_tool.name}"
            description = mcp_tool.description
            parameters = mcp_tool.input_schema.get("properties", {})
            required = mcp_tool.input_schema.get("required", [])
            permission_level = PermissionLevel.SAFE

            def __init__(self, mcp_client: MCPClient, original_name: str):
                self._client = mcp_client
                self._original_name = original_name

            async def execute(self, arguments: Dict, context: ToolContext) -> ToolResult:
                try:
                    result = await self._client.call_tool(self._original_name, arguments)
                    if result.get("is_error"):
                        return ToolResult.error(result.get("content", "Unknown error"))
                    return ToolResult.ok(result.get("content", ""))
                except Exception as e:
                    return ToolResult.error(f"MCP tool error: {e}")

        wrapper = MCPToolWrapper(client, mcp_tool.name)
        self.tool_registry.register(wrapper, category="mcp")
```

### MCP 配置文件

```yaml
# mcp-config.yaml
mcpServers:
  filesystem:
    transport: stdio
    command: mcp-server-filesystem
    args: ["/workspace"]
    enabled: true

  github:
    transport: stdio
    command: mcp-server-github
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
    enabled: true

  slack:
    transport: stdio
    command: mcp-server-slack
    env:
      SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN}
    enabled: false

  custom-api:
    transport: http
    url: https://api.example.com/mcp
    enabled: true
```

### 使用示例

```python
from harness import AgentHarness

agent = AgentHarness()

# 添加 MCP 服务器
agent.mcp.add_server(MCPServerConfig(
    name="filesystem",
    transport="stdio",
    command="mcp-server-filesystem",
    args=["/workspace"]
))

# 连接
await agent.mcp.connect_all()

# MCP 工具已自动注册为 mcp_{server}_{tool} 格式
# 例如: mcp_filesystem_read_file, mcp_github_create_issue

result = await agent.run("使用 filesystem 工具读取 config.yaml")
```

## 测试

```python
import pytest

@pytest.fixture
def tool_registry():
    registry = ToolRegistry()
    registry.register_defaults()
    return registry

@pytest.fixture
def sandbox_permissions():
    return PermissionSet.sandbox("/workspace")

@pytest.mark.asyncio
async def test_read_tool(tool_registry, sandbox_permissions):
    tool = tool_registry.get("read")

    context = ToolContext(
        session_id="test",
        working_directory="/workspace",
        permissions=sandbox_permissions
    )

    # 测试读取文件
    result = await tool.execute({"file_path": "/workspace/test.txt"}, context)
    assert result.success

@pytest.mark.asyncio
async def test_permission_deny():
    permissions = PermissionSet.sandbox("/workspace")
    assert not permissions.is_path_allowed("/etc/passwd", "read")
    assert not permissions.is_command_allowed("rm -rf /")
```
