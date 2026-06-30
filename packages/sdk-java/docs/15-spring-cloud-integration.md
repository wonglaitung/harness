# 14 - Spring Cloud 集成指南

> 本文档描述 Harness SDK 与 Spring Cloud 微服务架构的集成方案。
> 所有代码示例均已实现，位于 `packages/sdk/src/harness/service/` 目录。

---

## 一、架构概述

### 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Spring Cloud Gateway                      │
│  (路由、熔断、限流、JWT 认证、链路追踪、服务发现)             │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 Harness Agent Service (Python)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  FastAPI Service (harness.service)                  │   │
│  │  - /health      健康检查                             │   │
│  │  - /metrics     Prometheus 指标                      │   │
│  │  - /api/run     同步执行                             │   │
│  │  - /ws/run      WebSocket 流式执行                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AgentHarness (SDK 核心)                            │   │
│  │  - AgentLoop (ReAct 循环)                           │   │
│  │  - OpenTelemetry Tracing                            │   │
│  │  - Circuit Breaker                                  │   │
│  │  - Cost Controller                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  外部存储 (可选)                                     │   │
│  │  - Redis (分布式状态/锁)                             │   │
│  │  - Nacos/Eureka (服务发现)                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 分层治理

| 层级 | 技术架构 | 负责范畴 |
| --- | --- | --- |
| **基础设施层** | Spring Cloud | 流量管控、熔断、负载均衡、服务发现、配置管理、分布式追踪 |
| **代理逻辑层** | Harness SDK | 代理的状态管理、决策路径、工具调用、上下文记忆 |

---

## 二、模块概览

SDK 已实现完整的 Spring Cloud 集成模块：

```
packages/sdk/src/harness/service/
├── __init__.py          # FastAPI 服务入口
├── tracing.py           # TraceID 传播中间件
├── metrics.py           # Prometheus 指标导出
├── error_handler.py     # 统一错误响应格式
├── store_redis.py       # Redis 分布式会话存储
└── discovery.py         # Nacos/Eureka 服务发现
```

### 已实现的功能

| 功能 | 模块 | 状态 |
|-----|------|------|
| HTTP 服务包装 | `service/__init__.py` | ✅ 已实现 |
| 健康检查 `/health` | `service/__init__.py` | ✅ 已实现 |
| Prometheus 指标 `/metrics` | `service/metrics.py` | ✅ 已实现 |
| TraceID 传播 | `service/tracing.py` | ✅ 已实现 |
| WebSocket 流式执行 | `service/__init__.py` | ✅ 已实现 |
| Redis 分布式会话 | `service/store_redis.py` | ✅ 已实现 |
| Redis 分布式锁 | `service/store_redis.py` | ✅ 已实现 |
| Nacos 服务注册 | `service/discovery.py` | ✅ 已实现 |
| Eureka 服务注册 | `service/discovery.py` | ✅ 已实现 |
| 统一错误响应 | `service/error_handler.py` | ✅ 已实现 |

---

## 三、快速开始

### 启动服务

```bash
# 开发模式
cd packages/sdk
PYTHONPATH=src uv run uvicorn harness.service:app --reload --port 8000

# 生产模式（多 Worker）
gunicorn -w 4 -k uvicorn.workers.UvicornWorker harness.service:app --bind 0.0.0.0:8000
```

### 端点列表

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/health` | GET | 健康检查 |
| `/metrics` | GET | Prometheus 指标 |
| `/api/run` | POST | 同步执行 Agent（适合短任务） |
| `/api/sessions/{id}` | GET | 获取会话信息 |
| `/api/sessions/{id}` | DELETE | 清除会话 |
| `/ws/run` | WebSocket | 流式执行（适合长任务） |

### 测试请求

```bash
# 健康检查
curl http://localhost:8000/health

# 同步执行
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, who are you?"}'
```

---

## 四、核心模块详解

### 4.1 链路追踪 (TracingMiddleware)

从 Spring Cloud Gateway 提取 W3C TraceContext 并传播到 SDK：

```python
from harness.service.tracing import TracingMiddleware, get_trace_id

# FastAPI 应用自动添加中间件
app.add_middleware(TracingMiddleware)

