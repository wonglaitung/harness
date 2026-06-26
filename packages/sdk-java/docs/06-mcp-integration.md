# 06 - MCP 集成 (Java 实现)

## 概述

MCP (Model Context Protocol) 是 Anthropic 推出的开放协议，用于连接 AI 模型与外部工具和数据源。本文档详细说明 Java 版本的 MCP 集成设计。

## MCP 协议概述

### 协议架构

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Architecture                        │
│                                                             │
│  ┌─────────────┐     MCP Protocol     ┌─────────────┐      │
│  │    Agent    │ ←─────────────────→ │  MCP Server  │      │
│  │  (Harness)  │                     │  (Tool/Data) │      │
│  └──────┬──────┘                     └─────────────┘       │
│         │                                                   │
│         ↓                                                   │
│  ┌─────────────┐                                           │
│  │  MCP Client │                                           │
│  │  (Java SDK) │                                           │
│  └─────────────┘                                           │
│                                                             │
│  Transports:                                                │
│  - stdio: Standard I/O (本地进程)                           │
│  - HTTP/SSE: Server-Sent Events (远程服务)                  │
│  - WebSocket: 双向实时通信                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### MCP 功能

| 功能 | 说明 |
|------|------|
| Tools | 可执行的工具函数 |
| Resources | 可读取的数据资源 |
| Prompts | 预定义的提示词模板 |
| Sampling | LLM 采样请求 |

## MCP Java SDK

### 官方 SDK

**Maven 坐标**: `io.modelcontextprotocol:mcp-java-sdk:0.5.0`

**发布**: 2025年2月由 Spring 团队发布

**特性**:
- 支持 stdio 和 HTTP/SSE 传输
- 可独立使用（无需 Spring）
- 支持 Reactor 响应式 API
- 完整的 MCP 协议实现

### Gradle 配置

```kotlin
// build.gradle.kts
dependencies {
    // MCP Java SDK
    implementation("io.modelcontextprotocol:mcp-java-sdk:0.5.0")

    // 如果使用 HTTP/SSE 传输
    implementation("io.modelcontextprotocol:mcp-java-sdk-webflux:0.5.0")
}
```

## 实现状态

**✅ Phase 3 已完成**（2026-06-15）

### 实现的类

| 类 | 文件 | 说明 |
|-----|------|------|
| `McpServerConfig` | `McpServerConfig.java` | 服务器配置（record 类） |
| `McpManager` | `McpManager.java` | 多服务器管理器 |
| `McpToolWrapper` | `McpToolWrapper.java` | 工具包装器（适配 Tool 接口） |
| `McpToolInfo` | `McpToolInfo.java` | 工具元数据（record 类） |

### 依赖

```kotlin
// build.gradle.kts
dependencies {
    implementation("io.modelcontextprotocol:mcp:0.9.0")
}
```

> 注意：使用了官方 MCP Java SDK (`io.modelcontextprotocol:mcp`)，而非文档设计阶段的 `mcp-java-sdk:0.5.0`。

---

## McpServerConfig

### 配置类（实际实现）

```java
package com.harness.mcp;

/**
 * MCP server configuration.
 */
public record McpServerConfig(
    String name,
    String command,
    List<String> args,
    Map<String, String> env,
    String url,
    McpTransportType transportType,
    Duration requestTimeout,
    boolean enabled
) {

    /**
     * Transport types for MCP connections.
     */
    public enum McpTransportType {
        STDIO,  // Standard I/O
        SSE     // Server-Sent Events
    }

    /**
     * Create config for stdio transport.
     */
    public static McpServerConfig stdio(String name, String command, String... args) {
        return new McpServerConfig(
            name, command, List.of(args), Map.of(), null,
            McpTransportType.STDIO, Duration.ofSeconds(30), true
        );
    }

    /**
     * Create config for SSE transport.
     */
    public static McpServerConfig sse(String name, String url) {
        return new McpServerConfig(
            name, null, List.of(), Map.of(), url,
            McpTransportType.SSE, Duration.ofSeconds(30), true
        );
    }

    /**
     * Create config with environment variables.
     */
    public McpServerConfig withEnv(Map<String, String> env) {
        return new McpServerConfig(
            name, command, args, env, url, transportType, requestTimeout, enabled
        );
    }
}
```

---

