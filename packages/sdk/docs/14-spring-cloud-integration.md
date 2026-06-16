# 14 - Spring Cloud 集成指南

> 本文档是 [12-deployment.md](./12-deployment.md) 的延伸章节。
> 适用于将 Agent 集成到 Spring Cloud 微服务架构的场景。
> 
> 评估日期：2026-06-16

---

## 一、背景与目标

### 问题陈述

业界对于"AI Agent SDK 与微服务架构的结合"存在架构抉择：
- **Spring Cloud** 解决的是"系统的韧性与营运"
- **专用 MAS 框架**（如 AutoGen, LangGraph）解决的是"代理的智慧逻辑"

 Harness SDK 需要从"单体运行"转变为"混合架构下的微服务组件"，直接对接 Spring Cloud。

### 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Spring Cloud Gateway                      │
│  (路由、熔断、限流、JWT 认证、链路追踪、服务发现)             │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/gRPC
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 Harness Agent Service (Python)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  FastAPI / gRPC Server (需要新增)                    │   │
│  │  - 暴露 REST API                                     │   │
│  │  - 提取 TraceID                                      │   │
│  │  - 健康检查 /metrics                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AgentHarness (现有 SDK)                             │   │
│  │  - AgentLoop (ReAct 循环)                           │   │
│  │  - OpenTelemetry Tracing                            │   │
│  │  - Circuit Breaker                                  │   │
│  │  - Cost Controller                                  │   │
│  │  - Session Store (SQLite)                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  外部存储 (需要集成)                                 │   │
│  │  - Redis (分布式状态/锁)                             │   │
│  │  - PostgreSQL/MySQL (会话持久化)                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、分层治理理念

### 业界共识

业界目前倾向于将基础设施与代理逻辑进行**纵向分层**，而不是横向二选一：

| 层级 | 技术架构 | 负责范畴 |
| --- | --- | --- |
| **基础设施层** | Spring Cloud | 流量管控、熔断、负载均衡、服务发现、配置管理、分布式追踪 |
| **代理逻辑层** | MAS SDK | 代理的状态管理、决策路径、工具调用、上下文记忆 |

### 为什么两者必须结合

1. **Spring Cloud 提供"监控与可追踪性"**：在每一个 Agent 决策节点打上 Trace ID，审计"为什么 Agent 做出这个决策"
2. **Spring Cloud 提供"隔离性与弹性"**：当 Agent 进入死循环时，熔断器直接切断流量，不拖垮整个后台

---

## 三、SDK 现状 vs Spring Cloud 要求

### Spring Cloud 对微服务的基本要求

| 要求 | SDK 现状 | 差距 | 需要做什么 |
|-----|---------|-----|-----------|
| **HTTP/gRPC 服务** | ❌ SDK 是库，不暴露服务 | 大 | 需要包装层 |
| **健康检查** (`/health`) | ❌ 无 | 中 | 需要添加 |
| **服务注册/发现** | ❌ 无 | 中 | 需要集成 Nacos/Eureka |
| **链路追踪** (TraceID) | ⚠️ 有 OpenTelemetry，但无入口提取 | 小 | 需要添加 TraceID 提取中间件 |
| **指标导出** (`/metrics`) | ⚠️ 有 OTel，无 Prometheus 端点 | 小 | 需要配置 Prometheus exporter |
| **配置中心** | ❌ 无 | 中 | 需要集成 Nacos Config |
| **分布式状态** | ⚠️ SQLite 是本地的 | 中 | 需要支持 Redis/PostgreSQL |

### SDK 已具备的能力（可复用）

| 能力 | 实现位置 | 如何复用 |
|-----|---------|---------|
| OpenTelemetry 集成 | `core/observability.py` | 添加 TraceContext 提取 |
| 熔断器 | `core/circuit_breaker.py` | 直接使用 |
| 成本控制 | `core/cost_controller.py` | 直接使用 |
| 步骤预算 | `core/step_budget.py` | 直接使用 |
| 会话存储抽象 | `memory/store.py` (SessionStore 接口) | 实现 Redis/PostgreSQL 版本 |
| 快照/恢复 | `types.py` (LoopSnapshot) | 用于断点续传 |
| Stuck 检测 | `core/stuck_detector.py` | 直接使用 |

---

## 四、对业界建议的评估

### 业界建议的正确观点

| 建议 | 评估 | 说明 |
|-----|-----|------|
| "SDK 必须具备网络通讯能力" | ✅ 正确 | SDK 需要包装成 HTTP/gRPC 服务 |
| "拦截器层提取 TraceID" | ✅ 正确 | 需要 Middleware 从 Header 提取 |
| "Health Check 端点" | ✅ 正确 | Spring Cloud 需要此端点判断服务存活 |
| "Registry Client" | ✅ 正确 | 需要向 Nacos/Eureka 注册 |
| "状态外部化 (Redis)" | ✅ 正确 | 多实例部署必须 |
| "分布式锁" | ✅ 正确 | 金融级场景需要 |
| "递归深度控制" | ✅ 已有 | `StepBudgetController` 已实现 |
| "停止条件判定" | ✅ 已有 | `StuckDetector` + 硬规则已实现 |

### 业界建议中过度工程的部分

| 建议 | 评估 | 理由 |
|-----|-----|------|
| "工作流引擎" | ❌ 过度 | `AgentLoop` 本身就是状态机，状态存在 Session 中即可 |
| "Kafka 消息队列" | ❌ 过度 | 不是所有场景都需要，可选项 |
| "独立的 Planner Service" | ❌ 过度 | 增加运维复杂度，SDK 内置足够 |
| "完全重写存储层" | ⚠️ 部分 | 只需实现新的 `SessionStore` 子类 |

---

## 五、实施路径

### Phase 1: 最小可部署版本

**目标**：SDK 包装成 Spring Cloud 可识别的微服务

**需要新增**：

```python
# agent_service.py - FastAPI 服务包装

from fastapi import FastAPI, Request
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

app = FastAPI()
propagator = TraceContextTextMapPropagator()

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/run")
async def run_agent(request: Request):
    # 提取 Spring Cloud 传递的 TraceID
    headers = dict(request.headers)
    ctx = propagator.extract(headers)
    
    # 注入到 SDK 的 OpenTelemetry context
    # ... 调用 AgentHarness
```

**改动清单**：

| 文件 | 改动 | 代码量 |
|-----|-----|-------|
| 新增 `agent_service.py` | FastAPI 服务包装 | ~100 行 |
| 新增 `middleware/tracing.py` | TraceID 提取中间件 | ~50 行 |
| 新增 `config/nacos_client.py` | Nacos 服务注册 | ~50 行 |
| 修改 `observability.py` | 接受外部 TraceContext | ~20 行 |

