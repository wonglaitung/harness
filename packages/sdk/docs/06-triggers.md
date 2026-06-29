# 06 - Trigger & Orchestration 触发与编排

> **状态**: 设计完成，待实现
> **关联**: Loop Engineering Phase 2 (Automations)
> **优先级**: P0

## 概述

Trigger System 让 Agent 能够自主运行，不仅响应用户消息，还能根据时间、事件、状态变化自动触发执行。

### 与 Loop Engineering 的关系

Trigger System 是 **Loop Engineering Phase 2: Automations** 的核心实现：

```
Loop Engineering 架构:
┌─────────────────────────────────────────────────────────────┐
│                    LoopOrchestrator                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Automation (简化 API)                   │    │
│  │  automation = Automation(schedule="0 9 * * *",       │    │
│  │                        goal="生成每日报告")           │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│  ┌────────────────────────┴────────────────────────────┐    │
│  │                 Trigger System                        │    │
│  │  - CronTrigger / IntervalTrigger / WebhookTrigger   │    │
│  │  - TriggerManager                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│  ┌────────────────────────┴────────────────────────────┐    │
│  │              GoalLoop (Phase 1 ✅)                   │    │
│  │  - GoalVerifier                                       │    │
│  │  - GoalConfig / GoalResult                           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**数据流**:
```
Trigger 触发 → TriggerManager 创建 GoalConfig → GoalLoop 执行 → GoalVerifier 验证
```

### 与 SkillTrigger 的区别

| 组件 | 用途 | 触发条件 |
|------|------|----------|
| `SkillTrigger` | 激活技能 | 用户输入内容匹配关键词/正则 |
| `Trigger` (本文档) | 自动执行 Goal | 时间/事件/外部请求 |

**示例**:
```python
# SkillTrigger: 用户说 "review" 时激活 code-review 技能
skill_trigger = SkillTrigger(keywords=["review"])
skill_trigger.matches("请 review 这段代码")  # → True

# Trigger: 每天 9:00 自动执行 "生成报告"
cron_trigger = CronTrigger(schedule="0 9 * * *", goal="生成每日报告")
```

---

## 实现状态

| 组件 | 状态 | 优先级 | 说明 |
|------|------|--------|------|
| Trigger 基类 | ✅ 已实现 | P0 | `triggers/base.py` |
| TriggerType | ✅ 已实现 | P0 | `triggers/types.py` |
| TriggerEvent | ✅ 已实现 | P0 | `triggers/types.py` |
| TriggerAction | ✅ 已实现 | P0 | `triggers/types.py` |
| CronTrigger | ✅ 已实现 | P0 | `triggers/cron.py` |
| IntervalTrigger | ✅ 已实现 | P0 | `triggers/interval.py` |
| TriggerManager | ✅ 已实现 | P0 | `triggers/manager.py` |
| Automation | ✅ 已实现 | P0 | `loop/automation.py` |
| WebhookTrigger | ❌ 待实现 | P1 | HTTP webhook |
| HeartbeatTrigger | ❌ 待实现 | P1 | 心跳触发 |
| FileWatchTrigger | ❌ 待实现 | P2 | 文件变化 |
| EventBusTrigger | ❌ 待实现 | P2 | 事件总线 |
| OutputHandler | ❌ 待实现 | P1 | 输出处理器 |
| DistributedTriggerManager | ❌ 待实现 | P2 | 分布式支持 |

---

## Automation 简化 API

Automation 是 Trigger System 的主要入口，整合 Trigger + GoalConfig：

```python
from harness.loop import Automation, AutomationStatus

# 方式 1：定时任务（最常用）
automation = Automation(
    name="daily-report",
    schedule="0 9 * * *",           # cron 表达式
    goal="生成每日报告并发送到 Slack",
    workspace_dir=".",
    max_iterations=30,
    output_channels=["slack"],
)

# 方式 2：间隔任务
automation = Automation(
    name="health-check",
    interval_seconds=3600,          # 每小时
    goal="检查系统健康状态",
)

# 方式 3：自定义 Trigger
automation = Automation(
    name="pr-review",
    trigger=WebhookTrigger(endpoint="/webhook/github"),
    goal="Review the pull request changes",
    skills=["code-review"],
)

