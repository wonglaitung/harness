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

```java
import com.harness.triggers.TriggerEvent;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

public abstract class Trigger {
    private final TriggerType triggerType;
    private TriggerAction action;
    private TriggerState state = TriggerState.CREATED;
    private String id;

    protected Trigger(TriggerType triggerType) {
        this.triggerType = triggerType;
    }

    public abstract CompletableFuture<Void> start(Consumer<TriggerEvent> callback);

    public abstract CompletableFuture<Void> stop();

    public abstract TriggerEvent createEvent(Map<String, Object> payload);

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public TriggerType getTriggerType() { return triggerType; }
    public TriggerAction getAction() { return action; }
    public void setAction(TriggerAction action) { this.action = action; }
    public TriggerState getState() { return state; }
    public boolean isRunning() { return state == TriggerState.RUNNING; }
    protected void setRunning() { this.state = TriggerState.RUNNING; }
    protected void setStopped() { this.state = TriggerState.STOPPED; }
    protected void setError(String message) { this.state = TriggerState.ERROR; }
}
```

### TriggerEvent

```java
import java.time.Instant;
import java.util.Map;

public class TriggerEvent {
    private final String triggerId;
    private final TriggerType triggerType;
    private final Map<String, Object> payload;
    private final Instant timestamp;

    public TriggerEvent(String triggerId, TriggerType triggerType,
                        Map<String, Object> payload, Instant timestamp) {
        this.triggerId = triggerId;
        this.triggerType = triggerType;
        this.payload = payload;
        this.timestamp = timestamp;
    }

    public String getTriggerId() { return triggerId; }
    public TriggerType getTriggerType() { return triggerType; }
    public Map<String, Object> getPayload() { return payload; }
    public Instant getTimestamp() { return timestamp; }
}
```

## TriggerManager

```java
import com.harness.triggers.TriggerManager;
import com.harness.triggers.Trigger;
import java.util.List;
import java.util.Map;

public class TriggerManager {
    private final GoalLoop.AgentRunner agentRunner;
    private final int maxConcurrentGoals;

    public TriggerManager(GoalLoop.AgentRunner agentRunner) { ... }
    public TriggerManager(GoalLoop.AgentRunner agentRunner, int maxConcurrentGoals) { ... }

    public String register(Trigger trigger) { ... }
    public String register(Trigger trigger, TriggerAction action) { ... }
    public boolean unregister(String triggerId) { ... }
    public CompletableFuture<Void> start() { ... }
    public CompletableFuture<Void> stop() { ... }
    public TriggerRegistration getTrigger(String triggerId) { ... }
    public List<Map<String, Object>> listTriggers() { ... }
}
```

## CronTrigger（定时触发）

```java
import com.harness.triggers.CronTrigger;
import com.harness.triggers.TriggerAction;

public class CronTrigger extends Trigger {
    public CronTrigger(String schedule, TriggerAction action) { ... }
    public CronTrigger(String schedule, TriggerAction action,
                       String timezone, int jitterSeconds) { ... }
}
```

### 使用示例

```java
import com.harness.triggers.CronTrigger;
import com.harness.triggers.TriggerAction;
import com.harness.triggers.TriggerManager;
import com.harness.loop.GoalLoop;

GoalLoop.AgentRunner agent = ...;
TriggerManager triggerManager = new TriggerManager(agent);

// 每天 9:00 生成日报
CronTrigger cron = new CronTrigger(
    "0 9 * * *",
    new TriggerAction.Builder()
        .goal("生成昨日工作日报")
        .addSkill("report")
        .build()
);
triggerManager.register(cron);

// 每小时检查系统状态
CronTrigger healthCheck = new CronTrigger(
    "0 * * * *",
    new TriggerAction.Builder()
        .goal("检查系统健康状态并报告异常")
        .build()
);
triggerManager.register(healthCheck);

// 启动所有触发器
triggerManager.start().join();
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

```java
import com.harness.triggers.WebhookTrigger;
import com.harness.triggers.TriggerAction;

// WebhookTrigger is typically configured via ConnectorManager
// See 20-connectors.md for full WebhookConnector usage
```

### 使用示例

```java
import com.harness.connectors.WebhookConnector;
import com.harness.connectors.ConnectorManager;
import com.harness.connectors.ConnectorEvent;
import com.harness.triggers.TriggerManager;
import com.harness.loop.GoalLoop;

GoalLoop.AgentRunner agent = ...;
TriggerManager triggerManager = new TriggerManager(agent);
ConnectorManager manager = new ConnectorManager();

// GitHub PR 事件触发代码审查
WebhookConnector githubPr = new WebhookConnector()
    .withEndpoint("/webhook/github")
    .withSecret("whsec_...");
manager.registerConnector(githubPr);

