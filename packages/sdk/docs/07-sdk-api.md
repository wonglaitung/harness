# 07 - SDK 与 API 设计

## 概述

Harness SDK 提供简洁的 Python API，让开发者能够轻松地将 AI Agent 能力嵌入到自己的应用中。

## 设计原则

1. **简洁优先**: 核心操作一行代码搞定
2. **渐进式复杂度**: 从简单到高级逐步展开
3. **类型安全**: 完整的类型注解和 IDE 支持
4. **异步优先**: 原生支持异步操作
5. **可扩展**: 易于添加自定义组件

## 快速开始

### 安装

```bash
pip install harness-ai
```

### 最简示例

```python
from harness import AgentHarness

# 创建 agent
agent = AgentHarness()

# 运行
response = await agent.run("分析当前目录的代码结构")
print(response.content)
```

### 模型预设配置

Harness 内置主流 LLM 的预设配置，自动适配上下文窗口和输出 token 上限。

#### 支持的模型预设

| 模型 | 上下文窗口 | 默认输出 | 提供商 |
|-----|----------|---------|-------|
| claude-opus-4-6 | 200K | 16K | anthropic |
| claude-sonnet-4-6 | 200K | 16K | anthropic |
| claude-haiku-4-5 | 200K | 8K | anthropic |
| gpt-4o | 128K | 16K | openai |
| gpt-4-turbo | 128K | 4K | openai |
| glm-4 | 128K | 4K | openai |
| glm-5 | 64K | 4K | openai |
| qwen-max | 32K | 6K | openai |
| deepseek-chat | 64K | 4K | openai |

#### 使用示例

```python
from harness import AgentHarness

# 方式1：自动检测（推荐）
agent = AgentHarness(model="glm-5")  # 自动使用 64K 上下文

# 方式2：指定上下文级别
agent = AgentHarness(
    model="unknown-model",
    context_window="64k",  # 可选: "32k", "64k", "128k", "200k"
)

# 方式3：指定具体数值
agent = AgentHarness(
    model="custom-model",
    context_window=65536,  # 64K
)

# 方式4：完整配置
agent = AgentHarness(
    model="glm-5",
    context_window="64k",
    max_tokens=4096,  # 输出上限
)
```

#### 查询模型预设

```python
from harness import get_model_preset, parse_context_window, CONTEXT_LEVELS

# 获取模型预设
preset = get_model_preset("glm-5")
print(f"上下文窗口: {preset.context_window}")  # 65536
print(f"默认输出: {preset.default_output_tokens}")  # 4096

# 解析上下文配置
tokens = parse_context_window("64k")  # 65536
tokens = parse_context_window("auto", "glm-5")  # 65536

# 上下文级别映射
print(CONTEXT_LEVELS)  # {"32k": 32768, "64k": 65536, ...}
```

### 完整配置

```python
from harness import AgentHarness, HarnessConfig, ToolConfig

config = HarnessConfig(
    model="claude-sonnet-4-6",
    api_key="your-api-key",
    memory_dir="~/.harness/memory",
    tools=ToolConfig(
        enabled=["read", "write", "bash", "web_search"],
        permission_mode="sandbox"
    )
)

agent = AgentHarness(config)
```

## 核心 API

### LLM 客户端

Harness 支持三种 LLM 客户端实现，提供统一的接口抽象：

| 客户端 | 用途 | 支持模型 |
|-------|------|---------|
| `AnthropicClient` | Anthropic Claude API | claude-sonnet-4-6, claude-opus-4-6 等 |
| `OpenAIClient` | OpenAI / 第三方 OpenAI 兼容 API | gpt-4o, gpt-4-turbo, 第三方模型 |
| `MockLLMClient` | 测试用模拟客户端 | - |

#### 基类定义

```python
from harness.llm import LLMClient, LLMConfig, ToolDefinition
from harness.types import LLMResponse, StopReason, TokenUsage

class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """同步调用 LLM"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式调用 LLM"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """返回模型名称"""
        pass
```

#### AnthropicClient

用于 Anthropic Claude 模型：

```python
from harness.llm import AnthropicClient, LLMConfig

# 方式1：直接创建
client = AnthropicClient(
    api_key="your-anthropic-api-key",  # 或设置 ANTHROPIC_API_KEY 环境变量
    model="claude-sonnet-4-6",
)

# 方式2：使用配置
client = AnthropicClient(
    config=LLMConfig(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        temperature=0.7,
    )
)

# 调用
response = await client.call(
    messages=[{"role": "user", "content": "Hello"}],
    system="You are a helpful assistant.",
)
```

#### OpenAIClient

用于 OpenAI 模型或任何兼容 OpenAI API 格式的第三方服务：

```python
from harness.llm import OpenAIClient, LLMConfig

# OpenAI 官方
client = OpenAIClient(
    api_key="your-openai-api-key",  # 或设置 OPENAI_API_KEY 环境变量
    model="gpt-4o",
)

# 第三方 OpenAI 兼容 API（如 DeepSeek、Moonshot、Ollama 等）
client = OpenAIClient(
    api_key="your-api-key",
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",  # 自定义 API 地址
)

# Ollama 本地模型
client = OpenAIClient(
    api_key="ollama",  # Ollama 不需要真实 key
    model="llama3",
    base_url="http://localhost:11434/v1",
)

# 环境变量配置
# export OPENAI_API_KEY=your-api-key
# export OPENAI_BASE_URL=https://api.your-provider.com/v1
client = OpenAIClient(model="your-model")
```

