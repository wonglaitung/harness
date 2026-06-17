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

## McpClient 实现

### 客户端包装类

```java
package com.harness.mcp;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.transport.StdioTransport;
import io.modelcontextprotocol.client.transport.HttpSseTransport;
import io.modelcontextprotocol.spec.McpSchema.*;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * MCP 客户端包装器。
 */
public class HarnessMcpClient {

    private final McpClient client;
    private final String serverName;
    private final McpConfig config;
    private volatile boolean connected = false;

    public HarnessMcpClient(String serverName, McpConfig config) {
        this.serverName = serverName;
        this.config = config;

        // 创建传输
        McpTransport transport = createTransport(config);

        // 创建客户端
        this.client = McpClient.builder()
            .transport(transport)
            .requestTimeout(config.requestTimeout())
            .build();
    }

    /**
     * 连接到 MCP 服务器。
     */
    public CompletableFuture<Void> connect() {
        return CompletableFuture.runAsync(() -> {
            try {
                client.connect();
                connected = true;
            } catch (Exception e) {
                throw new McpConnectionException("连接失败: " + e.getMessage(), e);
            }
        });
    }

    /**
     * 断开连接。
     */
    public CompletableFuture<Void> disconnect() {
        return CompletableFuture.runAsync(() -> {
            try {
                client.disconnect();
                connected = false;
            } catch (Exception e) {
                throw new McpConnectionException("断开连接失败: " + e.getMessage(), e);
            }
        });
    }

    /**
     * 获取工具列表。
     */
    public CompletableFuture<List<McpToolInfo>> listTools() {
        return CompletableFuture.supplyAsync(() -> {
            if (!connected) {
                throw new McpNotConnectedException("未连接到服务器");
            }

            ListToolsResult result = client.listTools();

            return result.tools().stream()
                .map(tool -> new McpToolInfo(
                    serverName,
                    tool.name(),
                    tool.description(),
                    tool.inputSchema()
                ))
                .toList();
        });
    }

    /**
     * 调用工具。
     */
    public CompletableFuture<McpToolResult> callTool(String name, Map<String, Object> args) {
        return CompletableFuture.supplyAsync(() -> {
            if (!connected) {
                throw new McpNotConnectedException("未连接到服务器");
            }

            CallToolResult result = client.callTool(name, args);

            return new McpToolResult(
                result.isError() == null || !result.isError(),
                extractContent(result.content()),
                result.isError() ? extractError(result.content()) : null
            );
        });
    }

    /**
     * 获取资源列表。
     */
    public CompletableFuture<List<McpResourceInfo>> listResources() {
        return CompletableFuture.supplyAsync(() -> {
            if (!connected) {
                throw new McpNotConnectedException("未连接到服务器");
            }

            ListResourcesResult result = client.listResources();

            return result.resources().stream()
                .map(resource -> new McpResourceInfo(
                    serverName,
                    resource.uri(),
                    resource.name(),
                    resource.description(),
                    resource.mimeType()
                ))
                .toList();
        });
    }

    /**
     * 读取资源。
     */
    public CompletableFuture<String> readResource(String uri) {
        return CompletableFuture.supplyAsync(() -> {
            if (!connected) {
                throw new McpNotConnectedException("未连接到服务器");
            }

            ReadResourceResult result = client.readResource(uri);
            return extractResourceContent(result.contents());
        });
    }

    /**
     * 获取提示词列表。
     */
    public CompletableFuture<List<McpPromptInfo>> listPrompts() {
        return CompletableFuture.supplyAsync(() -> {
            if (!connected) {
                throw new McpNotConnectedException("未连接到服务器");
            }

            ListPromptsResult result = client.listPrompts();

            return result.prompts().stream()
                .map(prompt -> new McpPromptInfo(
                    serverName,
                    prompt.name(),
                    prompt.description(),
                    prompt.arguments()
                ))
                .toList();
        });
    }

    /**
     * 获取提示词模板。
     */
    public CompletableFuture<String> getPrompt(String name, Map<String, Object> args) {
        return CompletableFuture.supplyAsync(() -> {
            if (!connected) {
                throw new McpNotConnectedException("未连接到服务器");
            }

            GetPromptResult result = client.getPrompt(name, args);
            return extractPromptContent(result.messages());
        });
    }

    // 私有方法
    private McpTransport createTransport(McpConfig config) {
        switch (config.transport()) {
            case STDIO:
                return new StdioTransport(
                    config.command(),
                    config.args(),
                    config.env()
                );

            case HTTP_SSE:
                return new HttpSseTransport(config.url());

            default:
                throw new IllegalArgumentException("不支持的传输类型: " + config.transport());
        }
    }

    private String extractContent(List<Content> contents) {
        StringBuilder sb = new StringBuilder();
        for (Content content : contents) {
            if (content instanceof TextContent text) {
                sb.append(text.text());
            } else if (content instanceof ImageContent image) {
                sb.append("[Image: ").append(image.mimeType()).append("]");
            }
        }
        return sb.toString();
    }

    private String extractError(List<Content> contents) {
        for (Content content : contents) {
            if (content instanceof TextContent text) {
                return text.text();
            }
        }
        return "未知错误";
    }

    private String extractResourceContent(List<ResourceContents> contents) {
        StringBuilder sb = new StringBuilder();
        for (ResourceContents content : contents) {
            if (content instanceof TextResourceContents text) {
                sb.append(text.text());
            } else if (content instanceof BlobResourceContents blob) {
                sb.append("[Binary data: ").append(blob.mimeType()).append("]");
            }
        }
        return sb.toString();
    }

    private String extractPromptContent(List<PromptMessage> messages) {
        StringBuilder sb = new StringBuilder();
        for (PromptMessage msg : messages) {
            sb.append(msg.role()).append(": ");
            if (msg.content() instanceof TextContent text) {
                sb.append(text.text());
            }
            sb.append("\n");
        }
        return sb.toString();
    }

    // Getter
    public String serverName() { return serverName; }
    public boolean isConnected() { return connected; }
}
```

