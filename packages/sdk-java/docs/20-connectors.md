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

```java
import com.harness.loop.GoalLoop;
import com.harness.connectors.ConnectorManager;
import com.harness.connectors.SlackConnector;
import com.harness.connectors.SlackConfig;
import com.harness.connectors.GitHubConnector;
import com.harness.connectors.GitHubConfig;
import com.harness.connectors.WebhookConnector;
import com.harness.connectors.OutputChannel;
import com.harness.triggers.TriggerManager;

GoalLoop.AgentRunner agent = ...;
TriggerManager triggerManager = new TriggerManager(agent);

// 创建 ConnectorManager
ConnectorManager manager = new ConnectorManager();

// 注册 Slack 连接器
SlackConnector slack = new SlackConnector(
    new SlackConfig.Builder()
        .botToken("xoxb-...")
        .appToken("xapp-...")
        .build()
);
manager.registerConnector(slack);

// 注册 GitHub 连接器
GitHubConnector github = new GitHubConnector(
    new GitHubConfig.Builder()
        .appId("123456")
        .privateKey("-----BEGIN RSA PRIVATE KEY-----\n...")
        .build()
);
manager.registerConnector(github);

// 注册 Webhook 连接器
WebhookConnector webhook = new WebhookConnector()
    .withEndpoint("/webhook/github")
    .withSecret("whsec_...");
manager.registerConnector(webhook);

// 注册输出通道
manager.registerOutputChannel(OutputChannel.builder()
    .type("slack")
    .name("alerts")
    .addConfig("channel", "#alerts")
    .build());

// 启动所有连接器
manager.start().join();
```

## 连接器类型

### 1. WebhookConnector

接收 HTTP POST 请求作为触发源。

```java
import com.harness.connectors.WebhookConnector;

WebhookConnector webhook = new WebhookConnector()
    .withEndpoint("/webhook/github")     // URL 路径
    .withSecret("whsec_xxx")             // HMAC 签名验证（可选）
    .withRateLimit(100);                 // 每分钟请求限制

// 注册到 ConnectorManager
ConnectorManager manager = new ConnectorManager();
manager.registerConnector(webhook);
```

### 2. SlackConnector

通过 Slack Socket Mode 接收消息和命令。

```java
import com.harness.connectors.SlackConnector;
import com.harness.connectors.SlackConfig;

SlackConnector slack = new SlackConnector(
    new SlackConfig.Builder()
        .botToken("xoxb-...")            // Bot User OAuth Token
        .appToken("xapp-...")            // App-Level Token
        .build()
);

// 用户在 Slack 发送 "/harness analyze this code"
// Agent 自动执行并回复到原线程
```

### 3. GitHubConnector

接收 GitHub Webhook 事件（PR, Issue, Push 等）。

```java
import com.harness.connectors.GitHubConnector;
import com.harness.connectors.GitHubConfig;

GitHubConnector github = new GitHubConnector(
    new GitHubConfig.Builder()
        .appId("123456")                           // GitHub App ID
        .privateKey("-----BEGIN RSA PRIVATE KEY...") // 私钥
        .webhookSecret("whsec_...")                 // Webhook 密钥
        .build()
);

// PR opened → Agent 自动 review 并评论
// Issue created → Agent 自动分析和回复
```

## 路由元数据（RoutingKeys）

用于实现结果的"原路返回"功能。

```java
import com.harness.connectors.RoutingKeys;
import com.harness.connectors.ConnectorEvent;
import java.util.Map;

// Slack: 回复到原线程
ConnectorEvent slackEvent = new ConnectorEvent(
    ...,
    Map.of(
        RoutingKeys.SLACK_THREAD_TS, "17123456.0001",
        RoutingKeys.SLACK_CHANNEL_ID, "C123456"
    )
);
// 结果会回复到该线程

// GitHub: 评论到原 PR
ConnectorEvent githubEvent = new ConnectorEvent(
    ...,
    Map.of(
        RoutingKeys.GITHUB_PR_NUMBER, 42,
        RoutingKeys.GITHUB_REPO, "owner/repo"
    )
);
// 结果会评论到该 PR
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

```java
import com.harness.connectors.OutputChannel;
import java.util.Map;

// Slack 输出
manager.registerOutputChannel(OutputChannel.builder()
    .type("slack")
    .name("alerts")
    .addConfig("channel", "#alerts")
    .build());

// Webhook 输出
manager.registerOutputChannel(OutputChannel.builder()
    .type("webhook")
    .name("external_api")
    .addConfig("url", "https://example.com/webhook")
    .addConfig("headers", Map.of("Authorization", "Bearer token"))
    .build());

// 文件输出
manager.registerOutputChannel(OutputChannel.builder()
    .type("file")
    .name("logs")
    .addConfig("path", "/var/log/harness/output.txt")
    .build());
```

### 路由输出

```java
import com.harness.connectors.RoutingKeys;
import java.util.Map;
import java.util.List;
import java.util.concurrent.CompletableFuture;

// 将结果发送到指定通道
CompletableFuture<List<OutputResult>> results = manager.routeOutput(
    goalResult,
    List.of("alerts", "logs"),
    Map.of(RoutingKeys.SLACK_THREAD_TS, "17123456.0001")
);
```

## 完整示例

### Slack Bot 集成

```java
import com.harness.loop.GoalLoop;
import com.harness.connectors.ConnectorManager;
import com.harness.connectors.SlackConnector;
import com.harness.connectors.SlackConfig;
import com.harness.connectors.OutputChannel;
import java.util.concurrent.CompletableFuture;

public class SlackBotExample {
    public static void main(String[] args) throws Exception {
        GoalLoop.AgentRunner agent = ...;
        ConnectorManager manager = new ConnectorManager();

        // 配置 Slack
        SlackConnector slack = new SlackConnector(
            new SlackConfig.Builder()
                .botToken("xoxb-your-bot-token")
                .appToken("xapp-your-app-token")
                .build()
        );
        manager.registerConnector(slack);

        // 配置输出通道
        manager.registerOutputChannel(OutputChannel.builder()
            .type("slack")
            .name("default")
            .addConfig("channel", "#general")
            .build());

        // 启动
        manager.start().join();
        System.out.println("Slack connector started. Send '/agent help' in Slack.");

        // 保持运行
        try {
            Thread.sleep(3600_000);  // 运行 1 小时
        } finally {
            manager.stop().join();
        }
    }
}
```

### GitHub PR 自动审查

```java
import com.harness.connectors.GitHubConnector;
import com.harness.connectors.GitHubConfig;
import java.nio.file.Files;

GitHubConnector github = new GitHubConnector(
    new GitHubConfig.Builder()
        .appId("123456")
        .privateKey(Files.readString(Path.of("private-key.pem")))
        .webhookSecret("your-webhook-secret")
        .build()
);

// 当 PR 被打开时，Agent 会自动：
// 1. 获取 PR diff
// 2. 分析代码变更
// 3. 在 PR 中添加审查评论
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

## 下一步

- [10-loop-engineering.md](./18-loop-engineering.md) - Loop Engineering 总览
- [11-worktrees.md](./19-worktrees.md) - 并行隔离执行
- [13-orchestrator.md](./21-orchestrator.md) - 工作流编排
