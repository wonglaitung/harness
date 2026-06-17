# 15 - Spring Cloud 集成指南

> 本文档描述 Harness SDK Java 版本与 Spring Cloud 微服务架构的集成方案。
> 参考 Python SDK 的 `14-spring-cloud-integration.md` 进行 Java 版本迁移。

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
│                 Harness Agent Service (Java)                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Spring Boot Service                                 │   │
│  │  - /health      健康检查                             │   │
│  │  - /metrics     Prometheus 指标                      │   │
│  │  - /api/run     同步执行                             │   │
│  │  - /ws/run      WebSocket 流式执行                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Harness (SDK 核心)                                  │   │
│  │  - AgentLoop (ReAct 循环)                           │   │
│  │  - OpenTelemetry Tracing                            │   │
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

## 二、快速开始

### Maven 依赖

```xml
<dependencies>
    <!-- Harness SDK -->
    <dependency>
        <groupId>com.harness</groupId>
        <artifactId>harness-sdk-all</artifactId>
        <version>1.0.0</version>
    </dependency>
    
    <!-- Spring Boot -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
        <version>3.2.0</version>
    </dependency>
    
    <!-- Spring Boot WebSocket -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-websocket</artifactId>
        <version>3.2.0</version>
    </dependency>
    
    <!-- Spring Boot Actuator (健康检查、指标) -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
        <version>3.2.0</version>
    </dependency>
    
    <!-- Redis (分布式会话) -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
        <version>3.2.0</version>
    </dependency>
    
    <!-- Spring Cloud Nacos (服务发现) -->
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
        <version>2022.0.0.0</version>
    </dependency>
</dependencies>
```

### 基础服务类

```java
// HarnessAgentService.java
@RestController
@RequestMapping("/api")
public class HarnessAgentService {

    private final Harness agent;

    public HarnessAgentService() {
        HarnessConfig config = HarnessConfig.builder()
            .model("claude-sonnet-4-6")
            .baseUrl(System.getenv("LLM_API_URL"))  // 银行 API Gateway
            .apiKey(System.getenv("LLM_API_KEY"))
            .tools(List.of(
                new ReadTool(),
                new BashTool(true)  // sandbox mode
            ))
            .memoryDir(Path.of(System.getenv("MEMORY_DIR", "/tmp/harness/memory")))
            .build();
        
        this.agent = new Harness(config);
    }

    @PostMapping("/run")
    public ResponseEntity<AgentResponse> run(
            @RequestBody AgentRequest request,
            @RequestHeader(value = "X-Trace-Id", required = false) String traceId,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {
        
        LoopResult result = agent.run(request.getPrompt(), request.getSessionId());
        
        return ResponseEntity.ok(new AgentResponse(
            "completed",
            result.getContent(),
            request.getSessionId(),
            result.getIterations(),
            result.getTokenUsage()
        ));
    }
}
```

---

## 三、端点列表

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/actuator/health` | GET | 健康检查（Spring Boot Actuator） |
| `/actuator/prometheus` | GET | Prometheus 指标 |
| `/api/run` | POST | 同步执行 Agent（适合短任务） |
| `/api/sessions/{id}` | GET | 获取会话信息 |
| `/api/sessions/{id}` | DELETE | 清除会话 |
| `/ws/run` | WebSocket | 流式执行（适合长任务） |

---

## 四、链路追踪

### TraceID 传播

从 Spring Cloud Gateway 提取 W3C TraceContext：

```java
// TracingFilter.java
@Component
public class TracingFilter implements WebFilter {

    private static final String TRACE_PARENT = "traceparent";
    private static final String X_B3_TRACE_ID = "X-B3-TraceId";
    private static final String X_TRACE_ID = "X-Trace-Id";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        String traceId = extractTraceId(exchange.getRequest());
        
        // 存入 ThreadLocal（用于 SDK 内部）
        TraceContext.setTraceId(traceId);
        
        // 添加到响应头
        exchange.getResponse().getHeaders().add("X-Trace-Id", traceId);
        
