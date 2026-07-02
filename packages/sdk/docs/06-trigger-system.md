# 06 - 触发器系统详解

> **状态**: ✅ 已实现 (Phase 2: Automations)
> **相关文档**: [phase2-automations.md](../design/phase2-automations.md)

## 概述

触发器系统让 Agent 能够自主运行——不仅响应用户消息，还能响应定时任务、外部事件等触发源。

**已实现的组件**：
- `CronTrigger` - Cron 表达式调度
- `IntervalTrigger` - 固定间隔调度
- `TriggerManager` - 统一管理 + 并发执行
- `Automation` - 简化 API

## 架构

```
┌─────────────────────────────────────────────────┐
│              Trigger System                      │
│                                                  │
│  ┌───────────────┐  ┌───────────────────┐       │
│  │TriggerManager │  │  Trigger Base     │       │
│  │ (并发调度)     │  │  (触发器抽象类)    │       │
│  └───────┬───────┘  └───────┬───────────┘       │
│          │                  │                    │
│          ↓                  ↓                    │
│  ┌─────────────────────────────────────────┐    │
│  │           Trigger Types                  │    │
│  │  CronTrigger │ IntervalTrigger │ ...    │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

## Trigger 基类

```python
from harness.triggers.base import Trigger, TriggerEvent