##### Windows/qasync 兼容性

OpenAIClient 在 Windows 平台上使用同步客户端 + 线程池模式，以解决 qasync 与 asyncio 的兼容性问题：

```python
# 内部实现（无需用户配置）
# - 使用 openai.OpenAI (同步客户端) 而非 AsyncOpenAI
# - 通过 ThreadPoolExecutor 在后台线程执行 API 调用
# - 使用 async polling 检查 Future 完成状态，保持 UI 响应
```

**注意事项**：
- 在 Windows + PyQt6/qasync 环境中，OpenAIClient 自动使用兼容模式
- 无需用户额外配置，客户端会自动处理
- 流式响应使用 sync queue 桥接线程和协程

#### MockLLMClient

用于单元测试和开发，无需真实 API 调用：

```python
from harness.llm import MockLLMClient, LLMConfig
from harness.llm.mock import MockResponse, create_tool_use_mock

# 创建模拟客户端
client = MockLLMClient(
    model="mock-model",
    responses=[
        MockResponse(content="Hello! How can I help?", stop_reason=StopReason.END_TURN),
    ]
)

# 模拟工具调用场景
client.set_responses(create_tool_use_mock(
    tool_name="read",
    tool_args={"path": "/tmp/test.txt"},
    final_response="File content: ...",
))

# 测试
response = await client.call([{"role": "user", "content": "Read the file"}])
assert response.content == "File content: ..."

# 检查调用次数
assert client.call_count == 2  # 工具调用 + 最终响应
```

#### 自定义客户端

实现自己的 LLM 客户端：

```python
from harness.llm import LLMClient, LLMConfig, ToolDefinition
from harness.types import LLMResponse, StopReason, TokenUsage

class MyCustomLLM(LLMClient):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # 初始化你的客户端

    @property
    def model_name(self) -> str:
        return self.config.model

    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        # 实现你的 LLM 调用逻辑
        return LLMResponse(
            content="Response from custom LLM",
            tool_calls=[],
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=10, output_tokens=20),
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        # 实现流式响应
        yield "Response"
```

### AgentHarness 类