        return chain.filter(exchange)
            .doFinally(signalType -> TraceContext.clear());
    }

    private String extractTraceId(ServerHttpRequest request) {
        // 优先 W3C TraceContext
        String traceparent = request.getHeaders().getFirst(TRACE_PARENT);
        if (traceparent != null) {
            return parseW3CTraceParent(traceparent);
        }
        
        // Zipkin/Sleuth
        String b3TraceId = request.getHeaders().getFirst(X_B3_TRACE_ID);
        if (b3TraceId != null) {
            return b3TraceId;
        }
        
        // 自定义
        String customTraceId = request.getHeaders().getFirst(X_TRACE_ID);
        if (customTraceId != null) {
            return customTraceId;
        }
        
        // 生成新的 TraceID
        return UUID.randomUUID().toString().replace("-", "");
    }

    private String parseW3CTraceParent(String traceparent) {
        // 格式: 00-{trace-id}-{parent-id}-{flags}
        String[] parts = traceparent.split("-");
        return parts.length >= 2 ? parts[1] : traceparent;
    }
}
```

### SDK 内部使用 TraceID

```java
// 在 HarnessConfig 中配置审计日志
HarnessConfig config = HarnessConfig.builder()
    // ...
    .auditLogConfig(AuditLogConfig.builder()
        .includeTraceId(true)
        .traceIdSupplier(() -> TraceContext.getTraceId())
        .build())
    .build();
```

---

## 五、Prometheus 指标

### 使用 Spring Boot Actuator

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: health, prometheus, metrics
  prometheus:
    metrics:
      export:
        enabled: true
```

### 自定义 Harness 指标

```java
// HarnessMetrics.java
@Component
public class HarnessMetrics {

    private final MeterRegistry meterRegistry;

    // Counter: 总循环迭代次数
    private final Counter loopIterations;
    
    // Counter: 工具调用次数
    private final Counter toolCalls;
    
    // Counter: Token 使用量
    private final Counter llmTokensInput;
    private final Counter llmTokensOutput;
    
    // Histogram: LLM 调用耗时
    private final Timer llmCallDuration;
    
    // Histogram: 工具调用耗时
    private final Timer toolCallDuration;
    
    // Gauge: 当前活跃会话数
    private final AtomicInteger activeSessions = new AtomicInteger(0);

    public HarnessMetrics(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
        
        this.loopIterations = Counter.builder("harness_loop_iterations_total")
            .description("Total loop iterations")
            .register(meterRegistry);
        
        this.toolCalls = Counter.builder("harness_tool_calls_total")
            .description("Tool calls")
            .tag("tool", "unknown")
            .tag("status", "success")
            .register(meterRegistry);
        
        this.llmTokensInput = Counter.builder("harness_llm_tokens_total")
            .description("LLM token usage")
            .tag("type", "input")
            .register(meterRegistry);
        
        this.llmTokensOutput = Counter.builder("harness_llm_tokens_total")
            .description("LLM token usage")
            .tag("type", "output")
            .register(meterRegistry);
        
        this.llmCallDuration = Timer.builder("harness_llm_call_duration_seconds")
            .description("LLM call duration")
            .register(meterRegistry);
        
        this.toolCallDuration = Timer.builder("harness_tool_call_duration_seconds")
            .description("Tool call duration")
            .register(meterRegistry);
        
        // Gauge
        meterRegistry.gauge("harness_active_sessions", activeSessions);
    }

    // Hook 回调方法
    public void onLoopStart() {
        activeSessions.incrementAndGet();
    }

    public void onLoopEnd() {
        loopIterations.increment();
        activeSessions.decrementAndGet();
    }

    public void onToolCall(String toolName, boolean success, long durationMs) {
        toolCalls.increment();
        toolCallDuration.record(durationMs, TimeUnit.MILLISECONDS);
    }

    public void onLlmCall(int inputTokens, int outputTokens, long durationMs) {
        llmTokensInput.increment(inputTokens);
        llmTokensOutput.increment(outputTokens);
        llmCallDuration.record(durationMs, TimeUnit.MILLISECONDS);
    }
}
```

### 集成到 Harness

```java
// 使用 Hook 系统收集指标
HarnessConfig config = HarnessConfig.builder()
    // ...
    .hooks(List.of(
        new MetricsHook(harnessMetrics)
    ))
    .build();

// MetricsHook.java
public class MetricsHook implements Hook {
    
    private final HarnessMetrics metrics;
    
    @Override
    public void beforeLoop(LoopContext ctx) {
        metrics.onLoopStart();
    }
    
    @Override
    public void afterLoop(LoopContext ctx, LoopResult result) {
        metrics.onLoopEnd();
    }
    
    @Override
    public void afterTool(LoopContext ctx, ToolCall call, ToolResult result) {
        metrics.onToolCall(
            call.getName(),
            result.isSuccess(),
            result.getDurationMs()
        );
    }
    
    @Override
    public void afterLlm(LoopContext ctx, LLMResponse response) {
        metrics.onLlmCall(
            response.getInputTokens(),
            response.getOutputTokens(),
            response.getDurationMs()
        );
    }
}
```

