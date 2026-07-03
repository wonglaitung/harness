# 12 - Connectors 外部系统集成

> **状态**: ✅ 已实现
> **设计文档**: [phase4-connectors.md](../design/phase4-connectors.md)

## 概述

Connectors 模块让 Agent 能够与外部系统**双向交互**：接收外部事件并输出结果。

**核心特性**：
- 标准化事件格式 - 统一的 `ConnectorEvent`
- 双向通信 - 接收事件 + 输出结果
- 路由元数据 - 支持结果"原路返回"
- 内置集成 - Webhook, Slack, GitHub

## 核心 API

### ConnectorManager

```python
from harness import AgentHarness
from harness.connectors import (
    ConnectorManager,
    SlackConnector,
    GitHubConnector,
    WebhookConnector,
    OutputChannel,
    SlackConfig,
    GitHubConfig,
    WebhookConfig,
)
from harness.triggers import TriggerManager

agent = AgentHarness(model="claude-sonnet-4-6")
trigger_manager = TriggerManager(agent)

# 创建 ConnectorManager
manager = ConnectorManager(trigger_manager)

# 注册 Slack 连接器
slack = SlackConnector(config=SlackConfig(
    bot_token="xoxb-...",
    app_token="xapp-...",
))
manager.register_connector(slack)

# 注册 GitHub 连接器
github = GitHubConnector(config=GitHubConfig(
    app_id="123456",
    private_key="-----BEGIN RSA PRIVATE KEY-----\n...",
))
manager.register_connector(github)

# 注册 Webhook 连接器
webhook = WebhookConnector(config=WebhookConfig(
    endpoint="/webhook/github",
    secret="whsec_...",
))
manager.register_connector(webhook)

# 注册输出通道
manager.register_output_channel(OutputChannel(
    type="slack",
    name="alerts",
    config={"channel": "#alerts"},
))

# 启动所有连接器
await manager.start()
```

## 连接器类型

### 1. WebhookConnector

接收 HTTP POST 请求作为触发源。

```python
from harness.connectors import WebhookConnector, WebhookConfig

webhook = WebhookConnector(config=WebhookConfig(
    endpoint="/webhook/github",     # URL 路径
    secret="whsec_xxx",              # HMAC 签名验证（可选）
    rate_limit=100,                  # 每分钟请求限制
))

# 注册到 FastAPI（可选）
webhook.set_app(fastapi_app)
```

### 2. SlackConnector

通过 Slack Socket Mode 接收消息和命令。

```python
from harness.connectors import SlackConnector, SlackConfig

slack = SlackConnector(config=SlackConfig(
    bot_token="xoxb-...",            # Bot User OAuth Token
    app_token="xapp-...",            # App-Level Token
    command_prefix="/harness",       # 命令前缀
))

# 用户在 Slack 发送 "/harness analyze this code"
# Agent 自动执行并回复到原线程
```

### 3. GitHubConnector

接收 GitHub Webhook 事件（PR, Issue, Push 等）。

```python
from harness.connectors import GitHubConnector, GitHubConfig

github = GitHubConnector(config=GitHubConfig(
    app_id="123456",                           # GitHub App ID
    private_key="-----BEGIN RSA PRIVATE KEY...",  # 私钥
    webhook_secret="whsec_...",                # Webhook 密钥
    events=["push", "pull_request"],           # 订阅的事件
))

# PR opened → Agent 自动 review 并评论
# Issue created → Agent 自动分析和回复
```

## 路由元数据（RoutingKeys）

用于实现结果的"原路返回"功能。

```python
from harness.connectors import RoutingKeys

# Slack: 回复到原线程
event = ConnectorEvent(
    ...,
    routing_metadata={
        RoutingKeys.SLACK_THREAD_TS: "17123456.0001",
        RoutingKeys.SLACK_CHANNEL_ID: "C123456",
    }
)
# 结果会回复到该线程

# GitHub: 评论到原 PR
event = ConnectorEvent(
    ...,
    routing_metadata={
        RoutingKeys.GITHUB_PR_NUMBER: 42,
        RoutingKeys.GITHUB_REPO: "owner/repo",
    }
)
# 结果会评论到该 PR
```

### RoutingKeys 常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `SLACK_THREAD_TS` | "slack_thread_ts" | Slack 线程时间戳 |
| `SLACK_CHANNEL_ID` | "slack_channel_id" | Slack 频道 ID |
| `GITHUB_PR_NUMBER` | "github_pr_number" | GitHub PR 编号 |
| `GITHUB_ISSUE_NUMBER` | "github_issue_number" | GitHub Issue 编号 |
| `GITHUB_REPO` | "github_repo" | GitHub 仓库名 (owner/repo) |
| `WEBHOOK_REQUEST_ID` | "webhook_request_id" | Webhook 请求追踪 ID |