```python
from typing import Optional, List, Dict, Any, AsyncIterator, Callable
from dataclasses import dataclass, field

@dataclass
class HarnessConfig:
    """Harness 配置"""

    # LLM 配置
    model: str = "claude-sonnet-4-6"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096

    # 记忆配置
    memory_type: str = "file"          # file, sqlite, redis
    memory_dir: str = "~/.harness"
    max_context_tokens: int = 200000
    auto_compress: bool = True

    # 工具配置
    tools_enabled: List[str] = field(default_factory=lambda: ["all"])
    permission_mode: str = "sandbox"    # sandbox, ask, full

    # 技能配置
    skill_dirs: List[str] = field(default_factory=list)
    auto_load_skills: bool = True

    # 触发器配置
    triggers_enabled: bool = True

    # 调试
    debug: bool = False
    log_level: str = "INFO"


class AgentHarness:
    """Harness 主类"""

    def __init__(
        self,
        config: Optional[HarnessConfig] = None,
        **kwargs
    ):
        """
        初始化 Harness

        Args:
            config: 配置对象，如果为 None 则使用默认配置
            **kwargs: 配置参数，会覆盖 config 中的对应项
        """
        self.config = config or HarnessConfig(**kwargs)
        self._initialize_components()

    def _initialize_components(self):
        """初始化内部组件"""
        # LLM 客户端
        self.llm = self._create_llm_client()

        # 记忆系统
        self.memory = MemoryManager(
            MemoryConfig(
                storage_type=self.config.memory_type,
                storage_path=self.config.memory_dir,
                max_context_tokens=self.config.max_context_tokens,
                auto_compress=self.config.auto_compress
            ),
            llm_client=self.llm
        )

        # 工具系统
        self.tools = ToolRegistry()
        self.tools.register_defaults()
        self._apply_tool_permissions()

        # 技能系统
        self.skills = SkillRegistry()
        self._load_skills()

        # 触发器管理器
        self.triggers = TriggerManager(self)

        # 事件总线
        self.events = EventBus()

    # ==================== 核心方法 ====================

    async def run(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        on_progress: Optional[Callable[[ProgressEvent], None]] = None,
        verbose: bool = False,
        **kwargs
    ) -> "RunResult":
        """
        运行 agent（异步）

        Args:
            prompt: 用户输入
            session_id: 会话 ID，如果为 None 则创建新会话
            on_progress: 进度事件回调函数
            verbose: 是否打印进度日志（on_progress 优先）
            **kwargs: 额外参数

        Returns:
            RunResult: 运行结果

        Example:
            result = await agent.run("分析代码", session_id="my-session")
            print(result.content)
        """
        # 获取或创建会话
        if session_id:
            session = await self.memory.get_session(session_id)
            if not session:
                session = await self.memory.create_session(session_id=session_id)
        else:
            session = await self.memory.create_session()

        # 添加用户消息
        session.add_message(Message(role="user", content=prompt))

        # 构建上下文
        context = await self.memory.build_context(
            session=session,
            skills=self.skills.get_active_skills(),
            tools=self.tools.list_tools()
        )

        # 注入技能
        system_prompt = self.skills.injector.inject_skills(
            context.system_prompt,
            prompt
        )

        # 运行代理循环
        result = await self._loop.run(prompt, session)

        # 更新会话
        await self.memory.update_session(session)

        return result

    def run_sync(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> "RunResult":
        """
        运行 agent（同步）

        Args:
            prompt: 用户输入
            session_id: 会话 ID

        Returns:
            RunResult: 运行结果

        Example:
            result = agent.run_sync("分析代码")
        """
        import asyncio
        return asyncio.run(self.run(prompt, session_id, **kwargs))

    async def stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> AsyncIterator["StreamChunk"]:
        """
        流式运行 agent

        注意：当前实现为模拟流式输出。内部先完成完整响应，
        然后分块 yield，以解决 Windows/qasync 兼容性问题。

        Args:
            prompt: 用户输入
            session_id: 会话 ID
            on_chunk: chunk 回调函数

        Yields:
            StreamChunk: 流式输出块

        Example:
            async for chunk in agent.stream("分析代码"):
                print(chunk.content, end="")
        """
        # 当前实现：先运行完成，再分块输出
        result = await self.run(prompt, session_id)
        # 将结果分块 yield
        for chunk in split_into_chunks(result.content):
            if on_chunk:
                on_chunk(chunk)
            yield chunk

    async def interrupt(self):
        """
        中断当前运行

        Example:
            # 在另一个任务中
            await agent.interrupt()
        """
        self._loop.interrupt()

    # ==================== 工具管理 ====================

    def register_tool(
        self,
        tool: Tool,
        category: str = "custom"
    ):
        """
        注册自定义工具

        Args:
            tool: 工具实例
            category: 工具分类

        Example:
            @agent.tool()
            def my_tool(arg: str) -> str:
                '''My custom tool'''
                return f"Result: {arg}"
        """
        self.tools.register(tool, category)

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permission: PermissionLevel = PermissionLevel.SAFE
    ):
        """
        工具装饰器

        Example:
            @agent.tool(description="Get weather info")
            async def weather(city: str) -> str:
                return f"Weather in {city}: sunny"
        """
        def decorator(func):
            tool_instance = create_tool_from_function(
                func,
                name=name,
                description=description,
                permission=permission
            )
            self.register_tool(tool_instance)
            return func
        return decorator

    # ==================== 技能管理 ====================

    def load_skill(self, path: str):
        """
        加载技能文件

        Args:
            path: 技能文件路径

        Example:
            agent.load_skill("skills/code-review.md")
        """
        skill = Skill.from_file(Path(path))
        self.skills.register(skill)

    def activate_skill(self, skill_name: str):
        """
        激活技能

        Args:
            skill_name: 技能名称

        Example:
            agent.activate_skill("code-review")
        """
        self.skills.activate(skill_name)

    def deactivate_skill(self, skill_name: str):
        """
        关闭技能

        Args:
            skill_name: 技能名称
        """
        self.skills.deactivate(skill_name)

    # ==================== 触发器管理 ====================

    def on_schedule(
        self,
        schedule: str,
        prompt: str,
        **kwargs
    ) -> str:
        """
        设置定时触发

        Args:
            schedule: cron 表达式
            prompt: 触发时执行的提示

        Returns:
            trigger_id: 触发器 ID

        Example:
            @agent.on_schedule("0 9 * * *")
            async def morning_report():
                return "Generate daily report"
        """
        trigger = CronTrigger(
            schedule=schedule,
            action=TriggerAction(agent_prompt=prompt, **kwargs)
        )
        return self.triggers.register(trigger, trigger.action)

    def on_webhook(
        self,
        endpoint: str,
        prompt: str,
        **kwargs
    ) -> str:
        """
        设置 webhook 触发

        Args:
            endpoint: webhook 路径
            prompt: 触发时执行的提示

        Returns:
            trigger_id: 触发器 ID

        Example:
            @agent.on_webhook("/github/pr")
            async def handle_pr(payload):
                return f"Review PR #{payload['number']}"
        """
        trigger = WebhookTrigger(
            config=WebhookConfig(endpoint=endpoint),
            action=TriggerAction(agent_prompt=prompt, **kwargs)
        )
        return self.triggers.register(trigger, trigger.action)

    # ==================== 会话管理 ====================

    async def create_session(
        self,
        user_id: Optional[str] = None,
        working_directory: str = ""
    ) -> Session:
        """
        创建新会话

        Returns:
            Session: 会话对象
        """
        return await self.memory.create_session(
            user_id=user_id,
            working_directory=working_directory
        )

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话

        Args:
            session_id: 会话 ID

        Returns:
            Session: 会话对象，如果不存在返回 None
        """
        return await self.memory.get_session(session_id)

    async def list_sessions(self) -> List[Session]:
        """
        列出所有会话

        Returns:
            List[Session]: 会话列表
        """
        return await self.memory.session_store.list_sessions()

    async def delete_session(self, session_id: str):
        """
        删除会话

        Args:
            session_id: 会话 ID
        """
        await self.memory.session_store.delete(session_id)

    # ==================== 记忆管理 ====================

    async def remember(
        self,
        content: str,
        memory_type: str = "knowledge",
        metadata: Optional[Dict] = None
    ):
        """
        存储记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型
            metadata: 元数据

        Example:
            await agent.remember(
                "User prefers Python over JavaScript",
                memory_type="preference"
            )
        """
        await self.memory.store_memory(memory_type, content, metadata)

    async def recall(
        self,
        query: str,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """
        检索记忆

        Args:
            query: 查询字符串
            limit: 返回数量限制

        Returns:
            List[MemoryEntry]: 记忆条目列表

        Example:
            memories = await agent.recall("user preferences")
        """
        return await self.memory.retrieve_memory(query, limit=limit)

    # ==================== 配置 ====================

    @classmethod
    def from_config(cls, config_path: str) -> "AgentHarness":
        """
        从配置文件创建

        Args:
            config_path: 配置文件路径 (YAML 或 JSON)

        Returns:
            AgentHarness: Harness 实例

        Example:
            agent = AgentHarness.from_config("harness.yaml")
        """
        import yaml

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        config = HarnessConfig(**config_data)
        return cls(config)

    @classmethod
    def from_env(cls) -> "AgentHarness":
        """
        从环境变量创建

        Returns:
            AgentHarness: Harness 实例

        环境变量:
            ANTHROPIC_API_KEY or OPENAI_API_KEY
            HARNESS_MODEL
            HARNESS_MEMORY_DIR
            ...
        """
        import os

        config = HarnessConfig(
            model=os.getenv("HARNESS_MODEL", "claude-sonnet-4-6"),
            api_key=os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"),
            memory_dir=os.getenv("HARNESS_MEMORY_DIR", "~/.harness"),
            debug=os.getenv("HARNESS_DEBUG", "false").lower() == "true"
        )
        return cls(config)

    # ==================== 生命周期 ====================

    async def start(self):
        """
        启动 Harness（启动触发器等后台服务）
        """
        if self.config.triggers_enabled:
            await self.triggers.start()

        # 启动事件总线
        asyncio.create_task(self.events.run())

    async def stop(self):
        """
        停止 Harness
        """
        await self.triggers.stop()
```

