# Phase 2: Automations 设计文档

> **状态**: ✅ 已实现
> **创建时间**: 2026-06-30（补写）
> **最后更新**: 2026-06-30

---

## 背景

Loop Engineering Phase 1 实现了目标驱动执行（Goal-Driven Execution），用户可以描述目标，Agent 自主运行直到完成。

Phase 2 Automations 的核心需求是：**让 Agent 能够根据时间或事件自动触发执行，实现"自动化 Agent"**。

**设计目标**：
1. 支持多种触发方式（cron 定时、固定间隔、事件驱动）
2. 触发后自动调用 Phase 1 的 GoalLoop 执行目标
3. 提供简洁的用户 API
4. 支持触发器生命周期管理（注册、启动、停止）

---

## 设计原则

### TriggerAction 直接映射 GoalConfig

Phase 2 没有重新实现执行引擎，而是将 `TriggerAction` 设计为直接映射到 `GoalConfig`：

```
Trigger (Cron/Interval)
    ↓ 触发
TriggerEvent
    ↓
TriggerAction.to_goal_config()
    ↓
GoalConfig
    ↓
TriggerManager._on_trigger()
    ↓
agent.run_goal(config)
    ↓
GoalLoop (Phase 1)
```

**原因**：
1. **避免重复实现**：GoalLoop 已有完整的迭代控制、上下文重置、超时处理逻辑
2. **单一执行路径**：无论是用户调用 `run_goal()` 还是触发器触发，都走同一代码路径
3. **便于维护**：Goal 相关的改进自动适用于 Trigger

---

## 架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Trigger System                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ CronTrigger  │  │IntervalTrigger│  │   (Future)   │          │
│  │              │  │              │  │ WebhookTrigger│          │
│  │ "0 9 * * *"  │  │  300 seconds │  │ FileWatch    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └────────────────┬┴─────────────────┘                   │
│                          │                                       │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    TriggerManager                          │  │
│  │  - register(trigger, action)                               │  │
│  │  - start() / stop()                                        │  │
│  │  - Event Queue → Goal Execution                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Phase 1: GoalLoop                           │
│                                                                  │
│  agent.run_goal(config) → GoalResult                            │
└─────────────────────────────────────────────────────────────────┘
```

### 简化 API: Automation

`Automation` 类封装了 Trigger + GoalConfig，提供更简洁的 API：

```
┌─────────────────────────────────────────────────────────────────┐
│                        Automation                                │
│                                                                  │
│  name: "daily-report"                                           │
│  schedule: "0 9 * * *"                                          │
│  goal: "生成每日报告"                                            │
│  skills: ["report-generation"]                                  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Internal:                                                │   │
│  │  CronTrigger(schedule) + TriggerAction(goal, skills)     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Methods:                                                        │
│  - start(agent)                                                  │
│  - stop()                                                        │
│  - pause() / resume()                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心类型定义

```python
# triggers/types.py

class TriggerType(Enum):
    """触发器类型."""
    CRON = "cron"           # Cron 表达式调度
    INTERVAL = "interval"   # 固定间隔调度
    WEBHOOK = "webhook"     # HTTP webhook 触发
    HEARTBEAT = "heartbeat" # 周期性心跳检查
    FILE_WATCH = "file_watch"  # 文件系统变化
    EVENT = "event"         # 事件总线订阅


class TriggerState(Enum):
    """触发器状态."""
    IDLE = "idle"       # 未启动
    RUNNING = "running" # 运行中
    PAUSED = "paused"   # 已暂停
    STOPPED = "stopped" # 已停止
    ERROR = "error"     # 错误状态


@dataclass
class TriggerEvent:
    """触发事件."""
    trigger_type: TriggerType
    trigger_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerAction:
    """触发后动作 - 映射到 GoalConfig."""
    
    # Goal 配置
    goal: str                    # 目标描述
    
    # 执行环境
    workspace_dir: str = "."     # 工作目录
    
    # 迭代控制
    max_iterations: int = 50
    timeout_seconds: int = 3600
    
    # 验证
    custom_verifier: Callable | None = None
    
    # Skills 和输出
    skills: list[str] = field(default_factory=list)
    output_channels: list[str] = field(default_factory=list)
    
    def to_goal_config(self, event: TriggerEvent | None = None) -> GoalConfig:
        """转换为 GoalConfig."""
        goal = self.goal
        if event and event.payload:
            # 注入事件上下文
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

---

## 核心组件实现

### Trigger 基类

```python
# triggers/base.py