**总计**：~220 行

### Phase 2: 可观测性集成

**目标**：让 Spring Cloud 能监控 Agent 执行指标

**需要新增**：

```python
# Prometheus 指标导出
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import make_asgi_app

# 挂载 /metrics 端点
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

**改动清单**：

| 文件 | 改动 | 代码量 |
|-----|-----|-------|
| 修改 `observability.py` | 添加 Prometheus exporter | ~30 行 |
| 修改 `agent_service.py` | 挂载 `/metrics` 端点 | ~20 行 |

**总计**：~50 行

### Phase 3: 分布式状态

**目标**：让 Agent 能多实例部署

**需要新增**：

```python
# memory/store_redis.py - Redis Session Store

import redis
from harness.memory.store import SessionStore
from harness.types import Session

class RedisSessionStore(SessionStore):
    """Redis-based session storage for distributed deployment."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
    
    def save(self, session: Session) -> None:
        self.redis.set(
            f"session:{session.id}",
            session.to_json(),
            ex=3600  # 1 hour TTL
        )
    
    def load(self, session_id: str) -> Session | None:
        data = self.redis.get(f"session:{session_id}")
        return Session.from_json(data) if data else None
    
    def delete(self, session_id: str) -> None:
        self.redis.delete(f"session:{session_id}")
```

**改动清单**：

| 文件 | 改动 | 代码量 |
|-----|-----|-------|
| 新增 `memory/store_redis.py` | Redis Session Store | ~100 行 |
| 新增 `core/distributed_lock.py` | Redis 分布式锁 | ~50 行 |
| 修改 `sdk/harness.py` | 支持 Redis 配置选项 | ~20 行 |

**总计**：~170 行

### Phase 4: 服务发现

**目标**：Agent 自动注册到 Nacos/Eureka

**需要新增**：

```python
# config/nacos_client.py - 服务注册

import nacos
import socket

client = nacos.NacosClient("nacos:8848")

def get_local_ip():
    return socket.gethostbyname(socket.gethostname())

@app.on_event("startup")
async def register_service():
    client.register_service(
        service_name="harness-agent",
        ip=get_local_ip(),
        port=8000,
        metadata={"version": "1.0"}
    )

@app.on_event("shutdown")
async def deregister_service():
    client.deregister_service(
        service_name="harness-agent",
        ip=get_local_ip(),
        port=8000
    )
```

**改动清单**：

| 文件 | 改动 | 代码量 |
|-----|-----|-------|
| 新增 `config/nacos_client.py` | Nacos 服务注册/注销 | ~80 行 |

**总计**：~80 行

---

## 六、总代码量估计

| Phase | 内容 | 必要性 | 代码量 |
|-------|------|--------|--------|
| 1 | HTTP 服务包装 + Health Check + TraceID 提取 | **必需** | ~220 行 |
| 2 | Prometheus 指标导出 | 推荐 | ~50 行 |
| 3 | Redis 分布式状态 | 按需 | ~170 行 |
| 4 | Nacos/Eureka 服务注册 | 可选 | ~80 行 |

**总计：~520 行**，不破坏现有 SDK 架构。

---

## 七、长时任务与超时策略

### 问题

AI 的规划（Planning）和递迴（Recursion）是"耗时且具状态的"过程，若硬塞进标准 RESTful HTTP，会导致超时、死锁。

### SDK 现有的长时任务处理机制

Harness SDK 已经内置了完整的流式事件机制，非常适合处理长时任务：

#### 1. ProgressEvent 进度事件系统

SDK 定义了 `ProgressEvent` 和 `ProgressCallback` 类型，用于实时反馈执行状态：

```python
# types.py
class ProgressEventType(Enum):
    LOOP_START = "loop_start"            # Agent 循环开始
    LOOP_END = "loop_end"                # Agent 循环结束
    STATE_CHANGE = "state_change"        # 状态变化
    TOOL_CALL = "tool_call"              # 工具调用开始
    TOOL_RESULT = "tool_result"          # 工具调用结果
    LLM_CALL = "llm_call"                # LLM 调用开始
    LLM_RESPONSE = "llm_response"        # LLM 响应接收
    TEXT_CHUNK = "text_chunk"            # 流式文本块
    ITERATION = "iteration"              # 迭代计数
    ERROR = "error"                      # 错误发生
    STREAM_BACKPRESSURE = "stream_backpressure"  # 流式输出背压

@dataclass
class ProgressEvent:
    type: ProgressEventType
    message: str
    timestamp: datetime
    data: dict[str, Any]  # 工具名、参数、耗时等
    duration_ms: float | None = None

ProgressCallback = Callable[[ProgressEvent], None]
```

**使用方式**：

```python
# 使用进度回调
result = await agent.run(
    "Analyze the codebase",
    on_progress=lambda event: print(f"[{event.type.value}] {event.message}")
)
```

#### 2. LoopSnapshot 快照恢复机制

SDK 支持中断恢复，长时任务可以保存快照，后续从中断点继续：

```python
# types.py
@dataclass
class LoopSnapshot:
    session_id: str
    messages: list[Message]
    current_iteration: int
    pending_tool_calls: list[ToolCall]  # 待执行的工具调用
    last_llm_response: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoopSnapshot": ...
```

**使用方式**：

```python
# 保存快照
snapshot = agent.create_snapshot(session_id="task-123")
snapshot_dict = snapshot.to_dict()

# 存储到 Redis
await redis.set(f"snapshot:{task_id}", json.dumps(snapshot_dict))

# 恢复执行
snapshot = LoopSnapshot.from_dict(snapshot_dict)
result = await agent.restore_from_snapshot(snapshot)
```

#### 3. StreamingHandler 流式处理器

SDK 内置流式处理器，支持背压控制：

```python
# core/streaming.py
class StreamingHandler:
    def __init__(self, config: StreamingConfig, on_progress: ProgressCallback):
        self._buffer: deque[Chunk] = deque(maxlen=config.buffer_size)
        self._is_paused = False

    @property
    def should_pause(self) -> bool:
        """检查是否需要暂停上游（背压控制）"""
        return self.buffer_usage >= self.config.backpressure_threshold

    async def handle(self, chunk: Chunk) -> None:
        """处理流入的 chunk，自动管理背压"""
        ...

    def get_full_content(self) -> str:
        """获取累积的完整内容"""
        return "".join(self._text_content)
```

### 集成到 Spring Cloud 的方案

> **架构说明**：以下示例分为两部分：
> - **服务器端**（Python FastAPI）：Harness Agent Service 暴露的端点
> - **客户端**（Java）：Spring Cloud 微服务调用 Agent Service 的代码

#### 方案 A：WebSocket 流式模式（推荐）

SDK 的 `ProgressEvent` 天然支持 WebSocket 推送：

```
Java Client -> WebSocket /ws/run
              <- ProgressEvent (LOOP_START)
              <- ProgressEvent (LLM_CALL)
              <- ProgressEvent (TOOL_CALL)
              <- ProgressEvent (TOOL_RESULT)
              <- ProgressEvent (TEXT_CHUNK)
              ...
              <- ProgressEvent (LOOP_END) + 最终结果
```

**服务器端（Python FastAPI）**：

```python
from fastapi import WebSocket
from harness import AgentHarness, ProgressEvent

@app.websocket("/ws/run")
async def run_agent_ws(websocket: WebSocket):
    await websocket.accept()

    async def on_progress(event: ProgressEvent):
        await websocket.send_json({
            "type": event.type.value,
            "message": event.message,
            "data": event.data,
        })

    agent = AgentHarness()

    async for chunk in agent.stream(prompt, on_progress=on_progress):
        await websocket.send_json({"type": "chunk", "content": chunk})

    await websocket.send_json({"type": "done"})
```

**客户端（Java Spring）**：

```java
// 使用 Spring WebSocket 客户端
@Component
public class AgentWebSocketClient {

    private final WebSocketClient webSocketClient;

    public AgentWebSocketClient(WebSocketClient webSocketClient) {
        this.webSocketClient = webSocketClient;
    }

    public Flux<ProgressEvent> runAgent(String prompt) {
        return Flux.create(emitter -> {
            webSocketClient.execute(
                URI.create("ws://harness-agent:8000/ws/run"),
                new WebSocketHandler() {
                    @Override
                    public void afterConnectionEstablished(WebSocketSession session) {
                        // 发送任务请求
                        session.sendMessage(new TextMessage(
                            "{\"prompt\": \"" + prompt + "\"}"
                        ));
                    }

                    @Override
                    public void handleMessage(WebSocketSession session, WebSocketMessage<?> message) {
                        // 接收 ProgressEvent
                        JSONObject event = new JSONObject(message.getPayload());
                        String type = event.getString("type");

                        emitter.next(new ProgressEvent(
                            type,
                            event.getString("message"),
                            event.getJSONObject("data")
                        ));

                        if ("done".equals(type)) {
                            emitter.complete();
                        }
                    }

                    @Override
                    public void handleTransportError(WebSocketSession session, Throwable exception) {
                        emitter.error(exception);
                    }
                }
            );
        });
    }
}

// 调用示例
@Service
public class MyService {

    @Autowired
    private AgentWebSocketClient agentClient;

    public void analyzeCode(String prompt) {
        agentClient.runAgent(prompt)
            .doOnNext(event -> log.info("收到事件: {}", event.getType()))
            .doOnComplete(() -> log.info("任务完成"))
            .subscribe();
    }
}
```

**优势**：
- 实时反馈，用户体验好
- 不会因 Gateway 超时而断开（WebSocket 是长连接）
- SDK 已有完整的事件类型定义

#### 方案 B：异步任务 + 轮询模式

适合需要离线执行的场景：

**服务器端（Python FastAPI）**：

```python
# 提交任务
@app.post("/api/tasks")
async def create_task(request: RunRequest):
    task_id = str(uuid4())

    # 保存快照到 Redis
    snapshot = agent.create_snapshot()
    await redis.set(f"task:{task_id}", snapshot.to_json())

    # 后台执行
    asyncio.create_task(run_agent_background(task_id, request))

    return {"task_id": task_id, "status": "PENDING"}

# 查询状态
@app.get("/api/tasks/{task_id}/status")
async def get_status(task_id: str):
    status = await redis.get(f"task:{task_id}:status")
    return {"task_id": task_id, "status": status}

# 获取结果
@app.get("/api/tasks/{task_id}/result")
async def get_result(task_id: str):
    result = await redis.get(f"task:{task_id}:result")
    return result
```

**客户端（Java Spring）**：

```java
// 使用 RestTemplate 或 WebClient
@Service
public class AgentTaskClient {

    private final WebClient webClient;
    private final String agentServiceUrl = "http://harness-agent:8000";

    public AgentTaskClient(WebClient.Builder builder) {
        this.webClient = builder.baseUrl(agentServiceUrl).build();
    }

    // 提交任务
    public Mono<TaskResponse> createTask(String prompt) {
        return webClient.post()
            .uri("/api/tasks")
            .bodyValue(new RunRequest(prompt))
            .retrieve()
            .bodyToMono(TaskResponse.class);
    }

    // 查询状态（轮询）
    public Mono<TaskStatus> getStatus(String taskId) {
        return webClient.get()
            .uri("/api/tasks/{taskId}/status", taskId)
            .retrieve()
            .bodyToMono(TaskStatus.class);
    }

    // 获取结果
    public Mono<TaskResult> getResult(String taskId) {
        return webClient.get()
            .uri("/api/tasks/{taskId}/result", taskId)
            .retrieve()
            .bodyToMono(TaskResult.class);
    }

    // 完整流程：提交 + 轮询 + 获取结果
    public Mono<TaskResult> runAndWait(String prompt) {
        return createTask(prompt)
            .flatMap(task -> pollUntilComplete(task.getTaskId()))
            .flatMap(this::getResult);
    }

    private Mono<String> pollUntilComplete(String taskId) {
        return Mono.defer(() ->
            getStatus(taskId)
                .flatMap(status -> {
                    if ("COMPLETED".equals(status.getStatus())) {
                        return Mono.just(taskId);
                    } else if ("ERROR".equals(status.getStatus())) {
                        return Mono.error(new AgentException("任务失败"));
                    } else {
                        // 继续轮询，间隔 1 秒
                        return Mono.delay(Duration.ofSeconds(1))
                            .then(pollUntilComplete(taskId));
                    }
                })
        );
    }
}

// 数据模型
@Data
public class TaskResponse {
    private String taskId;
    private String status;
}

@Data
public class TaskStatus {
    private String taskId;
    private String status;  // PENDING, RUNNING, COMPLETED, ERROR
}

@Data
public class TaskResult {
    private String taskId;
    private String status;
    private String content;  // Agent 最终输出
    private Integer iterations;
    private TokenUsage tokenUsage;
}

// 调用示例
@RestController
public class MyController {

    @Autowired
    private AgentTaskClient agentClient;

    @PostMapping("/analyze")
    public Mono<String> analyze(@RequestBody String prompt) {
        return agentClient.runAndWait(prompt)
            .map(result -> result.getContent());
    }
}
```

#### 方案 C：Webhook 回调模式

适合需要通知外部系统的场景：

**服务器端（Python FastAPI）**：

```python
async def run_agent_with_callback(task_id: str, request: RunRequest, callback_url: str):
    result = await agent.run(request.prompt)

    # 完成后回调
    async with httpx.AsyncClient() as client:
        await client.post(callback_url, json={
            "task_id": task_id,
            "status": "COMPLETED",
            "result": result.content,
        })
```

**客户端（Java Spring）**：

```java
// 提交任务时指定回调 URL
@Service
public class AgentWebhookClient {

    private final WebClient webClient;
    private final String agentServiceUrl = "http://harness-agent:8000";
    private final String myCallbackUrl = "http://my-service:8080/api/callback";

    public Mono<TaskResponse> createTaskWithCallback(String prompt) {
        return webClient.post()
            .uri("/api/tasks")
            .bodyValue(new RunRequest(
                prompt,
                myCallbackUrl  // 指定回调地址
            ))
            .retrieve()
            .bodyToMono(TaskResponse.class);
    }
}

// 接收回调
@RestController
public class CallbackController {

    @PostMapping("/api/callback")
    public void handleCallback(@RequestBody CallbackPayload payload) {
        log.info("任务 {} 完成，结果: {}", payload.getTaskId(), payload.getResult());

        // 处理结果
        processResult(payload);
    }
}

@Data
public class CallbackPayload {
    private String taskId;
    private String status;
    private String result;
}
```

### 方案对比

| 方案 | 适用场景 | SDK 支持度 | Gateway 超时风险 | 客户端复杂度 |
|-----|---------|-----------|----------------|-------------|
| WebSocket 流式 | 实时交互 | ✅ 完整支持 | 无（长连接） | 中（需 WebSocket 客户端） |
| 异步轮询 | 离线任务 | ✅ LoopSnapshot | 无（已返回 202） | 低（标准 REST） |
| Webhook 回调 | 系统集成 | ⚠️ 需自行实现 | 无（已返回 202） | 低（需回调端点） |

**推荐**：方案 A（WebSocket）- SDK 已有 `ProgressEvent` 机制，最适合实时反馈

---

## 八、风险评估

| 风险 | 级别 | 缓解措施 |
|-----|-----|---------|
| Python 服务注册到 Nacos | 低 | `python-nacos` 库成熟 |
| OpenTelemetry 与 Spring Cloud Sleuth 兼容 | 低 | 标准 W3C TraceContext |
| Redis 状态管理 | 低 | SDK 已有 `SessionStore` 抽象 |
| 长时任务超时 | 中 | 使用 WebSocket 流式模式 |
| 多实例会话一致性 | 中 | 分布式锁 + 会话粘性路由 |

---

## 十、架构师视角的关键补充

### 10.1 Redis 状态管理的序列化陷阱 (Phase 3)

**风险点**：如果 SDK 原本在 SQLite 中存的是 Python 物件（使用 `pickle`），换到 Redis 后，如果不同 Agent 实例之间的 Python 环境版本或依赖不一致，序列化会崩溃。

**最佳实践**：

1. **严格 JSON 化**：确保所有的 `Session` 资料在写入 Redis 前，都必须经过 `Pydantic` 或类似的 Schema 模型转换为标准 JSON。不要直接存序列化后的 Python 物件。

```python
# 推荐：使用 Pydantic 模型
from pydantic import BaseModel

class SessionModel(BaseModel):
    id: str
    messages: list[MessageModel]
    created_at: datetime
    updated_at: datetime
    metadata: dict

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "SessionModel":
        return cls.model_validate_json(data)
```

2. **Schema 版本管理**：未来如果 SDK 修改了 Session 的结构（例如加了栏位），JSON 储存必须具备向后相容性，否则旧的 Redis 资料会导致 Agent 启动报错。

```python
class SessionModel(BaseModel):
    # 版本栏位，用于未来迁移
    schema_version: int = 1
    
    # 向后相容：新栏位使用默认值
    new_field: str | None = None
```

### 10.2 长时任务的标准微服务处理模式

**问题**：如果 Agent 的逻辑（ReAct 循环）超过了 Gateway 的预设超时时间（通常 30s），Gateway 会强制断开连线。

**非同步模式 (Async Pattern)**：

```
1. Client 发起请求，Agent 返回 202 Accepted，并附带一个 task_id
2. Client 通过 GET /status/{task_id} 轮询 (Polling) 状态，或者使用 WebSocket 接收推播
3. 这是标准的微服务处理长时任务的做法
```

**实现示例**：

```python
# 异步任务管理
from asyncio import create_task
from uuid import uuid4

tasks: dict[str, TaskStatus] = {}

@app.post("/api/tasks")
async def create_task(request: RunRequest) -> TaskResponse:
    task_id = str(uuid4())
    tasks[task_id] = TaskStatus(status="PENDING")
    
    # 后台执行
    create_task(run_agent_background(task_id, request))
    
    return TaskResponse(task_id=task_id, status="PENDING")

@app.get("/api/tasks/{task_id}/status")
async def get_task_status(task_id: str) -> TaskStatus:
    return tasks.get(task_id) or {"status": "NOT_FOUND"}
```

### 10.3 健康检查的深度检测 (Phase 4)

**不要只检查 HTTP 服务是否活着**：建议 `/health` 端点包含"资源状态检查"。如果 Agent 连不上 Redis，或者 LLM 连线失效，`/health` 应该回传 `503 Service Unavailable`。这样 Nacos 会自动将该节点从路由中剔除，实现自动降级。

```python
@app.get("/health")
async def health():
    checks = {
        "redis": await check_redis_connection(),
        "llm": await check_llm_connection(),
    }
    
    if not all(checks.values()):
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "checks": checks}
        )
    
    return {"status": "healthy", "checks": checks}

async def check_redis_connection() -> bool:
    try:
        await redis.ping()
        return True
    except:
        return False

async def check_llm_connection() -> bool:
    # 简单的健康检查调用
    try:
        await llm_client.call(messages=[{"role": "user", "content": "ping"}])
        return True
    except:
        return False
```

### 10.4 并发控制：Gunicorn/Uvicorn 配置

**风险**：Python 的 ASGI Server 预设是单执行绪或依赖 Worker 机制的。如果一个 Agent 正在进行耗时的 LLM 推理（Blocked I/O），它会阻塞整个 Worker。

**建议**：

1. 使用多 Worker 模式：
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker agent_service:app
```

2. 确保 Agent SDK 逻辑中，LLM 的呼叫使用 `async/await` 方式：

```python
# 正确：异步呼叫
async def run_agent():
    response = await llm_client.call(...)  # async
    return response

# 错误：同步呼叫会阻塞 Worker
def run_agent():
    response = llm_client.call(...)  # sync - 阻塞！
    return response
```

### 10.5 认证与安全性：网关鉴权 + 内部头传递

**问题**：Python 服务端如何验证 JWT？如果在 Python 端重复做鉴权逻辑，会增加复杂度和性能开销。

**最佳实践**：采用 **网关鉴权 + 内部头传递** 模式。

```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│   Client    │────>│  Spring Cloud       │────>│  Python Agent   │
│  (带 JWT)   │     │  Gateway            │     │  Service        │
└─────────────┘     │  1. 验证 JWT        │     │  信任 Gateway   │
                    │  2. 解析 Claims     │     │  读取 Header    │
                    │  3. 注入 Header     │     │                 │
                    └─────────────────────┘     └─────────────────┘
```

**Spring Cloud Gateway 配置**：

```yaml
# application.yml
spring:
  cloud:
    gateway:
      routes:
        - id: harness-agent
          uri: http://harness-agent:8000
          predicates:
            - Path=/api/agent/**
          filters:
            - AuthFilter  # 自定义鉴权过滤器
```

```java
// AuthFilter.java
@Component
public class AuthFilter implements GlobalFilter {
    
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String token = exchange.getRequest().getHeaders().getFirst("Authorization");
        
        // 1. 验证 JWT
        Claims claims = jwtUtil.validateToken(token);
        
        // 2. 注入内部头
        ServerHttpRequest request = exchange.getRequest().mutate()
            .header("X-User-Id", claims.get("userId", String.class))
            .header("X-Tenant-Id", claims.get("tenantId", String.class))
            .header("X-Trace-Id", exchange.getRequest().getId())
            .build();
        
        return chain.filter(exchange.mutate().request(request).build());
    }
}
```

**Python 服务端**：

```python
# agent_service.py
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

# 信任的 Gateway IP 白名单
GATEWAY_IPS = {"10.0.0.1", "10.0.0.2"}

@app.middleware("http")
async def verify_gateway_request(request: Request, call_next):
    # 1. 验证请求来自 Gateway
    client_ip = request.client.host
    if client_ip not in GATEWAY_IPS:
        raise HTTPException(status_code=403, detail="Forbidden: not from Gateway")
    
    # 2. 从 Header 读取用户上下文
    user_id = request.headers.get("X-User-Id")
    tenant_id = request.headers.get("X-Tenant-Id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user context")
    
    # 3. 注入到请求上下文
    request.state.user_id = user_id
    request.state.tenant_id = tenant_id
    
    return await call_next(request)

@app.post("/api/run")
async def run_agent(request: Request, body: RunRequest):
    # 直接使用已验证的用户上下文
    user_id = request.state.user_id
    # ... 执行 Agent 逻辑
```

### 10.6 K8s 环境下的服务发现陷阱 (Phase 4)

**问题**：在 Kubernetes 中使用 Nacos 注册时，`socket.gethostname()` 返回的是容器内部 hostname，而非可访问的 Pod IP。

**错误示例**：

```python
# 错误：在 K8s 中会返回无法访问的地址
import socket
ip = socket.gethostbyname(socket.gethostname())  # 可能返回 127.0.0.1
```

**正确做法**：

```python
# 正确：使用 K8s 注入的 POD_IP 环境变量
import os

def get_pod_ip():
    # K8s 会自动注入 POD_IP 环境变量
    return os.getenv("POD_IP", "127.0.0.1")

@app.on_event("startup")
async def register_service():
    client.register_service(
        service_name="harness-agent",
        ip=get_pod_ip(),  # 使用 Pod IP
        port=8000,
    )
```

**K8s Deployment 配置**：

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: harness-agent
spec:
  template:
    spec:
      containers:
        - name: agent
          image: harness-agent:latest
          env:
            - name: POD_IP
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP  # K8s 自动注入 Pod IP
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
```

### 10.7 统一错误码映射

**问题**：Python 异常直接返回 Traceback，前端无法解析。需要符合 Spring Cloud 的统一错误格式。

**Python 服务端统一错误处理**：

```python
# error_handler.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    """符合 Spring Cloud 规范的错误响应"""
    errorCode: str
    errorMessage: str
    traceId: str | None = None
    timestamp: str

# 定义错误码
class ErrorCode:
    # 客户端错误 (4xx)
    INVALID_INPUT = "AGENT_400_001"
    UNAUTHORIZED = "AGENT_401_001"
    FORBIDDEN = "AGENT_403_001"
    
    # 服务端错误 (5xx)
    INTERNAL_ERROR = "AGENT_500_001"
    LLM_ERROR = "AGENT_500_002"
    TOOL_ERROR = "AGENT_500_003"
    TIMEOUT = "AGENT_504_001"

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            errorCode=ErrorCode.INVALID_INPUT,
            errorMessage=str(exc),
            traceId=request.headers.get("X-Trace-Id"),
            timestamp=datetime.now().isoformat(),
        ).model_dump()
    )

@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    return JSONResponse(
        status_code=502,
        content=ErrorResponse(
            errorCode=ErrorCode.LLM_ERROR,
            errorMessage=f"LLM 服务异常: {exc}",
            traceId=request.headers.get("X-Trace-Id"),
            timestamp=datetime.now().isoformat(),
        ).model_dump()
    )

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    # 生产环境不应暴露堆栈信息
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            errorCode=ErrorCode.INTERNAL_ERROR,
            errorMessage="服务内部错误，请联系管理员",
            traceId=request.headers.get("X-Trace-Id"),
            timestamp=datetime.now().isoformat(),
        ).model_dump()
    )
```

**Java 客户端处理**：

```java
// 统一错误响应类
@Data
public class ErrorResponse {
    private String errorCode;
    private String errorMessage;
    private String traceId;
    private String timestamp;
}

// 自定义异常
public class AgentException extends RuntimeException {
    private final String errorCode;
    
    public AgentException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }
}

// WebClient 错误处理
@Service
public class AgentClient {
    
    public Mono<TaskResult> runAgent(String prompt) {
        return webClient.post()
            .uri("/api/run")
            .bodyValue(new RunRequest(prompt))
            .retrieve()
            .onStatus(
                status -> status.is4xxClientError() || status.is5xxServerError(),
                response -> response.bodyToMono(ErrorResponse.class)
                    .map(err -> new AgentException(err.getErrorCode(), err.getErrorMessage()))
            )
            .bodyToMono(TaskResult.class);
    }
}
```

### 10.8 资源隔离与限制

**问题**：Python Agent 在高并发时内存增长恐怖，若无限制会被 K8s OOM Kill。

**K8s 资源配置**：

```yaml
# deployment.yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"      # 内存上限
    cpu: "2000m"       # CPU 上限

# 探针配置
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5

# 优雅关闭
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 10"]  # 等待任务完成
```

**HPA 自动扩缩容**：

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: harness-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: harness-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

**Redis 快照脏数据处理**：

```python
# store_redis.py
import json
from pydantic import ValidationError

class RedisSessionStore(SessionStore):
    
    async def load(self, session_id: str) -> Session | None:
        try:
            data = await self.redis.get(f"session:{session_id}")
            if not data:
                return None
            
            # 1. 解析 JSON
            raw = json.loads(data)
            
            # 2. Schema 版本检查
            schema_version = raw.get("schema_version", 1)
            
            # 3. 验证并转换
            return SessionModel.model_validate(raw).to_session()
            
        except json.JSONDecodeError as e:
            # JSON 损坏，删除脏数据
            logger.warning(f"Session {session_id} JSON corrupted: {e}")
            await self.redis.delete(f"session:{session_id}")
            return None
            
        except ValidationError as e:
            # Schema 不匹配（可能是旧版本数据）
            logger.warning(f"Session {session_id} schema mismatch: {e}")
            # 尝试迁移或删除
            await self.migrate_or_delete(session_id, raw, e)
            return None
```

---

## 十一、结论

### 核心观点

1. **分层治理正确**：基础设施层（Spring Cloud）与代理逻辑层（SDK）分离
2. **SDK 已具备核心能力**：熔断器、成本控制、步骤预算、链路追踪、状态持久化
3. **需要补充的是"集成点"**：HTTP 服务包装、TraceID 提取、服务注册、分布式存储

### 实施建议

- **不重写架构**：分阶段最小改动
- **复用现有能力**：OpenTelemetry、Circuit Breaker、SessionStore 抽象
- **总代码量可控**：~520 行，约 2-3 天开发量

### 关键注意事项

| Phase | 关键陷阱 | 缓解措施 |
|-------|---------|---------|
| 1 | 认证安全性 | 网关鉴权 + 内部头传递 |
| 2 | 错误码不统一 | 统一 ErrorResponse 格式 |
| 3 | Redis 序列化不一致 | 严格 JSON 化 + Schema 版本管理 |
| 3 | 快照脏数据 | 捕获 JSONDecodeError + 自动清理 |
| 4 | K8s 服务发现 | 使用 POD_IP 环境变量 |
| 4 | 健康检查不够深 | 资源状态检查（Redis/LLM） |
| 全局 | 长时任务超时 | 异步模式 + WebSocket |
| 全局 | Worker 阻塞 | 多 Worker + async/await |
| 全局 | OOM Kill | K8s 资源限制 + HPA |

### 优先级

1. **Phase 1（必需）**：HTTP 服务包装 + TraceID 传播
2. **Phase 2（推荐）**：可观测性集成
3. **Phase 3-4（按需）**：分布式状态 + 服务发现

### Phase 1 实施建议

Phase 1 中最容易踩坑的是 `middleware/tracing.py`（OpenTelemetry 注入逻辑），建议优先实现以下内容：

```python
# middleware/tracing.py - Phase 1 核心
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry import context

propagator = TraceContextTextMapPropagator()

@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    # 1. 从 Spring Cloud Gateway 提取 TraceContext
    headers = dict(request.headers)
    ctx = propagator.extract(headers)
    
    # 2. 设置为当前上下文
    token = context.attach(ctx)
    
    try:
        # 3. 执行请求
        response = await call_next(request)
        return response
    finally:
        context.detach(token)
```

---

> 本报告可作为项目的 **Technical Design Document (TDD)**，指导实施工作。

---

## 十二、快速整合示例

本章节提供一个完整的端到端示例，展示如何将 Harness SDK 整合到 Spring Cloud 微服务架构中。

### 12.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Spring Cloud Gateway                           │
│                      (端口 8080，统一入口)                               │
│  - JWT 认证                                                              │
│  - 路由分发                                                              │
│  - 熔断限流                                                              │
│  - 链路追踪                                                              │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│  Java 服务 A        │   │  Java 服务 B        │   │  Python 服务        │
│  :8081              │   │  :8082              │   │  Harness Agent      │
│                     │   │                     │   │  :8000              │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
                                                              │
                                                              ▼
                                                    ┌─────────────────────┐
                                                    │  Redis              │
                                                    │  (分布式 Session)   │
                                                    └─────────────────────┘
```

### 12.2 Python 服务端实现

#### 步骤 1：安装依赖

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装 Harness SDK + 服务依赖
pip install harness-sdk[service,prometheus,redis]
```

#### 步骤 2：创建服务入口

```python
# agent_service.py
"""
Harness Agent Service - Spring Cloud 微服务节点

