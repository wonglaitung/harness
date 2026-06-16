# 12 - 内嵌部署指南

## 概述

本文档详细说明 Harness 在不同部署拓扑下的使用方式、限制和最佳实践。

---

## 支持的部署拓扑

### 拓扑 A：单进程脚本 ✅ MVP 支持

```python
# script.py
from harness import AgentHarness

agent = AgentHarness(model="claude-sonnet-4-6")
result = agent.run_sync("分析代码")
```

**特点**：
- 无状态持久化需求
- 内存存储或文件存储
- 无并发问题

**推荐配置**：
```python
agent = (HarnessBuilder()
    .with_llm("claude-sonnet-4-6")
    .with_memory("file", path="./sessions")
    .build()
)
```

---

### 拓扑 B：FastAPI + 单 Worker ✅ MVP 支持

```python
# app.py
from fastapi import FastAPI
from harness import AgentHarness

app = FastAPI()
agent = AgentHarness(model="claude-sonnet-4-6")

@app.post("/chat")
async def chat(message: str, session_id: str = None):
    result = await agent.run(message, session_id=session_id)
    return {"response": result.content}

# 启动：uvicorn app:app --workers 1
```

**特点**：
- 支持 WebSocket 流式响应
- SQLite WAL 模式可支持一定并发
- Cron Trigger 进程内运行

**推荐配置**：
```python
agent = (HarnessBuilder()
    .with_llm("claude-sonnet-4-6")
    .with_memory("sqlite", db_path="harness.db", pool_size=5)
    .with_security("sandbox")
    .build()
)
```

---

### 拓扑 C：FastAPI + Gunicorn（多 Worker）⚠️ Phase 2

```python
# 需要 Redis/PostgreSQL 后端
agent = (HarnessBuilder()
    .with_llm("claude-sonnet-4-6")
    .with_memory("redis", url="redis://localhost:6379")
    .with_triggers(mode="leader_election")  # Leader 选举
    .build()
)
```

**关键问题**：

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Trigger 重复执行 | 每个 Worker 都启动 CronTrigger | Leader 选举或独立 Trigger Worker |
| Session 缓存不一致 | Worker A 的缓存，Worker B 无法访问 | Redis 共享存储 |
| SQLite 锁竞争 | 多进程写入冲突 | PostgreSQL 或 Redis |

**解决方案**：

```python
# 方案 1：独立 Trigger Worker
# trigger_worker.py
agent = AgentHarness(...)
agent.start_trigger_worker()  # 独立进程

# 方案 2：Celery Beat 集成
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

---

### 拓扑 D：Kubernetes 多副本 ⚠️ Phase 2

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
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
---
# 独立 Trigger Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: harness-trigger
spec:
  replicas: 1  # 单副本
  template:
    spec:
      containers:
      - name: trigger
        env:
        - name: TRIGGER_MODE
          value: "singleton"
```

**关键配置**：
- 使用 Redis 作为 Session 和 Lock 存储
- Trigger 作为独立 Deployment（单副本）
- 或使用 K8s CronJob 替代内置 Trigger

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

```python
# ❌ 错误
result = agent.run_sync("hello")
# RuntimeError: Event loop is already running

# ✅ 正确
result = await agent.run("hello")

# 或安装 nest_asyncio
import nest_asyncio
nest_asyncio.apply()
result = agent.run_sync("hello")  # 现在可以工作
```

### 陷阱 2：热重载丢失状态

```python
# 开发环境热重载会重置内存状态
# 解决：使用持久化存储
agent = AgentHarness(
    memory_dir="./persistent_memory"  # 久化到磁盘
)
```

### 陷阱 3：Gunicorn Worker 数量 > 1 导致 Trigger 重复

```python
# ❌ 错误：每个 Worker 都会执行定时任务
# 解决：使用独立 Trigger Worker 或 Celery Beat
```

### 陷阱 4：MCP 子进程孤儿问题

宿主应用崩溃时，MCP 子进程可能变为孤儿进程。解决方案见 [03-tool-system.md](./03-tool-system.md) 的 MCP 子进程生命周期管理章节。

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

## 拓扑 E：Spring Cloud 微服务架构

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

### 关键要求对比

| 要求 | SDK 现状 | 需要新增 |
|-----|---------|---------|
| HTTP 服务 | ❌ SDK 是库 | FastAPI 包装层 |
| 健康检查 `/health` | ❌ | 需要添加 |
| 服务注册/发现 | ❌ | Nacos/Eureka 注册 |
| 链路追踪 | ⚠️ 有 OpenTelemetry | TraceID 提取中间件 |
| 指标导出 `/metrics` | ⚠️ 有 OTel | Prometheus exporter |
| 分布式状态 | ⚠️ SQLite 本地 | Redis/PostgreSQL |

### 实施路径

| Phase | 内容 | 代码量 | 优先级 |
|-------|------|--------|--------|
| 1 | HTTP 服务包装 + Health Check + TraceID 提取 | ~220 行 | **必需** |
| 2 | Prometheus 指标导出 | ~50 行 | 推荐 |
| 3 | Redis 分布式状态 | ~170 行 | 按需 |
| 4 | Nacos/Eureka 服务注册 | ~80 行 | 可选 |

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

**👉 [14-spring-cloud-integration.md](./14-spring-cloud-integration.md)**