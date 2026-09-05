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

```java
// TracingMiddleware（Java Spring Boot 中使用 Filter）
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

@Component
public class TracingFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request,
            HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String traceId = request.getHeader("traceparent");
        if (traceId == null) {
            traceId = request.getHeader("X-B3-TraceId");
        }
        if (traceId == null) {
            traceId = request.getHeader("X-Trace-Id");
        }
        // 将 traceId 存入 MDC 以便日志跟踪
        if (traceId != null) {
            org.slf4j.MDC.put("traceId", traceId);
        }
        try {
            chain.doFilter(request, response);
        } finally {
            org.slf4j.MDC.clear();
        }
    }
}
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

```java
// MetricsCollector（Java Spring Boot 中使用 Micrometer）
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.binder.jvm.ClassLoaderMetrics;
import io.micrometer.core.instrument.binder.jvm.JvmGcMetrics;
import io.micrometer.core.instrument.binder.jvm.JvmMemoryMetrics;
import org.springframework.stereotype.Component;

@Component
public class MetricsCollector {
    private final Counter loopIterationCounter;
    private final Counter toolCallCounter;
    private final Counter tokenCounter;
    private final Timer llmCallTimer;
    private final Timer toolCallTimer;

    public MetricsCollector(MeterRegistry registry) {
        // 初始化指标
        this.loopIterationCounter = Counter.builder("harness_loop_iterations_total")
            .description("总循环迭代次数")
            .register(registry);
        this.toolCallCounter = Counter.builder("harness_tool_calls_total")
            .description("工具调用次数")
            .register(registry);
        this.tokenCounter = Counter.builder("harness_llm_tokens_total")
            .description("Token 使用量")
            .register(registry);
        this.llmCallTimer = Timer.builder("harness_llm_call_duration_seconds")
            .description("LLM 调用耗时")
            .register(registry);
        this.toolCallTimer = Timer.builder("harness_tool_call_duration_seconds")
            .description("工具调用耗时")
            .register(registry);

        // 注册 JVM 指标
        new ClassLoaderMetrics().bindTo(registry);
        new JvmGcMetrics().bindTo(registry);
        new JvmMemoryMetrics().bindTo(registry);
    }

    public void recordIteration() { loopIterationCounter.increment(); }
    public void recordToolCall(String tool, boolean success, double duration) {
        toolCallCounter.increment();
        toolCallTimer.record(java.time.Duration.ofMillis((long)(duration * 1000)));
    }
    public void recordTokenUsage(int inputTokens, int outputTokens) {
        tokenCounter.increment(inputTokens + outputTokens);
    }
}
```

### 4.3 Redis 分布式会话

用于多实例部署的会话存储：

```java
// Redis 分布式会话（Java 中使用 Spring Session + Redis）
import org.springframework.session.data.redis.RedisIndexedSessionRepository;
import org.springframework.data.redis.core.RedisTemplate;

// Spring Boot 自动配置 Redis Session Store
// application.yml:
// spring.session.store-type: redis
// spring.data.redis.host: localhost
// spring.data.redis.port: 6379

// 操作会话（Spring Session 自动管理）
// Session 自动保存到 Redis，支持分布式环境

// 分布式锁（使用 Redisson）
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;

RLock lock = redisson.getLock("my-resource");
try {
    if (lock.tryLock(30, TimeUnit.SECONDS)) {
        // 执行需要锁保护的操作
    }
} finally {
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}
```

**特点**：
- JSON 序列化（非 pickle），跨语言兼容
- Schema 版本管理，支持向后兼容
- TTL 自动清理
- 损坏数据自动删除

### 4.4 服务发现

支持 Nacos 和 Eureka：

```java
// 服务发现（Java 中使用 Spring Cloud Discovery）
import org.springframework.cloud.client.discovery.DiscoveryClient;
import org.springframework.cloud.client.ServiceInstance;
import org.springframework.stereotype.Component;

// Spring Cloud 自动配置服务发现
// application.yml:
// spring.cloud.nacos.discovery.server-addr: nacos:8848
// 或
// eureka.client.service-url.defaultZone: http://eureka:8761/eureka/

@Component
public class ServiceDiscoveryExample {
    private final DiscoveryClient discoveryClient;

    public ServiceDiscoveryExample(DiscoveryClient discoveryClient) {
        this.discoveryClient = discoveryClient;
    }

    public void discoverServices() {
        // 获取服务实例
        java.util.List<ServiceInstance> instances =
            discoveryClient.getInstances("harness-agent");
        for (ServiceInstance instance : instances) {
            System.out.println("Instance: " + instance.getHost() + ":" + instance.getPort());
        }
    }
}
```

**Kubernetes 环境**：

```java
// Kubernetes 环境中获取 Pod IP
// 使用环境变量 POD_IP（Kubernetes 自动注入）
String podIp = System.getenv("POD_IP");
if (podIp == null) {
    // 回退：尝试获取本机 IP
    podIp = java.net.InetAddress.getLocalHost().getHostAddress();
}
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