class Trigger(ABC):
    """触发器抽象基类."""
    
    trigger_type: TriggerType
    id: str = ""
    state: TriggerState = TriggerState.IDLE
    action: TriggerAction | None = None
    
    @abstractmethod
    async def start(self, callback: Callable[[TriggerEvent], None]) -> None:
        """启动触发器."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止触发器."""
        pass
    
    @abstractmethod
    def create_event(self, payload: dict | None = None) -> TriggerEvent:
        """创建触发事件."""
        pass
    
    def is_running(self) -> bool:
        """检查是否运行中."""
        return self.state == TriggerState.RUNNING
```

### CronTrigger

```python
# triggers/cron.py

class CronTrigger(Trigger):
    """Cron 表达式调度触发器."""
    
    trigger_type = TriggerType.CRON
    
    def __init__(
        self,
        schedule: str,          # Cron 表达式："0 9 * * *"
        action: TriggerAction,
        timezone: str = "local",
        jitter_seconds: int = 0, # 随机抖动（避免惊群效应）
        trigger_id: str = "",
    ):
        self.schedule = schedule
        self.action = action
        self.timezone = timezone
        self.jitter_seconds = jitter_seconds
        self.id = trigger_id or self._generate_id()
        
        # 解析 cron 表达式
        self._cron = croniter.croniter(schedule)
        self._task: asyncio.Task | None = None
    
    async def start(self, callback: Callable[[TriggerEvent], None]) -> None:
        """启动定时器."""
        self._callback = callback
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
    
    async def _run_loop(self) -> None:
        """主循环：等待到预定时间后触发事件."""
        while self._running:
            # 计算下次运行时间
            next_run = self.get_next_run()
            wait_seconds = (next_run - datetime.now()).total_seconds()
            
            # 添加随机抖动
            if self.jitter_seconds > 0:
                wait_seconds += random.uniform(0, self.jitter_seconds)
            
            # 等待
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            
            # 触发事件
            if self._running and self._callback:
                event = self.create_event({"scheduled_time": next_run.isoformat()})
                self._callback(event)
    
    def get_next_run(self, base_time: datetime | None = None) -> datetime:
        """获取下次运行时间."""
        self._cron = croniter.croniter(self.schedule, base_time or datetime.now())
        return self._cron.get_next(datetime)
```

### IntervalTrigger

```python
# triggers/interval.py

class IntervalTrigger(Trigger):
    """固定间隔触发器."""
    
    trigger_type = TriggerType.INTERVAL
    
    def __init__(
        self,
        interval_seconds: int | float,
        action: TriggerAction,
        start_immediately: bool = False,  # 启动时立即触发
        trigger_id: str = "",
    ):
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be at least 1 second")
        
        self.interval_seconds = float(interval_seconds)
        self.action = action
        self.start_immediately = start_immediately
        self.id = trigger_id or self._generate_id()
    
    async def _run_loop(self) -> None:
        """主循环：固定间隔触发事件."""
        # 立即触发
        if self.start_immediately and self._callback:
            await self._fire_event()
        
        while self._running:
            await asyncio.sleep(self.interval_seconds)
            
            if self._running and self._callback:
                await self._fire_event()
```

### TriggerManager

```python
# triggers/manager.py

