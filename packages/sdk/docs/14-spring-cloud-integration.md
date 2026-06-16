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
