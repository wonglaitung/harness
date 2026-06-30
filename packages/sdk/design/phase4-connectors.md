# Phase 4: Connectors 设计文档

> **状态**: 设计阶段
> **创建时间**: 2026-06-30
> **依赖**: Phase 1 (Goal), Phase 2 (Automations)

---

## 背景

Phase 1-3 已实现 Agent 的自主执行能力：
- Phase 1: Goal Verifier - 目标驱动执行
- Phase 2: Automations - 定时触发/调度
- Phase 3: Worktrees - 多 Agent 并行隔离

Phase 4 Connectors 的核心需求是：**让 Agent 能够与外部系统双向交互，接收外部事件并输出结果**。

**设计目标**：
1. 标准化的外部系统集成接口
2. 双向通信：接收事件 + 输出结果
3. 可插拔的 Connector 架构
4. 内置常用集成（Webhook, Slack, GitHub）

---

## 架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Connector System                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    ConnectorManager                        │  │
│  │  - register(connector)                                     │  │
│  │  - start() / stop()                                        │  │
│  │  - Event routing → TriggerManager                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│         ┌─────────────────┼─────────────────┐                   │
│         ▼                 ▼                 ▼                   │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │  Webhook    │   │   Slack     │   │   GitHub    │          │
│  │  Connector  │   │  Connector  │   │  Connector  │          │
│  └─────────────┘   └─────────────┘   └─────────────┘          │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    OutputRouter                            │  │
│  │  - route(result, channels)                                 │  │
│  │  - Slack / Email / Webhook / File                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Phase 2: TriggerManager + GoalLoop                  │
└─────────────────────────────────────────────────────────────────┘
```

### 数据流

```
外部事件 (Webhook/Slack/GitHub)
    │
    ▼
Connector 接收并标准化为 ConnectorEvent
    │
    ▼
ConnectorManager 路由到 TriggerManager
    │
    ▼
TriggerManager 创建 TriggerEvent → GoalConfig
    │
    ▼
GoalLoop 执行 → GoalResult
    │
    ▼
OutputRouter 分发到指定 Channel
    │
    ▼
外部系统 (Slack/Email/Webhook)
```

---

## 核心类型定义

```python
# connectors/types.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class ConnectorType(Enum):
    """Connector 类型."""
    WEBHOOK = "webhook"       # HTTP webhook
    SLACK = "slack"           # Slack App
    GITHUB = "github"         # GitHub App
    DISCORD = "discord"       # Discord Bot
    EMAIL = "email"           # Email (IMAP/SMTP)
    CUSTOM = "custom"         # 自定义


class ConnectorState(Enum):
    """Connector 状态."""
    IDLE = "idle"           # 未启动
    RUNNING = "running"     # 运行中
    STOPPED = "stopped"     # 已停止
    ERROR = "error"         # 错误状态


@dataclass
class ConnectorEvent:
    """
    标准化的外部事件.

    所有 Connector 必须将外部事件转换为此格式。

    Attributes:
        routing_metadata: 路由元数据，用于结果原路返回
            例如：{"slack_thread_ts": "17123456.0001", "github_pr_number": 42}
            这些元数据会随事件流转到 GoalResult，最终由 OutputRouter 使用
    """
    connector_type: ConnectorType
    connector_id: str
    event_type: str                    # 事件类型（如 "pr_opened", "message"）
    source: str                        # 来源标识（如用户名、仓库名）
    timestamp: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)

    # 可选：认证信息
    user_id: str | None = None
    channel_id: str | None = None

    # 路由元数据：用于结果"原路返回"
    # 例如：Slack thread_ts, GitHub PR number, Issue number 等
    routing_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_command(self) -> bool:
        """是否是命令事件."""
        return self.event_type.endswith(".command")


@dataclass
class OutputChannel:
    """
    输出通道配置.
    
    定义如何将结果发送到外部系统。
    """
    type: str                           # "slack" | "email" | "webhook" | "file"
    name: str                           # 通道名称
    
    # 通道特定配置
    config: dict[str, Any] = field(default_factory=dict)
    
    # 示例：
    # Slack: {"channel": "#alerts", "webhook_url": "..."}
    # Email: {"to": ["user@example.com"], "subject_prefix": "[Harness]"}
    # Webhook: {"url": "https://...", "headers": {}}


@dataclass
class OutputResult:
    """输出结果."""
    channel_name: str
    success: bool
    message: str | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
```

---

## Connector 基类

```python
# connectors/base.py