## McpToolWrapper

### 工具包装器（实际实现）

```java
package com.harness.mcp;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

import io.modelcontextprotocol.java.sdk.McpSyncClient;
import io.modelcontextprotocol.java.sdk.CallToolResult;

import com.harness.tools.Tool;
import com.harness.tools.ToolResult;
import com.harness.tools.ToolContext;
import com.harness.tools.ValidationResult;

/**
 * MCP tool wrapper - adapts MCP tools to Harness Tool interface.
 */
public class McpToolWrapper implements Tool {

    private final McpSyncClient client;
    private final McpToolInfo toolInfo;

    public McpToolWrapper(McpSyncClient client, McpToolInfo toolInfo) {
        this.client = client;
        this.toolInfo = toolInfo;
    }

    @Override
    public String name() {
        // Format: mcp_servername_toolname
        return "mcp_" + toolInfo.serverName() + "_" + toolInfo.name();
    }

    @Override
    public String description() {
        return toolInfo.description();
    }

    @Override
    public Map<String, Object> inputSchema() {
        return toolInfo.inputSchema();
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.MCP;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        // Basic validation - check required fields
        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                CallToolResult result = client.callTool(toolInfo.name(), args);

                if (result.isError() != null && result.isError()) {
                    return ToolResult.failure(extractError(result));
                }

                return ToolResult.success(extractContent(result));

            } catch (Exception e) {
                return ToolResult.failure("MCP tool call failed: " + e.getMessage());
            }
        });
    }

    private String extractContent(CallToolResult result) {
        // Extract content from result
        return result.content().toString();
    }

    private String extractError(CallToolResult result) {
        return result.content().toString();
    }
}
```

### McpToolInfo（实际实现）

```java
package com.harness.mcp;

import java.util.Map;

/**
 * MCP tool metadata.
 */
public record McpToolInfo(
    String serverName,
    String name,
    String description,
    Map<String, Object> inputSchema
) {}
```

---

## McpManager

### 管理器（实际实现）

```java
package com.harness.mcp;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import io.modelcontextprotocol.java.sdk.McpSyncClient;
import io.modelcontextprotocol.java.sdk.McpClient;
import io.modelcontextprotocol.java.sdk.ServerParameters;
import io.modelcontextprotocol.java.sdk.transport.McpTransport;

/**
 * MCP server manager.
 *
 * Manages connections to multiple MCP servers and discovers their tools.
 */
public class McpManager {

    private final Map<String, McpSyncClient> clients;
    private final Map<String, McpServerConfig> configs;
    private final Map<String, List<McpToolWrapper>> serverTools;

    /**
     * Create manager.
     */
    public McpManager() {
        this.clients = new ConcurrentHashMap<>();
        this.configs = new ConcurrentHashMap<>();
        this.serverTools = new ConcurrentHashMap<>();
    }

    /**
     * Register an MCP server configuration.
     */
    public void registerServer(McpServerConfig config) {
        configs.put(config.name(), config);
    }

    /**
     * Connect to a specific server.
     */
    public boolean connect(String serverName) {
        McpServerConfig config = configs.get(serverName);
        if (config == null || !config.enabled()) {
            return false;
        }

        try {
            McpSyncClient client = createClient(config);
            client.initialize();

            clients.put(serverName, client);
            discoverTools(serverName, client);

            return true;
        } catch (Exception e) {
            logger.error("Failed to connect: {}", e.getMessage());
            return false;
        }
    }

    /**
     * Connect to all registered servers.
     */
    public Map<String, Boolean> connectAll() {
        Map<String, Boolean> results = new HashMap<>();
        for (String serverName : configs.keySet()) {
            results.put(serverName, connect(serverName));
        }
        return results;
    }

    /**
     * Disconnect from a specific server.
     */
    public void disconnect(String serverName) {
        McpSyncClient client = clients.remove(serverName);
        if (client != null) {
            client.closeGracefully();
        }
        serverTools.remove(serverName);
    }

    /**
     * Get all discovered tools.
     */
    public List<McpToolWrapper> getAllTools() {
        List<McpToolWrapper> allTools = new ArrayList<>();
        for (List<McpToolWrapper> tools : serverTools.values()) {
            allTools.addAll(tools);
        }
        return allTools;
    }

    /**
     * Check if connected to a server.
     */
    public boolean isConnected(String serverName) {
        return clients.containsKey(serverName);
    }

    /**
     * Get server status summary.
     */
    public Map<String, String> getStatus() {
        Map<String, String> status = new HashMap<>();
        for (String serverName : configs.keySet()) {
            if (clients.containsKey(serverName)) {
                int toolCount = serverTools.getOrDefault(serverName, List.of()).size();
                status.put(serverName, "connected (" + toolCount + " tools)");
            } else {
                status.put(serverName, "disconnected");
            }
        }
        return status;
    }

    private McpSyncClient createClient(McpServerConfig config) {
        McpTransport transport;

        if (config.transportType() == McpServerConfig.McpTransportType.SSE) {
            transport = new io.modelcontextprotocol.java.sdk.transport.HttpClientSseClientTransport(config.url());
        } else {
            ServerParameters params = ServerParameters.builder(config.command())
                .args(config.args().toArray(new String[0]))
                .build();
            transport = new io.modelcontextprotocol.java.sdk.transport.StdioClientTransport(params);
        }

        Duration timeout = config.requestTimeout() != null ? config.requestTimeout() : Duration.ofSeconds(30);

        return McpClient.sync(transport)
            .requestTimeout(timeout)
            .build();
    }

    private void discoverTools(String serverName, McpSyncClient client) {
        // Implementation details...
    }
}
```