# 生命周期管理
await automation.start()            # 启动
status = automation.status          # 获取状态
await automation.stop()             # 停止
```

### Automation 类定义

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, List, Optional

class AutomationStatus(Enum):
    PENDING = "pending"         # 等待启动
    RUNNING = "running"         # 运行中
    PAUSED = "paused"           # 已暂停
    STOPPED = "stopped"         # 已停止
    ERROR = "error"             # 错误状态


@dataclass
class AutomationConfig:
    """Automation 配置"""
    name: str
    goal: str                           # 目标描述
    
    # 触发方式（三选一）
    schedule: str | None = None         # cron 表达式
    interval_seconds: int | None = None # 间隔秒数
    trigger: Trigger | None = None      # 自定义 Trigger
    
    # Goal 配置
    workspace_dir: str = "."
    max_iterations: int = 50
    timeout_seconds: int = 3600
    custom_verifier: Callable | None = None
    
    # 输出配置
    output_channels: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    
    # 重试配置
    max_retries: int = 3
    retry_delay_seconds: float = 5.0


@dataclass
class AutomationResult:
    """Automation 执行结果"""
    automation_name: str
    status: AutomationStatus
    goal_result: GoalResult | None = None
    last_run: datetime | None = None
    run_count: int = 0
    error_count: int = 0
    error_message: str | None = None


class Automation:
    """
    Automation - Trigger + Goal 的简化 API
    
    主要功能：
    1. 创建和管理 Trigger
    2. 触发时创建 GoalConfig 并调用 GoalLoop
    3. 处理输出和错误
    """
    
    def __init__(self, config: AutomationConfig):
        self.config = config
        self._trigger: Trigger | None = None
        self._status = AutomationStatus.PENDING
        self._result = AutomationResult(automation_name=config.name, status=AutomationStatus.PENDING)
    
    @classmethod
    def create(
        cls,
        name: str,
        goal: str,
        schedule: str | None = None,
        interval_seconds: int | None = None,
        **kwargs
    ) -> "Automation":
        """便捷创建方法"""
        return cls(AutomationConfig(
            name=name,
            goal=goal,
            schedule=schedule,
            interval_seconds=interval_seconds,
            **kwargs
        ))
    
    @property
    def status(self) -> AutomationStatus:
        return self._status
    
    @property
    def result(self) -> AutomationResult:
        return self._result
    
    async def start(self) -> None:
        """启动 Automation"""
        # 创建 Trigger
        if self.config.schedule:
            self._trigger = CronTrigger(
                schedule=self.config.schedule,
                action=self._create_action()
            )
        elif self.config.interval_seconds:
            self._trigger = IntervalTrigger(
                interval_seconds=self.config.interval_seconds,
                action=self._create_action()
            )
        elif self.config.trigger:
            self._trigger = self.config.trigger
        else:
            raise ValueError("必须指定 schedule、interval_seconds 或 trigger")
        
        # 启动 Trigger
        await self._trigger.start(self._on_trigger)
        self._status = AutomationStatus.RUNNING
    
    async def stop(self) -> None:
        """停止 Automation"""
        if self._trigger:
            await self._trigger.stop()
        self._status = AutomationStatus.STOPPED
    
    async def pause(self) -> None:
        """暂停 Automation"""
        if self._trigger:
            await self._trigger.stop()
        self._status = AutomationStatus.PAUSED
    
    async def resume(self) -> None:
        """恢复 Automation"""
        if self._trigger:
            await self._trigger.start(self._on_trigger)
        self._status = AutomationStatus.RUNNING
    
    def _create_action(self) -> "TriggerAction":
        """创建 TriggerAction"""
        return TriggerAction(
            agent_prompt=self.config.goal,
            skills_to_activate=self.config.skills,
            output_channels=self.config.output_channels,
        )
    
    async def _on_trigger(self, event: "TriggerEvent") -> None:
        """Trigger 触发时的回调"""
        try:
            # 创建 GoalConfig
            goal_config = GoalConfig(
                description=self.config.goal,
                workspace_dir=self.config.workspace_dir,
                max_iterations=self.config.max_iterations,
                timeout_seconds=self.config.timeout_seconds,
                custom_verifier=self.config.custom_verifier,
            )
            
            # 执行 GoalLoop
            result = await self._run_goal(goal_config, event)
            
            # 更新结果
            self._result.goal_result = result
            self._result.last_run = datetime.now()
            self._result.run_count += 1
            
            # 处理输出
            await self._handle_output(result)
            
        except Exception as e:
            self._result.error_count += 1
            self._result.error_message = str(e)
            self._status = AutomationStatus.ERROR
    
    async def _run_goal(self, config: GoalConfig, event: TriggerEvent) -> GoalResult:
        """执行 Goal（调用 GoalLoop）"""
        # 这里调用 Phase 1 实现的 GoalLoop
        from harness.loop import GoalLoop
        
        agent = AgentHarness()  # 或从外部传入
        goal_loop = GoalLoop(agent, config)
        return await goal_loop.run()
    
    async def _handle_output(self, result: GoalResult) -> None:
        """处理输出"""
        for channel in self.config.output_channels:
            if channel == "console":
                print(result.final_response)
            elif channel == "slack":
                # 发送到 Slack
                pass
            elif channel == "email":
                # 发送邮件
                pass
```

