# 12 - 内嵌部署指南

## 概述

本文档详细说明 Harness 在不同部署拓扑下的使用方式、限制和最佳实践。

---

## 支持的部署拓扑

### 拓扑 A：单进程脚本 ✅ 支持

```java
// Script.java
import com.harness.integration.AgentHarness;
import com.harness.types.LoopResult;

AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .build();
LoopResult result = agent.run("分析代码").join();
```

**特点**：
- 无状态持久化需求
- 内存存储或文件存储
- 无并发问题

**推荐配置**：
```java
import com.harness.core.HarnessConfig;
import com.harness.integration.AgentHarness;

HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .memoryDir("./sessions")
    .build();
AgentHarness agent = new AgentHarness(config);
```

---

### 拓扑 B：FastAPI + 单 Worker ✅ 支持

```java
// AgentService.java — 使用内置 harness.service 模块
import com.harness.integration.AgentHarness;
import com.harness.types.LoopResult;

// Spring Boot Web Controller
@RestController
public class AgentService {

    private final AgentHarness agent = AgentHarness.builder()
        .model("claude-sonnet-4-6")
        .build();

    @PostMapping("/chat")
    public Map<String, String> chat(@RequestParam String message,
                                    @RequestParam(required = false) String sessionId) {
        LoopResult result = agent.run(message, sessionId).join();
        return Map.of("response", result.content());
    }
}

// 启动：gunicorn -w 1 -k uvicorn.workers.UvicornWorker agent_service:app
```

**特点**：
- 支持 WebSocket 流式响应
- SQLite WAL 模式可支持一定并发
- Cron Trigger 进程内运行

---

### 拓扑 C：FastAPI + Gunicorn（多 Worker）✅ 支持

多 Worker 模式需要使用 Redis 作为共享存储：

```java
import com.harness.integration.AgentHarness;
import com.harness.core.HarnessConfig;
import com.harness.memory.SessionManager;

// 配置 Redis 存储
SessionManager sessionManager = new SessionManager("redis://localhost:6379");
HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .storage(HarnessConfig.StorageConfig.builder()
        .type("redis")
        .build())
    .build();
AgentHarness agent = new AgentHarness(config);

// 或使用 harness.service 完整服务
// 见 15-spring-cloud-integration.md
```

**关键问题及解决方案**：

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Trigger 重复执行 | 每个 Worker 都启动 CronTrigger | 独立 Trigger Worker 或 Celery Beat |
| Session 缓存不一致 | Worker A 的缓存，Worker B 无法访问 | Redis 共享存储 |
| SQLite 锁竞争 | 多进程写入冲突 | 使用 PostgreSQL 或 Redis |

**推荐方案**：

```java
// 方案 1：使用 harness.service（推荐）
// 完整的 Spring Boot 服务，支持多 Worker
// 启动：java -jar harness-service.jar

// 方案 2：独立 Trigger Worker
// TriggerWorker.java
AgentHarness agent = AgentHarness.builder().build();
agent.startTriggerWorker();  // 独立进程

// 方案 3：Spring Task 调度
import org.springframework.scheduling.annotation.Scheduled;

@Component
public class AgentScheduler {

    private final AgentHarness agent = AgentHarness.builder().build();

    @Scheduled(cron = "0 9 * * *")
    public void runDailyReport() {
        agent.run("生成每日报告").join();
    }
}
```

---

### 拓扑 D：Kubernetes 多副本 ✅ 支持

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: harness-agent
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: agent
        image: harness-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: POD_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: NACOS_SERVER
          value: "nacos-service:8848"  # 可选
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
```

**关键配置**：
- 使用 Redis 作为 Session 和 Lock 存储
- `POD_IP` 环境变量用于服务注册
- 健康检查端点 `/health`
- 可选：Nacos/Eureka 服务发现

---

## 存储后端选型矩阵

| 存储类型 | 单进程 | 多 Worker | K8s 多副本 | 延迟 | 持久化 | 成本 |
|----------|--------|-----------|------------|------|--------|------|
| 内存 | ✅ | ❌ | ❌ | 最低 | ❌ | 低 |
| 文件 | ✅ | ⚠️ 加锁 | ❌ | 低 | ✅ | 低 |
| SQLite (WAL) | ✅ | ⚠️ 有限并发 | ❌ | 低 | ✅ | 低 |
| Redis | ✅ | ✅ | ✅ | 中 | ⚠️ 需配置 | 中 |
| PostgreSQL | ✅ | ✅ | ✅ | 中 | ✅ | 中-高 |

---

## 常见陷阱

### 陷阱 1：在 Jupyter 中使用 run_sync()

```java
// ❌ 错误：同步调用阻塞主线程
LoopResult result = agent.run("hello").join();  // 阻塞调用

// ✅ 正确：使用 CompletableFuture 异步处理
agent.run("hello").thenAccept(result -> {
    System.out.println(result.content());
});