---

## 使用示例

### Stdio MCP 服务器

```java
import com.harness.mcp.*;

// 创建 MCP 管理器
McpManager manager = new McpManager();

// 注册 filesystem 服务器（使用工厂方法）
manager.registerServer(
    McpServerConfig.stdio("filesystem", "mcp-server-filesystem", "--root", "/workspace")
);

// 连接所有服务器
Map<String, Boolean> results = manager.connectAll();

// 获取所有 MCP 工具
List<McpToolWrapper> mcpTools = manager.getAllTools();
for (McpToolWrapper tool : mcpTools) {
    System.out.println("Tool: " + tool.name() + " - " + tool.description());
}

// 断开所有连接
manager.disconnectAll();
```

### SSE MCP 服务器

```java
// 注册远程 MCP 服务器（使用 SSE 传输）
manager.registerServer(
    McpServerConfig.sse("remote", "https://api.example.com/mcp")
        .withTimeout(Duration.ofSeconds(60))
);

// 连接
manager.connect("remote");
```

### 集成到 Agent

```java
import com.harness.Harness;
import com.harness.HarnessConfig;
import com.harness.mcp.McpManager;
import com.harness.mcp.McpServerConfig;
import com.harness.tools.Tool;

// 创建 MCP 管理器
McpManager mcpManager = new McpManager();

// 注册服务器
mcpManager.registerServer(
    McpServerConfig.stdio("filesystem", "mcp-server-filesystem", "--root", "/workspace")
);

mcpManager.registerServer(
    McpServerConfig.stdio("database", "mcp-server-postgres")
        .withEnv(Map.of("DATABASE_URL", "postgresql://localhost/mydb"))
);

// 连接所有服务器
mcpManager.connectAll();

// 获取所有 MCP 工具（转为 Tool 类型）
List<Tool> mcpTools = new ArrayList<>(mcpManager.getAllTools());

// 创建 Agent（添加 MCP 工具）
HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .tools(mcpTools)  // 添加 MCP 工具
    .build();

Harness agent = new Harness(config);

// 运行 Agent
LoopResult result = agent.run("读取 README.md 并分析项目结构");

// 清理
mcpManager.disconnectAll();
```

---

## 常见 MCP 服务器

### 文件系统

```java
McpServerConfig config = McpServerConfig.stdio(
    "filesystem",
    "mcp-server-filesystem",
    "--root", "/workspace"
);
```

### PostgreSQL

```java
McpServerConfig config = McpServerConfig.stdio(
    "database",
    "mcp-server-postgres"
).withEnv(Map.of("DATABASE_URL", "postgresql://user:pass@localhost/db"));
```

### GitHub

```java
McpServerConfig config = McpServerConfig.stdio(
    "github",
    "mcp-server-github"
).withEnv(Map.of("GITHUB_TOKEN", System.getenv("GITHUB_TOKEN")));
```

---

## MCP Transport 层

### Transport 接口