## 输出通道

### 注册输出通道

```python
# Slack 输出
manager.register_output_channel(OutputChannel(
    type="slack",
    name="alerts",
    config={"channel": "#alerts"},
))

# Webhook 输出
manager.register_output_channel(OutputChannel(
    type="webhook",
    name="external_api",
    config={
        "url": "https://example.com/webhook",
        "headers": {"Authorization": "Bearer token"},
    },
))

# 文件输出
manager.register_output_channel(OutputChannel(
    type="file",
    name="logs",
    config={"path": "/var/log/harness/output.txt"},
))
```

### 路由输出

```python
# 将结果发送到指定通道
results = await manager.route_output(
    result=goal_result,
    channels=["alerts", "logs"],
    routing_metadata={
        RoutingKeys.SLACK_THREAD_TS: "17123456.0001",
    },
)
```

## 完整示例

### Slack Bot 集成

```python
import asyncio
from harness import AgentHarness
from harness.connectors import (
    ConnectorManager,
    SlackConnector,
    OutputChannel,
    SlackConfig,
)
from harness.triggers import TriggerManager

async def main():
    agent = AgentHarness(model="claude-sonnet-4-6")
    trigger_manager = TriggerManager(agent)
    manager = ConnectorManager(trigger_manager)

    # 配置 Slack
    slack = SlackConnector(config=SlackConfig(
        bot_token="xoxb-your-bot-token",
        app_token="xapp-your-app-token",
        command_prefix="/agent",
    ))
    manager.register_connector(slack)

    # 配置输出通道
    manager.register_output_channel(OutputChannel(
        type="slack",
        name="default",
        config={"channel": "#general"},
    ))

    # 启动
    await manager.start()
    print("Slack connector started. Send '/agent help' in Slack.")

    # 保持运行
    try:
        await asyncio.sleep(3600)  # 运行 1 小时
    finally:
        await manager.stop()

asyncio.run(main())
```

### GitHub PR 自动审查

```python
from harness.connectors import (
    GitHubConnector,
    GitHubConfig,
)

github = GitHubConnector(config=GitHubConfig(
    app_id="123456",
    private_key=open("private-key.pem").read(),
    webhook_secret="your-webhook-secret",
    events=["pull_request.opened", "pull_request.synchronize"],
))

# 当 PR 被打开时，Agent 会自动：
# 1. 获取 PR diff
# 2. 分析代码变更
# 3. 在 PR 中添加审查评论
```

## 数据流

```
外部事件 (Slack 消息 / GitHub PR / Webhook)
    │
    ▼
Connector 接收并转换为 ConnectorEvent
    │
    ▼
ConnectorManager.enqueue_event() → TriggerManager
    │
    ▼
TriggerManager 创建 GoalConfig
    │
    ▼
GoalLoop 执行 → GoalResult
    │
    ▼
ConnectorManager.route_output()
    │
    ▼
输出到原来源（通过 routing_metadata）
```

## Java SDK 示例

Java SDK 提供完整的 Connector 实现，支持 GitHub、Slack 和 Webhook 集成。

### GitHubConnector

```java
import com.harness.connectors.GitHubConnector;
import com.harness.connectors.GitHubConfig;
import com.harness.connectors.ConnectorManager;

// 配置 GitHub App
GitHubConfig config = new GitHubConfig.Builder()
    .appId("123456")
    .privateKey("-----BEGIN RSA PRIVATE KEY-----\n...")
    .webhookSecret("whsec_...")
    .build();

// 创建连接器
GitHubConnector connector = new GitHubConnector(config);

// 注册到管理器
ConnectorManager manager = new ConnectorManager(triggerManager);
manager.registerConnector(connector);

// 启动
manager.startAll().join();
```

### GitHubAPIClient

Java SDK 提供独立的 GitHub API 客户端，支持 GitHub App JWT 认证：

```java
import com.harness.connectors.GitHubAPIClient;

// 创建 API 客户端
GitHubAPIClient client = new GitHubAPIClient("123456", privateKeyPem);

// 创建 Issue/PR 评论
client.createIssueComment("owner/repo", 42, "评论内容")
    .thenAccept(success -> {
        if (success) {
            System.out.println("评论创建成功");
        }
    });

// 获取 PR 详情
client.getPr("owner/repo", 42)
    .thenAccept(pr -> {
        System.out.println("PR 标题: " + pr.get("title"));
    });

// 创建 PR Review
client.createPrReview("owner/repo", 42, "APPROVE", "LGTM!")
    .thenAccept(success -> System.out.println("Review 创建成功"));

// 获取 Installation Token（自动缓存）
client.getInstallationToken(12345L)
    .thenAccept(token -> System.out.println("Token: " + token));
```