// 或在 Spring 中使用 @Async
@Async
public CompletableFuture<LoopResult> runAsync(String prompt) {
    return agent.run(prompt);
}
```

### 陷阱 2：热重载丢失状态

```java
// 开发环境热重载会重置内存状态
// 解决：使用持久化存储
HarnessConfig config = HarnessConfig.builder()
    .memoryDir("./persistent_memory")  // 持久化到磁盘
    .build();
AgentHarness agent = new AgentHarness(config);
```

### 陷阱 3：Gunicorn Worker 数量 > 1 导致 Trigger 重复

```java
// ❌ 错误：每个 Worker 都会执行定时任务
// 解决：使用独立 Trigger Worker 或 Spring Task 调度
```

### 陷阱 4：MCP 子进程孤儿问题

宿主应用崩溃时，MCP 子进程可能变为孤儿进程。解决方案见 [03-tool-system.md](./04-tool-system.md) 的 MCP 子进程生命周期管理章节。

---

## 安全配置清单

| 配置项 | 开发环境 | 生产环境 |
|--------|----------|----------|
| 沙箱模式 | `full_access` | `sandbox` |
| 允许的路径 | `["./"]` | 显式白名单 |
| 网络访问 | 无限制 | 仅内网 |
| 资源限制 | 无 | CPU/Memory/Time |
| 日志级别 | DEBUG | INFO |
| 审计日志 | 可选 | 必须 |

---

## 监控与告警

### 推荐指标

- `harness_loop_iterations_total`：循环迭代次数
- `harness_tool_calls_total{tool, success}`：工具调用计数
- `harness_llm_tokens_total{type}`：Token 使用量
- `harness_session_duration_seconds`：会话持续时间

### Prometheus 告警规则

```yaml
groups:
- name: harness
  rules:
  - alert: AgentLoopStuck
    expr: harness_loop_iterations_total > 20
    for: 5m
    annotations:
      summary: "Agent 循环可能卡住"

  - alert: HighTokenUsage
    expr: rate(harness_llm_tokens_total{type="output"}[5m]) > 10000
    annotations:
      summary: "Token 使用率过高"

  - alert: ToolFailure
    expr: rate(harness_tool_calls_total{success="false"}[5m]) > 0.1
    annotations:
      summary: "工具调用失败率过高"
```

---

## 已知限制

1. **单进程模式**: SQLite 适合低并发，高并发需切换 WAL 模式
2. **多进程模式**: 必须使用 Redis/PostgreSQL，且 Trigger 需要 Leader 选举
3. **热重载**: 开发环境热重载会丢失内存状态，需要持久化存储
4. **Windows**: 部分信号处理和沙箱功能（如 `setrlimit`）受限
5. **MCP 进程组**: `preexec_fn` 在 Windows 上不可用

---

## 拓扑 E：Spring Cloud 微服务架构 ✅ 支持

适用场景：将 Agent 集成到 Spring Cloud 微服务生态。

### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Spring Cloud Gateway                      │
│  (路由、熔断、限流、JWT 认证、链路追踪、服务发现)             │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 Harness Agent Service (Python)               │
│  - FastAPI 服务包装                                          │
│  - 健康检查 /health                                          │
│  - TraceID 提取                                              │
│  - AgentHarness 核心                                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  外部存储 (Redis/PostgreSQL)                                 │
│  - Session 状态                                               │
│  - 分布式锁                                                   │
└─────────────────────────────────────────────────────────────┘
```

### 已实现功能

| 功能 | 模块 | 状态 |
|-----|------|------|
| HTTP 服务包装 | `harness.service` | ✅ |
| 健康检查 `/health` | `harness.service` | ✅ |
| Prometheus 指标 `/metrics` | `harness.service.metrics` | ✅ |
| TraceID 传播 | `harness.service.tracing` | ✅ |
| WebSocket 流式执行 | `harness.service` | ✅ |
| Redis 分布式会话 | `harness.service.store_redis` | ✅ |
| Redis 分布式锁 | `harness.service.store_redis` | ✅ |
| Nacos 服务注册 | `harness.service.discovery` | ✅ |
| Eureka 服务注册 | `harness.service.discovery` | ✅ |
| 统一错误响应 | `harness.service.error_handler` | ✅ |

### 长时任务处理

Agent 的 ReAct 循环可能耗时较长，推荐使用 **WebSocket 流式模式**：

```
Java Client -> WebSocket /ws/run
              <- ProgressEvent (LOOP_START)
              <- ProgressEvent (LLM_CALL)
              <- ProgressEvent (TOOL_CALL)
              ...
              <- ProgressEvent (LOOP_END) + 最终结果
```

SDK 已有 `ProgressEvent` 机制，天然支持 WebSocket 推送。

### 详细设计

完整的实施指南（含 Java 客户端示例、K8s 配置、安全设计等）见：

**👉 [15-spring-cloud-integration.md](./15-spring-cloud-integration.md)**