class TriggerManager:
    """
    触发器管理器 - 支持并发执行.
    
    核心特性:
    - 事件队列解耦触发和执行
    - Semaphore 控制并发数，防止 API 限流
    - 任务追踪，优雅关闭
    """
    
    def __init__(
        self,
        agent: AgentHarness,
        max_concurrent_goals: int = 5,  # 最大并发数
    ):
        self.agent = agent
        self.max_concurrent_goals = max_concurrent_goals
        self._registrations: dict[str, TriggerRegistration] = {}
        self._event_queue: asyncio.Queue[TriggerEvent] = asyncio.Queue()
        self._processor_task: asyncio.Task | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._running_tasks: set[asyncio.Task] = set()  # 活跃任务追踪
    
    def register(
        self,
        trigger: Trigger,
        action: TriggerAction | None = None,
        enabled: bool = True,
    ) -> str:
        """注册触发器."""
        action = action or trigger.action
        
        if not trigger.id:
            trigger.id = f"trigger_{uuid.uuid4().hex[:8]}"
        
        self._registrations[trigger.id] = TriggerRegistration(
            trigger=trigger,
            action=action,
            enabled=enabled,
        )
        
        return trigger.id
    
    async def start(self) -> None:
        """启动所有触发器."""
        # 初始化并发控制
        self._semaphore = asyncio.Semaphore(self.max_concurrent_goals)
        
        # 启动事件处理器
        self._processor_task = asyncio.create_task(self._process_events())
        
        # 启动所有触发器
        for reg in self._registrations.values():
            if reg.enabled:
                await reg.trigger.start(self._enqueue_event)
    
    async def stop(self) -> None:
        """停止所有触发器（等待活跃任务完成）."""
        self._running = False
        
        # 等待活跃任务完成（最多 30 秒）
        if self._running_tasks:
            done, pending = await asyncio.wait(
                self._running_tasks,
                timeout=30.0,
            )
            for task in pending:
                task.cancel()
        
        # 停止所有触发器
        for reg in self._registrations.values():
            await reg.trigger.stop()
        
        if self._processor_task:
            self._processor_task.cancel()
    
    def _enqueue_event(self, event: TriggerEvent) -> None:
        """事件入队."""
        self._event_queue.put_nowait(event)
    
    async def _process_events(self) -> None:
        """处理事件队列（并发执行）."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0,
                )
                # 并发执行，不阻塞队列消费
                task = asyncio.create_task(self._handle_event_concurrent(event))
                self._running_tasks.add(task)
                task.add_done_callback(self._running_tasks.discard)
            except asyncio.TimeoutError:
                continue
    
    async def _handle_event_concurrent(self, event: TriggerEvent) -> None:
        """并发处理事件（受 semaphore 限制）."""
        async with self._semaphore:
            await self._handle_event(event)
    
    async def _handle_event(self, event: TriggerEvent) -> None:
        """处理触发事件：执行 Goal."""
        reg = self._registrations.get(event.trigger_id)
        if not reg or not reg.enabled:
            return
        
        # 激活 skills
        for skill_name in reg.action.skills:
            self.agent.activate_skill(skill_name)
        
        # 构建 GoalConfig 并执行
        goal_config = reg.action.to_goal_config(event)
        result = await self.agent.run_goal(goal_config)
        
        # 更新统计
        reg.last_fired = datetime.now()
        reg.fire_count += 1
```

---

## Automation 简化 API

```python
# loop/automation.py

# 全局 TriggerManager 单例
_global_manager: TriggerManager | None = None

def get_global_manager(agent: AgentHarness | None = None) -> TriggerManager:
    """获取全局 TriggerManager 单例."""
    global _global_manager
    if _global_manager is None:
        if agent is None:
            raise ValueError("Agent is required to initialize global manager")
        _global_manager = TriggerManager(agent)
    return _global_manager


class Automation:
    """
    自动化任务 - 整合 Trigger + Goal.
    
    Automation 现在通过全局 TriggerManager 统一管理，
    支持并发执行和全局监控。
    """
    
    def __init__(
        self,
        name: str,
        goal: str,
        schedule: str | None = None,      # Cron 表达式
        interval_seconds: int | None = None,  # 或固定间隔
        trigger: Trigger | None = None,   # 或自定义触发器
        **kwargs,
    ):
        self.config = AutomationConfig(
            name=name,
            goal=goal,
            schedule=schedule,
            interval_seconds=interval_seconds,
            trigger=trigger,
            **kwargs,
        )
        
        self._trigger: Trigger | None = None
        self._agent: AgentHarness | None = None
        self._manager: TriggerManager | None = None  # 关联的 TriggerManager
        self._trigger_id: str | None = None          # 注册后的触发器 ID
        self._status = AutomationStatus.PENDING
    
    async def start(
        self,
        agent: AgentHarness,
        manager: TriggerManager | None = None,
    ) -> None:
        """
        启动自动化.
        
        Args:
            agent: AgentHarness 实例
            manager: 可选的 TriggerManager，不提供则使用全局管理器
        """
        self._agent = agent
        
        # 使用提供的 manager 或全局 manager
        if manager is None:
            manager = get_global_manager(agent)
        self._manager = manager
        
        # 创建触发器
        action = self._create_action()
        
        if self.config.schedule:
            self._trigger = CronTrigger(
                schedule=self.config.schedule,
                action=action,
            )
        elif self.config.interval_seconds:
            self._trigger = IntervalTrigger(
                interval_seconds=self.config.interval_seconds,
                action=action,
            )
        
        # 注册到 TriggerManager（而非独立启动）
        self._trigger_id = manager.register(self._trigger, action)
        
        # 确保 manager 正在运行
        if not manager.is_running:
            await manager.start()
        
        self._status = AutomationStatus.RUNNING
    
    async def stop(self) -> None:
        """停止自动化."""
        # 从 TriggerManager 注销
        if self._manager and self._trigger_id:
            self._manager.unregister(self._trigger_id)
            self._trigger_id = None
        elif self._trigger:
            # 兼容旧模式
            await self._trigger.stop()
        self._status = AutomationStatus.STOPPED
    
    async def pause(self) -> None:
        """暂停自动化."""
        if self._manager and self._trigger_id:
            self._manager.disable(self._trigger_id)
        elif self._trigger:
            await self._trigger.stop()
        self._status = AutomationStatus.PAUSED
    
    async def resume(self) -> None:
        """恢复自动化."""
        if self._manager and self._trigger_id:
            self._manager.enable(self._trigger_id)
            self._status = AutomationStatus.RUNNING
        elif self._trigger and self._agent:
            await self._trigger.start(self._on_trigger)
            self._status = AutomationStatus.RUNNING
    
    @property
    def result(self) -> AutomationResult:
        """执行结果（自动从 TriggerManager 同步统计）."""
        if self._manager and self._trigger_id:
            reg = self._manager.get_trigger(self._trigger_id)
            if reg:
                self._result.fire_count = reg.fire_count
                self._result.error_count = reg.error_count
                self._result.error_message = reg.last_error
                if reg.last_fired:
                    self._result.last_run = reg.last_fired
        return self._result
```

---

## 文件结构

```
packages/sdk/src/harness/
├── triggers/
│   ├── __init__.py        # 模块入口
│   ├── types.py           # TriggerType, TriggerEvent, TriggerAction
│   ├── base.py            # Trigger ABC
│   ├── cron.py            # CronTrigger
│   ├── interval.py        # IntervalTrigger
│   └── manager.py         # TriggerManager
│
└── loop/
    ├── types.py           # GoalConfig, GoalResult (Phase 1)
    ├── goal.py            # GoalVerifier (Phase 1)
    ├── goal_loop.py       # GoalLoop (Phase 1)
    └── automation.py      # Automation (Phase 2)
```

---

## API 使用示例

### 基础用法：Automation

```python
from harness import AgentHarness
from harness.loop import Automation

agent = AgentHarness(model="claude-sonnet-4-6")

# Cron 定时任务
automation = Automation(
    name="daily-report",
    schedule="0 9 * * *",  # 每天 9:00
    goal="生成每日报告并发送到 Slack",
    skills=["report-generation"],
)

await automation.start(agent)

# 检查状态
print(automation.status)  # AutomationStatus.RUNNING

# 停止
await automation.stop()
```

### 固定间隔任务

```python
# 每 5 分钟执行一次
health_check = Automation(
    name="health-check",
    interval_seconds=300,
    goal="检查系统健康状态",
)

await health_check.start(agent)
```

### 高级用法：TriggerManager

```python
from harness.triggers import TriggerManager, CronTrigger, TriggerAction

agent = AgentHarness()
manager = TriggerManager(agent)

# 注册多个触发器
trigger1 = CronTrigger(
    schedule="0 9 * * *",
    action=TriggerAction(goal="Morning report"),
)

trigger2 = IntervalTrigger(
    interval_seconds=300,
    action=TriggerAction(goal="Health check"),
)

manager.register(trigger1)
manager.register(trigger2)

# 启动所有
await manager.start()

# 查看状态
for info in manager.list_triggers():
    print(f"{info['id']}: {info['state']}")

# 停止所有
await manager.stop()
```

### 自定义验证器

```python
async def check_report_generated(result):
    """验证报告是否生成."""
    import os
    return os.path.exists("/reports/daily_report.pdf")

automation = Automation(
    name="daily-report",
    schedule="0 9 * * *",
    goal="生成每日报告",
    custom_verifier=check_report_generated,
)
```

---

## 与 Phase 1 的集成

### 数据流

```
1. Trigger 触发
   CronTrigger / IntervalTrigger
       ↓
2. 创建 TriggerEvent
   TriggerEvent(trigger_type, trigger_id, payload)
       ↓
3. 转换为 GoalConfig
   TriggerAction.to_goal_config(event)
       ↓
4. 调用 Phase 1 GoalLoop
   agent.run_goal(goal_config)
       ↓
5. 返回 GoalResult
   GoalResult(status, iterations, tokens, ...)
```

### 关键集成点

| Phase 1 组件 | Phase 2 使用方式 |
|-------------|-----------------|
| `GoalConfig` | `TriggerAction.to_goal_config()` 创建 |
| `GoalLoop` | `agent.run_goal()` 内部调用 |
| `GoalVerifier` | 通过 `custom_verifier` 传递 |
| `GoalResult` | 触发后执行的结果 |

---

## 设计决策

### 1. 为什么用事件队列而不是直接回调？

`TriggerManager` 使用 `asyncio.Queue` 作为事件队列，而不是直接在触发器回调中执行 Goal：

```python
# ✅ 当前设计：事件队列 + 并发执行
def _enqueue_event(self, event):
    self._event_queue.put_nowait(event)

async def _process_events(self):
    while self._running:
        event = await self._event_queue.get()
        # 并发执行，不阻塞队列消费
        task = asyncio.create_task(self._handle_event_concurrent(event))
        self._running_tasks.add(task)

# ❌ 直接回调（不推荐）
def _on_trigger(self, event):
    await self._handle_event(event)  # 可能阻塞触发器循环
```

**原因**：
1. **解耦触发和执行**：触发器只需负责"点火"，不需等待执行完成
2. **防止阻塞**：Goal 执行可能需要几分钟，不应阻塞触发器的调度循环
3. **更好的错误隔离**：一个 Goal 失败不会影响其他触发器
4. **支持并发**：多个触发器同时触发时，可以并发执行多个 Goal

### 2. 为什么 Automation 使用全局 TriggerManager？

`Automation` 现在通过全局 `TriggerManager` 统一管理：

```python
# ✅ 当前设计：Automation 注册到全局 TriggerManager
class Automation:
    async def start(self, agent, manager=None):
        if manager is None:
            manager = get_global_manager(agent)
        
        self._trigger_id = manager.register(self._trigger, action)
        
        if not manager.is_running:
            await manager.start()
```

**原因**：
1. **统一管理入口**：所有 Automation 可被全局监控和管理
2. **并发执行**：多个 Automation 触发时并发执行，而非串行等待
3. **简化 API**：用户仍只需 `automation.start(agent)` 一行代码
4. **灵活控制**：支持传入自定义 TriggerManager 用于隔离场景

### 3. Jitter（随机抖动）的作用

`CronTrigger` 支持 `jitter_seconds` 参数：

```python
trigger = CronTrigger(
    schedule="0 9 * * *",
    action=action,
    jitter_seconds=300,  # 最多延迟 5 分钟
)
```

**原因**：
1. **避免惊群效应**：多个 Agent 同时触发可能导致 API 限流
2. **负载均衡**：将请求分散到时间窗口内
3. **更自然的执行模式**：模拟人类的随机性

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 触发器循环崩溃 | 高 | try-except 包裹，错误后继续运行 |
| Goal 执行超时 | 中 | `GoalConfig.timeout_seconds` 限制 |
| API 限流 | 高 | `max_concurrent_goals` 限制 + `jitter_seconds` 分散 |
| 并发执行导致资源耗尽 | 高 | Semaphore 控制最大并发数 |
| 任务泄漏（未正确清理） | 中 | `_running_tasks` 追踪 + `stop()` 超时取消 |
| 进程崩溃丢失触发器 | 高 | 持久化配置（用户责任） |
| 事件队列溢出 | 低 | 无界队列 + 监控 |

---

## 测试策略

### 单元测试

```python
# tests/test_triggers.py

class TestCronTrigger:
    """CronTrigger 测试."""
    
    async def test_schedule_parsing(self):
        """测试 cron 表达式解析."""
        trigger = CronTrigger(
            schedule="0 9 * * *",
            action=TriggerAction(goal="Test"),
        )
        
        next_run = trigger.get_next_run()
        assert next_run.hour == 9
        assert next_run.minute == 0
    
    async def test_trigger_fires(self):
        """测试触发器触发."""
        trigger = IntervalTrigger(
            interval_seconds=1,
            action=TriggerAction(goal="Test"),
        )
        
        events = []
        await trigger.start(lambda e: events.append(e))
        
        await asyncio.sleep(1.5)
        await trigger.stop()
        
        assert len(events) >= 1


class TestTriggerManagerConcurrency:
    """TriggerManager 并发测试."""
    
    async def test_concurrent_goal_execution(self):
        """测试多个触发器并发执行."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent, max_concurrent_goals=3)

        # 创建 3 个触发器
        for i in range(3):
            trigger = IntervalTrigger(
                interval_seconds=1,
                action=TriggerAction(goal=f"Task {i}"),
            )
            manager.register(trigger)

        await manager.start()
        await asyncio.sleep(1.5)

        # 验证并发执行
        assert manager._semaphore is not None
        total_fires = sum(reg.fire_count for reg in manager._registrations.values())
        assert total_fires >= 3

        await manager.stop()

    async def test_max_concurrent_limit(self):
        """测试并发限制."""
        from harness.testing import MockHarness

        agent = MockHarness()
        manager = TriggerManager(agent, max_concurrent_goals=2)

        # 创建 5 个触发器
        for i in range(5):
            trigger = IntervalTrigger(
                interval_seconds=1,
                action=TriggerAction(goal=f"Task {i}"),
            )
            manager.register(trigger)

        await manager.start()
        await asyncio.sleep(1.5)

        # 验证最大并发数
        assert manager.max_concurrent_goals == 2

        await manager.stop()