from collections.abc import Coroutine
from typing import Any

# 异步事件回调类型
EventCallback = Callable[[ConnectorEvent], Coroutine[Any, Any, None]]


class Connector(ABC):
    """
    Connector 抽象基类.

    所有外部系统集成必须继承此类。

    重要：事件回调必须是异步函数，以避免阻塞事件循环。
    """

    connector_type: ConnectorType
    id: str = ""
    state: ConnectorState = ConnectorState.IDLE

    @abstractmethod
    async def start(
        self,
        event_callback: EventCallback,
    ) -> None:
        """
        启动 Connector.

        Args:
            event_callback: 异步事件回调函数，用于将事件发送到 ConnectorManager

        注意：
            回调必须是异步函数（async def），不能是同步函数。
            这确保了在异步事件循环（如 Slack Socket Mode）中不会阻塞。
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止 Connector."""
        pass
    
    @abstractmethod
    def create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "",
    ) -> ConnectorEvent:
        """创建标准化事件."""
        pass
    
    def is_running(self) -> bool:
        """检查是否运行中."""
        return self.state == ConnectorState.RUNNING
    
    async def health_check(self) -> bool:
        """健康检查."""
        return self.is_running()
```

---

## 内置 Connectors

### 1. WebhookConnector

```python
# connectors/webhook.py

from fastapi import FastAPI, Request, Response
import hmac
import hashlib

@dataclass
class WebhookConfig:
    """Webhook 配置."""
    endpoint: str                    # URL 路径（如 "/webhook/github"）
    secret: str | None = None        # 验证签名
    allowed_ips: list[str] = field(default_factory=list)
    rate_limit: int = 100            # 每分钟限制


class WebhookConnector(Connector):
    """
    HTTP Webhook Connector.
    
    支持任意 HTTP POST 请求作为触发源。
    """
    
    connector_type = ConnectorType.WEBHOOK
    
    def __init__(
        self,
        config: WebhookConfig,
        connector_id: str = "",
    ):
        self.config = config
        self.id = connector_id or f"webhook_{uuid.uuid4().hex[:8]}"
        self._callback: Callable[[ConnectorEvent], None] | None = None
        self._app: FastAPI | None = None
    
    async def start(
        self,
        event_callback: Callable[[ConnectorEvent], None],
    ) -> None:
        """注册 webhook endpoint."""
        self._callback = event_callback
        self.state = ConnectorState.RUNNING
        
        # 如果提供了 FastAPI app，注册路由
        if self._app:
            @self._app.post(self.config.endpoint)
            async def handle_webhook(request: Request):
                return await self._handle_request(request)
    
    async def _handle_request(self, request: Request) -> Response:
        """处理 webhook 请求."""
        # 验证签名
        if self.config.secret:
            body = await request.body()
            signature = request.headers.get("X-Signature", "")
            expected = hmac.new(
                self.config.secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return Response(status_code=401, content="Invalid signature")
        
        # 解析 payload
        try:
            payload = await request.json()
        except Exception:
            return Response(status_code=400, content="Invalid JSON")
        
        # 创建事件
        event = self.create_event(
            event_type="webhook.received",
            payload=payload,
            source=request.headers.get("X-Forwarded-For", "unknown"),
        )
        
        # 回调
        if self._callback:
            self._callback(event)
        
        return Response(status_code=200, content="OK")
    
    def create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "",
    ) -> ConnectorEvent:
        return ConnectorEvent(
            connector_type=self.connector_type,
            connector_id=self.id,
            event_type=event_type,
            source=source,
            payload=payload,
        )
    
    async def stop(self) -> None:
        """停止 webhook."""
        self.state = ConnectorState.STOPPED
        self._callback = None


# =============================================================================
# 使用示例
# =============================================================================

# 方式 1: 注入现有 FastAPI 应用（推荐）
from fastapi import FastAPI

app = FastAPI()
webhook = WebhookConnector(
    config=WebhookConfig(
        endpoint="/webhook/github",
        secret="whsec_...",
    )
)
webhook._app = app  # 注入应用
await webhook.start(callback)

# 方式 2: 独立使用，手动处理请求
webhook = WebhookConnector(
    config=WebhookConfig(
        endpoint="/webhook/custom",
        secret="whsec_...",
    )
)
await webhook.start(callback)  # 不注入 _app

# 在你自己的路由中调用:
# @app.post("/webhook/custom")
# async def custom_webhook(request: Request):
#     return await webhook._handle_request(request)

