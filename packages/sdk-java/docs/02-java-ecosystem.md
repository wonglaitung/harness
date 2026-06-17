# 02 - Java 生态系统依赖分析

## 概述

本文档详细分析 Harness SDK Java 版本所需的依赖，以及与 Python 版本的对应关系。

## 核心依赖对照表

| 功能 | Python 依赖 | Java 依赖 | 版本 | 许可证 |
|------|------------|-----------|------|--------|
| LLM API (Anthropic Claude) | `anthropic` | `com.anthropic:anthropic-java` | 2.40.1 | Apache 2.0 |
| LLM API (OpenAI 兼容) | `openai` | `com.openai:openai-java` | 4.39.1 | Apache 2.0 |
| MCP 协议 | `mcp` | `io.modelcontextprotocol:mcp-java-sdk` | 0.5.0 | MIT |
| Token 计数 | `tiktoken` | `com.knuddelsgmbh:jtokkit` | 1.0.0 | MIT |
| JSON 处理 | `pydantic` | `com.fasterxml.jackson.core:jackson-databind` | 2.17.0 | Apache 2.0 |
| HTTP 客户端 | `aiohttp` | (SDK 内置 OkHttp) | - | Apache 2.0 |
| 日志 | `logging` | `org.slf4j:slf4j-api` | 2.0.0 | MIT |

**重要说明**:
- **Anthropic Claude API**: 使用官方 `anthropic-java` SDK
- **第三方 OpenAI 格式 API**: 使用官方 `openai-java` SDK，支持自定义 `base-url`
- 两个官方 SDK 都支持自定义 `baseUrl`，可连接银行内部 API Gateway

## 详细分析

### 1. Anthropic Java SDK（官方）

**Maven 坐标**: `com.anthropic:anthropic-java:2.40.1`

**官方支持**:
- Anthropic 官方维护
- 支持 Java 8+
- **支持自定义 base URL**，可用于银行内部 API Gateway
- 同步和异步 API
- 流式响应支持

**银行第三方 API 配置**:
```java
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;

// 方式 1: 通过环境变量配置
// export ANTHROPIC_BASE_URL=https://api.your-bank.com/anthropic
// export ANTHROPIC_API_KEY=your-api-key
AnthropicClient client = AnthropicOkHttpClient.fromEnv();

// 方式 2: 通过 Builder 配置
AnthropicClient client = AnthropicOkHttpClient.builder()
    .baseUrl("https://api.your-bank.com/anthropic")  // 银行内部 API Gateway
    .apiKey(getApiKeyFromVault())                     // 从密钥管理系统获取
    .build();
```

**使用示例**:
```java
import com.anthropic.models.messages.Message;

// 发送请求
MessageCreateParams params = MessageCreateParams.builder()
    .model(Model.CLAUDE_SONNET_4_6)
    .maxTokens(1024)
    .addUserMessage("Hello, Claude")
    .build();

Message message = client.messages().create(params);
System.out.println(message.content().get(0).asText().text());
```

**流式响应**:
```java
// 流式 API
client.messages().createStreaming(params)
    .subscribe(chunk -> {
        System.out.print(chunk.content().get(0).asText().text());
    });
```

**配置文件方式**:
```yaml
# application.yml
anthropic:
  base-url: https://api.your-bank.com/anthropic
  api-key: ${BANK_API_KEY}
```

```properties
# application.properties
anthropic.base-url=https://api.your-bank.com/anthropic
anthropic.api-key=${BANK_API_KEY}
```

### 2. OpenAI Java SDK（官方，支持第三方 API）

**Maven 坐标**: `com.openai:openai-java:4.39.1`

**官方支持**:
- OpenAI 官方维护
- 支持 Java 8+
- **支持自定义 base URL**，可用于第三方 OpenAI 格式 API
- 同步和异步 API
- 流式响应支持

**银行第三方 API 配置**:
```java
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;

// 方式 1: 通过环境变量配置
// export OPENAI_BASE_URL=https://api.your-bank.com/v1
// export OPENAI_API_KEY=your-api-key
OpenAIClient client = OpenAIOkHttpClient.fromEnv();

// 方式 2: 通过 Builder 配置
OpenAIClient client = OpenAIOkHttpClient.builder()
    .baseUrl("https://api.your-bank.com/v1")  // 银行内部 API Gateway
    .apiKey(getApiKeyFromVault())              // 从密钥管理系统获取
    .build();
```

**使用示例**:
```java
import com.openai.models.chat.completions.*;

// 发送请求
ChatCompletionCreateParams params = ChatCompletionCreateParams.builder()
    .model("your-model-name")
    .messages(List.of(
        ChatCompletionUserMessageParam.builder()
            .content("Hello")
            .build()
    ))
    .build();

ChatCompletion completion = client.chat().completions().create(params);
```