# 在请求处理中获取 TraceID
trace_id = get_trace_id()
```

**支持的 Header 格式**：
- `traceparent` (W3C TraceContext)
- `X-B3-TraceId` (Zipkin/Sleuth)
- `X-Trace-Id` (自定义)

### 4.2 Prometheus 指标

导出的指标：

| 指标名 | 类型 | 说明 |
|-------|------|------|
| `harness_loop_iterations_total` | Counter | 总循环迭代次数 |
| `harness_tool_calls_total` | Counter | 工具调用次数（按工具名和状态分组） |
| `harness_llm_tokens_total` | Counter | Token 使用量（按 input/output 分组） |
| `harness_session_duration_seconds` | Histogram | 会话持续时间 |
| `harness_llm_call_duration_seconds` | Histogram | LLM 调用耗时 |
| `harness_tool_call_duration_seconds` | Histogram | 工具调用耗时 |
| `harness_active_sessions` | Gauge | 当前活跃会话数 |

**使用方式**：

```python
from harness.service.metrics import MetricsCollector, get_metrics_collector

# 初始化
collector = get_metrics_collector()
collector.setup()

# 创建进度处理器（自动记录指标）
result = await agent.run(
    prompt="...",
    on_progress=collector.create_progress_handler()
)
```

### 4.3 Redis 分布式会话

用于多实例部署的会话存储：

```python
from harness.service.store_redis import RedisSessionStore, RedisDistributedLock

# 创建会话存储
store = RedisSessionStore("redis://localhost:6379")

# 保存会话
await store.save(session)

# 加载会话
session = await store.load("session-123")

# 分布式锁
lock = RedisDistributedLock("redis://localhost:6379")
token = await lock.acquire("my-resource", timeout=30)
# ... 执行需要锁保护的操作 ...
await lock.release("my-resource", token)
```

**特点**：
- JSON 序列化（非 pickle），跨语言兼容
- Schema 版本管理，支持向后兼容
- TTL 自动清理
- 损坏数据自动删除

### 4.4 服务发现

支持 Nacos 和 Eureka：

```python
from harness.service.discovery import (
    NacosServiceRegistry,
    EurekaServiceRegistry,
    get_service_instance,
    get_pod_ip,
)

# Nacos 注册
registry = NacosServiceRegistry("nacos:8848")
instance = get_service_instance("harness-agent", 8000)
await registry.register(instance)

# 服务关闭时注销
await registry.deregister(instance)
```

**Kubernetes 环境**：

```python
# 自动使用 POD_IP 环境变量
ip = get_pod_ip()  # 返回正确的 Pod IP
```

### 4.5 统一错误响应

符合 Spring Cloud 规范的错误格式：

```json
{
    "errorCode": "AGENT_400_001",
    "errorMessage": "Invalid input parameter",
    "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
    "timestamp": "2026-06-16T10:30:00Z"
}
```

**错误码定义**：

| 错误码 | HTTP 状态 | 说明 |
|-------|----------|------|
| `AGENT_400_001` | 400 | 输入参数无效 |
| `AGENT_401_001` | 401 | 未授权 |
| `AGENT_403_001` | 403 | 禁止访问 |
| `AGENT_404_001` | 404 | 资源不存在 |
| `AGENT_500_001` | 500 | 内部错误 |
| `AGENT_502_001` | 502 | LLM 服务错误 |
| `AGENT_502_002` | 502 | 工具执行错误 |
| `AGENT_400_002` | 400 | 预算超限 |
| `AGENT_400_003` | 400 | 迭代次数超限 |
| `AGENT_400_004` | 400 | 检测到死循环 |

---

## 五、Spring Cloud Gateway 配置

### application.yml

```yaml
server:
  port: 8080

