# 06 - Trigger & Orchestration 触发与编排

> **注意**: 完整的触发器系统是计划功能，当前版本仅实现了 `SkillTrigger`（技能触发器）。本文档描述的是完整的设计架构，具体实现将在后续版本中完成。

## 概述

Trigger System 让 Agent 能够自主运行，不仅响应用户消息，还能根据时间、事件、状态变化自动触发执行。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     Trigger System                           │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Trigger Sources                     │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │  User       │ │  Cron       │ │  Webhook    │    │   │
│  │  │  Message    │ │  Scheduler  │ │  Handler    │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │  Heartbeat  │ │  File Watch │ │  Event Bus  │    │   │
│  │  │  Monitor    │ │             │ │             │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Trigger Manager                      │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │  Registry   │ │  Priority   │ │  Execution  │    │   │
│  │  │             │ │  Queue      │ │  Scheduler  │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Agent Loop                          │   │
│  │                                                       │   │
│  │  Trigger → Context → LLM → Tools → Result            │   │
│  │                                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                               │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 Action Handler                        │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │  Message    │ │  File       │ │  External   │    │   │
│  │  │  Output     │ │  Update     │ │  API Call   │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 触发类型

### Trigger Type 定义

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import asyncio
import croniter

class TriggerType(Enum):
    USER_MESSAGE = "user_message"      # 用户消息触发
    CRON = "cron"                       # 定时触发
    WEBHOOK = "webhook"                 # HTTP webhook
    HEARTBEAT = "heartbeat"             # 周期性心跳
    FILE_WATCH = "file_watch"           # 文件变化
    EVENT = "event"                     # 事件总线
    CONDITION = "condition"             # 条件触发

@dataclass
class TriggerEvent:
    """触发事件"""
    trigger_type: TriggerType
    trigger_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    priority: int = 0

    @property
    def is_scheduled(self) -> bool:
        return self.trigger_type == TriggerType.CRON

    @property
    def is_external(self) -> bool:
        return self.trigger_type in [TriggerType.WEBHOOK, TriggerType.EVENT]