# 方式 3: 与 ConnectorManager 配合使用
from harness.connectors import ConnectorManager

manager = ConnectorManager(trigger_manager)
webhook = WebhookConnector(
    config=WebhookConfig(
        endpoint="/webhook/github",
        secret="whsec_...",
    )
)
webhook._app = existing_fastapi_app  # 可选
manager.register_connector(webhook)
await manager.start()
```

### 2. SlackConnector

```python
# connectors/slack.py

@dataclass
class SlackConfig:
    """Slack 配置."""
    bot_token: str                   # xoxb-...
    app_token: str | None = None     # xapp-... (Socket Mode)
    signing_secret: str | None = None
    
    # 命令触发词
    command_prefix: str = "/harness"
    
    # 允许的频道
    allowed_channels: list[str] = field(default_factory=list)


class SlackConnector(Connector):
    """
    Slack Connector.
    
    功能：
    - 接收 Slack 命令和消息
    - 发送消息到频道
    - 支持 Slash Commands 和 Events API
    """
    
    connector_type = ConnectorType.SLACK
    
    def __init__(
        self,
        config: SlackConfig,
        connector_id: str = "",
    ):
        self.config = config
        self.id = connector_id or f"slack_{uuid.uuid4().hex[:8]}"
        self._client: SlackClient | None = None
        self._callback: Callable[[ConnectorEvent], None] | None = None
    
    async def start(
        self,
        event_callback: Callable[[ConnectorEvent], None],
    ) -> None:
        """启动 Slack 连接."""
        self._callback = event_callback
        self._client = SlackClient(token=self.config.bot_token)
        
        # 启动 Socket Mode 或 Webhook
        if self.config.app_token:
            # Socket Mode（推荐，无需公网 IP）
            await self._start_socket_mode()
        
        self.state = ConnectorState.RUNNING
    
    async def _start_socket_mode(self) -> None:
        """启动 Socket Mode."""
        # 使用 Slack SDK 的 Socket Mode
        from slack_sdk.socket_mode.aiohttp import SocketModeClient
        
        client = SocketModeClient(
            app_token=self.config.app_token,
        )
        
        @client.event
        async def handle_event(event):
            connector_event = self._parse_slack_event(event)
            if connector_event and self._callback:
                self._callback(connector_event)
        
        await client.connect()
    
    def _parse_slack_event(self, event: dict) -> ConnectorEvent | None:
        """解析 Slack 事件."""
        event_type = event.get("type")
        
        if event_type == "message":
            return self.create_event(
                event_type="slack.message",
                payload={
                    "text": event.get("text"),
                    "user": event.get("user"),
                    "channel": event.get("channel"),
                    "ts": event.get("ts"),
                },
                source=event.get("user", "unknown"),
            )
        
        elif event_type == "slash_command":
            return self.create_event(
                event_type="slack.command",
                payload={
                    "command": event.get("command"),
                    "text": event.get("text"),
                    "user_id": event.get("user_id"),
                    "channel_id": event.get("channel_id"),
                },
                source=event.get("user_id", "unknown"),
            )
        
        return None
    
    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict] | None = None,
        thread_ts: str | None = None,
    ) -> bool:
        """
        发送 Slack 消息.

        Args:
            channel: 频道 ID 或名称
            text: 消息文本
            blocks: Slack Block Kit blocks
            thread_ts: 线程时间戳，用于回复到特定线程

        Returns:
            是否成功
        """
        if not self._client:
            return False

        try:
            await self._client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
                thread_ts=thread_ts,  # 回复到原始线程
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    def create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "",
    ) -> ConnectorEvent:
        return ConnectorEvent(
            connector_type=self.connector_type,
            connector_id=self.id,
            event_type=event_type,
            source=source,
            payload=payload,
            user_id=payload.get("user_id"),
            channel_id=payload.get("channel_id"),
        )
    
    async def stop(self) -> None:
        """停止连接."""
        self.state = ConnectorState.STOPPED
        self._client = None


# 使用示例
slack = SlackConnector(
    config=SlackConfig(
        bot_token="xoxb-...",
        app_token="xapp-...",
        command_prefix="/harness",
    )
)
```

### 3. GitHubConnector

```python
# connectors/github.py

@dataclass
class GitHubConfig:
    """GitHub 配置."""
    app_id: str
    private_key: str               # GitHub App 私钥
    webhook_secret: str
    
    # 监听的事件
    events: list[str] = field(default_factory=lambda: [
        "push", "pull_request", "issues", "issue_comment"
    ])