spring:
  application:
    name: api-gateway
  cloud:
    gateway:
      routes:
        # Harness Agent Service
        - id: harness-agent
          uri: http://harness-agent:8000
          predicates:
            - Path=/api/agent/**, /ws/agent/**
          filters:
            - StripPrefix=1
            - AuthFilter

      # 限流配置
      default-filters:
        - name: RequestRateLimiter
          args:
            redis-rate-limiter.replenishRate: 10
            redis-rate-limiter.burstCapacity: 20
```

### 网关鉴权过滤器 (AuthFilter.java)

```java
@Component
public class AuthFilter implements GlobalFilter {

    private final JwtUtil jwtUtil;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String token = exchange.getRequest().getHeaders().getFirst("Authorization");

        if (token == null || !token.startsWith("Bearer ")) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        Claims claims = jwtUtil.validateToken(token.substring(7));

        // 注入用户上下文到请求头
        ServerHttpRequest request = exchange.getRequest().mutate()
            .header("X-User-Id", claims.get("userId", String.class))
            .header("X-Tenant-Id", claims.get("tenantId", String.class))
            .header("X-Trace-Id", exchange.getRequest().getId())
            .build();

        return chain.filter(exchange.mutate().request(request).build());
    }
}
```

---

## 六、Java 客户端示例

### HTTP 同步调用

```java
@Service
public class AgentClient {

    private final WebClient webClient;

    public AgentClient(WebClient.Builder builder) {
        this.webClient = builder
            .baseUrl("http://api-gateway:8080")
            .build();
    }

    public Mono<AgentResponse> runAgent(String prompt, String sessionId) {
        return webClient.post()
            .uri("/api/agent/api/run")
            .header("Authorization", "Bearer " + getCurrentToken())
            .bodyValue(new AgentRequest(prompt, sessionId))
            .retrieve()
            .bodyToMono(AgentResponse.class);
    }
}

record AgentRequest(String prompt, String sessionId) {}
record AgentResponse(String status, String content, String sessionId,
                     int iterations, Map<String, Integer> tokenUsage) {}
```

### WebSocket 流式调用

```java
@Service
public class AgentWebSocketClient {

    private final ReactorNettyWebSocketClient webSocketClient;

    public Flux<ProgressEvent> runAgentStreaming(String prompt, String sessionId) {
        return Flux.create(emitter -> {
            webSocketClient.execute(
                URI.create("ws://api-gateway:8080/ws/agent/ws/run"),
                session -> {
                    // 发送请求
                    Mono<Void> sendRequest = session.send(
                        Mono.just(session.textMessage(
                            String.format("{\"prompt\": \"%s\", \"session_id\": \"%s\"}",
                                prompt, sessionId)
                        ))
                    );

                    // 接收响应
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
```

---

## 七、长时任务处理

### 问题背景

AI Agent 的执行时间可能超过 Gateway 的默认超时时间（通常 30s），需要特殊处理。

### 解决方案：WebSocket 流式模式

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

**优势**：
- 实时反馈，用户体验好
- 不会因 Gateway 超时而断开（WebSocket 是长连接）
- SDK 已有完整的事件类型定义

---

## 八、Kubernetes 部署

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: harness-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: harness-agent
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
              value: "nacos-service:8848"
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
```

### HPA 自动扩缩容

```yaml
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
```

---

## 九、关键注意事项

### 认证安全

采用 **网关鉴权 + 内部头传递** 模式：

```
Client (JWT) -> Gateway (验证 JWT) -> Python Service (信任 Gateway)
                                     读取 X-User-Id 头部
```

Python 服务只需验证请求来自 Gateway IP 白名单。

### Redis 序列化

使用 JSON（非 pickle），确保：
- 跨语言兼容（Java/Spring 服务可读取）
- Schema 版本管理（向后兼容）
- 损坏数据自动清理

### K8s 服务发现

在 Kubernetes 中，`socket.gethostbyname()` 可能返回错误 IP。使用 `POD_IP` 环境变量：

```python
from harness.service.discovery import get_pod_ip
ip = get_pod_ip()  # 正确返回 Pod IP
```

### 健康检查深度

`/health` 端点应检查依赖服务：

```python
@app.get("/health")
async def health_check():
    checks = {
        "service": True,
        "redis": await check_redis(),  # 可选
        "llm": await check_llm(),      # 可选
    }
    all_healthy = all(checks.values())
    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={"status": "healthy" if all_healthy else "unhealthy", "checks": checks}
    )
```

---

## 十、依赖安装

```bash
# 基础服务
pip install harness-sdk

# Prometheus 指标
pip install harness-sdk[prometheus]
# 或
pip install prometheus-client

# Redis 分布式存储
pip install harness-sdk[redis]
# 或
pip install redis

# Nacos 服务发现
pip install nacos-sdk-python

# Eureka 服务发现（使用 HTTP API，无需额外依赖）
```

---

## 十一、完整示例

参见 `packages/sdk/src/harness/service/__init__.py` 中的完整服务实现。

启动命令：

```bash
# 开发
uvicorn harness.service:app --reload --port 8000

# 生产
gunicorn -w 4 -k uvicorn.workers.UvicornWorker harness.service:app --bind 0.0.0.0:8000
```

---

## 十二、改造现有应用为微服务

本节以 `harness-scraper` 为例，演示如何将一个基于 Harness SDK 的 CLI 应用改造为 Spring Cloud 微服务。

### 12.1 改造前分析

**现有架构**：`harness-scraper` 是一个 CLI 工具

```
packages/scraper/
├── src/harness_scraper/
│   ├── agent.py          # IntelAgent (封装 AgentHarness)
│   ├── cli.py            # CLI 入口
│   ├── config.py         # 配置加载
│   ├── models.py         # 数据模型
│   └── tools/            # 自定义工具
│       ├── fetch_rss.py
│       ├── fetch_hn.py
│       └── ...
└── skills/               # 技能文件
    ├── ai-intelligence.md
    └── hk-stocks-alpha.md
```

**调用方式**：
```bash
# CLI 调用
harness-scraper --skill ai-intelligence
harness-scraper agent "抓取 AI 新闻"
```

### 12.2 改造目标

将 CLI 改造为微服务，支持：
- HTTP REST 调用
- WebSocket 流式调用
- 健康检查
- Prometheus 指标
- Spring Cloud Gateway 路由

```
Java Service → Gateway → Scraper Service (:8001)
                              │
                              ▼
                         IntelAgent
                              │
                              ▼
                     AgentHarness + Tools
```

### 12.3 改造步骤

#### 步骤 1：创建服务入口文件

在 `packages/scraper/src/harness_scraper/` 目录下创建 `service.py`：

```python
# packages/scraper/src/harness_scraper/service.py
"""
Harness Scraper Service - 微服务入口

启动方式:
    uvicorn harness_scraper.service:app --port 8001

路由:
    GET  /health              - 健康检查
    GET  /metrics             - Prometheus 指标
    POST /api/scrape          - 同步执行
    POST /api/scrape/skill    - 按技能执行
    WebSocket /ws/scrape      - 流式执行
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

# Harness SDK Service 模块
from harness.service import (
    TracingMiddleware,
    ErrorCode,
    create_error_response,
    get_metrics_collector,
    PROMETHEUS_AVAILABLE,
)

# Scraper 本地模块
from harness_scraper.agent import IntelAgent, REPO_SKILL_DIR
from harness_scraper.config import load_config
from harness_scraper.models import ScraperConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# 配置
# =============================================================================

SERVICE_NAME = os.getenv("SERVICE_NAME", "harness-scraper")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8001"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/tmp/scraper/output"))

# =============================================================================
# 应用状态
# =============================================================================

class AppState:
    def __init__(self):
        self.config: ScraperConfig | None = None
        self.agents: dict[str, IntelAgent] = {}  # skill_name -> agent

app_state = AppState()


def get_agent(skill: str | None = None) -> IntelAgent:
    """获取或创建 IntelAgent 实例"""
    skill_name = skill or "ai-intelligence"
    
    if skill_name not in app_state.agents:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        app_state.agents[skill_name] = IntelAgent(
            config=app_state.config,
            skill=skill_name,
            memory_path=OUTPUT_DIR / "MEMORY.md",
        )
    
    return app_state.agents[skill_name]


# =============================================================================
# 生命周期
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动和关闭"""
    logger.info(f"Starting {SERVICE_NAME}...")
    
    # 加载配置
    app_state.config = load_config()
    
    # 初始化 Prometheus
    if PROMETHEUS_AVAILABLE:
        get_metrics_collector().setup()
    
    yield
    
    logger.info(f"Shutting down {SERVICE_NAME}...")


# =============================================================================
# FastAPI 应用
# =============================================================================

app = FastAPI(
    title="Harness Scraper Service",
    description="AI 情报提取微服务",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TracingMiddleware)


# =============================================================================
# 请求/响应模型
# =============================================================================

class ScrapeRequest(BaseModel):
    prompt: str
    skill: str | None = None  # ai-intelligence, hk-stocks-alpha, etc.
    session_id: str | None = None

class ScrapeResponse(BaseModel):
    status: str
    content: str
    skill: str
    session_id: str | None = None


class SkillInfo(BaseModel):
    name: str
    description: str | None = None


# =============================================================================
# 端点：健康检查
# =============================================================================

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "skills_loaded": list(app_state.agents.keys()),
    }


# =============================================================================
# 端点：Prometheus 指标
# =============================================================================

@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
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
# 端点：列出可用技能
# =============================================================================

@app.get("/api/skills", response_model=list[SkillInfo])
async def list_skills():
    """列出所有可用的技能"""
    skills = []
    if REPO_SKILL_DIR.exists():
        for skill_file in REPO_SKILL_DIR.glob("*.md"):
            skills.append(SkillInfo(
                name=skill_file.stem,
                description=f"Skill file: {skill_file.name}",
            ))
    return skills


# =============================================================================
# 端点：REST API
# =============================================================================

@app.post("/api/scrape", response_model=ScrapeResponse)
async def scrape(request: Request, body: ScrapeRequest):
    """
    同步执行情报提取（适合短任务）
    
    Body:
        - prompt: 执行提示词
        - skill: 技能名称（默认 ai-intelligence）
        - session_id: 会话 ID（可选，用于多轮对话）
    """
    trace_id = request.headers.get("X-Trace-Id")
    user_id = request.headers.get("X-User-Id")
    
    try:
        agent = get_agent(body.skill)
        
        result = await agent.run(
            prompt=body.prompt,
            session_id=body.session_id,
            verbose=False,
        )
        
        return ScrapeResponse(
            status="completed",
            content=result.content,
            skill=body.skill or "ai-intelligence",
            session_id=body.session_id,
        )
    
    except Exception as e:
        logger.exception(f"Scrape failed: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                ErrorCode.INTERNAL_ERROR,
                str(e),
                trace_id,
            ).model_dump(),
        )


# =============================================================================
# 端点：WebSocket 流式
# =============================================================================

@app.websocket("/ws/scrape")
async def scrape_ws(websocket: WebSocket):
    """
    WebSocket 流式执行（适合长任务）
    
    协议:
    1. 客户端发送: {"prompt": "...", "skill": "ai-intelligence"}
    2. 服务端流式返回 ProgressEvent
    3. 服务端最终返回: {"type": "done", "result": {...}}
    """
    await websocket.accept()
    
    try:
        data = await websocket.receive_json()
        prompt = data.get("prompt", "")
        skill = data.get("skill", "ai-intelligence")
        session_id = data.get("session_id")
        
        agent = get_agent(skill)
        
        # 进度回调
        async def on_progress(event):
            await websocket.send_json({
                "type": "progress",
                "event_type": event.type.value,
                "message": event.message,
                "data": event.data,
            })
        
        result = await agent._agent.run(
            prompt=prompt,
            session_id=session_id,
            on_progress=on_progress,
        )
        
        await websocket.send_json({
            "type": "done",
            "result": {
                "status": "completed",
                "content": result.content,
                "skill": skill,
                "session_id": result.session.id,
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

#### 步骤 2：更新 pyproject.toml

添加 FastAPI 依赖：

```toml
# packages/scraper/pyproject.toml

[project]
dependencies = [
    "harness-sdk",
    "harness-sdk[service]",   # FastAPI + uvicorn
    "harness-sdk[prometheus]", # 可选：Prometheus 指标
    # ... 其他现有依赖
]

[project.scripts]
harness-scraper = "harness_scraper.cli:main"
harness-scraper-service = "harness_scraper.service:app"  # 新增
```

#### 步骤 3：创建 Dockerfile

```dockerfile
# packages/scraper/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# 复制技能文件
COPY skills/ /app/skills/

# 环境变量
ENV SERVICE_NAME=harness-scraper
ENV SERVICE_PORT=8001
ENV OUTPUT_DIR=/app/output
ENV SKILL_DIR=/app/skills

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 启动命令
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", \
     "harness_scraper.service:app", "--bind", "0.0.0.0:8001"]
```

#### 步骤 4：更新 Spring Cloud Gateway 配置

```yaml
# application.yml
spring:
  cloud:
    gateway:
      routes:
        # Harness Agent Service
        - id: harness-agent
          uri: http://harness-agent:8000
          predicates:
            - Path=/api/agent/**, /ws/agent/**
          filters:
            - StripPrefix=1
        
        # Harness Scraper Service (新增)
        - id: harness-scraper
          uri: http://harness-scraper:8001
          predicates:
            - Path=/api/scraper/**, /ws/scraper/**
          filters:
            - StripPrefix=1
```

#### 步骤 5：Java 客户端调用

```java
// ScraperClient.java
@Service
public class ScraperClient {

    private final WebClient webClient;

    public ScraperClient(WebClient.Builder builder) {
        this.webClient = builder
            .baseUrl("http://api-gateway:8080")
            .build();
    }

    /**
     * 获取可用技能列表
     */
    public Mono<List<SkillInfo>> getSkills() {
        return webClient.get()
            .uri("/api/scraper/api/skills")
            .retrieve()
            .bodyToFlux(SkillInfo.class)
            .collectList();
    }

    /**
     * 执行情报提取
     */
    public Mono<ScrapeResponse> scrape(String prompt, String skill) {
        return webClient.post()
            .uri("/api/scraper/api/scrape")
            .header("Authorization", "Bearer " + getToken())
            .bodyValue(new ScrapeRequest(prompt, skill, null))
            .retrieve()
            .bodyToMono(ScrapeResponse.class);
    }
}