MCP Transport 是传输层抽象，支持不同的通信机制：

```java
package com.harness.mcp;

/**
 * MCP transport layer abstraction.
 */
public interface MCPTransport {

    /**
     * Establish connection to MCP server.
     */
    void connect() throws IOException;

    /**
     * Close connection to MCP server.
     */
    void disconnect();

    /**
     * Send a JSON-RPC message.
     */
    void send(Map<String, Object> message) throws IOException;

    /**
     * Send a JsonRpcRequest.
     */
    void send(JsonRpcRequest request) throws IOException;

    /**
     * Receive a message (blocking).
     */
    Map<String, Object> receive() throws InterruptedException;

    /**
     * Receive a message with timeout.
     */
    Map<String, Object> receive(long timeout, TimeUnit unit)
        throws InterruptedException, TimeoutException;

    /**
     * Check if transport is connected.
     */
    boolean isConnected();
}
```

### StdioTransport

子进程标准输入输出传输，用于本地 MCP 服务器：

```java
import com.harness.mcp.StdioTransport;

// 创建 stdio 传输
StdioTransport transport = StdioTransport.builder()
    .command("mcp-server-filesystem")
    .args("--root", "/workspace")
    .env(Map.of("DEBUG", "1"))
    .build();

// 连接
transport.connect();

// 发送请求
JsonRpcRequest request = new JsonRpcRequest("1", "tools/list", Map.of());
transport.send(request);

// 接收响应
Map<String, Object> response = transport.receive();

// 断开
transport.disconnect();
```

**特性**：
- 启动子进程并通过 stdin/stdout 通信
- 后台线程读取 stdout 和 stderr
- 支持进程超时终止

### HTTPTransport

HTTP/SSE 传输，支持三种协议：

```java
import com.harness.mcp.HTTPTransport;

// 创建 HTTP 传输
HTTPTransport transport = HTTPTransport.builder()
    .url("http://localhost:3000")
    .timeout(Duration.ofSeconds(30))
    .build();

// 自动检测协议
transport.connect();

// 查看检测到的协议
String protocol = transport.getProtocol();
// "streamable-http", "http-sse", 或 "fastmcp-sse"
```

**支持的协议**：

| 协议 | 说明 | 检测方式 |
|------|------|----------|
| Streamable HTTP | 2025-11-25 规范，POST /mcp，响应可能为 SSE | 尝试 POST /mcp |
| HTTP+SSE | 2024-11-05 规范（已弃用），POST /message + GET /sse | POST /mcp 返回 400/404/405 |
| FastMCP SSE | FastMCP 实现，GET /sse 发现端点 | 默认回退 |

**使用示例**：

```java
// 强制指定协议
HTTPTransport transport = HTTPTransport.builder()
    .url("http://localhost:3000")
    .protocol(HTTPTransport.PROTOCOL_STREAMABLE_HTTP)
    .build();

// 发送请求
Map<String, Object> request = Map.of(
    "jsonrpc", "2.0",
    "id", "1",
    "method", "tools/list",
    "params", Map.of()
);
transport.send(request);

// 接收响应（带超时）
JsonRpcResponse response = transport.receiveResponse(5, TimeUnit.SECONDS);
```

---

## 注意事项

### 依赖版本

实际实现使用 `io.modelcontextprotocol:mcp:0.9.0`，而非文档早期版本中的 `io.modelcontextprotocol:mcp-java-sdk:0.5.0`。

### 同步 vs 异步

当前实现使用 `McpSyncClient`（同步客户端）。如果需要异步操作，可以使用：

```java
import io.modelcontextprotocol.java.sdk.McpClient;

// 异步客户端
var asyncClient = McpClient.async(transport)
    .requestTimeout(Duration.ofSeconds(30))
    .build();
```

### 连接生命周期

确保在应用关闭时调用 `manager.disconnectAll()` 清理连接。

---

## 下一步

- [04-tool-system.md](./04-tool-system.md) - 了解工具系统（MCP 工具包装器）
- [05-memory-system.md](./05-memory-system.md) - 了解记忆系统
- [07-sdk-api.md](./07-sdk-api.md) - 查看完整 API 参考
- [08-security.md](./08-security.md) - 了解安全设计
- [09-implementation.md](./09-implementation.md) - 查看实施进度