---

## 六、Redis 分布式会话

### 配置

```yaml
# application.yml
spring:
  data:
    redis:
      host: redis-service
      port: 6379
      password: ${REDIS_PASSWORD}
```

### Redis Session Store

```java
// RedisSessionStore.java
@Component
public class RedisSessionStore {

    private final StringRedisTemplate redisTemplate;
    private static final String SESSION_PREFIX = "harness:session:";
    private static final Duration SESSION_TTL = Duration.ofHours(24);

    public RedisSessionStore(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public void saveSession(String sessionId, SessionData data) {
        String key = SESSION_PREFIX + sessionId;
        String json = toJson(data);
        redisTemplate.opsForValue().set(key, json, SESSION_TTL);
    }

    public SessionData loadSession(String sessionId) {
        String key = SESSION_PREFIX + sessionId;
        String json = redisTemplate.opsForValue().get(key);
        if (json == null) {
            return null;
        }
        return fromJson(json);
    }

    public void deleteSession(String sessionId) {
        String key = SESSION_PREFIX + sessionId;
        redisTemplate.delete(key);
    }

    private String toJson(SessionData data) {
        // JSON 序列化（跨语言兼容）
        ObjectMapper mapper = new ObjectMapper();
        try {
            return mapper.writeValueAsString(data);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize session", e);
        }
    }

    private SessionData fromJson(String json) {
        ObjectMapper mapper = new ObjectMapper();
        try {
            return mapper.readValue(json, SessionData.class);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to deserialize session", e);
        }
    }
}
```

### 分布式锁

```java
// RedisDistributedLock.java
@Component
public class RedisDistributedLock {

    private final StringRedisTemplate redisTemplate;
    private static final String LOCK_PREFIX = "harness:lock:";

    public String acquire(String resource, Duration timeout) {
        String key = LOCK_PREFIX + resource;
        String token = UUID.randomUUID().toString();
        
        Boolean success = redisTemplate.opsForValue()
            .setIfAbsent(key, token, timeout);
        
        return Boolean.TRUE.equals(success) ? token : null;
    }

    public boolean release(String resource, String token) {
        String key = LOCK_PREFIX + resource;
        
        // Lua script: 只有 token 匹配时才删除
        String script = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            else
                return 0
            end
            """;
        
        Long result = redisTemplate.execute(
            new DefaultRedisScript<>(script, Long.class),
            List.of(key),
            token
        );
        
        return result != null && result == 1;
    }
}
```

---

## 七、服务发现

### Nacos 配置

```yaml
# application.yml
spring:
  application:
    name: harness-agent
  cloud:
    nacos:
      discovery:
        server-addr: nacos-service:8848
        namespace: ${NACOS_NAMESPACE:public}
        group: ${NACOS_GROUP:DEFAULT_GROUP}
```

### Kubernetes Pod IP

```java
// PodIpProvider.java
@Component
public class PodIpProvider {

    private String podIp;

    public PodIpProvider() {
        // Kubernetes 环境变量
        this.podIp = System.getenv("POD_IP");
        
        if (this.podIp == null) {
            // 本地开发环境
            try {
                this.podIp = InetAddress.getLocalHost().getHostAddress();
            } catch (UnknownHostException e) {
                this.podIp = "127.0.0.1";
            }
        }
    }

    public String getPodIp() {
        return podIp;
    }
}
```

---

## 八、统一错误响应

### 错误格式

符合 Spring Cloud 规范：

```json
{
    "errorCode": "AGENT_400_001",
    "errorMessage": "Invalid input parameter",
    "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
    "timestamp": "2026-06-17T10:30:00Z"
}
```

### 错误码定义

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

### 全局异常处理

```java
// GlobalExceptionHandler.java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(AgentException.class)
    public ResponseEntity<ErrorResponse> handleAgentException(
            AgentException ex,
            HttpServletRequest request) {
        
        String traceId = request.getHeader("X-Trace-Id");
        
        ErrorResponse response = new ErrorResponse(
            ex.getErrorCode(),
            ex.getMessage(),
            traceId,
            Instant.now()
        );
        
        return ResponseEntity
            .status(ex.getHttpStatus())
            .body(response);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGenericException(
            Exception ex,
            HttpServletRequest request) {
        
        String traceId = request.getHeader("X-Trace-Id");
        
        ErrorResponse response = new ErrorResponse(
            "AGENT_500_001",
            "Internal server error",
            traceId,
            Instant.now()
        );
        
        return ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(response);
    }
}

// ErrorResponse.java
public record ErrorResponse(
    String errorCode,
    String errorMessage,
    String traceId,
    Instant timestamp
) {}
```