### 使用示例

```python
from harness.loop import Automation
import asyncio

async def main():
    # 创建定时报告任务
    daily_report = Automation.create(
        name="daily-report",
        schedule="0 9 * * *",
        goal="分析昨天的系统日志，生成每日报告并发送到 #ops 频道",
        output_channels=["slack"],
    )
    
    # 创建健康检查任务
    health_check = Automation.create(
        name="health-check",
        interval_seconds=300,  # 每 5 分钟
        goal="检查 API 健康状态，如果异常则发送告警",
        output_channels=["slack", "email"],
    )
    
    # 启动所有任务
    await daily_report.start()
    await health_check.start()
    
    # 查看状态
    print(f"Daily report: {daily_report.status}")
    print(f"Health check: {health_check.status}")
    
    # 运行一段时间后停止
    await asyncio.sleep(3600)
    
    await daily_report.stop()
    await health_check.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

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
    """
    触发后的动作配置
    
    用于创建 GoalConfig，指定 Trigger 触发后如何执行 Goal。
    """
    
    # Goal 配置
    goal: str                              # 目标描述（映射到 GoalConfig.description）
    workspace_dir: str = "."               # 工作目录
    max_iterations: int = 50               # 最大迭代次数
    timeout_seconds: int = 3600            # 超时时间
    custom_verifier: Callable | None = None  # 自定义验证器
    
    # 上下文配置
    session_id: Optional[str] = None       # 使用哪个会话
    skills_to_activate: List[str] = field(default_factory=list)
    
    # 输出配置
    output_channels: List[str] = field(default_factory=list)
    save_result: bool = True
    
    # 重试配置
    retry_on_failure: int = 3
    retry_delay_seconds: float = 5.0
    
    def to_goal_config(self, event: TriggerEvent) -> "GoalConfig":
        """转换为 GoalConfig"""
        from harness.loop.types import GoalConfig
        
        # 将事件上下文添加到目标描述
        goal = self.goal
        if event.payload:
            context = "\n\nEvent context:\n"
            for key, value in event.payload.items():
                context += f"- {key}: {value}\n"
            goal += context
        
        return GoalConfig(
            description=goal,
            workspace_dir=self.workspace_dir,
            max_iterations=self.max_iterations,
            timeout_seconds=self.timeout_seconds,
            custom_verifier=self.custom_verifier,
        )
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
            # 激活技能
            for skill_name in reg.action.skills_to_activate:
                self.harness.skills.activate(skill_name)
            
            # 创建 GoalConfig
            goal_config = reg.action.to_goal_config(event)
            
            # 执行 GoalLoop
            from harness.loop import GoalLoop
            goal_loop = GoalLoop(self.harness, goal_config)
            result = await goal_loop.run()

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

    async def _handle_output(self, result: "GoalResult", action: TriggerAction):
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
            await asyncio.sleep(reg.action.retry_delay_seconds * (attempt + 1))

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