启动方式:
    # 开发模式
    uvicorn agent_service:app --reload --port 8000

    # 生产模式
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker agent_service:app --bind 0.0.0.0:8000
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

# Harness SDK
from harness import AgentHarness, HarnessConfig, ProgressEvent
from harness.service import (
    TracingMiddleware,
    ErrorCode,
    create_error_response,
    get_metrics_collector,
    PROMETHEUS_AVAILABLE,
    RedisSessionStore,
    RedisDistributedLock,
    get_service_instance,
    NacosServiceRegistry,
    REDIS_AVAILABLE,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# 配置
# =============================================================================

# 从环境变量读取配置
SERVICE_NAME = os.getenv("SERVICE_NAME", "harness-agent")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8000"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
NACOS_SERVER = os.getenv("NACOS_SERVER", "")  # 可选


# =============================================================================
# 应用状态
# =============================================================================

class AppState:
    def __init__(self):
        self.config: HarnessConfig | None = None
        self.session_store: RedisSessionStore | None = None
        self.registry: NacosServiceRegistry | None = None
        self.service_instance = None

app_state = AppState()


# =============================================================================
# 生命周期管理
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动和关闭时的初始化/清理"""
    logger.info(f"Starting {SERVICE_NAME}...")

    # 1. 初始化配置
    app_state.config = HarnessConfig.from_env()

    # 2. 初始化 Redis Session Store
    if REDIS_AVAILABLE and REDIS_URL:
        app_state.session_store = RedisSessionStore(REDIS_URL)
        logger.info("Redis session store initialized")

    # 3. 初始化 Prometheus 指标
    if PROMETHEUS_AVAILABLE:
        get_metrics_collector().setup()
        logger.info("Prometheus metrics enabled")

    # 4. 注册到 Nacos（可选）
    if NACOS_SERVER:
        app_state.registry = NacosServiceRegistry(NACOS_SERVER)
        app_state.service_instance = get_service_instance(SERVICE_NAME, SERVICE_PORT)
        await app_state.registry.register(app_state.service_instance)
        logger.info(f"Registered to Nacos: {SERVICE_NAME}")

    yield

    # 清理：从 Nacos 注销
    if app_state.registry and app_state.service_instance:
        await app_state.registry.deregister(app_state.service_instance)
        logger.info(f"Deregistered from Nacos: {SERVICE_NAME}")

    logger.info(f"Shutting down {SERVICE_NAME}...")


# =============================================================================
# FastAPI 应用
# =============================================================================

app = FastAPI(
    title="Harness Agent Service",
    description="AI Agent 服务，供 Spring Cloud 微服务调用",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS（生产环境应限制允许的域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TraceID 提取中间件
app.add_middleware(TracingMiddleware)


# =============================================================================
# 请求/响应模型
# =============================================================================

class RunRequest(BaseModel):
    prompt: str
    session_id: str | None = None
    model: str | None = None
    max_iterations: int | None = None


class RunResponse(BaseModel):
    status: str
    content: str
    session_id: str
    iterations: int
    token_usage: dict[str, int]


# =============================================================================
# 端点：健康检查
# =============================================================================

@app.get("/health")
async def health_check(request: Request):
    """
    健康检查端点。

    Spring Cloud Gateway / K8s 会定期调用此端点判断服务是否存活。
    """
    checks = {
        "service": True,
    }

    # 检查 Redis 连接（如果配置了）
    if app_state.session_store:
        try:
            # 简单的 ping 测试
            await app_state.session_store._get_redis().ping()
            checks["redis"] = True
        except Exception as e:
            checks["redis"] = False
            logger.warning(f"Redis health check failed: {e}")

    all_healthy = all(checks.values())

    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
        },
    )


# =============================================================================
# 端点：Prometheus 指标
# =============================================================================

@app.get("/metrics")
async def metrics():
    """Prometheus 指标导出端点。"""
    if not PROMETHEUS_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={"error": "Prometheus not available"},
        )

    collector = get_metrics_collector()
    return Response(
        content=collector.export(),
        media_type=collector.get_content_type(),
    )


# =============================================================================
# 端点：REST API
# =============================================================================

@app.post("/api/run", response_model=RunResponse)
async def run_agent(request: Request, body: RunRequest):
    """
    同步执行 Agent（适合短任务，< 30s）。

    注意：对于长时间运行的任务，请使用 WebSocket 端点。
    """
    # 从 Gateway 传递的头部获取用户上下文
    user_id = request.headers.get("X-User-Id")
    tenant_id = request.headers.get("X-Tenant-Id")
    trace_id = request.headers.get("X-Trace-Id")

    try:
        agent = AgentHarness(config=app_state.config)

        # 执行 Agent
        result = await agent.run(
            prompt=body.prompt,
            session_id=body.session_id,
        )

        return RunResponse(
            status=result.status.value,
            content=result.content,
            session_id=result.session.id,
            iterations=result.iterations,
            token_usage={
                "input": result.token_usage.input_tokens,
                "output": result.token_usage.output_tokens,
            },
        )

    except Exception as e:
        logger.exception(f"Agent execution failed: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                ErrorCode.INTERNAL_ERROR,
                str(e),
                trace_id,
            ).model_dump(),
        )


# =============================================================================
# 端点：WebSocket（长任务）
# =============================================================================

@app.websocket("/ws/run")
async def run_agent_ws(websocket: WebSocket):
    """
    WebSocket 流式执行（适合长任务）。

    协议:
    1. 客户端发送: {"prompt": "...", "session_id": "可选"}
    2. 服务端流式返回 ProgressEvent
    3. 服务端最终返回: {"type": "done", "result": {...}}
    """
    await websocket.accept()

    try:
        # 接收请求
        data = await websocket.receive_json()
        request = RunRequest(**data)

        agent = AgentHarness(config=app_state.config)

        # 进度回调
        async def on_progress(event: ProgressEvent):
            await websocket.send_json({
                "type": "progress",
                "event_type": event.type.value,
                "message": event.message,
                "data": event.data,
            })

        # 执行 Agent
        result = await agent.run(
            prompt=request.prompt,
            session_id=request.session_id,
            on_progress=on_progress,
        )

        # 返回最终结果
        await websocket.send_json({
            "type": "done",
            "result": {
                "status": result.status.value,
                "content": result.content,
                "session_id": result.session.id,
                "iterations": result.iterations,
            },
        })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "error": str(e),
        })


# =============================================================================
# 启动入口
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
```

#### 步骤 3：创建 requirements.txt

```txt
# requirements.txt
harness-sdk[service,prometheus,redis]>=0.1.0
uvicorn>=0.23.0
gunicorn>=21.0.0
```

#### 步骤 4：创建 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY agent_service.py .

# 环境变量
ENV SERVICE_NAME=harness-agent
ENV SERVICE_PORT=8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", \
     "agent_service:app", "--bind", "0.0.0.0:8000"]
```

### 12.3 Spring Cloud Gateway 配置

#### application.yml

```yaml
# Spring Cloud Gateway 配置
server:
  port: 8080

spring:
  application:
    name: api-gateway

  cloud:
    gateway:
      # 全局跨域配置
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOrigins: "*"
            allowedMethods: "*"
            allowedHeaders: "*"

      # 路由配置
      routes:
        # Harness Agent Service
        - id: harness-agent
          uri: http://harness-agent:8000
          predicates:
            - Path=/api/agent/**, /ws/agent/**
          filters:
            - StripPrefix=1
            - AuthFilter  # 自定义鉴权过滤器

      # 默认过滤器
      default-filters:
        - name: RequestRateLimiter
          args:
            redis-rate-limiter.replenishRate: 10
            redis-rate-limiter.burstCapacity: 20

# Nacos 服务发现（可选）
nacos:
  discovery:
    server-addr: nacos:8848
```

#### AuthFilter.java（网关鉴权）

```java
// src/main/java/com/example/gateway/AuthFilter.java
package com.example.gateway;

import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Component
public class AuthFilter implements GlobalFilter {

    private final JwtUtil jwtUtil;

    public AuthFilter(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String token = exchange.getRequest().getHeaders().getFirst("Authorization");

        if (token == null || !token.startsWith("Bearer ")) {
            exchange.getResponse().setStatusCode(org.springframework.http.HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        // 验证 JWT
        Claims claims = jwtUtil.validateToken(token.substring(7));

        // 注入用户上下文到请求头（传递给 Python 服务）
        ServerHttpRequest request = exchange.getRequest().mutate()
            .header("X-User-Id", claims.get("userId", String.class))
            .header("X-Tenant-Id", claims.get("tenantId", String.class))
            .header("X-Trace-Id", exchange.getRequest().getId())
            .build();

        return chain.filter(exchange.mutate().request(request).build());
    }
}
```

### 12.4 Java 客户端调用示例

#### HTTP 同步调用

```java
// src/main/java/com/example/service/AgentClient.java
package com.example.service;

import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

@Service
public class AgentClient {

    private final WebClient webClient;

    public AgentClient(WebClient.Builder builder) {
        this.webClient = builder
            .baseUrl("http://api-gateway:8080")
            .build();
    }

    /**
     * 同步执行 Agent（适合短任务）
     */
    public Mono<AgentResponse> runAgent(String prompt, String sessionId) {
        return webClient.post()
            .uri("/api/agent/api/run")
            .header("Authorization", "Bearer " + getCurrentToken())
            .bodyValue(new AgentRequest(prompt, sessionId))
            .retrieve()
            .bodyToMono(AgentResponse.class);
    }

    private String getCurrentToken() {
        // 从 SecurityContext 获取当前用户的 token
        return SecurityContextHolder.getContext().getAuthentication().getCredentials().toString();
    }
}

// 请求/响应模型
record AgentRequest(String prompt, String sessionId) {}
record AgentResponse(String status, String content, String sessionId, 
                     int iterations, Map<String, Integer> tokenUsage) {}
```

#### WebSocket 流式调用

```java
// src/main/java/com/example/service/AgentWebSocketClient.java
package com.example.service;

import org.springframework.stereotype.Service;
import org.springframework.web.reactive.socket.WebSocketMessage;
import org.springframework.web.reactive.socket.client.ReactorNettyWebSocketClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@Service
public class AgentWebSocketClient {

    private final ReactorNettyWebSocketClient webSocketClient;
    private final String gatewayUrl = "ws://api-gateway:8080";

    public AgentWebSocketClient() {
        this.webSocketClient = new ReactorNettyWebSocketClient();
    }

    /**
     * 流式执行 Agent（适合长任务）
     */
    public Flux<ProgressEvent> runAgentStreaming(String prompt, String sessionId) {
        return Flux.create(emitter -> {
            String uri = gatewayUrl + "/ws/agent/ws/run";

            webSocketClient.execute(
                java.net.URI.create(uri),
                session -> {
                    // 1. 发送请求
                    String request = String.format(
                        "{\"prompt\": \"%s\", \"session_id\": \"%s\"}",
                        prompt, sessionId
                    );
                    Mono<Void> sendRequest = session.send(
                        Mono.just(session.textMessage(request))
                    );

                    // 2. 接收响应
                    Flux<Void> receiveResponses = session.receive()
                        .map(WebSocketMessage::getPayloadAsText)
                        .doOnNext(payload -> {
                            JSONObject event = new JSONObject(payload);
                            String type = event.getString("type");

                            if ("done".equals(type)) {
                                emitter.complete();
                            } else if ("error".equals(type)) {
                                emitter.error(new AgentException(event.getString("error")));
                            } else {
                                emitter.next(new ProgressEvent(
                                    type,
                                    event.optString("message", ""),
                                    event.optJSONObject("data")
                                ));
                            }
                        })
                        .then();

                    return sendRequest.then(receiveResponses);
                }
            ).subscribe();
        });
    }
}

// 进度事件
record ProgressEvent(String type, String message, JSONObject data) {}
```

#### Controller 使用示例

```java
// src/main/java/com/example/controller/AgentController.java
package com.example.controller;

import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final AgentClient agentClient;
    private final AgentWebSocketClient wsClient;

    public ChatController(AgentClient agentClient, AgentWebSocketClient wsClient) {
        this.agentClient = agentClient;
        this.wsClient = wsClient;
    }

    /**
     * 简单对话（同步，适合短任务）
     */
    @PostMapping("/simple")
    public Mono<AgentResponse> simpleChat(@RequestBody ChatRequest request) {
        return agentClient.runAgent(request.message(), null);
    }

    /**
     * 复杂任务（流式，适合长任务）
     */
    @GetMapping("/stream")
    public Flux<ProgressEvent> streamChat(@RequestParam String message) {
        return wsClient.runAgentStreaming(message, null);
    }
}

record ChatRequest(String message) {}
```

### 12.5 Kubernetes 部署配置

#### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: harness-agent
  labels:
    app: harness-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: harness-agent
  template:
    metadata:
      labels:
        app: harness-agent
    spec:
      containers:
        - name: agent
          image: harness-agent:latest
          ports:
            - containerPort: 8000
          env:
            - name: SERVICE_NAME
              value: "harness-agent"
            - name: SERVICE_PORT
              value: "8000"
            - name: POD_IP
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP
            - name: REDIS_URL
              value: "redis://redis-service:6379"
            - name: NACOS_SERVER
              value: "nacos-service:8848"
            - name: ANTHROPIC_API_KEY
              valueFrom:
                secretKeyRef:
                  name: harness-secrets
                  key: anthropic-api-key
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: harness-agent
spec:
  selector:
    app: harness-agent
  ports:
    - port: 8000
      targetPort: 8000
```

#### HPA（自动扩缩容）

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: harness-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: harness-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### 12.6 快速启动清单

#### 本地开发环境

```bash
# 1. 启动 Redis（可选，用于分布式 Session）
docker run -d --name redis -p 6379:6379 redis:alpine

# 2. 启动 Nacos（可选，用于服务发现）
docker run -d --name nacos -p 8848:8848 nacos/nacos-server:latest

# 3. 启动 Harness Agent Service
cd packages/sdk
PYTHONPATH=src uv run uvicorn harness.service:app --reload --port 8000

# 4. 测试健康检查
curl http://localhost:8000/health

# 5. 测试 Agent 执行
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, who are you?"}'
```

#### 生产部署

```bash
# 1. 构建 Docker 镜像
docker build -t harness-agent:latest .

# 2. 推送到镜像仓库
docker push your-registry/harness-agent:latest

# 3. 部署到 Kubernetes
kubectl apply -f k8s/

# 4. 验证部署
kubectl get pods -l app=harness-agent
kubectl logs -f deployment/harness-agent
```

### 12.7 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|-----|---------|---------|
| 健康检查失败 | Redis 连接问题 | 检查 REDIS_URL 配置 |
| 请求超时 | Agent 执行时间过长 | 改用 WebSocket 端点 |
| JWT 认证失败 | Gateway 未正确注入头部 | 检查 AuthFilter 配置 |
| 服务未注册到 Nacos | NACOS_SERVER 未配置 | 设置环境变量 |
| 内存溢出 | 请求量过大 | 调整 K8s 资源限制 |