### MCP 配置类

```java
package com.harness.mcp;

import java.util.List;
import java.util.Map;

/**
 * MCP 配置。
 */
public record McpConfig(
    McpTransport transport,      // 传输类型
    String command,              // stdio 命令
    List<String> args,           // 命令参数
    Map<String, String> env,     // 环境变量
    String url,                  // HTTP/SSE URL
    long requestTimeout,         // 请求超时（毫秒）
    boolean autoReconnect        // 自动重连
) {

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private McpTransport transport = McpTransport.STDIO;
        private String command;
        private List<String> args = List.of();
        private Map<String, String> env = Map.of();
        private String url;
        private long requestTimeout = 30000;
        private boolean autoReconnect = true;

        public Builder transport(McpTransport transport) {
            this.transport = transport;
            return this;
        }

        public Builder command(String command) {
            this.command = command;
            return this;
        }

        public Builder args(List<String> args) {
            this.args = args;
            return this;
        }

        public Builder env(Map<String, String> env) {
            this.env = env;
            return this;
        }

        public Builder url(String url) {
            this.url = url;
            return this;
        }

        public Builder requestTimeout(long timeout) {
            this.requestTimeout = timeout;
            return this;
        }

        public Builder autoReconnect(boolean autoReconnect) {
            this.autoReconnect = autoReconnect;
            return this;
        }

        public McpConfig build() {
            return new McpConfig(transport, command, args, env, url, requestTimeout, autoReconnect);
        }
    }
}

/**
 * MCP 传输类型。
 */
public enum McpTransport {
    STDIO,      // 标准输入输出
    HTTP_SSE,   // HTTP Server-Sent Events
    WEBSOCKET   // WebSocket（未来支持）
}
```

## MCP 工具包装器

### 工具适配器

```java
package com.harness.mcp;

import com.harness.tools.*;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * MCP 工具包装器 - 将 MCP 工具适配为 Harness Tool 接口。
 */
public class McpToolWrapper implements Tool {

    private final HarnessMcpClient client;
    private final McpToolInfo toolInfo;

    public McpToolWrapper(HarnessMcpClient client, McpToolInfo toolInfo) {
        this.client = client;
        this.toolInfo = toolInfo;
    }

    @Override
    public String name() {
        // 格式: mcp_{server}_{tool}
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
        // MCP 工具通常使用 JSON Schema 验证
        return JsonSchemaValidator.validate(args, inputSchema());
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return client.callTool(toolInfo.name(), args)
            .thenApply(result -> {
                if (result.success()) {
                    return ToolResult.success(result.output());
                } else {
                    return ToolResult.failure(result.error());
                }
            })
            .exceptionally(e -> ToolResult.failure("MCP 工具调用失败: " + e.getMessage()));
    }
}
```