class Trigger(ABC):
    """触发器基类"""

    trigger_type: TriggerType
    id: str = ""

    @abstractmethod
    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查是否应该触发"""
        pass

    @abstractmethod
    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        """创建触发事件"""
        pass

    @abstractmethod
    async def start(self, callback: Callable[[TriggerEvent], None]):
        """启动触发器（对于持续型触发器）"""
        pass

    @abstractmethod
    async def stop(self):
        """停止触发器"""
        pass


@dataclass
class TriggerAction:
    """触发后的动作"""
    agent_prompt: str                    # 发送给 Agent 的提示
    session_id: Optional[str] = None     # 使用哪个会话
    skills_to_activate: List[str] = field(default_factory=list)
    output_channels: List[str] = field(default_factory=list)
    save_result: bool = True
    retry_on_failure: int = 0
```

### 6.1 Cron Trigger

```python
class CronTrigger(Trigger):
    """定时触发器"""

    trigger_type = TriggerType.CRON

    def __init__(
        self,
        schedule: str,          # cron 表达式
        action: TriggerAction,
        timezone: str = "local",
        jitter_seconds: int = 0  # 添加随机延迟避免同时触发
    ):
        self.schedule = schedule
        self.action = action
        self.timezone = timezone
        self.jitter_seconds = jitter_seconds
        self._cron = croniter.croniter(schedule)
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查是否到达触发时间"""
        now = datetime.now()
        next_run = self._cron.get_next(datetime)
        return now >= next_run

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.CRON,
            trigger_id=self.id,
            payload={
                "schedule": self.schedule,
                "action": self.action,
                **(payload or {})
            }
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """启动定时器"""
        self._running = True
        self._task = asyncio.create_task(self._run_loop(callback))

    async def stop(self):
        """停止定时器"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self, callback: Callable[[TriggerEvent], None]):
        """定时运行循环"""
        while self._running:
            # 计算下次运行时间
            now = datetime.now()
            next_run = self._cron.get_next(datetime)
            wait_seconds = (next_run - now).total_seconds()

            # 添加 jitter
            if self.jitter_seconds > 0:
                import random
                wait_seconds += random.uniform(0, self.jitter_seconds)

            # 等待
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            # 触发
            if self._running:
                try:
                    event = self.create_event()
                    callback(event)
                except Exception as e:
                    print(f"Cron trigger error: {e}")

    def get_next_runs(self, n: int = 5) -> List[datetime]:
        """获取接下来的 N 次运行时间"""
        return [self._cron.get_next(datetime) for _ in range(n)]


# 使用示例
daily_report = CronTrigger(
    schedule="0 9 * * *",      # 每天 9:00
    action=TriggerAction(
        agent_prompt="Generate daily report summarizing yesterday's activities",
        skills_to_activate=["report"],
        output_channels=["email", "slack"]
    )
)

hourly_check = CronTrigger(
    schedule="0 * * * *",      # 每小时
    action=TriggerAction(
        agent_prompt="Check system health and report any issues",
        output_channels=["slack"]
    ),
    jitter_seconds=300         # 添加最多 5 分钟随机延迟
)
```

### 6.2 Webhook Trigger

```python
from fastapi import FastAPI, Request, Response
import hashlib
import hmac

@dataclass
class WebhookConfig:
    """Webhook 配置"""
    endpoint: str              # URL 路径
    secret: Optional[str] = None  # 验证签名
    allowed_sources: List[str] = field(default_factory=list)
    verify_signature: bool = False
    rate_limit: int = 100      # 每分钟限制


class WebhookTrigger(Trigger):
    """HTTP Webhook 触发器"""

    trigger_type = TriggerType.WEBHOOK

    def __init__(
        self,
        config: WebhookConfig,
        action: TriggerAction,
        payload_transform: Callable[[dict], dict] = None
    ):
        self.config = config
        self.action = action
        self.payload_transform = payload_transform
        self._callback: Optional[Callable] = None

    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查请求是否有效"""
        request = context.get("request")

        # 检查来源
        if self.config.allowed_sources:
            source = request.headers.get("X-Forwarded-For", "")
            if source not in self.config.allowed_sources:
                return False

        return True

    def verify_signature(self, request: Request, body: bytes) -> bool:
        """验证签名"""
        if not self.config.secret:
            return True

        signature = request.headers.get("X-Signature", "")
        expected = hmac.new(
            self.config.secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.WEBHOOK,
            trigger_id=self.id,
            payload=payload,
            source=payload.get("source", "webhook")
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """注册 webhook endpoint"""
        self._callback = callback

    async def stop(self):
        """注销 webhook"""
        self._callback = None

    async def handle_request(self, request: Request) -> Response:
        """处理 webhook 请求"""
        body = await request.body()

        # 验证签名
        if self.config.verify_signature:
            if not self.verify_signature(request, body):
                return Response(status_code=401, content="Invalid signature")

        # 解析 payload
        try:
            import json
            payload = json.loads(body)
        except json.JSONDecodeError:
            return Response(status_code=400, content="Invalid JSON")

        # 转换 payload
        if self.payload_transform:
            payload = self.payload_transform(payload)

        # 创建事件并回调
        event = self.create_event(payload)
        if self._callback:
            self._callback(event)

        return Response(status_code=200, content="OK")


# Webhook Manager
class WebhookManager:
    """管理所有 webhook"""

    def __init__(self, app: FastAPI = None):
        self.app = app or FastAPI()
        self.triggers: Dict[str, WebhookTrigger] = {}

    def register(self, trigger: WebhookTrigger):
        """注册 webhook"""
        self.triggers[trigger.config.endpoint] = trigger

        # 创建路由
        @self.app.post(trigger.config.endpoint)
        async def handle(request: Request):
            return await trigger.handle_request(request)

    def unregister(self, endpoint: str):
        """注销 webhook"""
        if endpoint in self.triggers:
            del self.triggers[endpoint]


# 使用示例
github_pr_webhook = WebhookTrigger(
    config=WebhookConfig(
        endpoint="/webhook/github",
        secret="your-webhook-secret",
        verify_signature=True
    ),
    action=TriggerAction(
        agent_prompt="Review the pull request changes",
        skills_to_activate=["code-review"]
    ),
    payload_transform=lambda p: {
        "pr_number": p.get("number"),
        "repo": p.get("repository", {}).get("full_name"),
        "action": p.get("action")
    }
)
```

### 6.3 Heartbeat Trigger

```python
class HeartbeatTrigger(Trigger):
    """心跳触发器"""

    trigger_type = TriggerType.HEARTBEAT

    def __init__(
        self,
        interval_seconds: int,
        action: TriggerAction,
        check_conditions: Callable[[], bool] = None
    ):
        self.interval = interval_seconds
        self.action = action
        self.check_conditions = check_conditions
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查条件"""
        if self.check_conditions:
            return self.check_conditions()
        return True

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.HEARTBEAT,
            trigger_id=self.id,
            payload={
                "interval": self.interval,
                "timestamp": datetime.now().isoformat(),
                **(payload or {})
            }
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """启动心跳"""
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop(callback))

    async def stop(self):
        """停止心跳"""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _heartbeat_loop(self, callback: Callable[[TriggerEvent], None]):
        """心跳循环"""
        while self._running:
            await asyncio.sleep(self.interval)

            if self._running and self.should_fire({}):
                event = self.create_event()
                callback(event)
```

### 6.4 File Watch Trigger

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

class FileWatchTrigger(Trigger):
    """文件变化触发器"""

    trigger_type = TriggerType.FILE_WATCH

    def __init__(
        self,
        watch_path: str,
        action: TriggerAction,
        patterns: List[str] = None,      # 只监听特定模式
        ignore_patterns: List[str] = None
    ):
        self.watch_path = watch_path
        self.action = action
        self.patterns = patterns or ["*"]
        self.ignore_patterns = ignore_patterns or []
        self._observer: Optional[Observer] = None
        self._callback: Optional[Callable] = None

    def should_fire(self, context: Dict[str, Any]) -> bool:
        """检查文件变化是否匹配模式"""
        path = context.get("path", "")
        import fnmatch

        # 检查是否匹配监听模式
        for pattern in self.patterns:
            if fnmatch.fnmatch(path, pattern):
                break
        else:
            return False

        # 检查是否在忽略列表
        for ignore in self.ignore_patterns:
            if fnmatch.fnmatch(path, ignore):
                return False

        return True

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.FILE_WATCH,
            trigger_id=self.id,
            payload={
                "path": payload.get("path"),
                "event_type": payload.get("event_type"),
                **payload
            }
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """启动文件监听"""
        self._callback = callback
        self._observer = Observer()

        handler = self._create_handler()
        self._observer.schedule(handler, self.watch_path, recursive=True)
        self._observer.start()

    async def stop(self):
        """停止监听"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
        self._callback = None

    def _create_handler(self) -> FileSystemEventHandler:
        """创建文件事件处理器"""
        class Handler(FileSystemEventHandler):
            def __init__(self, trigger):
                self.trigger = trigger

            def on_modified(self, event):
                if event.is_directory:
                    return

                path = event.src_path
                if self.trigger.should_fire({"path": path}):
                    event_obj = self.trigger.create_event({
                        "path": path,
                        "event_type": "modified"
                    })
                    if self.trigger._callback:
                        self.trigger._callback(event_obj)

        return Handler(self)


# 使用示例
config_watch = FileWatchTrigger(
    watch_path="~/.harness/config",
    action=TriggerAction(
        agent_prompt="Configuration file changed, reload settings",
        skills_to_activate=["config-reload"]
    ),
    patterns=["*.yaml", "*.json"],
    ignore_patterns=["*.bak", "*.tmp"]
)
```

### 6.5 Event Bus Trigger

```python
from collections import defaultdict
import asyncio

class EventBus:
    """事件总线"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._queue: asyncio.Queue = asyncio.Queue()

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event_type: str, payload: Dict[str, Any]):
        """发布事件"""
        self._queue.put_nowait((event_type, payload))

    async def run(self):
        """运行事件处理循环"""
        while True:
            event_type, payload = await self._queue.get()

            for callback in self._subscribers[event_type]:
                try:
                    await callback(payload)
                except Exception as e:
                    print(f"Event handler error: {e}")


class EventBusTrigger(Trigger):
    """事件总线触发器"""

    trigger_type = TriggerType.EVENT

    def __init__(
        self,
        event_type: str,
        action: TriggerAction,
        event_bus: EventBus
    ):
        self.event_type = event_type
        self.action = action
        self.event_bus = event_bus
        self._registered = False

    def should_fire(self, context: Dict[str, Any]) -> bool:
        return True

    def create_event(self, payload: Dict[str, Any] = None) -> TriggerEvent:
        return TriggerEvent(
            trigger_type=TriggerType.EVENT,
            trigger_id=self.id,
            payload={
                "event_type": self.event_type,
                **(payload or {})
            }
        )

    async def start(self, callback: Callable[[TriggerEvent], None]):
        """订阅事件"""
        def handler(payload):
            event = self.create_event(payload)
            callback(event)

        self.event_bus.subscribe(self.event_type, handler)
        self._registered = True

    async def stop(self):
        """取消订阅"""
        self.event_bus.unsubscribe(self.event_type, None)


# 使用示例
bus = EventBus()

user_login_trigger = EventBusTrigger(
    event_type="user.login",
    action=TriggerAction(
        agent_prompt="New user logged in, send welcome message"
    ),
    event_bus=bus
)

# 发布事件
bus.publish("user.login", {"user_id": "123", "name": "John"})
```

## Trigger Manager

```python
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import asyncio
from datetime import datetime
from queue import PriorityQueue

@dataclass
class TriggerRegistration:
    """触发器注册信息"""
    trigger: Trigger
    action: TriggerAction
    enabled: bool = True
    last_fired: Optional[datetime] = None
    fire_count: int = 0
    error_count: int = 0


class TriggerManager:
    """触发器管理器"""

    def __init__(self, agent_harness: "AgentHarness"):
        self.harness = agent_harness
        self._registrations: Dict[str, TriggerRegistration] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._priority_queue: PriorityQueue = PriorityQueue()
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

    def register(
        self,
        trigger: Trigger,
        action: TriggerAction,
        enabled: bool = True
    ) -> str:
        """注册触发器"""
        trigger_id = trigger.id or self._generate_id()
        trigger.id = trigger_id

        self._registrations[trigger_id] = TriggerRegistration(
            trigger=trigger,
            action=action,
            enabled=enabled
        )

        return trigger_id

    def unregister(self, trigger_id: str):
        """注销触发器"""
        if trigger_id in self._registrations:
            reg = self._registrations[trigger_id]
            asyncio.create_task(reg.trigger.stop())
            del self._registrations[trigger_id]

    def enable(self, trigger_id: str):
        """启用触发器"""
        if trigger_id in self._registrations:
            self._registrations[trigger_id].enabled = True

    def disable(self, trigger_id: str):
        """禁用触发器"""
        if trigger_id in self._registrations:
            self._registrations[trigger_id].enabled = False

    async def start(self):
        """启动所有触发器"""
        self._running = True

        # 启动事件处理器
        self._processor_task = asyncio.create_task(self._process_events())

        # 启动所有触发器
        for reg in self._registrations.values():
            if reg.enabled:
                await reg.trigger.start(self._enqueue_event)

    async def stop(self):
        """停止所有触发器"""
        self._running = False

        # 停止所有触发器
        for reg in self._registrations.values():
            await reg.trigger.stop()

        # 停止处理器
        if self._processor_task:
            self._processor_task.cancel()

    def _enqueue_event(self, event: TriggerEvent):
        """将事件加入队列"""
        self._event_queue.put_nowait(event)

    async def _process_events(self):
        """处理事件队列"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )

                await self._handle_event(event)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _handle_event(self, event: TriggerEvent):
        """处理单个事件"""
        trigger_id = event.trigger_id

        if trigger_id not in self._registrations:
            return

        reg = self._registrations[trigger_id]

        if not reg.enabled:
            return

        try:
            # 获取或创建会话
            session_id = reg.action.session_id
            if session_id:
                session = await self.harness.memory.get_session(session_id)
            else:
                session = await self.harness.memory.create_session()

            # 构建提示
            prompt = self._build_prompt(reg.action, event)

            # 激活技能
            for skill_name in reg.action.skills_to_activate:
                self.harness.skills.activate(skill_name)

            # 运行 Agent
            result = await self.harness.run(prompt, session.id)

            # 输出结果
            await self._handle_output(result, reg.action)

            # 更新统计
            reg.last_fired = datetime.now()
            reg.fire_count += 1

        except Exception as e:
            reg.error_count += 1
            print(f"Trigger execution error: {e}")

            # 重试
            if reg.action.retry_on_failure > 0:
                await self._retry(reg, event)

    def _build_prompt(self, action: TriggerAction, event: TriggerEvent) -> str:
        """构建提示"""
        prompt = action.agent_prompt

        # 添加事件上下文
        if event.payload:
            context = "\n\nEvent context:\n"
            for key, value in event.payload.items():
                context += f"- {key}: {value}\n"
            prompt += context

        return prompt

    async def _handle_output(self, result: Any, action: TriggerAction):
        """处理输出"""
        for channel in action.output_channels:
            if channel == "console":
                print(result)
            elif channel == "file":
                # 写入文件
                pass
            elif channel == "slack":
                # 发送到 Slack
                pass
            elif channel == "email":
                # 发送邮件
                pass

    async def _retry(self, reg: TriggerRegistration, event: TriggerEvent):
        """重试触发"""
        for attempt in range(reg.action.retry_on_failure):
            await asyncio.sleep(5 * (attempt + 1))

            try:
                await self._handle_event(event)
                break
            except Exception:
                continue

    def list_triggers(self) -> List[Dict]:
        """列出所有触发器"""
        return [
            {
                "id": trigger_id,
                "type": reg.trigger.trigger_type.value,
                "enabled": reg.enabled,
                "last_fired": reg.last_fired,
                "fire_count": reg.fire_count,
                "error_count": reg.error_count
            }
            for trigger_id, reg in self._registrations.items()
        ]

    def _generate_id(self) -> str:
        import uuid
        return f"trigger_{uuid.uuid4().hex[:8]}"
```

## 多代理编排

```python
@dataclass
class AgentTeam:
    """代理团队"""
    name: str
    agents: Dict[str, "AgentConfig"] = field(default_factory=dict)
    coordinator: str = ""        # 协调者 agent
    communication_bus: str = "internal"


@dataclass
class AgentConfig:
    """代理配置"""
    name: str
    role: str
    skills: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    max_iterations: int = 10
    priority: int = 0


class MultiAgentOrchestrator:
    """多代理编排器"""

    def __init__(
        self,
        harness: "AgentHarness",
        event_bus: EventBus
    ):
        self.harness = harness
        self.event_bus = event_bus
        self._teams: Dict[str, AgentTeam] = {}
        self._agent_results: Dict[str, List[Any]] = {}

    def create_team(self, team: AgentTeam) -> str:
        """创建代理团队"""
        team_id = team.name
        self._teams[team_id] = team
        return team_id

    async def dispatch(
        self,
        task: str,
        team_id: str,
        strategy: str = "parallel"
    ) -> Dict[str, Any]:
        """分发任务到团队"""

        team = self._teams.get(team_id)
        if not team:
            raise ValueError(f"Team not found: {team_id}")

        if strategy == "parallel":
            # 并行执行所有 agent
            results = await self._parallel_dispatch(task, team)

        elif strategy == "sequential":
            # 顺序执行
            results = await self._sequential_dispatch(task, team)

        elif strategy == "coordinated":
            # 协调执行
            results = await self._coordinated_dispatch(task, team)

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        return results

    async def _parallel_dispatch(
        self,
        task: str,
        team: AgentTeam
    ) -> Dict[str, Any]:
        """并行分发"""
        tasks = []
        for agent_name, config in team.agents.items():
            tasks.append(self._run_agent(agent_name, config, task))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            name: result
            for name, result in zip(team.agents.keys(), results)
        }

    async def _sequential_dispatch(
        self,
        task: str,
        team: AgentTeam
    ) -> Dict[str, Any]:
        """顺序分发"""
        results = {}

        # 按 priority 排序
        sorted_agents = sorted(
            team.agents.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )

        current_task = task
        for agent_name, config in sorted_agents:
            result = await self._run_agent(agent_name, config, current_task)
            results[agent_name] = result

            # 将结果传递给下一个 agent
            if isinstance(result, dict) and "output" in result:
                current_task = f"{task}\n\nPrevious agent output: {result['output']}"

        return results

    async def _coordinated_dispatch(
        self,
        task: str,
        team: AgentTeam
    ) -> Dict[str, Any]:
        """协调分发"""
        results = {}
        coordinator = team.agents.get(team.coordinator)

        if not coordinator:
            return await self._parallel_dispatch(task, team)

        # 协调者分配任务
        allocation = await self._run_agent(
            team.coordinator,
            coordinator,
            f"Coordinate the following task among team members:\n{task}\n\nAvailable agents: {list(team.agents.keys())}"
        )

        # 执行分配的任务
        if isinstance(allocation, dict) and "assignments" in allocation:
            for agent_name, subtask in allocation.get("assignments", {}).items():
                if agent_name in team.agents:
                    result = await self._run_agent(
                        agent_name,
                        team.agents[agent_name],
                        subtask
                    )
                    results[agent_name] = result

        return results

    async def _run_agent(
        self,
        agent_name: str,
        config: AgentConfig,
        task: str
    ) -> Any:
        """运行单个代理"""
        # 创建专用会话
        session = await self.harness.memory.create_session()

        # 激活技能
        for skill_name in config.skills:
            self.harness.skills.activate(skill_name)

        # 运行
        result = await self.harness.run(task, session.id)

        return {
            "agent": agent_name,
            "output": result.final_response.content if hasattr(result, 'final_response') else result,
            "iterations": result.iterations if hasattr(result, 'iterations') else 0
        }

    def broadcast(self, message: str, team_id: str):
        """广播消息到团队"""
        self.event_bus.publish(
            f"team.{team_id}.broadcast",
            {"message": message}
        )