## 返回类型

```python
@dataclass
class RunResult:
    """运行结果"""
    status: LoopState
    content: str
    messages: List[Message]
    iterations: int
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: TokenUsage = None
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == LoopState.COMPLETED

    @property
    def was_interrupted(self) -> bool:
        return self.status == LoopState.INTERRUPTED

    @property
    def was_stuck(self) -> bool:
        return self.status == LoopState.STUCK


@dataclass
class StreamChunk:
    """流式输出块"""
    type: ChunkType
    content: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None

    @property
    def is_text(self) -> bool:
        return self.type == ChunkType.TEXT

    @property
    def is_tool_call(self) -> bool:
        return self.type == ChunkType.TOOL_CALL_START
```

## 装饰器 API

```python
# 工具装饰器
@agent.tool(description="Get current weather")
async def get_weather(city: str, unit: str = "celsius") -> str:
    """获取指定城市的天气"""
    return f"Weather in {city}: 25°{unit[0].upper()}"

# 技能装饰器
@agent.skill(
    name="daily-brief",
    triggers=["brief", "summary", "report"]
)
async def daily_brief():
    """生成每日简报"""
    return """Generate a daily brief with:
1. Key activities from yesterday
2. Upcoming tasks
3. Important notifications"""

# 触发器装饰器
@agent.on_schedule("0 9 * * *")
async def morning_brief():
    return "Generate morning brief"

@agent.on_webhook("/slack/events")
async def handle_slack(payload):
    return f"Process Slack event: {payload['type']}"
```

## 上下文管理器

```python
class HarnessContext:
    """上下文管理器"""

    def __init__(self, agent: AgentHarness, session_id: str):
        self.agent = agent
        self.session_id = session_id
        self.session: Optional[Session] = None

    async def __aenter__(self) -> "HarnessContext":
        self.session = await self.agent.get_session(self.session_id)
        if not self.session:
            self.session = await self.agent.create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.agent.memory.update_session(self.session)

    async def run(self, prompt: str) -> RunResult:
        return await self.agent.run(prompt, session_id=self.session_id)

    async def stream(self, prompt: str) -> AsyncIterator[StreamChunk]:
        async for chunk in self.agent.stream(prompt, self.session_id):
            yield chunk


# 使用示例
async with agent.session("my-session") as ctx:
    result1 = await ctx.run("分析这个文件")
    result2 = await ctx.run("重构它")  # 保持上下文连续
```

## FastAPI 集成

```python
from fastapi import FastAPI
from harness import AgentHarness, HarnessContext

app = FastAPI()
agent = AgentHarness.from_config("harness.yaml")

@app.on_event("startup")
async def startup():
    await agent.start()

@app.on_event("shutdown")
async def shutdown():
    await agent.stop()

@app.post("/chat")
async def chat(message: str, session_id: str = None):
    """聊天接口"""
    result = await agent.run(message, session_id=session_id)
    return {
        "response": result.content,
        "session_id": result.session_id,
        "iterations": result.iterations
    }

@app.post("/chat/stream")
async def chat_stream(message: str, session_id: str = None):
    """流式聊天接口"""
    from fastapi.responses import StreamingResponse

    async def generate():
        async for chunk in agent.stream(message, session_id):
            yield f"data: {chunk.content}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# Webhook 端点
@app.post("/webhook/{trigger_id}")
async def handle_webhook(trigger_id: str, request: Request):
    """Webhook 处理"""
    payload = await request.json()
    # 触发器会自动处理
    return {"status": "ok"}
```

## CLI 工具