### JSON Schema 验证器

```java
package com.harness.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;

import java.util.Map;
import java.util.Set;

/**
 * JSON Schema 验证器。
 */
public class JsonSchemaValidator {

    private static final ObjectMapper mapper = new ObjectMapper();
    private static final JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V7);

    /**
     * 验证参数是否符合 Schema。
     */
    public static ValidationResult validate(Map<String, Object> args, Map<String, Object> schema) {
        try {
            JsonNode schemaNode = mapper.valueToTree(schema);
            JsonNode argsNode = mapper.valueToTree(args);

            JsonSchema jsonSchema = factory.getSchema(schemaNode);
            Set<ValidationMessage> errors = jsonSchema.validate(argsNode);

            if (errors.isEmpty()) {
                return ValidationResult.valid();
            }

            String errorMessage = errors.stream()
                .map(ValidationMessage::getMessage)
                .collect(Collectors.joining("\n"));

            return ValidationResult.invalid(errorMessage);

        } catch (Exception e) {
            return ValidationResult.invalid("验证失败: " + e.getMessage());
        }
    }
}
```

## MCP 管理器

```java
package com.harness.mcp;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * MCP 服务器管理器 - 管理多个 MCP 服务器连接。
 */
public class McpManager {

    private final Map<String, HarnessMcpClient> clients = new ConcurrentHashMap<>();
    private final Map<String, McpConfig> configs = new ConcurrentHashMap<>();

    /**
     * 添加 MCP 服务器配置。
     */
    public void addServer(String name, McpConfig config) {
        configs.put(name, config);
    }

    /**
     * 连接所有 MCP 服务器。
     */
    public CompletableFuture<Void> connectAll() {
        List<CompletableFuture<Void>> futures = configs.entrySet().stream()
            .map(entry -> {
                String name = entry.getKey();
                McpConfig config = entry.getValue();

                HarnessMcpClient client = new HarnessMcpClient(name, config);
                clients.put(name, client);

                return client.connect();
            })
            .toList();

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]));
    }

    /**
     * 断开所有连接。
     */
    public CompletableFuture<Void> disconnectAll() {
        List<CompletableFuture<Void>> futures = clients.values().stream()
            .map(HarnessMcpClient::disconnect)
            .toList();

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
            .thenRun(() -> clients.clear());
    }

    /**
     * 获取所有工具。
     */
    public CompletableFuture<List<Tool>> getAllTools() {
        List<CompletableFuture<List<Tool>>> futures = clients.values().stream()
            .map(client -> client.listTools()
                .thenApply(toolInfos -> toolInfos.stream()
                    .map(info -> new McpToolWrapper(client, info))
                    .toList()))
            .toList();

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
            .thenApply(v -> futures.stream()
                .map(CompletableFuture::join)
                .flatMap(List::stream)
                .toList());
    }

    /**
     * 获取指定服务器的客户端。
     */
    public HarnessMcpClient getClient(String name) {
        return clients.get(name);
    }

    /**
     * 获取所有连接状态。
     */
    public Map<String, Boolean> getConnectionStatus() {
        return clients.entrySet().stream()
            .collect(Collectors.toMap(
                Map.Entry::getKey,
                e -> e.getValue().isConnected()
            ));
    }
}
```

## 使用示例

### Stdio MCP 服务器

```java
import com.harness.mcp.*;

// 配置 filesystem MCP 服务器
McpConfig fsConfig = McpConfig.builder()
    .transport(McpTransport.STDIO)
    .command("mcp-server-filesystem")
    .args(List.of("--root", "/workspace"))
    .build();

// 创建客户端
HarnessMcpClient fsClient = new HarnessMcpClient("filesystem", fsConfig);

// 连接
fsClient.connect().join();

// 获取工具列表
List<McpToolInfo> tools = fsClient.listTools().join();
for (McpToolInfo tool : tools) {
    System.out.println("Tool: " + tool.name() + " - " + tool.description());
}

// 调用工具
Map<String, Object> args = Map.of("path", "/workspace/README.md");
McpToolResult result = fsClient.callTool("read_file", args).join();
System.out.println(result.output());

// 断开连接
fsClient.disconnect().join();
```