```

## Output Handler

```python
class OutputHandler:
    """输出处理器"""

    def __init__(self):
        self._channels: Dict[str, "OutputChannel"] = {}

    def register_channel(self, name: str, channel: "OutputChannel"):
        """注册输出通道"""
        self._channels[name] = channel

    async def send(self, result: Any, channels: List[str]):
        """发送结果到指定通道"""
        for channel_name in channels:
            if channel_name in self._channels:
                await self._channels[channel_name].send(result)


class OutputChannel(ABC):
    """输出通道抽象"""

    @abstractmethod
    async def send(self, content: Any):
        """发送内容"""
        pass


class ConsoleChannel(OutputChannel):
    """控制台输出"""

    async def send(self, content: Any):
        print(content)


class FileChannel(OutputChannel):
    """文件输出"""

    def __init__(self, file_path: str, mode: str = "a"):
        self.file_path = file_path
        self.mode = mode

    async def send(self, content: Any):
        with open(self.file_path, self.mode) as f:
            f.write(str(content) + "\n")


class SlackChannel(OutputChannel):
    """Slack 输出"""

    def __init__(self, webhook_url: str, channel: str):
        self.webhook_url = webhook_url
        self.channel = channel

    async def send(self, content: Any):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            await session.post(
                self.webhook_url,
                json={
                    "channel": self.channel,
                    "text": str(content)
                }
            )