**流式响应**:
```java
// 流式 API
client.chat().completions().createStreaming(params)
    .subscribe(chunk -> {
        System.out.print(chunk.choices().get(0).delta().content());
    });
```

**配置文件方式**:
```yaml
# application.yml
openai:
  base-url: https://api.your-bank.com/v1
  api-key: ${BANK_API_KEY}
```

```properties
# application.properties
openai.base-url=https://api.your-bank.com/v1
openai.api-key=${BANK_API_KEY}
```

### 3. MCP Java SDK

**Maven 坐标**: `io.modelcontextprotocol:mcp-java-sdk:0.5.0`

**官方支持**:
- 2025年2月由 Spring 团队发布
- 支持 stdio 和 HTTP/SSE 传输
- 可独立使用（无需 Spring）
- 支持 Reactor 响应式 API

**传输方式**:

| 传输 | 说明 | 适用场景 |
|------|------|----------|
| stdio | 标准输入输出 | 本地 MCP 服务器 |
| HTTP/SSE | Server-Sent Events | 远程 MCP 服务器 |
| WebSocket | 双向通信 | 实时交互 |

**使用示例**:
```java
import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.transport.StdioTransport;
import io.modelcontextprotocol.spec.McpSchema.Tool;

// 创建客户端
McpClient client = McpClient.builder()
    .transport(new StdioTransport("mcp-server-filesystem", List.of("--root", "/workspace")))
    .build();

// 连接并获取工具列表
client.connect();
List<Tool> tools = client.listTools();

// 调用工具
var result = client.callTool("read_file", Map.of("path", "README.md"));
```

### 4. Token 计数 (jtokkit)

**Maven 坐标**: `com.knuddelsgmbh:jtokkit:1.0.0`

**支持的编码**:
| 编码名 | 模型 |
|--------|------|
| `cl100k_base` | GPT-4, Claude, GPT-3.5-turbo |
| `p50k_base` | GPT-3 (davinci) |
| `r50k_base` | GPT-3 (ada, babbage, curie) |

**注意**: Claude 使用 `cl100k_base`，与 GPT-4 相同。

**使用示例**:
```java
import com.knuddelsgmbh.jtokkit.Encodings;
import com.knuddelsgmbh.jtokkit.api.Encoding;
import com.knuddelsgmbh.jtokkit.api.EncodingType;

// 获取编码器
Encoding encoding = Encodings.newDefaultEncodingRegistry()
    .getEncoding(EncodingType.CL100K_BASE);

// 计算 token 数量
int tokenCount = encoding.encode("Hello, world!").size();

// 解码 token
String decoded = encoding.decode(List.of(9906, 11, 1917, 0));
```

**与 tiktoken 对比**:
| 特性 | tiktoken (Python) | jtokkit (Java) |
|------|-------------------|----------------|
| cl100k_base | ✅ | ✅ |
| o200k_base | ✅ | ❌ (不需要，Claude 用 cl100k_base) |
| 性能 | 高 | 中等 |
| 精确度 | 参考 | 可能有细微差异 |

### 5. JSON 处理 (Jackson)

**Maven 坐标**: `com.fasterxml.jackson.core:jackson-databind:2.17.0`

**为什么选择 Jackson**:
- Java 生态系统标准 JSON 库
- Spring Boot 默认 JSON 处理器
- 高性能，成熟稳定
- 支持注解自定义序列化

**使用示例**:
```java
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.annotation.JsonProperty;

public record Message(
    String role,
    String content,
    @JsonProperty(defaultValue = "{}")
    Map<String, Object> metadata
) {}

// 序列化
ObjectMapper mapper = new ObjectMapper();
String json = mapper.writeValueAsString(new Message("user", "Hello", Map.of()));

// 反序列化
Message msg = mapper.readValue(json, Message.class);
```

### 6. HTTP 客户端 (OkHttp)

**Maven 坐标**: `com.squareup.okhttp3:okhttp:4.12.0`

**为什么选择 OkHttp**:
- 高性能，连接池管理
- 支持 HTTP/2
- 拦截器机制方便添加日志/追踪
- Square 公司维护，成熟稳定

**使用示例**:
```java
import okhttp3.*;

OkHttpClient client = new OkHttpClient.Builder()
    .connectTimeout(30, TimeUnit.SECONDS)
    .addInterceptor(new LoggingInterceptor())
    .build();

Request request = new Request.Builder()
    .url("https://api.anthropic.com/v1/messages")
    .addHeader("x-api-key", apiKey)
    .post(RequestBody.create(json, MediaType.parse("application/json")))
    .build();

try (Response response = client.newCall(request).execute()) {
    String body = response.body().string();
}
```

## Gradle 配置

### 根项目 build.gradle.kts

```kotlin
plugins {
    kotlin("jvm") version "1.9.0" apply false
}

subprojects {
    apply(plugin = "java-library")
    apply(plugin = "maven-publish")
    
    java {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    
    repositories {
        mavenCentral()
    }
}
```