### HTTP/SSE MCP 服务器

```java
// 配置远程 MCP 服务器
McpConfig remoteConfig = McpConfig.builder()
    .transport(McpTransport.HTTP_SSE)
    .url("https://api.example.com/mcp")
    .requestTimeout(60000)
    .autoReconnect(true)
    .build();

HarnessMcpClient remoteClient = new HarnessMcpClient("remote", remoteConfig);
remoteClient.connect().join();
```

### 集成到 Agent

```java
import com.harness.Harness;
import com.harness.HarnessConfig;
import com.harness.mcp.McpManager;

// 创建 MCP 管理器
McpManager mcpManager = new McpManager();

// 添加服务器
mcpManager.addServer("filesystem", McpConfig.builder()
    .transport(McpTransport.STDIO)
    .command("mcp-server-filesystem")
    .args(List.of("--root", "/workspace"))
    .build());

mcpManager.addServer("database", McpConfig.builder()
    .transport(McpTransport.STDIO)
    .command("mcp-server-postgres")
    .args(List.of("--connection", "postgresql://localhost/mydb"))
    .build());

// 连接所有服务器
mcpManager.connectAll().join();

// 获取所有 MCP 工具
List<Tool> mcpTools = mcpManager.getAllTools().join();

// 创建 Agent
HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .tools(mcpTools)  // 添加 MCP 工具
    .build();

Harness agent = new Harness(config);

// 运行 Agent
LoopResult result = agent.run("读取 README.md 并分析项目结构");
```

## MCP 类型定义

```java
package com.harness.mcp;

/**
 * MCP 工具信息。
 */
public record McpToolInfo(
    String serverName,
    String name,
    String description,
    Map<String, Object> inputSchema
) {}

/**
 * MCP 工具执行结果。
 */
public record McpToolResult(
    boolean success,
    String output,
    String error
) {}

/**
 * MCP 资源信息。
 */
public record McpResourceInfo(
    String serverName,
    String uri,
    String name,
    String description,
    String mimeType
) {}

/**
 * MCP 提示词信息。
 */
public record McpPromptInfo(
    String serverName,
    String name,
    String description,
    List<PromptArgument> arguments
) {}

public record PromptArgument(
    String name,
    String description,
    boolean required
) {}
```

## 常见 MCP 服务器

### 文件系统

```kotlin
// Gradle
implementation("io.modelcontextprotocol:mcp-server-filesystem:0.1.0")
```

```java
McpConfig config = McpConfig.builder()
    .transport(McpTransport.STDIO)
    .command("mcp-server-filesystem")
    .args(List.of("--root", "/workspace"))
    .build();
```

### PostgreSQL

```kotlin
// Gradle
implementation("io.modelcontextprotocol:mcp-server-postgres:0.1.0")
```

```java
McpConfig config = McpConfig.builder()
    .transport(McpTransport.STDIO)
    .command("mcp-server-postgres")
    .args(List.of("--connection", "postgresql://user:pass@localhost/db"))
    .build();
```

### GitHub

```java
McpConfig config = McpConfig.builder()
    .transport(McpTransport.STDIO)
    .command("mcp-server-github")
    .env(Map.of("GITHUB_TOKEN", System.getenv("GITHUB_TOKEN")))
    .build();
```

## 错误处理

```java
package com.harness.mcp;

/**
 * MCP 连接异常。
 */
public class McpConnectionException extends RuntimeException {
    public McpConnectionException(String message) {
        super(message);
    }

    public McpConnectionException(String message, Throwable cause) {
        super(message, cause);
    }
}

/**
 * MCP 未连接异常。
 */
public class McpNotConnectedException extends RuntimeException {
    public McpNotConnectedException(String message) {
        super(message);
    }
}

/**
 * MCP 工具调用异常。
 */
public class McpToolCallException extends RuntimeException {
    public McpToolCallException(String message) {
        super(message);
    }
}
```

## 下一步

- [07-sdk-api.md](./07-sdk-api.md) - 查看完整 API 参考
- [08-security.md](./08-security.md) - 了解安全设计