class EmailChannel(OutputChannel):
    """邮件输出"""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender: str,
        recipients: List[str]
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients

    async def send(self, content: Any):
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = "Harness Agent Output"
        msg.set_content(str(content))

        await aiosmtplib.send(
            msg,
            hostname=self.smtp_server,
            port=self.smtp_port
        )
```

## 测试

```python
@pytest.mark.asyncio
async def test_cron_trigger():
    trigger = CronTrigger(
        schedule="* * * * *",  # 每分钟
        action=TriggerAction(agent_prompt="test")
    )

    events = []
    await trigger.start(lambda e: events.append(e))

    # 等待触发
    await asyncio.sleep(65)

    await trigger.stop()

    assert len(events) >= 1

@pytest.mark.asyncio
async def test_trigger_manager():
    harness = AgentHarness(config)
    manager = TriggerManager(harness)

    trigger = CronTrigger(
        schedule="0 * * * *",
        action=TriggerAction(agent_prompt="test")
    )

    trigger_id = manager.register(trigger, trigger.action)

    assert trigger_id in manager.list_triggers()

    await manager.start()
    await manager.stop()
```

---

## 分布式环境下的 Trigger 管理

内嵌 SDK 在多进程环境（Gunicorn 多 Worker、K8s 多副本）下，Trigger 会在每个进程独立启动，导致重复触发。需要引入分布式状态后端 + 分布式锁 + Leader 选举。

```python
from dataclasses import dataclass
from enum import Enum