```python
# harness/cli.py
import click
import asyncio

@click.group()
def cli():
    """Harness CLI"""
    pass

@cli.command()
@click.argument("prompt")
@click.option("--session", "-s", help="Session ID")
@click.option("--stream", is_flag=True, help="Stream output")
def run(prompt: str, session: str, stream: bool):
    """运行 agent"""
    agent = AgentHarness.from_env()

    if stream:
        async def main():
            async for chunk in agent.stream(prompt, session):
                print(chunk.content, end="", flush=True)
            print()
        asyncio.run(main())
    else:
        result = agent.run_sync(prompt, session)
        print(result.content)

@cli.command()
def sessions():
    """列出所有会话"""
    agent = AgentHarness.from_env()
    for session_id in asyncio.run(agent.list_sessions()):
        print(session_id)

@cli.command()
@click.argument("session_id")
def session(session_id: str):
    """显示会话详情"""
    agent = AgentHarness.from_env()
    session = asyncio.run(agent.get_session(session_id))
    if session:
        print(f"Session: {session.id}")
        print(f"Messages: {len(session.messages)}")
        for msg in session.messages[-5:]:
            print(f"  {msg.role}: {msg.content[:50]}...")

@cli.command()
def skills():
    """列出所有技能"""
    agent = AgentHarness.from_env()
    for skill in agent.skills.list_skills():
        print(f"{skill.name}: {skill.description}")

@cli.command()
def triggers():
    """列出所有触发器"""
    agent = AgentHarness.from_env()
    for trigger in agent.triggers.list_triggers():
        print(f"{trigger['id']}: {trigger['type']} ({'enabled' if trigger['enabled'] else 'disabled'})")

@cli.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8000)
def serve(host: str, port: int):
    """启动 HTTP 服务"""
    import uvicorn
    from harness.server import create_app

    app = create_app()
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    cli()
```

## 配置文件格式

```yaml
# harness.yaml

# LLM 配置
model: claude-sonnet-4-6
api_key: ${ANTHROPIC_API_KEY}  # 支持环境变量
temperature: 0.7
max_tokens: 4096

# 记忆配置
memory:
  type: sqlite
  path: ~/.harness/harness.db
  max_context_tokens: 200000
  auto_compress: true
  compression_threshold: 0.8

# 工具配置
tools:
  enabled:
    - read
    - write
    - edit
    - glob
    - grep
    - bash
    - web_search
  permission_mode: sandbox
  sandbox_paths:
    - /workspace
  blocked_commands:
    - rm -rf /
    - sudo

# 技能配置
skills:
  directories:
    - ~/.harness/skills
    - ./skills
  auto_load: true

# 触发器配置
triggers:
  - type: cron
    schedule: "0 9 * * *"
    prompt: "Generate daily report"
    output_channels:
      - console

  - type: webhook
    endpoint: /webhook/github
    prompt: "Process GitHub webhook"
    verify_signature: true

# 日志配置
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: ~/.harness/harness.log

# 调试
debug: false
```

## 错误处理

```python
from harness import HarnessError, LLMError, ToolError

try:
    result = await agent.run("分析代码")
except LLMError as e:
    print(f"LLM 错误: {e}")
except ToolError as e:
    print(f"工具错误: {e}")
except HarnessError as e:
    print(f"Harness 错误: {e}")
```

## 测试支持

```python
from harness.testing import MockHarness, MockTool

# 创建 mock harness
agent = MockHarness()

# 设置预期响应
agent.expect("分析代码").respond("代码分析结果...")

# 运行测试
result = await agent.run("分析代码")
assert result.content == "代码分析结果..."
```

---

## 可观测性 API

Harness 内置 OpenTelemetry 集成，支持 Jaeger、Datadog、Langfuse 等 OTel 兼容后端。

### 快速开始

```python
from harness import AgentHarness, setup_observability, ObservabilityConfig

# 方式1：全局设置
setup_observability(ObservabilityConfig(
    service_name="my-agent",
    export_console=True,  # 调试时输出到控制台
))

# 方式2：OTLP 导出（生产环境）
setup_observability(ObservabilityConfig(
    service_name="my-agent",
    export_otlp=True,
    otlp_endpoint="http://jaeger:4317",  # OTLP gRPC 端点
))

# 创建 Agent，追踪自动启用
agent = AgentHarness(model="claude-sonnet-4-6")
result = await agent.run("分析代码")  # 自动追踪
```

### ObservabilityManager

```python
from harness import ObservabilityManager, ObservabilityConfig

# 创建管理器
manager = ObservabilityManager(config=ObservabilityConfig(
    service_name="harness-agent",
    service_version="1.0.0",
    enabled=True,
    export_console=False,
    export_otlp=True,
    otlp_endpoint="http://localhost:4317",
    sample_rate=1.0,  # 采样率 1.0 = 100%
))

# 初始化
manager.setup()

# 检查是否启用
if manager.is_enabled:
    print("OpenTelemetry 追踪已启用")

# 关闭
manager.shutdown()
```

### 手动追踪

```python
from harness import get_tracer, traced_operation

# 使用上下文管理器追踪操作
async with traced_operation("custom_operation", {"key": "value"}):
    # 业务逻辑
    pass

# 获取 tracer 自定义追踪
tracer = get_tracer()
if tracer:
    with tracer.start_as_current_span("my_span") as span:
        span.set_attribute("user.id", "user-123")
        # 业务逻辑
```

### 配置选项

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `service_name` | str | "harness-agent" | 服务名称 |
| `service_version` | str | "0.1.0" | 服务版本 |
| `enabled` | bool | True | 是否启用 |
| `export_console` | bool | False | 输出到控制台 |
| `export_otlp` | bool | False | 导出到 OTLP 端点 |
| `otlp_endpoint` | str | "http://localhost:4317" | OTLP gRPC 端点 |
| `sample_rate` | float | 1.0 | 采样率 (0.0-1.0) |

### 依赖安装