class Trigger(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """触发器名称"""

    @abstractmethod
    async def start(self, callback: Callable[[TriggerEvent], Awaitable[None]]) -> None:
        """启动触发器，事件触发时调用 callback"""

    @abstractmethod
    async def stop(self) -> None:
        """停止触发器"""

    @property
    def is_running(self) -> bool:
        """触发器是否在运行"""
```

### TriggerEvent

```python
@dataclass
class TriggerEvent:
    trigger_name: str          # 触发器名称
    trigger_type: str          # 触发器类型
    data: dict                 # 事件数据
    timestamp: datetime        # 事件时间
    metadata: dict | None = None  # 附加元数据
```

## TriggerManager

```python
from harness.triggers.manager import TriggerManager

class TriggerManager:
    def __init__(self, harness: AgentHarness)

    def register(self, trigger: Trigger) -> str:
        """注册触发器，返回 trigger_id"""

    def unregister(self, trigger_id: str) -> bool:
        """注销触发器"""

    async def start(self) -> None:
        """启动所有已注册且启用的触发器"""

    async def stop(self) -> None:
        """停止所有触发器"""

    def get_trigger(self, trigger_id: str) -> TriggerRegistration | None:
        """获取触发器"""

    def list_triggers(self) -> list[dict]:
        """列出所有触发器状态"""
```

### 目标执行

当触发器触发时，TriggerManager 会调用 `AgentHarness.run_goal()` 执行目标：

```python
# TriggerManager 内部实现
async def _handle_event(self, event: TriggerEvent):
    # 获取注册信息
    reg = self._registrations[event.trigger_id]

    # 构建 GoalConfig
    goal_config = reg.action.to_goal_config(event)

    # 执行目标（注意：run_goal 第一个参数是 goal 字符串）
    result = await self.agent.run_goal(
        goal=goal_config.description,           # goal 字符串
        success_criteria=goal_config.success_criteria,
        workspace_dir=goal_config.workspace_dir,
        max_iterations=goal_config.max_iterations,
        timeout_seconds=goal_config.timeout_seconds,
    )
```

**重要说明**：`TriggerAction.to_goal_config()` 返回 `GoalConfig` 对象，但 `AgentHarness.run_goal()` 的第一个参数是 `goal: str` 字符串，需要使用 `goal_config.description`。

## CronTrigger（定时触发）

```python
from harness.triggers.cron import CronTrigger

class CronTrigger(Trigger):
    def __init__(
        self,
        name: str,
        schedule: str,           # Cron 表达式
        task: str | None = None, # 要执行的任务
        skills: list[str] | None = None, # 使用的技能
        timezone: str = "UTC",   # 时区
    )
```

### 使用示例

```python
from harness import AgentHarness
from harness.triggers.cron import CronTrigger

agent = AgentHarness()

# 每天 9:00 生成日报
cron = CronTrigger(
    name="daily-report",
    schedule="0 9 * * *",
    task="生成昨日工作日报",
    skills=["report"],
)
agent.triggers.register(cron)

# 每小时检查系统状态
health_check = CronTrigger(
    name="health-check",
    schedule="0 * * * *",
    task="检查系统健康状态并报告异常",
)
agent.triggers.register(health_check)

# 启动所有触发器
await agent.triggers.start_all()
```

### Cron 表达式格式

```
┌──────── 分钟 (0-59)
│ ┌────── 小时 (0-23)
│ │ ┌──── 日 (1-31)
│ │ │ ┌── 月 (1-12)
│ │ │ │ ┌ 星期 (0-6, 0=Sunday)
│ │ │ │ │
* * * * *
```

常用模式：

| 表达式 | 说明 |
|--------|------|
| `*/5 * * * *` | 每 5 分钟 |
| `0 * * * *` | 每小时整点 |
| `0 9 * * *` | 每天 9:00 |
| `0 9 * * 1-5` | 工作日 9:00 |
| `0 0 1 * *` | 每月 1 日 |

## WebhookTrigger（Webhook 触发）

```python
from harness.triggers.webhook import WebhookTrigger

class WebhookTrigger(Trigger):
    def __init__(
        self,
        name: str,
        path: str,                    # Webhook 路径
        task: str | None = None,      # 要执行的任务模板
        skills: list[str] | None = None,
        secret: str | None = None,    # 验证密钥
        allowed_ips: list[str] | None = None, # IP 白名单
    )
```

### 使用示例

```python
from harness import AgentHarness
from harness.triggers.webhook import WebhookTrigger

agent = AgentHarness()

# GitHub PR 事件触发代码审查
github_pr = WebhookTrigger(
    name="github-pr",
    path="/webhook/github",
    task="审查 PR #{event.pull_request.number}: {event.pull_request.title}",
    skills=["code-review"],
    secret="whsec_...",
)
agent.triggers.register(github_pr)

# Slack 消息触发
slack_msg = WebhookTrigger(
    name="slack-message",
    path="/webhook/slack",
    task="处理来自 {event.user} 的消息: {event.text}",
)
agent.triggers.register(slack_msg)
```

### Webhook 事件数据

Webhook 事件的数据结构取决于外部服务。触发器会将请求体解析为 `TriggerEvent.data`：

```python
# GitHub PR Webhook
event.data = {
    "action": "opened",
    "pull_request": {
        "number": 42,
        "title": "Fix auth bug",
        "url": "https://github.com/...",
    },
}

# 模板变量使用 {event.field.subfield} 格式
```

## 自定义触发器

```python
from harness.triggers.base import Trigger, TriggerEvent

class FileWatchTrigger(Trigger):
    """文件变化触发器"""

    def __init__(self, name: str, watch_path: str, task: str | None = None):
        self._name = name
        self._watch_path = watch_path
        self._task = task
        self._running = False

    @property
    def name(self) -> str:
        return self._name

    async def start(self, callback):
        self._running = True
        # 实现文件监控逻辑
        # 文件变化时调用:
        # await callback(TriggerEvent(
        #     trigger_name=self._name,
        #     trigger_type="file_watch",
        #     data={"path": changed_file, "event": "modified"},
        #     timestamp=datetime.now(),
        # ))

    async def stop(self):
        self._running = False
```

## 触发器与 Agent 的集成

触发器事件触发后，TriggerManager 会自动调用 `AgentHarness.run()`：

```
触发器事件
    │
    ↓
TriggerManager 接收 TriggerEvent
    │
    ↓
构造任务描述（使用模板变量）
    │
    ↓
调用 AgentHarness.run(task, skills=...)
    │
    ↓
返回 LoopResult
```

## 触发器管理

```python
from harness.triggers import TriggerManager, IntervalTrigger, TriggerAction

# 创建 TriggerManager（支持并发控制）
manager = TriggerManager(agent, max_concurrent_goals=5)

# 注册触发器
trigger = IntervalTrigger(
    interval_seconds=300,
    action=TriggerAction(goal="健康检查"),
)
trigger_id = manager.register(trigger)

# 启动所有触发器
await manager.start()

# 查看状态
for info in manager.list_triggers():
    print(f"{info['id']}: fires={info['fire_count']}")

# 停止所有触发器
await manager.stop()
```

### 并发执行

TriggerManager 支持并发执行多个 Goal：

```python
# 最多同时执行 3 个 Goal
manager = TriggerManager(agent, max_concurrent_goals=3)

# 当多个触发器同时触发时，并发执行
# 超过限制的任务会等待 semaphore
```

## Automation 简化 API

Automation 是触发器系统的推荐入口，整合了 Trigger + Goal：

```python
from harness.loop import Automation

# 定时任务（Cron）
daily_report = Automation(
    name="daily-report",
    schedule="0 9 * * *",  # 每天 9:00
    goal="生成每日报告并发送到 Slack",
)

# 间隔任务
health_check = Automation(
    name="health-check",
    interval_seconds=300,  # 每 5 分钟
    goal="检查系统健康状态",
)

# 启动
await daily_report.start(agent)
await health_check.start(agent)

# 查看状态
print(daily_report.status)  # AutomationStatus.RUNNING

# 停止
await daily_report.stop()
```

### 全局管理

Automation 使用全局 TriggerManager 单例：

```python
from harness.loop.automation import get_global_manager

# 所有 Automation 自动注册到全局 manager
await automation1.start(agent)
await automation2.start(agent)

# 获取全局 manager 查看所有触发器
manager = get_global_manager()
print(f"Total triggers: {manager.trigger_count}")
```

## Java SDK 示例

Java SDK 提供完整的 Trigger 系统实现，使用 `CompletableFuture` 替代 Python 的 `asyncio`。

### CronTrigger

```java
import com.harness.triggers.CronTrigger;
import com.harness.triggers.TriggerAction;
import com.harness.triggers.TriggerManager;
import com.harness.sdk.AgentHarness;

AgentHarness agent = new AgentHarness(config);
TriggerManager manager = new TriggerManager(agent);

// 创建 Cron 触发器
CronTrigger trigger = new CronTrigger(
    "daily-report",                    // 名称
    "0 9 * * *",                       // cron 表达式：每天 9:00
    new TriggerAction.Builder()
        .goal("生成每日报告并发送到 Slack")
        .workspaceDir(".")
        .maxIterations(50)
        .build()
);

// 注册并启动
String triggerId = manager.register(trigger);
manager.start().join();

// 查看下次运行时间
List<Instant> nextRuns = trigger.getNextRuns(5);

// 停止
manager.stop().join();
manager.unregister(triggerId);
```

### IntervalTrigger

```java
import com.harness.triggers.IntervalTrigger;

IntervalTrigger trigger = new IntervalTrigger(
    "health-check",                    // 名称
    300,                               // 每 300 秒（5 分钟）
    new TriggerAction.Builder()
        .goal("检查系统健康状态")
        .build()
);

manager.register(trigger);
```

### TriggerManager

```java
import com.harness.triggers.TriggerManager;
import com.harness.triggers.TriggerState;
import com.harness.triggers.TriggerType;

// 创建 TriggerManager（支持并发控制）
TriggerManager manager = new TriggerManager(agent, 5);  // max_concurrent_goals = 5

// 注册触发器
String triggerId = manager.register(trigger);

// 列出所有触发器
for (Map<String, Object> info : manager.listTriggers()) {
    System.out.println("ID: " + info.get("id"));
    System.out.println("Type: " + info.get("type"));
    System.out.println("State: " + info.get("state"));
    System.out.println("Fire count: " + info.get("fire_count"));
}

// 启动所有触发器
manager.start().join();

// 停止所有触发器
manager.stop().join();
```

### TriggerState 枚举

```java
public enum TriggerState {
    IDLE,       // 空闲
    RUNNING,    // 运行中
    PAUSED,     // 已暂停
    STOPPED,    // 已停止
    ERROR       // 错误
}
```

## 下一步

- [02-agent-loop.md](./02-agent-loop.md) - 了解 Agent Loop
- [05-skills-system.md](./05-skills-system.md) - 了解技能系统
- [07-sdk-api.md](./07-sdk-api.md) - 查看 SDK API
- [../design/phase2-automations.md](../design/phase2-automations.md) - Automations 设计文档

---

## qasync 集成注意事项

### 问题：asyncio.Queue 与 qasync 不兼容

在 PyQt6 + qasync 环境中使用 `asyncio.Queue` 会导致以下错误：

```
RuntimeError: <Queue at 0x...> is bound to a different event loop
```

### 原因

`asyncio.Queue` 在创建时会绑定到当前的 event loop。qasync 可能会在运行过程中切换 event loop（例如关闭窗口、线程切换时），导致原先创建的 Queue 无法访问。

### 解决方案：EventQueue

TriggerManager 使用自定义的 `EventQueue` 替代 `asyncio.Queue`：

```python
class EventQueue:
    """
    Thread-safe event queue that works across event loop switches.

    Uses threading.Lock for thread-safety and asyncio.Event for async waiting.
    """

    def __init__(self):
        self._queue: deque[TriggerEvent] = deque()
        self._lock = threading.Lock()
        self._notifier: asyncio.Event | None = None

    def put_nowait(self, event: TriggerEvent) -> None:
        with self._lock:
            self._queue.append(event)
        if self._notifier is not None:
            try:
                self._notifier.set()
            except Exception:
                pass  # Event might be bound to old loop

    async def get(self) -> TriggerEvent:
        if self._notifier is None:
            self._notifier = asyncio.Event()

        while True:
            with self._lock:
                if self._queue:
                    return self._queue.popleft()

            self._notifier.clear()
            try:
                await self._notifier.wait()
            except Exception:
                self._notifier = asyncio.Event()
```

**设计要点**：

1. **存储层不绑定 event loop**：`collections.deque` + `threading.Lock` 是跨 event loop 安全的
2. **等待器动态创建**：`asyncio.Event` 在 `get()` 调用时创建，确保绑定到当前 event loop
3. **异常时重建**：如果等待器失效，自动创建新的等待器
4. **事件不丢失**：队列中的事件存储在 deque 中，不受 event loop 切换影响

### 关闭顺序

`TriggerManager.stop()` 必须先取消 processor task，再清理其他资源：

```python
async def stop(self) -> None:
    self._running = False

    # 1. 先取消 processor task（防止访问已销毁的队列）
    if self._processor_task:
        self._processor_task.cancel()
        await self._processor_task  # 等待取消完成

    # 2. 再清理其他资源
    # ...
```

### 参考

- 关键文件：`packages/sdk/src/harness/triggers/manager.py`
- 相关经验教训：`lessons.md` - "asyncio.Queue 与 qasync event loop 切换问题"