---

## 九、WebSocket 流式执行

### WebSocket Handler

```java
// AgentWebSocketHandler.java
@Component
public class AgentWebSocketHandler implements WebSocketHandler {

    private final Harness agent;

    @Override
    public Mono<Void> handle(WebSocketSession session) {
        return session.receive()
            .flatMap(message -> handleRequest(session, message));
    }

    private Mono<Void> handleRequest(WebSocketSession session, WebSocketMessage message) {
        String payload = message.getPayloadAsText();
        
        // 解析请求
        AgentRequest request = parseRequest(payload);
        
        // 流式执行
        return session.send(
            agent.stream(request.getPrompt(), request.getSessionId())
                .map(chunk -> session.textMessage(toJson(chunk)))
                .concatWith(Mono.just(session.textMessage(toJson(new DoneEvent()))))
        );
    }

    private AgentRequest parseRequest(String payload) {
        ObjectMapper mapper = new ObjectMapper();
        try {
            return mapper.readValue(payload, AgentRequest.class);
        } catch (JsonProcessingException e) {
            throw new AgentException("AGENT_400_001", "Invalid request format");
        }
    }

    private String toJson(Object obj) {
        ObjectMapper mapper = new ObjectMapper();
        try {
            return mapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            return "{\"error\": \"Serialization failed\"}";
        }
    }
}
```

### WebSocket 配置

```java
// WebSocketConfig.java
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final AgentWebSocketHandler agentWebSocketHandler;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(agentWebSocketHandler, "/ws/run")
            .setAllowedOrigins("*");
    }
}
```

---

## 十、Spring Cloud Gateway 配置

### application.yml (Gateway)

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
          uri: lb://harness-agent
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

### 网关鉴权过滤器

```java
// AuthFilter.java
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

## 十一、Kubernetes 部署

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
            - containerPort: 8080
          env:
            - name: POD_IP
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP
            - name: LLM_API_URL
              value: "https://api.your-bank.com/v1"
            - name: LLM_API_KEY
              valueFrom:
                secretKeyRef:
                  name: harness-secrets
                  key: llm-api-key
            - name: REDIS_HOST
              value: "redis-service"
            - name: NACOS_SERVER_ADDR
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
              path: /actuator/health/liveness
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
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

## 十二、关键注意事项

### 认证安全

采用 **网关鉴权 + 内部头传递** 模式：

```
Client (JWT) -> Gateway (验证 JWT) -> Java Service (信任 Gateway)
                                        读取 X-User-Id 头部
```

Java 服务只需验证请求来自 Gateway IP 白名单。

### Redis 序列化

使用 JSON（非 Java 序列化），确保：
- 跨语言兼容（Python 服务可读取）
- Schema 版本管理（向后兼容）
- 损坏数据自动清理

### K8s 服务发现

在 Kubernetes 中，使用 `POD_IP` 环境变量获取正确的 IP。

### 健康检查深度

`/actuator/health` 端点可配置检查依赖服务：

```yaml
management:
  health:
    redis:
      enabled: true
    llm:
      enabled: true  # 自定义检查
```

---

## 十三、与 Python SDK 的对应关系

| Python SDK 模块 | Java SDK 对应 | 说明 |
|----------------|---------------|------|
| `harness.service` | `HarnessAgentService` | Spring Boot 服务 |
| `harness.service.tracing` | `TracingFilter` | TraceID 传播 |
| `harness.service.metrics` | `HarnessMetrics` | Prometheus 指标 |
| `harness.service.store_redis` | `RedisSessionStore` | Redis 存储 |
| `harness.service.discovery` | Spring Cloud Nacos | 服务发现 |
| `harness.service.error_handler` | `GlobalExceptionHandler` | 错误处理 |

---

## 十四、同步策略

当 Python SDK 的 `14-spring-cloud-integration.md` 更新时：

1. **识别变更**：检查 Python SDK 的服务模块改动
2. **映射到 Java**：对应 Java Spring Boot 实现
3. **保持一致性**：API 端点、错误码、指标名称保持一致
4. **测试验证**：确保 Java 和 Python 服务行为一致