```bash
# 基础 OpenTelemetry
pip install harness-ai[observability]

# OTLP 导出（生产环境）
pip install opentelemetry-exporter-otlp
```

---

## 成本控制 API

Harness 支持多层级成本控制：会话级、用户级、全局级。

### CostStorage

```python
from harness import CostStorage, InMemoryCostStorage

# 内存存储（单进程应用）
storage = InMemoryCostStorage()

# 记录用户使用量
usage = storage.record_user_usage(
    user_id="user-123",
    input_tokens=1000,
    output_tokens=500,
    request=True,  # 计入请求次数
)
print(f"每日 Token: {usage.daily_tokens}")
print(f"每小时请求: {usage.hourly_requests}")

# 获取用户使用量
usage = storage.get_user_usage("user-123")

# 获取全局使用量
global_usage = storage.get_global_usage()
print(f"全局每日成本: ${global_usage.daily_cost_usd:.4f}")

# 重置每日计数（通常由定时任务调用）
storage.reset_daily()
```

### SQLite 持久化存储

```python
from harness.core.cost_storage import SQLiteCostStorage

# SQLite 持久化存储（生产环境）
storage = SQLiteCostStorage(db_path="~/.harness/costs.db")

# API 与 InMemoryCostStorage 相同
usage = storage.record_user_usage("user-123", input_tokens=1000)
```

### 与 CostController 集成

```python
from harness import AgentHarness, CostController, CostConfig, InMemoryCostStorage

# 创建成本控制器
storage = InMemoryCostStorage()
cost_controller = CostController(
    config=CostConfig(
        session_budget=10.0,      # 会话预算 $10
        user_daily_budget=50.0,   # 用户每日预算 $50
        global_daily_budget=500.0, # 全局每日预算 $500
    ),
    storage=storage,
)

# 创建 Agent
agent = AgentHarness(
    model="claude-sonnet-4-6",
    cost_controller=cost_controller,
)

# 运行时自动检查预算
result = await agent.run("分析代码")
```

### 使用量类型

| 类型 | 字段 | 说明 |
|-----|------|------|
| `UserUsage` | `user_id`, `daily_tokens`, `hourly_requests` | 用户级使用量 |
| `GlobalUsage` | `daily_cost_usd`, `daily_tokens` | 全局使用量 |
| `BudgetStatus` | `spent`, `remaining`, `percentage` | 预算状态 |

---

## 异步 API 使用指南

### run_sync() 的使用限制

`run_sync()` 方法仅适用于以下场景：
- CLI 脚本
- 独立 Python 脚本（无事件循环）

**不适用于**：
- Jupyter Notebook（使用 `await agent.run()`）
- FastAPI/Starlette（使用 `await agent.run()`）
- 已有 asyncio 事件循环环境

```python
# ✅ 正确：CLI 脚本
if __name__ == "__main__":
    agent = AgentHarness(model="claude-sonnet-4-6")
    result = agent.run_sync("分析代码")  # OK

# ✅ 正确：Jupyter Notebook
result = await agent.run("分析代码")

# ✅ 正确：FastAPI
@app.post("/chat")
async def chat(message: str):
    result = await agent.run(message)  # 使用 async API

# ❌ 错误：在异步上下文中使用 run_sync
async def wrong_usage():
    result = agent.run_sync("hello")  # RuntimeError!
```

### 检测已有事件循环

```python
class AgentHarness:
    def run_sync(self, prompt: str, **kwargs) -> "RunResult":
        import asyncio

        # 检测是否已有事件循环运行
        try:
            loop = asyncio.get_running_loop()
            raise RuntimeError(
                "run_sync() cannot be called from an async context. "
                "Use 'await agent.run()' instead."
            )
        except RuntimeError as e:
            if "no running event loop" in str(e):
                pass  # 正常：没有事件循环
            else:
                raise

        return asyncio.run(self.run(prompt, **kwargs))
```

### 同步包装器（遗留代码兼容）

```python
def sync_wrapper(agent, prompt):
    """在独立线程中运行异步代码"""
    import asyncio
    import threading

    result = None
    exception = None

    def run_in_thread():
        nonlocal result, exception
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(agent.run(prompt))
        except Exception as e:
            exception = e
        finally:
            loop.close()

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()

    if exception:
        raise exception
    return result
```

---

## Builder 模式 API

`AgentHarness.__init__` 承担过多职责，配置项爆炸。采用 Builder 模式保持组件解耦。