record ScrapeRequest(String prompt, String skill, String sessionId) {}
record ScrapeResponse(String status, String content, String skill, String sessionId) {}
record SkillInfo(String name, String description) {}
```

### 12.4 改造对比

| 方面 | 改造前 (CLI) | 改造后 (微服务) |
|-----|-------------|----------------|
| 调用方式 | `harness-scraper --skill xxx` | `POST /api/scrape` |
| 输出 | 控制台打印 | JSON 响应 |
| 流式输出 | 不支持 | WebSocket `/ws/scrape` |
| 健康检查 | 无 | `GET /health` |
| 指标 | 无 | `GET /metrics` |
| 认证 | 无 | Gateway JWT + X-User-Id |
| 多实例 | 不支持 | Redis Session Store |

### 12.5 改造清单

| 步骤 | 文件 | 改动 |
|-----|------|------|
| 1 | `service.py` | 新建，FastAPI 服务入口 |
| 2 | `pyproject.toml` | 添加 service 依赖 |
| 3 | `Dockerfile` | 新建，容器化配置 |
| 4 | Gateway `application.yml` | 添加路由 |
| 5 | Java 客户端 | 新建调用代码 |

### 12.6 测试验证

```bash
# 1. 启动服务
cd packages/scraper
PYTHONPATH=src uv run uvicorn harness_scraper.service:app --port 8001

# 2. 健康检查
curl http://localhost:8001/health

# 3. 列出技能
curl http://localhost:8001/api/skills

# 4. 执行情报提取
curl -X POST http://localhost:8001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"prompt": "抓取 AI 新闻", "skill": "ai-intelligence"}'

# 5. WebSocket 测试 (使用 wscat)
wscat -c ws://localhost:8001/ws/scrape
> {"prompt": "抓取 AI 新闻", "skill": "ai-intelligence"}
```

### 12.7 注意事项

1. **技能文件路径**：容器化时需要确保 `skills/` 目录被正确复制
2. **输出目录**：需要持久化 `OUTPUT_DIR` 或使用 Redis 存储
3. **Worker 数量**：情报提取是 CPU 密集型，建议 2-4 个 Worker
4. **超时配置**：Gateway 超时建议设为 60s 以上，或使用 WebSocket