class GitHubConnector(Connector):
    """
    GitHub Connector.
    
    功能：
    - 接收 GitHub Webhook 事件
    - 创建 PR 评论
    - 创建 Issue 评论
    - 更新 PR 状态
    """
    
    connector_type = ConnectorType.GITHUB
    
    def __init__(
        self,
        config: GitHubConfig,
        connector_id: str = "",
    ):
        self.config = config
        self.id = connector_id or f"github_{uuid.uuid4().hex[:8]}"
        self._callback: Callable[[ConnectorEvent], None] | None = None
        self._gh: GitHubAPI | None = None
    
    async def start(
        self,
        event_callback: Callable[[ConnectorEvent], None],
    ) -> None:
        """启动 GitHub 连接."""
        self._callback = event_callback
        self._gh = GitHubAPI(
            app_id=self.config.app_id,
            private_key=self.config.private_key,
        )
        self.state = ConnectorState.RUNNING
    
    async def handle_webhook(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        处理 GitHub Webhook.
        
        由 WebhookConnector 调用。
        """
        if event_type not in self.config.events:
            return
        
        connector_event = self.create_event(
            event_type=f"github.{event_type}",
            payload=payload,
            source=payload.get("repository", {}).get("full_name", "unknown"),
        )
        
        if self._callback:
            self._callback(connector_event)
    
    async def create_pr_comment(
        self,
        repo: str,
        pr_number: int,
        body: str,
    ) -> bool:
        """创建 PR 评论."""
        if not self._gh:
            return False
        
        try:
            await self._gh.issues.create_comment(
                owner=repo.split("/")[0],
                repo=repo.split("/")[1],
                issue_number=pr_number,
                body=body,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create PR comment: {e}")
            return False
    
    async def create_issue_comment(
        self,
        repo: str,
        issue_number: int,
        body: str,
    ) -> bool:
        """创建 Issue 评论."""
        return await self.create_pr_comment(repo, issue_number, body)
    
    def create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "",
    ) -> ConnectorEvent:
        return ConnectorEvent(
            connector_type=self.connector_type,
            connector_id=self.id,
            event_type=event_type,
            source=source,
            payload=payload,
        )
    
    async def stop(self) -> None:
        """停止连接."""
        self.state = ConnectorState.STOPPED
        self._gh = None


# 使用示例
github = GitHubConnector(
    config=GitHubConfig(
        app_id="123456",
        private_key="-----BEGIN RSA PRIVATE KEY-----\n...",
        webhook_secret="whsec_...",
        events=["pull_request", "issues"],
    )
)
```

---

## ConnectorManager

```python
# connectors/manager.py

class ConnectorManager:
    """
    Connector 管理器.
    
    职责：
    - 管理 Connector 生命周期
    - 路由事件到 TriggerManager
    - 管理输出通道
    """
    
    def __init__(
        self,
        trigger_manager: TriggerManager,
    ):
        self.trigger_manager = trigger_manager
        self._connectors: dict[str, Connector] = {}
        self._output_channels: dict[str, OutputChannel] = {}
        self._running = False
    
    def register_connector(
        self,
        connector: Connector,
        enabled: bool = True,
    ) -> str:
        """注册 Connector."""
        if not connector.id:
            connector.id = f"{connector.connector_type.value}_{uuid.uuid4().hex[:8]}"
        
        self._connectors[connector.id] = connector
        logger.info(f"Registered connector {connector.id}")
        return connector.id
    
    def register_output_channel(
        self,
        channel: OutputChannel,
    ) -> str:
        """注册输出通道."""
        self._output_channels[channel.name] = channel
        return channel.name
    
    async def start(self) -> None:
        """启动所有 Connector."""
        self._running = True
        
        for connector in self._connectors.values():
            try:
                await connector.start(self._on_connector_event)
                logger.info(f"Started connector {connector.id}")
            except Exception as e:
                logger.error(f"Failed to start connector {connector.id}: {e}")
    
    async def stop(self) -> None:
        """停止所有 Connector."""
        self._running = False
        
        for connector in self._connectors.values():
            try:
                await connector.stop()
            except Exception as e:
                logger.error(f"Error stopping connector {connector.id}: {e}")
    
    async def _on_connector_event(self, event: ConnectorEvent) -> None:
        """
        处理 Connector 事件.

        将 ConnectorEvent 转换为 TriggerEvent 并发送到 TriggerManager。

        注意：此方法是异步的，确保在 Slack Socket Mode 等
        异步事件循环中不会阻塞。
        """
        # 转换为 TriggerEvent
        trigger_event = TriggerEvent(
            trigger_type=TriggerType.EVENT,
            trigger_id=event.connector_id,
            payload={
                "connector_type": event.connector_type.value,
                "event_type": event.event_type,
                "source": event.source,
                **event.payload,
            },
            # 传递路由元数据，用于结果"原路返回"
            routing_metadata=event.routing_metadata,
        )

        # 发送到 TriggerManager（异步）
        await self.trigger_manager.enqueue_event(trigger_event)

    async def route_output(
        self,
        result: GoalResult,
        channels: list[str],
        routing_metadata: dict[str, Any] | None = None,
    ) -> list[OutputResult]:
        """
        将结果路由到指定通道.

        Args:
            result: Goal 执行结果
            channels: 输出通道名称列表
            routing_metadata: 路由元数据，用于"原路返回"
                例如：{"slack_thread_ts": "17123456.0001", "github_pr_number": 42}
                这些数据来自原始 ConnectorEvent，允许结果回复到正确的位置

        Returns:
            输出结果列表
        """
        outputs = []

        for channel_name in channels:
            channel = self._output_channels.get(channel_name)
            if not channel:
                logger.warning(f"Output channel not found: {channel_name}")
                continue

            output = await self._send_to_channel(
                result, channel, routing_metadata
            )
            outputs.append(output)

        return outputs

    async def _send_to_channel(
        self,
        result: GoalResult,
        channel: OutputChannel,
        routing_metadata: dict[str, Any] | None = None,
    ) -> OutputResult:
        """
        发送结果到指定通道（支持路由元数据）.

        routing_metadata 用于"原路返回"：
        - Slack: 使用 thread_ts 回复到原始消息线程
        - GitHub: 使用 pr_number 回复到正确的 PR
        """
        try:
            if channel.type == "slack":
                connector = self._find_connector(ConnectorType.SLACK)
                if connector and isinstance(connector, SlackConnector):
                    # 优先使用路由元数据中的 thread_ts
                    thread_ts = None
                    if routing_metadata and "slack_thread_ts" in routing_metadata:
                        thread_ts = routing_metadata["slack_thread_ts"]

                    success = await connector.send_message(
                        channel=channel.config.get("channel", "#general"),
                        text=result.final_response or "Task completed",
                        thread_ts=thread_ts,  # 回复到原始线程
                    )
                    return OutputResult(
                        channel_name=channel.name,
                        success=success,
                    )

            elif channel.type == "github":
                connector = self._find_connector(ConnectorType.GITHUB)
                if connector and isinstance(connector, GitHubConnector):
                    # 使用路由元数据中的 PR number
                    pr_number = None
                    if routing_metadata and "github_pr_number" in routing_metadata:
                        pr_number = routing_metadata["github_pr_number"]

                    if pr_number:
                        success = await connector.create_pr_comment(
                            repo=channel.config.get("repo", ""),
                            pr_number=pr_number,
                            body=result.final_response or "Task completed",
                        )
                        return OutputResult(
                            channel_name=channel.name,
                            success=success,
                        )

            elif channel.type == "webhook":
                # 发送到外部 webhook
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "result": result.final_response,
                        "status": result.status.value,
                    }
                    # 包含路由元数据
                    if routing_metadata:
                        payload["routing"] = routing_metadata

                    await session.post(
                        channel.config.get("url"),
                        json=payload,
                        headers=channel.config.get("headers", {}),
                    )
                return OutputResult(channel_name=channel.name, success=True)

            elif channel.type == "file":
                # 写入文件
                with open(channel.config.get("path", "output.txt"), "a") as f:
                    f.write(f"\n---\n{result.final_response}\n")
                return OutputResult(channel_name=channel.name, success=True)

            else:
                return OutputResult(
                    channel_name=channel.name,
                    success=False,
                    error=f"Unknown channel type: {channel.type}",
                )

        except Exception as e:
            return OutputResult(
                channel_name=channel.name,
                success=False,
                error=str(e),
            )
    
    def _find_connector(self, connector_type: ConnectorType) -> Connector | None:
        """查找指定类型的 Connector."""
        for connector in self._connectors.values():
            if connector.connector_type == connector_type:
                return connector
        return None
```

---

## 文件结构

```
packages/sdk/src/harness/connectors/
├── __init__.py           # 模块入口
├── types.py              # ConnectorType, ConnectorEvent, OutputChannel
├── base.py               # Connector ABC
├── manager.py            # ConnectorManager
├── webhook.py            # WebhookConnector
├── slack.py              # SlackConnector
├── github.py             # GitHubConnector
└── email.py              # EmailConnector (可选)
```

---

## API 使用示例

### 基础用法

```python
from harness import AgentHarness
from harness.connectors import (
    ConnectorManager,
    SlackConnector,
    GitHubConnector,
    OutputChannel,
)
from harness.triggers import TriggerManager

# 初始化
agent = AgentHarness(model="claude-sonnet-4-6")
trigger_manager = TriggerManager(agent)
connector_manager = ConnectorManager(trigger_manager)

# 配置 Slack
slack = SlackConnector(
    config=SlackConfig(
        bot_token="xoxb-...",
        app_token="xapp-...",
    )
)
connector_manager.register_connector(slack)

# 配置 GitHub
github = GitHubConnector(
    config=GitHubConfig(
        app_id="123456",
        private_key="...",
        webhook_secret="...",
    )
)
connector_manager.register_connector(github)

# 配置输出通道
connector_manager.register_output_channel(OutputChannel(
    type="slack",
    name="alerts",
    config={"channel": "#alerts"},
))

# 启动
await trigger_manager.start()
await connector_manager.start()
```

### 与 Automation 集成

使用 `EventTrigger` 绑定 Connector 事件：

```python
from harness.loop import Automation
from harness.triggers import EventTrigger, TriggerAction

# 定义事件触发器
pr_trigger = EventTrigger(
    source_connector="github_main",  # Connector ID
    event_type="github.pull_request.opened",
    action=TriggerAction(
        goal="Review the pull request changes and provide feedback",
        skills=["code-review"],
        output_channels=["slack:alerts"],
        reply_to_source=True,  # 自动回复到 PR
    ),
)

# 注册到 TriggerManager
trigger_manager.register(pr_trigger)

# 或使用 Automation 简化 API
pr_review = Automation(
    name="pr-review",
    event_trigger=pr_trigger,  # 传入 EventTrigger
)

await pr_review.start(agent, manager=trigger_manager)
```

**设计说明**：
- Connector 职责单一：只负责接收外部事件
- EventTrigger 负责：定义事件匹配规则和触发动作
- 这种分离确保了"关注点分离"，Connector 可被多个 EventTrigger 复用

---

## 与 Phase 2 的集成

### ConnectorEvent → TriggerEvent 转换

```python
# ConnectorManager 内部

async def _on_connector_event(self, event: ConnectorEvent) -> None:
    """
    异步处理 Connector 事件.

    注意：必须是异步方法，确保在 Slack Socket Mode 等
    异步事件循环中不会阻塞。
    """
    # 转换为 TriggerEvent
    trigger_event = TriggerEvent(
        trigger_type=TriggerType.EVENT,
        trigger_id=event.connector_id,
        payload={
            "connector_type": event.connector_type.value,
            "event_type": event.event_type,
            "source": event.source,
            **event.payload,
        },
        # 传递路由元数据，用于结果"原路返回"
        routing_metadata=event.routing_metadata,
    )

    # 异步发送到 TriggerManager 的事件队列
    await self.trigger_manager.enqueue_event(trigger_event)
```

### TriggerEvent 扩展（Phase 2）

```python
# triggers/types.py

@dataclass
class TriggerEvent:
    """触发事件."""
    trigger_type: TriggerType
    trigger_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)

    # Phase 4: 路由元数据
    # 用于将结果回复到正确的位置（如 Slack 线程、GitHub PR）
    routing_metadata: dict[str, Any] = field(default_factory=dict)
```

### TriggerAction 扩展

```python
@dataclass
class TriggerAction:
    goal: str
    # ... 现有字段 ...

    # Phase 4: 输出配置
    output_channels: list[str] = field(default_factory=list)

    # Phase 4: 回复配置（用于 Slack/GitHub 回复）
    reply_to_source: bool = False  # 是否回复到事件来源
```

---

## EventTrigger（Phase 4 新增）

```python
# triggers/event.py

@dataclass
class EventFilter:
    """事件过滤器."""
    source_connector: str              # Connector ID
    event_type: str | list[str]        # 事件类型（支持通配符）
    payload_filter: dict[str, Any] = field(default_factory=dict)  # payload 字段过滤

    def matches(self, event: TriggerEvent) -> bool:
        """检查事件是否匹配."""
        # 检查 connector ID
        if event.trigger_id != self.source_connector:
            return False

        # 检查事件类型
        if isinstance(self.event_type, list):
            if event.payload.get("event_type") not in self.event_type:
                return False
        else:
            if event.payload.get("event_type") != self.event_type:
                return False

        # 检查 payload 过滤条件
        for key, value in self.payload_filter.items():
            if event.payload.get(key) != value:
                return False

        return True


class EventTrigger(Trigger):
    """
    事件触发器.

    用于响应 Connector 产生的事件。

    Example:
        ```python
        trigger = EventTrigger(
            source_connector="github_main",
            event_type="github.pull_request.opened",
            action=TriggerAction(
                goal="Review the PR",
                output_channels=["slack:reviews"],
            ),
        )
        ```
    """

    trigger_type = TriggerType.EVENT

    def __init__(
        self,
        source_connector: str,
        event_type: str | list[str],
        action: TriggerAction,
        payload_filter: dict[str, Any] | None = None,
        trigger_id: str = "",
    ):
        self.filter = EventFilter(
            source_connector=source_connector,
            event_type=event_type,
            payload_filter=payload_filter or {},
        )
        self.action = action
        self.id = trigger_id or f"event_{source_connector}_{uuid.uuid4().hex[:8]}"

        # EventTrigger 不启动独立循环，由 TriggerManager 的事件队列驱动
        self._running = False

    async def start(
        self,
        callback: Callable[[TriggerEvent], Coroutine[Any, Any, None]],
    ) -> None:
        """
        启动触发器.

        注意：EventTrigger 不启动独立循环。
        它通过 TriggerManager 的事件队列接收事件，
        在 should_trigger() 中过滤匹配的事件。
        """
        self._running = True
        self._callback = callback

    async def stop(self) -> None:
        """停止触发器."""
        self._running = False

    def should_trigger(self, event: TriggerEvent) -> bool:
        """
        检查事件是否应该触发此触发器.

        由 TriggerManager 在处理事件时调用。
        """
        return self._running and self.filter.matches(event)

    def create_event(self, payload: dict | None = None) -> TriggerEvent:
        """创建触发事件（EventTrigger 由外部事件驱动，通常不调用此方法）."""
        return TriggerEvent(
            trigger_type=self.trigger_type,
            trigger_id=self.id,
            payload=payload or {},
        )
```

### TriggerManager 集成 EventTrigger

```python
# triggers/manager.py

class TriggerManager:
    async def _handle_event(self, event: TriggerEvent) -> None:
        """处理触发事件."""
        # 对于 EVENT 类型，检查所有 EventTrigger
        if event.trigger_type == TriggerType.EVENT:
            for reg in self._registrations.values():
                if isinstance(reg.trigger, EventTrigger):
                    if reg.trigger.should_trigger(event):
                        # 触发匹配的 EventTrigger
                        goal_config = reg.action.to_goal_config(event)

                        # 传递路由元数据
                        if event.routing_metadata:
                            goal_config.routing_metadata = event.routing_metadata

                        result = await self.agent.run_goal(goal_config)

                        # 路由输出
                        if reg.action.output_channels:
                            await self.connector_manager.route_output(
                                result,
                                reg.action.output_channels,
                                event.routing_metadata,
                            )
        else:
            # 处理其他类型的触发器
            reg = self._registrations.get(event.trigger_id)
            if reg and reg.enabled:
                goal_config = reg.action.to_goal_config(event)
                result = await self.agent.run_goal(goal_config)
```

---

## 设计决策

### 1. 为什么使用独立的事件类型？

**ConnectorEvent vs TriggerEvent**：

- `ConnectorEvent`: 来自外部系统的原始事件，包含 connector 特定信息
- `TriggerEvent`: 标准化的内部事件，由 TriggerManager 处理

**原因**：
1. **关注点分离**: Connector 负责接收，TriggerManager 负责调度
2. **可扩展性**: 可以添加其他事件源（如内部事件总线）
3. **标准化**: 所有事件最终统一为 TriggerEvent 格式

### 2. 为什么 OutputChannel 独立于 Connector？

**原因**：
1. **灵活性**: 可以将结果发送到多个通道
2. **解耦**: 输出通道不绑定到特定输入源
3. **复用**: 同一通道可用于多个 Automation

### 3. 为什么不内置 HTTP Server？

WebhookConnector 设计为可与现有 FastAPI 应用集成：

```python
# 用户自己的 FastAPI 应用
app = FastAPI()

# 注册 webhook
webhook = WebhookConnector(config=...)
webhook._app = app  # 注入应用

# 或者使用独立的路由
@app.post("/webhook/custom")
async def custom_webhook(request: Request):
    event = webhook.create_event(...)
    connector_manager._on_connector_event(event)
```

**原因**：
1. **灵活性**: 用户可以选择自己的 HTTP 框架
2. **集成友好**: 容易集成到现有服务
3. **避免端口冲突**: 不强制开启额外端口

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 外部 API 限流 | 高 | 速率限制 + 队列缓冲 |
| Webhook 签名验证失败 | 高 | HMAC 验证 + IP 白名单 |
| 敏感信息泄露 | 高 | 环境变量存储密钥 |
| Connector 崩溃影响其他 | 中 | 独立任务隔离 |
| 消息发送失败 | 中 | 重试机制 + 死信队列 |

---

## 实施步骤

### Step 1: 创建类型定义
- [ ] 创建 `connectors/types.py`
- [ ] 定义 `ConnectorType`, `ConnectorEvent`, `OutputChannel`

### Step 2: 实现 Connector 基类
- [ ] 创建 `connectors/base.py`
- [ ] 实现 `Connector` ABC

### Step 3: 实现 WebhookConnector
- [ ] 创建 `connectors/webhook.py`
- [ ] 支持签名验证
- [ ] 支持 FastAPI 集成

### Step 4: 实现 SlackConnector
- [ ] 创建 `connectors/slack.py`
- [ ] 支持 Socket Mode
- [ ] 支持消息发送

### Step 5: 实现 GitHubConnector
- [ ] 创建 `connectors/github.py`
- [ ] 支持 GitHub App 认证
- [ ] 支持 PR/Issue 评论

### Step 6: 实现 ConnectorManager
- [ ] 创建 `connectors/manager.py`
- [ ] 事件路由逻辑
- [ ] 输出通道管理

### Step 7: 集成测试
- [ ] 使用 Mock Server 测试 Webhook
- [ ] 使用 Slack API 测试发送消息
- [ ] 使用 GitHub API 测试评论创建

---

## 后续扩展

### Phase 4.1: 更多 Connectors
- DiscordConnector
- EmailConnector (IMAP/SMTP)
- TeamsConnector

### Phase 4.2: 高级功能
- 消息模板系统
- 多语言支持
- 媒体文件处理

### Phase 4.3: 企业功能
- OAuth 认证流程
- 多租户支持
- 审计日志

---

## 设计变更日志

### 2026-06-30: 架构审查修复

**问题 1: 事件回调同步/异步阻塞风险**

修复前：
```python
def _on_connector_event(self, event: ConnectorEvent) -> None:
    self.trigger_manager._enqueue_event(trigger_event)
```

修复后：
```python
async def _on_connector_event(self, event: ConnectorEvent) -> None:
    await self.trigger_manager.enqueue_event(trigger_event)
```

**原因**：Slack Socket Mode 等 async 事件循环中，同步回调会导致阻塞或线程错误。

---

**问题 2: 缺乏会话上下文穿透**

新增 `routing_metadata` 字段：

```python
@dataclass
class ConnectorEvent:
    # ... 其他字段 ...
    routing_metadata: dict[str, Any] = field(default_factory=dict)
    # 例如：{"slack_thread_ts": "17123456.0001", "github_pr_number": 42}
```

数据流：
```
ConnectorEvent.routing_metadata
    → TriggerEvent.routing_metadata
    → GoalConfig.routing_metadata
    → OutputRouter.route_output(routing_metadata=...)
    → SlackConnector.send_message(thread_ts=...)
```

**效果**：结果可以"原路返回"到正确的 Slack 线程或 GitHub PR。

---

**问题 3: Automation 示例中的 API 矛盾**

修复前（错误）：
```python
trigger=github.create_trigger(event_type="...")  # Connector 不应有此方法
```

修复后（正确）：
```python
trigger = EventTrigger(
    source_connector="github_main",
    event_type="github.pull_request.opened",
    action=TriggerAction(...),
)
```

新增 `EventTrigger` 类：
- 保持 Connector 职责单一
- EventTrigger 负责事件匹配和触发动作
- 支持事件类型过滤和 payload 过滤