class DeploymentMode(Enum):
    SINGLETON = "singleton"      # 单进程，使用 File/SQLite
    DISTRIBUTED = "distributed"  # 多进程，必须使用 Redis/PostgreSQL

@dataclass
class DistributedConfig:
    """分布式配置"""
    mode: DeploymentMode = DeploymentMode.SINGLETON

    # 分布式存储（当 mode=DISTRIBUTED 时必需）
    storage_backend: str = "redis"
    storage_url: str = ""

    # 分布式锁
    lock_backend: str = "redis"
    lock_ttl_seconds: int = 30

    # Trigger 配置
    trigger_leader_election: bool = True


class DistributedTriggerManager:
    """分布式触发器管理器"""

    def __init__(self, config: DistributedConfig):
        self.config = config
        self._lock = None
        self._is_leader = False

    async def acquire_leader_lock(self) -> bool:
        """获取 Leader 锁（只有 Leader 执行 Trigger）"""
        if self.config.mode == DeploymentMode.SINGLETON:
            return True

        # 使用 Redis Redlock
        import redis.asyncio as redis
        client = redis.from_url(self.config.storage_url)

        self._lock = client.lock(
            "harness:trigger:leader",
            timeout=self.config.lock_ttl_seconds,
            blocking=False
        )

        try:
            self._is_leader = await self._lock.acquire()
            return self._is_leader
        except Exception:
            return False

    async def should_execute_trigger(self) -> bool:
        """判断当前实例是否应该执行 Trigger"""
        if self.config.mode == DeploymentMode.SINGLETON:
            return True
        return self._is_leader

    async def renew_leader_lock(self) -> bool:
        """续期 Leader 锁"""
        if self._lock and self._is_leader:
            try:
                await self._lock.extend(self.config.lock_ttl_seconds)
                return True
            except Exception:
                self._is_leader = False
                return False
        return False
```

**部署架构**:

```
┌─────────────────────────────────────────────────────┐
│                    K8s Cluster                       │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ API Server  │  │ API Server  │  │ API Server  │ │
│  │ (Worker)    │  │ (Worker)    │  │ (Worker)    │ │
│  │ - 无 Trigger│  │ - 无 Trigger│  │ - 无 Trigger│ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │           Trigger Worker (单副本)            │   │
│  │           - Leader Election                  │   │
│  │           - 执行所有 Cron/Webhook            │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │                  Redis                        │   │
│  │           - Session Store                     │   │
│  │           - Distributed Lock                  │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**替代方案**:

1. **Celery Beat 集成**:
```python
from celery import Celery
from celery.schedules import crontab

app = Celery()
agent = AgentHarness(...)

@app.task
def run_agent_task(prompt):
    asyncio.run(agent.run(prompt))

app.conf.beat_schedule = {
    'daily-report': {
        'task': 'run_agent_task',
        'schedule': crontab(hour=9, minute=0),
        'args': ('生成每日报告',),
    },
}
```

2. **K8s CronJob**:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: harness-trigger
spec:
  schedule: "0 9 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: agent
            command: ["python", "-m", "harness", "run", "生成每日报告"]
```