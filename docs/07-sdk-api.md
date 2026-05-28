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
        **kwargs
    ) -> "RunResult":
        """
        运行 agent（异步）

        Args:
            prompt: 用户输入
            session_id: 会话 ID，如果为 None 则创建新会话
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
        async for chunk in self._loop.stream(prompt, session_id):
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