```python
from typing import Optional, List, Union
from dataclasses import dataclass

@dataclass
class HarnessComponents:
    """Harness 组件容器"""
    llm: Optional[LLMClient] = None
    memory: Optional[SessionStore] = None
    tools: Optional[ToolRegistry] = None
    skills: Optional[SkillRegistry] = None
    triggers: Optional[TriggerManager] = None
    security: Optional[SecurityManager] = None
    observability: Optional[ObservabilityManager] = None


class HarnessBuilder:
    """Harness 构建器"""

    def __init__(self):
        self._components = HarnessComponents()

    def with_llm(
        self,
        model: str,
        api_key: str = None,
        provider: str = "anthropic",
        **kwargs
    ) -> "HarnessBuilder":
        """配置 LLM"""
        if provider == "anthropic":
            self._components.llm = AnthropicClient(
                api_key=api_key,
                model=model,
                **kwargs
            )
        elif provider == "openai":
            self._components.llm = OpenAIClient(
                api_key=api_key,
                model=model,
                **kwargs
            )
        return self

    def with_memory(
        self,
        store: Union[str, SessionStore],
        **kwargs
    ) -> "HarnessBuilder":
        """配置记忆存储"""
        if isinstance(store, str):
            if store == "file":
                self._components.memory = FileSessionStore(**kwargs)
            elif store == "sqlite":
                self._components.memory = ProductionSQLiteStore(**kwargs)
            elif store == "redis":
                self._components.memory = RedisSessionStore(**kwargs)
        else:
            self._components.memory = store
        return self

    def with_tools(
        self,
        tools: List[Tool],
        permissions: PermissionSet = None
    ) -> "HarnessBuilder":
        """配置工具集"""
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)
        self._components.tools = registry
        return self

    def with_security(
        self,
        mode: str = "sandbox",
        **kwargs
    ) -> "HarnessBuilder":
        """配置安全策略"""
        if mode == "sandbox":
            self._components.security = SecurityManager(
                permissions=PermissionSet.sandbox(**kwargs)
            )
        elif mode == "readonly":
            self._components.security = SecurityManager(
                permissions=PermissionSet.read_only(**kwargs)
            )
        return self

    def with_observability(
        self,
        backend: str = "opentelemetry",
        **kwargs
    ) -> "HarnessBuilder":
        """配置可观测性"""
        self._components.observability = ObservabilityManager(
            backend=backend,
            **kwargs
        )
        return self

    def with_skills(self, skill_dirs: List[str]) -> "HarnessBuilder":
        """配置技能目录"""
        registry = SkillRegistry()
        for dir_path in skill_dirs:
            registry.add_skill_dir(Path(dir_path))
        self._components.skills = registry
        return self

    def build(self) -> "AgentHarness":
        """构建 Harness 实例"""
        if not self._components.llm:
            raise ValueError("LLM client is required")

        # 使用默认值填充缺失组件
        if not self._components.memory:
            self._components.memory = FileSessionStore()

        if not self._components.tools:
            self._components.tools = ToolRegistry()
            self._components.tools.register_defaults()

        if not self._components.security:
            self._components.security = SecurityManager(
                permissions=PermissionSet.sandbox()
            )

        return AgentHarness(components=self._components)


# 使用示例
agent = (HarnessBuilder()
    .with_llm("claude-sonnet-4-6", api_key=os.environ["ANTHROPIC_API_KEY"])
    .with_memory("sqlite", db_path="~/.harness/harness.db")
    .with_tools([ReadTool(), BashTool(), GrepTool()])
    .with_security("sandbox", workspace="/workspace")
    .with_observability("opentelemetry", service_name="my-agent")
    .with_skills(["./skills", "~/.harness/skills"])
    .build()
)
```

---

## API 稳定性分类

### Public API (稳定，向后兼容)

```python
# 核心接口
AgentHarness.run(prompt, session_id)
AgentHarness.stream(prompt, session_id)
AgentHarness.interrupt()

# 工具注册
AgentHarness.register_tool(tool)
@agent.tool()

# 技能管理
AgentHarness.load_skill(path)
AgentHarness.activate_skill(name)

# 记忆
AgentHarness.remember(content, type)
AgentHarness.recall(query)

# 会话存储
SessionStore, FileSessionStore, SQLiteSessionStore, AsyncSQLiteSessionStore

# 成本控制
CostController, CostStorage, InMemoryCostStorage, CostConfig

# 可观测性
ObservabilityManager, ObservabilityConfig, setup_observability
```

### Beta API (可能变更)

```python
# 触发器
AgentHarness.on_schedule(cron, prompt)
AgentHarness.on_webhook(endpoint, prompt)

# 中断恢复
AgentHarness.resume(session_id)

# 可观测性
AgentHarness.get_traces()

# SQLite 成本存储
SQLiteCostStorage
```

### Internal API (不保证兼容)

```python
# 内部组件
AgentHarness._loop
AgentHarness._components
ContextBuilder._compress_context()
```

---

## 配置类 API

Harness 提供四个配置类，用于精细控制 Agent 行为。这些配置可直接传入 `HarnessConfig`。

### SecurityConfig - 安全配置

控制输入验证、输出脱敏、审计日志、沙箱执行。

```python
from harness import AgentHarness, HarnessConfig, SecurityConfig

# 完整配置
security_config = SecurityConfig(
    # 输入验证
    enable_input_validation=True,
    max_input_length=100000,
    check_prompt_injection=True,

    # 输出脱敏
    enable_output_sanitization=True,
    max_output_length=100000,

    # 审计日志
    enable_audit_log=True,
    audit_log_dir="~/.harness/audit",
    audit_retention_days=30,

    # 沙箱设置
    enable_sandbox=True,
    sandbox_max_execution_time=30.0,
    sandbox_max_output_size=1_000_000,  # 1MB
    sandbox_blocked_commands=[
        "rm -rf /",
        "sudo",
        "chmod -R 777",
    ],
    sandbox_allowed_commands=None,  # None = 允许所有非禁止命令
)

# 与 AgentHarness 集成
agent = AgentHarness(
    model="claude-sonnet-4-6",
    config=HarnessConfig(
        security=security_config,
    ),
)
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `enable_input_validation` | bool | True | 启用输入验证 |
| `max_input_length` | int | 100000 | 最大输入长度 |
| `check_prompt_injection` | bool | True | 检测提示注入攻击 |
| `enable_output_sanitization` | bool | True | 启用输出脱敏 |
| `max_output_length` | int | 100000 | 最大输出长度 |
| `enable_audit_log` | bool | True | 启用审计日志 |
| `audit_log_dir` | str | "~/.harness/audit" | 审计日志目录 |
| `audit_retention_days` | int | 30 | 日志保留天数 |
| `enable_sandbox` | bool | True | 启用沙箱执行 |
| `sandbox_max_execution_time` | float | 30.0 | 最大执行时间（秒） |
| `sandbox_max_output_size` | int | 1000000 | 最大输出大小（字节） |
| `sandbox_blocked_commands` | list[str] | [...] | 禁止的命令列表 |
| `sandbox_allowed_commands` | list[str] \| None | None | 允许的命令白名单 |

---

### CostControlConfig - 成本控制配置

多层级成本控制：会话级、用户级、全局级。

```python
from harness import AgentHarness, HarnessConfig, CostControlConfig