### harness-sdk-core/build.gradle.kts

```kotlin
dependencies {
    // Jackson
    api("com.fasterxml.jackson.core:jackson-databind:2.17.0")
    
    // SLF4J
    api("org.slf4j:slf4j-api:2.0.0")
    
    // 测试
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testImplementation("org.mockito:mockito-core:5.10.0")
}
```

### harness-sdk-llm/build.gradle.kts

```kotlin
dependencies {
    api(project(":harness-sdk-core"))

    // Anthropic Java SDK (官方，支持自定义 base URL)
    api("com.anthropic:anthropic-java:2.40.1")

    // OpenAI Java SDK (官方，支持自定义 base URL，用于第三方 API)
    api("com.openai:openai-java:4.39.1")
}
```

### harness-sdk-mcp/build.gradle.kts

```kotlin
dependencies {
    api(project(":harness-sdk-core"))
    
    // MCP SDK
    api("io.modelcontextprotocol:mcp-java-sdk:0.5.0")
}
```

### harness-sdk-all/build.gradle.kts (Shadow JAR)

```kotlin
plugins {
    id("com.github.johnrengelman.shadow") version "8.1.1"
}

dependencies {
    api(project(":harness-sdk-core"))
    api(project(":harness-sdk-anthropic"))
    api(project(":harness-sdk-mcp"))
    api(project(":harness-sdk-tools"))
    api(project(":harness-sdk-memory"))
    api(project(":harness-sdk-skills"))
}

tasks.shadowJar {
    archiveClassifier.set("")
    mergeServiceFiles()
    
    // 排除签名文件
    exclude("META-INF/*.SF")
    exclude("META-INF/*.DSA")
    exclude("META-INF/*.RSA")
}
```

## 依赖大小估算

| 模块 | 大小（估算） |
|------|-------------|
| anthropic-java | ~2 MB |
| openai-java | ~2 MB |
| mcp-java-sdk | ~1 MB |
| jtokkit | ~500 KB |
| jackson-databind | ~1.5 MB |
| 其他依赖 | ~1 MB |
| **harness-sdk-all.jar** | **~10 MB** |

## 许可证兼容性

所有依赖均使用宽松许可证：

| 许可证 | 商业使用 | 修改 | 分发 |
|--------|----------|------|------|
| MIT | ✅ | ✅ | ✅ |
| Apache 2.0 | ✅ | ✅ | ✅ |

**银行合规**: 所有依赖都允许在银行商业环境中使用。

## 风险评估

### 依赖风险矩阵

| 依赖 | 风险等级 | 说明 |
|------|----------|------|
| anthropic-java | 低 | Anthropic 官方维护，支持自定义 base URL |
| openai-java | 低 | OpenAI 官方维护，支持自定义 base URL |
| mcp-java-sdk | 中 | 2025年新发布，API 可能变化 |
| jtokkit | 低 | 社区成熟方案 |
| jackson | 低 | Java 标准库 |

### 缓解措施

1. **MCP SDK 不稳定风险**:
   - 封装一层适配器，隔离 API 变化
   - 定期跟进官方更新

2. **jtokkit 精度差异**:
   - 编写测试对比 Python tiktoken 结果
   - 可选：使用 HuggingFace tokenizer.json

3. **第三方 API 兼容性**:
   - openai-java 支持自定义 base URL
   - 可配置的请求头（银行 API Gateway 可能需要额外认证）
   - 完善的错误处理和重试机制

## 离线部署支持

### 依赖预下载

```bash
# 下载所有依赖到本地目录
./gradlew dependencies --write-locks

# 构建离线部署包
./gradlew shadowJar
```

### 交付内容

```
harness-sdk-java-1.0.0.zip
├── jars/
│   ├── harness-sdk-all-1.0.0.jar    # 聚合 JAR（推荐）
│   ├── harness-sdk-core-1.0.0.jar   # 核心模块
│   ├── harness-sdk-anthropic-1.0.0.jar
│   ├── harness-sdk-mcp-1.0.0.jar
│   ├── harness-sdk-tools-1.0.0.jar
│   ├── harness-sdk-memory-1.0.0.jar
│   └── harness-sdk-skills-1.0.0.jar
├── docs/
│   ├── README.md
│   ├── API-reference.md
│   └── integration-guide.md
├── lib/                              # 第三方依赖（可选）
│   └── *.jar
├── metadata.json
├── checksums.sha256
└── LICENSE
```

## 下一步

- [03-agent-loop.md](./03-agent-loop.md) - 了解 Agent Loop 的 Java 实现
- [06-mcp-integration.md](./06-mcp-integration.md) - 详细了解 MCP 集成
- [12-deployment.md](./12-deployment.md) - 了解 JAR 包部署详情