```java
// 获取正确的 Pod IP（使用环境变量）
String podIp = System.getenv("POD_IP");
if (podIp == null) {
    podIp = java.net.InetAddress.getLocalHost().getHostAddress();
}
```

### 健康检查深度

`/health` 端点应检查依赖服务：

```java
// 健康检查端点（Spring Boot Actuator 自动提供）
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;
import java.util.Map;

@Component
public class HarnessHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        Map<String, Object> checks = new java.util.HashMap<>();
        checks.put("service", true);
        checks.put("redis", checkRedis());
        checks.put("llm", checkLlm());

        boolean allHealthy = checks.values().stream().allMatch(v -> Boolean.TRUE.equals(v));
        if (allHealthy) {
            return Health.up()
                .withDetail("service", "healthy")
                .withDetails(checks)
                .build();
        } else {
            return Health.down()
                .withDetail("service", "unhealthy")
                .withDetails(checks)
                .build();
        }
    }

    private boolean checkRedis() {
        // 检查 Redis 连接
        return true;
    }

    private boolean checkLlm() {
        // 检查 LLM 服务
        return true;
    }
}
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

```java
// packages/scraper/src/main/java/com/harness/scraper/ScraperServiceApplication.java
// Harness Scraper Service - 微服务入口

package com.harness.scraper;

import com.harness.integration.AgentHarness;
import com.harness.types.LoopResult;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@SpringBootApplication
@RestController
public class ScraperServiceApplication {

    private static final String SERVICE_NAME = System.getenv().getOrDefault("SERVICE_NAME", "harness-scraper");
    private static final int SERVICE_PORT = Integer.parseInt(System.getenv().getOrDefault("SERVICE_PORT", "8001"));
    private static final Map<String, AgentHarness> agents = new ConcurrentHashMap<>();

    public static void main(String[] args) {
        SpringApplication.run(ScraperServiceApplication.class, args);
    }

    private static AgentHarness getAgent(String skill) {
        String skillName = skill != null ? skill : "ai-intelligence";
        return agents.computeIfAbsent(skillName, k -> AgentHarness.builder().build());
    }

    // 端点：健康检查
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> healthCheck() {
        return ResponseEntity.ok(Map.of(
            "status", "healthy",
            "service", SERVICE_NAME,
            "skills_loaded", agents.keySet()
        ));
    }

    // 端点：Prometheus 指标
    @GetMapping("/metrics")
    public ResponseEntity<String> metrics() {
        return ResponseEntity.ok("# Prometheus metrics\nharness_loop_iterations_total 0\n");
    }

    // 端点：列出可用技能
    @GetMapping("/api/skills")
    public ResponseEntity<?> listSkills() {
        return ResponseEntity.ok(java.util.List.of(
            Map.of("name", "ai-intelligence", "description", "AI intelligence skill"),
            Map.of("name", "hk-stocks-alpha", "description", "HK stocks alpha skill")
        ));
    }

    // 端点：REST API
    @PostMapping("/api/scrape")
    public ResponseEntity<?> scrape(@RequestBody Map<String, String> body) {
        String prompt = body.getOrDefault("prompt", "");
        String skill = body.getOrDefault("skill", "ai-intelligence");
        String sessionId = body.get("session_id");

        try {
            AgentHarness agent = getAgent(skill);
            LoopResult result = agent.run(prompt, sessionId).join();

            return ResponseEntity.ok(Map.of(
                "status", "completed",
                "content", result.content(),
                "skill", skill,
                "session_id", sessionId != null ? sessionId : ""
            ));
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                "errorCode", "AGENT_500_001",
                "errorMessage", e.getMessage()
            ));
        }
    }

    // WebSocket 流式端点
    @org.springframework.web.socket.config.annotation.EnableWebSocket
    @org.springframework.web.socket.config.annotation.WebSocketConfigurer
    public class WebSocketConfig implements org.springframework.web.socket.config.annotation.WebSocketConfigurer {
        @Override
        public void registerWebSocketHandlers(org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry registry) {
            registry.addHandler(new ScraperWebSocketHandler(), "/ws/scrape").setAllowedOrigins("*");
        }
    }

    public static class ScraperWebSocketHandler extends TextWebSocketHandler {
        @Override
        public void afterConnectionEstablished(WebSocketSession session) throws Exception {
            // 连接已建立
        }

        @Override
        protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
            // 解析请求
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            Map<String, Object> data = mapper.readValue(message.getPayload(), Map.class);
            String prompt = (String) data.getOrDefault("prompt", "");
            String skill = (String) data.getOrDefault("skill", "ai-intelligence");

            AgentHarness agent = getAgent(skill);
            LoopResult result = agent.run(prompt).join();

            // 发送结果
            session.sendMessage(new TextMessage(mapper.writeValueAsString(Map.of(
                "type", "done",
                "result", Map.of(
                    "status", "completed",
                    "content", result.content(),
                    "skill", skill
                )
            ))));
        }
    }
}
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