// Handle events via ConnectorManager
manager.setEventHandler(event -> {
    if ("github.pull_request".equals(event.getEventType())) {
        String task = "审查 PR: " + event.getPayload().get("action");
        // Execute goal via triggerManager
    }
});
```

### Webhook 事件数据

Webhook 事件的数据结构取决于外部服务。触发器会将请求体解析为 `TriggerEvent.data`：

```java
// GitHub PR Webhook event data
Map<String, Object> data = Map.of(
    "action", "opened",
    "pull_request", Map.of(
        "number", 42,
        "title", "Fix auth bug",
        "url", "https://github.com/..."
    )
);
// Template variables use {event.field.subfield} format
```

## 自定义触发器

```java
import com.harness.triggers.Trigger;
import com.harness.triggers.TriggerEvent;
import com.harness.triggers.TriggerType;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;
import java.time.Instant;

public class FileWatchTrigger extends Trigger {
    private final String watchPath;
    private final String task;
    private Consumer<TriggerEvent> callback;

    public FileWatchTrigger(String name, String watchPath, String task) {
        super(TriggerType.CUSTOM);
        this.setId(name);
        this.watchPath = watchPath;
        this.task = task;
    }

    @Override
    public CompletableFuture<Void> start(Consumer<TriggerEvent> callback) {
        this.callback = callback;
        setRunning();
        // Implement file watching logic
        // When file changes, call:
        // callback.accept(createEvent(Map.of("path", changedFile, "event", "modified")));
        return CompletableFuture.completedFuture(null);
    }

    @Override
    public CompletableFuture<Void> stop() {
        setStopped();
        return CompletableFuture.completedFuture(null);
    }

    @Override
    public TriggerEvent createEvent(Map<String, Object> payload) {
        return new TriggerEvent(getId(), getTriggerType(), payload, Instant.now());
    }
}
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

```java
import com.harness.triggers.TriggerManager;
import com.harness.triggers.IntervalTrigger;
import com.harness.triggers.TriggerAction;
import com.harness.loop.GoalLoop;
import java.util.List;
import java.util.Map;

GoalLoop.AgentRunner agent = ...;

// 创建 TriggerManager（支持并发控制）
TriggerManager manager = new TriggerManager(agent, 5);

// 注册触发器
IntervalTrigger trigger = new IntervalTrigger(
    300,
    new TriggerAction.Builder()
        .goal("健康检查")
        .build()
);
String triggerId = manager.register(trigger);

// 启动所有触发器
manager.start().join();

// 查看状态
for (Map<String, Object> info : manager.listTriggers()) {
    System.out.println(info.get("id") + ": fires=" + info.get("fire_count"));
}

// 停止所有触发器
manager.stop().join();
```

### 并发执行

TriggerManager 支持并发执行多个 Goal：

```java
// 最多同时执行 3 个 Goal
TriggerManager manager = new TriggerManager(agent, 3);

// 当多个触发器同时触发时，并发执行
// 超过限制的任务会等待 semaphore
```

## Automation 简化 API

Automation 是触发器系统的推荐入口，整合了 Trigger + Goal：

```java
import com.harness.loop.automation.Automation;
import com.harness.loop.GoalLoop;

GoalLoop.AgentRunner agent = ...;

// 定时任务（Cron）
Automation dailyReport = Automation.builder()
    .name("daily-report")
    .schedule("0 9 * * *")  // 每天 9:00
    .goal("生成每日报告并发送到 Slack")
    .build();

// 间隔任务
Automation healthCheck = Automation.builder()
    .name("health-check")
    .intervalSeconds(300)  // 每 5 分钟
    .goal("检查系统健康状态")
    .build();

// 启动
dailyReport.start(agent).join();
healthCheck.start(agent).join();

// 查看状态
System.out.println(dailyReport.getStatus());  // AutomationStatus.RUNNING

// 停止
dailyReport.stop().join();
```

### 全局管理

Automation 使用全局 TriggerManager 单例：

```java
import com.harness.loop.automation.Automation;

// Automations can be managed individually or via TriggerManager
Automation automation1 = Automation.builder()
    .name("task-1").goal("...").schedule("0 9 * * *").build();
Automation automation2 = Automation.builder()
    .name("task-2").goal("...").intervalSeconds(300).build();

automation1.start(agent).join();
automation2.start(agent).join();

// Check status
System.out.println("Automation 1: " + automation1.getStatus());
System.out.println("Automation 2: " + automation2.getStatus());
```

## 下一步

- [02-agent-loop.md](./03-agent-loop.md) - 了解 Agent Loop
- [05-skills-system.md](./16-skills-system.md) - 了解技能系统
- [07-sdk-api.md](./07-sdk-api.md) - 查看 SDK API
- [../design/phase2-automations.md](../design/phase2-automations.md) - Automations 设计文档