class TestAutomationWithManager:
    """Automation 与 TriggerManager 集成测试."""
    
    async def test_automation_uses_global_manager(self):
        """测试 Automation 使用全局 manager."""
        from harness.testing import MockHarness
        from harness.loop.automation import (
            Automation,
            get_global_manager,
            reset_global_manager,
        )

        reset_global_manager()

        agent = MockHarness()
        automation = Automation(
            name="test",
            interval_seconds=60,
            goal="Test goal",
        )

        await automation.start(agent)

        # 验证注册到全局 manager
        manager = get_global_manager()
        assert manager.trigger_count >= 1

        await automation.stop()
        reset_global_manager()
```

---

## 验证方法

1. **运行单元测试**：
   ```bash
   PYTHONPATH=packages/sdk/src uv run pytest packages/sdk/tests/test_triggers.py -v
   ```

2. **手动验证**：
   ```python
   from harness import AgentHarness
   from harness.loop import Automation
   
   agent = AgentHarness()
   
   # 每 10 秒执行一次
   automation = Automation(
       name="test",
       interval_seconds=10,
       goal="打印当前时间",
   )
   
   await automation.start(agent)
   await asyncio.sleep(35)  # 等待 3 次触发
   await automation.stop()
   ```

---

## 后续扩展

### Phase 3 已支持的触发器类型

| 触发器类型 | 状态 | 说明 |
|-----------|------|------|
| CRON | ✅ 已实现 | Cron 表达式调度 |
| INTERVAL | ✅ 已实现 | 固定间隔调度 |
| WEBHOOK | 📝 待实现 | HTTP webhook 触发 |
| FILE_WATCH | 📝 待实现 | 文件系统变化监控 |
| EVENT | 📝 待实现 | 事件总线订阅 |

### 扩展点

添加新的触发器类型只需：

1. 继承 `Trigger` 基类
2. 实现 `start()`, `stop()`, `create_event()`
3. 设置 `trigger_type` 属性

```python
class WebhookTrigger(Trigger):
    trigger_type = TriggerType.WEBHOOK
    
    async def start(self, callback):
        # 启动 HTTP 服务器监听 webhook
        pass
    
    async def stop(self):
        # 关闭服务器
        pass
    
    def create_event(self, payload=None):
        return TriggerEvent(
            trigger_type=self.trigger_type,
            trigger_id=self.id,
            payload=payload,
        )
```

---

## 更新日志

### 2026-06-30: 并发执行重构

**TriggerManager 并发化**：
- 添加 `max_concurrent_goals` 参数控制最大并发数
- 使用 `asyncio.Semaphore` 控制并发
- `_process_events` 改为异步任务分发，不再串行等待
- `stop()` 方法现在等待活跃任务完成

**Automation 统一管理**：
- 添加全局 `TriggerManager` 单例
- `start()` 现在通过 TriggerManager 注册触发器
- `result` 属性自动同步 TriggerManager 统计
- 支持自定义 `manager` 参数用于隔离场景

**架构改进**：
```
Before:                          After:
Automation 1 → Trigger (独立)    Automation 1 ─┐
Automation 2 → Trigger (独立)    Automation 2 ─┼→ TriggerManager (并发)
                                 Automation 3 ─┘
❌ 无法全局监控                   ✅ 统一管理 + 并发执行
❌ 串行执行 Goals                 ✅ Semaphore 限流保护
```