**认证流程**：
1. 使用私钥生成 JWT（有效期 10 分钟）
2. 使用 JWT 获取 Installation Token
3. 使用 Installation Token 调用 GitHub API

**支持的 API**：
| 方法 | 说明 |
|------|------|
| `createIssueComment()` | 创建 Issue/PR 评论 |
| `getPr()` | 获取 PR 详情 |
| `getIssue()` | 获取 Issue 详情 |
| `createPrReview()` | 创建 PR Review |
| `getInstallationToken()` | 获取 Installation Token |

### SlackConnector

```java
import com.harness.connectors.SlackConnector;
import com.harness.connectors.SlackConfig;

SlackConfig config = new SlackConfig.Builder()
    .botToken("xoxb-...")
    .appToken("xapp-...")
    .build();

SlackConnector connector = new SlackConnector(config);
manager.registerConnector(connector);

// 发送消息
connector.sendMessage("C123456", "Hello from Harness!");

// 回复到线程
connector.replyToThread("C123456", "17123456.0001", "回复内容");
```

### SlackAPIClient

Java SDK 提供独立的 Slack API 客户端：

```java
import com.harness.connectors.SlackAPIClient;

// 创建 API 客户端
SlackAPIClient client = new SlackAPIClient(botToken, appToken);

// 发送消息到频道
client.postMessage("C123456", "Hello!", null, null)
    .thenAccept(success -> {
        if (success) {
            System.out.println("消息发送成功");
        }
    });

// 发送 Block Kit 消息
List<Map<String, Object>> blocks = List.of(
    Map.of("type", "section", "text", Map.of("type", "plain_text", "text", "Hello"))
);
client.postMessage("C123456", "Fallback text", blocks, null);

// 回复到线程
client.postMessage("C123456", "Thread reply", null, "17123456.0001");

// 发送 Ephemeral 消息（仅特定用户可见）
client.postEphemeral("C123456", "U123456", "私密消息", null);

// 添加 Reaction
client.addReaction("C123456", "17123456.0001", "thumbsup");

// 获取用户信息
client.getUserInfo("U123456")
    .thenAccept(user -> System.out.println("用户名: " + user.get("name")));

// 验证认证
client.authTest()
    .thenAccept(success -> System.out.println("认证有效: " + success));
```

**支持的 API**：
| 方法 | 说明 |
|------|------|
| `postMessage()` | 发送消息（支持 Block Kit） |
| `postEphemeral()` | 发送仅特定用户可见的消息 |
| `addReaction()` | 添加 Reaction |
| `getUserInfo()` | 获取用户信息 |
| `authTest()` | 验证认证是否有效 |

### WebhookConnector

```java
import com.harness.connectors.WebhookConnector;

WebhookConnector webhook = new WebhookConnector();
manager.registerConnector(webhook);

// 设置 HTTP 端点
// POST /webhook/{connector_id}
// 接收 JSON 并转换为 ConnectorEvent
```

### HttpClient（内部使用）

连接器内部使用统一的 HTTP 客户端：

```java
import com.harness.connectors.HttpClient;

HttpClient client = new HttpClient();

// GET 请求
HttpResponse<String> response = client.get(url, headers);

// POST 请求
Map<String, Object> body = Map.of("key", "value");
HttpResponse<String> response = client.post(url, body, headers);

// 解析 JSON 响应
Map<String, Object> data = client.parseJson(response.body());
```

**特性**：
- 自动重试（3 次）
- 超时控制（默认 30 秒）
- JSON 序列化/反序列化

### RoutingKeys

```java
import com.harness.connectors.RoutingKeys;
import com.harness.connectors.ConnectorEvent;
import java.util.Map;

// 创建带路由信息的事件
ConnectorEvent event = new ConnectorEvent(
    ConnectorType.SLACK,
    "message",
    Map.of("text", "Hello"),
    Map.of(
        RoutingKeys.SLACK_CHANNEL_ID, "C123456",
        RoutingKeys.SLACK_THREAD_TS, "17123456.0001"
    ),
    "slack-connector"
);

// 结果会根据 routing_metadata 返回到原线程
```

### ConnectorState 枚举

```java
public enum ConnectorState {
    IDLE,       // 空闲
    RUNNING,    // 运行中
    STOPPED,    // 已停止
    ERROR       // 错误
}
```

## 下一步

- [10-loop-engineering.md](./10-loop-engineering.md) - Loop Engineering 总览
- [11-worktrees.md](./11-worktrees.md) - 并行隔离执行
- [13-orchestrator.md](./13-orchestrator.md) - 工作流编排