cost_config = CostControlConfig(
    # 会话级限制
    max_tokens_per_session=1_000_000,
    max_tool_calls_per_session=500,
    max_iterations_per_request=20,

    # 用户级限制
    daily_token_limit=10_000_000,
    hourly_request_limit=100,

    # 全局限制
    global_daily_budget_usd=100.0,
    auto_throttle=True,  # 自动节流

    # 自适应降级
    fallback_model="claude-haiku-4-5",
    context_reduction_ratio=0.5,

    # 警告阈值
    warning_threshold=0.8,  # 使用 80% 时警告
)

agent = AgentHarness(
    model="claude-sonnet-4-6",
    config=HarnessConfig(
        cost_control=cost_config,
    ),
)
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `max_tokens_per_session` | int | 1000000 | 每会话最大 Token |
| `max_tool_calls_per_session` | int | 500 | 每会话最大工具调用 |
| `max_iterations_per_request` | int | 20 | 每请求最大迭代 |
| `daily_token_limit` | int | 10000000 | 每日 Token 限制（用户级） |
| `hourly_request_limit` | int | 100 | 每小时请求限制 |
| `global_daily_budget_usd` | float | 100.0 | 全局每日预算（美元） |
| `auto_throttle` | bool | True | 自动节流 |
| `fallback_model` | str \| None | None | 预算不足时的降级模型 |
| `context_reduction_ratio` | float | 0.5 | 上下文压缩比例 |
| `warning_threshold` | float | 0.8 | 警告阈值 (0.0-1.0) |

---

### ObservabilityConfig - 可观测性配置

OpenTelemetry 集成，支持 Jaeger、Datadog 等。

```python
from harness import AgentHarness, HarnessConfig, ObservabilityConfig

# 控制台输出（调试）
obs_config = ObservabilityConfig(
    enabled=True,
    service_name="my-agent",
    export_console=True,
)

# OTLP 导出（生产）
obs_config = ObservabilityConfig(
    enabled=True,
    service_name="production-agent",
    export_otlp=True,
    otlp_endpoint="http://jaeger:4317",
    sample_rate=1.0,
)

agent = AgentHarness(
    model="claude-sonnet-4-6",
    config=HarnessConfig(
        observability=obs_config,
    ),
)
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `enabled` | bool | False | 是否启用 |
| `service_name` | str | "harness-agent" | 服务名称 |
| `service_version` | str | "0.1.0" | 服务版本 |
| `export_console` | bool | False | 输出到控制台 |
| `export_otlp` | bool | False | 导出到 OTLP |
| `otlp_endpoint` | str | "http://localhost:4317" | OTLP gRPC 端点 |
| `sample_rate` | float | 1.0 | 采样率 (0.0-1.0) |

---

### StorageConfig - 存储配置

会话存储配置，支持文件或 SQLite。

```python
from harness import AgentHarness, HarnessConfig, StorageConfig

# 文件存储（默认）
storage_config = StorageConfig(
    type="file",
    storage_dir=".harness/sessions",
)

# SQLite 存储（生产）
storage_config = StorageConfig(
    type="sqlite",
    sqlite_path=".harness/harness.db",
    async_mode=True,
    pool_size=5,
)

agent = AgentHarness(
    model="claude-sonnet-4-6",
    config=HarnessConfig(
        storage=storage_config,
    ),
)
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `type` | "file" \| "sqlite" | "file" | 存储类型 |
| `storage_dir` | str | ".harness/sessions" | 文件存储目录 |
| `sqlite_path` | str | ".harness/harness.db" | SQLite 数据库路径 |
| `async_mode` | bool | True | 异步模式（仅 SQLite） |
| `pool_size` | int | 5 | 连接池大小（仅异步 SQLite） |

---

### 完整配置示例

```python
from harness import (
    AgentHarness,
    HarnessConfig,
    SecurityConfig,
    CostControlConfig,
    ObservabilityConfig,
    StorageConfig,
)

agent = AgentHarness(
    model="claude-sonnet-4-6",
    config=HarnessConfig(
        # LLM 配置
        api_key="your-api-key",
        base_url="https://api.example.com/v1",  # 第三方 API

        # 安全配置
        security=SecurityConfig(
            enable_input_validation=True,
            check_prompt_injection=True,
            enable_audit_log=True,
        ),

        # 成本控制
        cost_control=CostControlConfig(
            max_tokens_per_session=500000,
            global_daily_budget_usd=50.0,
            fallback_model="claude-haiku-4-5",
        ),

        # 可观测性
        observability=ObservabilityConfig(
            enabled=True,
            export_console=True,
        ),

        # 存储
        storage=StorageConfig(
            type="sqlite",
            sqlite_path=".harness/production.db",
        ),
    ),
)

result = await agent.run("分析代码")
```
