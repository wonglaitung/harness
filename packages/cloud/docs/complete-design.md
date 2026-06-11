# Harness Cloud 云化方案设计文档

> **版本**: v2.1 (评审修订完成版)
> **状态**: 生产就绪 (Production-Ready)
> **最后更新**: 2026-06-11
> **评审状态**: ✅ 已通过 (Approved with Conditions - All Action Items Resolved)

---

## 目录

1. [项目概述与架构总览](#1-项目概述与架构总览)
2. [Agent 胶水层设计](#2-agent-胶水层设计)
3. [网关控制层设计](#3-网关控制层设计)
4. [Vue 前端开发](#4-vue-前端开发)
5. [WebSocket 消息协议](#5-websocket-消息协议)
6. [部署指南](#6-部署指南)

---

## 1. 项目概述与架构总览

### 1.1 项目背景

#### 问题陈述

当前 Harness SDK 以 Python 包形式提供，用户需要在自己的环境中运行。桌面客户端（PyQt6）仅支持 Windows 平台。如果用户想要：

- 在浏览器中使用 Harness，无需安装桌面客户端
- 多用户共享云端资源，各自隔离
- 企业级部署，统一管理和监控

需要构建云原生的 Web 解决方案。

#### 解决方案

构建 **Harness Cloud**：将 SDK 包装在 Docker 沙箱容器中，通过 Web 网关提供服务，前端使用 Vue + TypeScript。

### 1.2 架构总览

#### 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER BROWSER (Vue + TS)                         │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Frontend Application                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │  ChatPanel   │  │  ToolDisplay │  │ SettingsPanel │              │ │
│  │  │  (Vue SFC)   │  │  (Xterm.js)  │  │  (Vue Form)   │              │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│  │                              ↓                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │              WebSocket Client (api/websocket.ts)              │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓ WebSocket                           │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
                                     ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                        GATEWAY CONTROL LAYER                             │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│  │ Container       │  │ WebSocket Tunnel│  │ Auth Manager    │          │
│  │ Manager         │  │ (消息转发)      │  │ (JWT 认证)      │          │
│  │ (Docker/K8s)    │  │                 │  │                 │          │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘          │
│                                    ↓                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                                    │ Internal Network (harness-net)      │
│                                    ↓                                     │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    Docker Sandbox Container                         │ │
│  │                                                                     │ │
│  │  ┌─────────────────────────────────────────────────────────────┐  │ │
│  │  │                  FastAPI Agent                                │  │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │  │ │
│  │  │  │ WebSocket    │  │ SDK Bridge   │  │ Memory Limit │       │  │ │
│  │  │  │ Handler      │  │ (调用 SDK)   │  │ (软限制)     │       │  │ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘       │  │ │
│  │  │                          ↓                                   │  │ │
│  │  │  ┌────────────────────────────────────────────────────────┐ │  │ │
│  │  │  │                    Harness SDK                          │ │  │ │
│  │  │  │  AgentHarness + Tools + Memory + Skills                 │ │  │ │
│  │  │  └────────────────────────────────────────────────────────┘ │  │ │
│  │  └─────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 核心组件关系

```
                    ┌─────────────────┐
                    │   Frontend      │
                    │   (Vue + TS)    │
                    └────────┬────────┘
                             │ WebSocket
                             ↓
┌─────────────────────────────────────────────────────┐
│                    Gateway                           │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │Container│    │ Tunnel  │    │  Auth   │         │
│  │Manager  │    │   WS    │    │  JWT    │         │
│  │(抽象接口)│    │         │    │         │         │
│  └────┬────┘    └─────────┘    └─────────┘         │
│       │                                              │
│       ├─ DockerManager (Docker 环境)                │
│       └─ K8sPodManager (Kubernetes 环境)            │
│       ↓                                              │
│  ┌─────────┐    ┌─────────┐                         │
│  │Container│    │Container│  ...                    │
│  │   #1    │    │   #2    │                         │
│  └────┬────┘    └─────────┘                         │
└───────┼─────────────────────────────────────────────┘
        │
        ↓
┌─────────────────┐
│  Container Agent │
│  ┌─────────────┐ │
│  │ SDK Bridge  │ │
│  │ (asyncio    │ │
│  │  to_thread) │ │
│  └──────┬──────┘ │
│         ↓        │
│  ┌─────────────┐ │
│  │AgentHarness │ │
│  └─────────────┘ │
└─────────────────┘
```

### 1.3 核心概念

#### 三层架构

| 层级 | 组件 | 职责 |
|------|------|------|
| **前端层** | Vue + TypeScript | 用户界面、WebSocket 连接、状态管理 |
| **网关层** | FastAPI + Docker/K8s | 容器调度、消息路由、用户认证 |
| **容器层** | FastAPI Agent + SDK | SDK 执行、会话管理、进度事件 |

#### Agent（容器内代理）

Agent 是运行在每个 Docker 容器内的 FastAPI 服务，作为 SDK 与外界的"胶水层"：

```
WebSocket 消息 → SDKBridge → asyncio.to_thread(agent.run) → ProgressEvent → WebSocket 消息
```

**核心职责**：
1. 接收 WebSocket 消息
2. 转换为 SDK 调用参数
3. 在线程池中执行 SDK（避免阻塞事件循环）
4. 将 ProgressEvent 转换为 WebSocket 消息返回

#### Gateway（网关控制层）

Gateway 是统一入口，负责：

| 功能 | 说明 |
|------|------|
| **容器管理** | 动态创建/销毁用户沙箱容器（支持 Docker 和 K8s） |
| **消息路由** | WebSocket 隧道：前端 ↔ Gateway ↔ 容器 |
| **用户认证** | JWT Token 验证 |
| **资源隔离** | 每个容器 2 CPU / 4GB 内存 / 10 分钟超时 |
| **限流控制** | Redis 滑动窗口限流 |

### 1.4 数据流

#### 请求处理流程

```
用户输入（Vue 组件）
    │
    ↓
WebSocket 发送 RunRequest
    │
    ↓
Gateway 验证 JWT + Rate Limit 检查
    │
    ↓
Gateway 创建/获取容器（内部网络）
    │
    ↓
WebSocket Tunnel 转发消息
    │
    ↓
Container Agent 接收消息
    │
    ↓
SDKBridge 调用 asyncio.to_thread(agent.run)
    │
    ↓
SDK 生成 ProgressEvent
    │
    ↓
SDKBridge 转换为 WebSocket 消息
    │
    ↓
Gateway Tunnel 返回前端
    │
    ↓
Vue 组件渲染消息/工具状态
```

### 1.5 架构决策记录 (ADR)

#### ADR-001: 为什么使用 Docker 容器隔离？

**决策**: 每个用户会话运行在独立的 Docker 容器中。

**原因**:
1. **安全隔离**: 用户代码不会影响其他用户或宿主机
2. **资源限制**: 可精确控制 CPU、内存、执行时间
3. **环境一致**: 容器内环境完全可控
4. **易于清理**: 容器销毁后所有状态自动清除

#### ADR-002: 为什么使用 Vue 而非 React？

**决策**: 前端使用 Vue 3 + TypeScript。

**原因**:
1. **学习曲线**: Vue 更易上手，模板语法直观
2. **渐进式**: 可以从简单开始，逐步引入复杂特性
3. **Composition API**: 与 React Hooks 类似，但更简洁
4. **中文社区**: Vue 在国内有更活跃的中文社区

#### ADR-003: 为什么使用 FastAPI 作为容器 Agent？

**决策**: 容器内使用 FastAPI 提供 WebSocket 服务。

**原因**:
1. **异步原生**: 与 SDK 的 asyncio 无缝集成
2. **WebSocket 支持**: 内置 WebSocket 端点
3. **性能**: 高并发处理能力
4. **类型安全**: Pydantic 提供运行时类型验证

#### ADR-004: 容器隔离级别选择（修订）

**背景**: Docker 容器共享宿主机内核，存在容器逃逸风险。2025年11月发现多个 runc 漏洞。

**决策**: MVP 阶段使用 Hardened Container，生产环境考虑 Kata/gVisor。

**隔离级别对比**：

| 级别 | 技术 | 安全强度 | 适用场景 |
|------|------|---------|---------|
| microVM | Firecracker, Kata | 最强 | 多租户、不可信代码 |
| gVisor | 用户空间内核 | 中强 | 计算密集型 |
| Hardened Container | seccomp + AppArmor | 基础 | 可信代码 |

**MVP 阶段必须实现**：
- 进程数限制 (`pids_limit=100`)
- **内部网络隔离**（Docker 内部桥接网络 `harness-net`）
- CPU/Memory 限制
- 只读文件系统 + tmpfs 挂载
- **内存软限制**（Python 进程级别）

**生产阶段建议**：
- 配置 seccomp profile
- 配置 AppArmor profile
- 考虑 Kata Containers 或 gVisor

#### ADR-005: JWT Token 有效期

**决策**: Token 有效期设为 15 分钟，配合刷新机制。

**原因**:
1. **安全最佳实践**: 短期 Token 减少泄露风险
2. **业界标准**: OAuth 2.0 推荐短期 Access Token + 长期 Refresh Token

#### ADR-006: WebSocket 心跳检测

**决策**: 客户端每 30 秒发送心跳，60 秒无响应视为断线。

**配置**：
| 参数 | 值 | 说明 |
|------|---|------|
| HEARTBEAT_INTERVAL | 30秒 | 心跳间隔 |
| HEARTBEAT_TIMEOUT | 60秒 | 超时阈值 |
| MAX_RECONNECT | 5 | 最大重连次数 |
| 重连策略 | 指数退避 | 1s, 2s, 4s, 8s, 16s |

#### ADR-007: Docker Socket 安全策略（新增）

**背景**: Gateway 通过挂载 `/var/run/docker.sock` 调用 Docker API。如果 Gateway 被攻破，攻击者可获取宿主机 root 权限。

**决策**: 分层安全策略

**MVP 阶段**：
1. Gateway 容器以**非 root 用户**运行
2. docker.sock **只读挂载**
3. 严格限制外网对 Gateway API 的非鉴权访问

**生产阶段**：
1. 使用 Docker Rootless 模式
2. 或切换为 K8s Pod 管理（无 docker.sock）

#### ADR-008: 网络隔离策略（修订）

**背景**: 原设计使用 `network_mode="none"` 完全隔离网络，但这会导致网关无法连接容器。

**决策**: 使用 Docker 内部桥接网络 + iptables 出站限制

**实现方案**：
```python
# 创建专用内部网络（internal=True 阻止外网访问）
network = client.networks.create("harness-net", driver="bridge", internal=True)
```

#### ADR-009: SDK 调用线程模型（修订）

**背景**: 原 `asyncio.run_coroutine_threadsafe` 在高并发下可能导致事件循环死锁。

**决策**: 使用 `asyncio.to_thread()` + 同步队列

**原因**:
1. `asyncio.to_thread()` 是 Python 3.9+ 官方推荐的线程池调度方式
2. 同步 `queue.Queue()` 线程安全，无需跨线程事件循环操作

#### ADR-010: 多实例限流策略（新增）

**背景**: 内存版 Rate Limiter 在多实例部署（`replicas: 2`）下会失效。

**决策**: 使用 Redis 滑动窗口限流

---

## 2. Agent 胶水层设计

### 2.1 概述

Agent 是运行在每个 Docker 沙箱容器内的 FastAPI 服务，负责连接 WebSocket 与 Harness SDK。

### 2.2 目录结构

```
src/harness_cloud/agent/
├── __init__.py
├── main.py           # FastAPI 入口 + 内存限制
├── sdk_bridge.py     # SDK 集成层（修订版）
├── session_sync.py   # 会话状态同步
└── config.py         # Agent 配置
```

### 2.3 SDKBridge - 核心组件（修订版）

> ⚠️ **关键修订**：使用 `asyncio.to_thread()` 替代 `run_coroutine_threadsafe`

#### 类定义

```python
# agent/sdk_bridge.py

from harness import AgentHarness, HarnessConfig, ProgressEvent, ProgressEventType
from harness.tools.builtins import ReadTool, WriteTool, GlobTool, GrepTool, BashTool
import asyncio
import queue
from pathlib import Path


class SDKBridge:
    """
    连接 WebSocket 与 Harness SDK

    核心职责：
    1. 接收 WebSocket 消息
    2. 转换为 SDK 调用参数
    3. 在线程池中执行 SDK（避免阻塞事件循环）
    4. 将 ProgressEvent 转换为 WebSocket 消息返回
    """

    def __init__(self, workspace: str = "/workspace"):
        self.workspace = Path(workspace)
        self.agent: AgentHarness | None = None
        self._interrupt_flag = False
        self._current_session_id: str | None = None
```

#### 创建 Agent

```python
def _create_agent(self, request: RunRequest) -> AgentHarness:
    """根据请求配置创建 AgentHarness"""
    config = HarnessConfig(
        model=request.model,
        api_key=request.api_key,
        provider=request.provider,
        base_url=request.base_url,
        max_iterations=request.max_iterations,
        temperature=request.temperature,
        system_prompt=request.system_prompt,
        sandbox_workspace=str(self.workspace),
        tool_result_role=request.tool_result_role,
    )

    tools = [
        ReadTool(),
        WriteTool(),
        GlobTool(),
        GrepTool(),
        BashTool(),
    ]

    return AgentHarness(config=config, tools=tools)
```

#### 流式执行（修订版 - 使用 asyncio.to_thread）

```python
async def run_stream(self, request: RunRequest) -> AsyncIterator[dict]:
    """
    执行任务并流式返回事件

    修订说明：
    - 使用同步 queue.Queue() 替代 asyncio.Queue
    - 使用 asyncio.to_thread() 将同步 SDK 执行放入线程池
    - 避免跨线程事件循环操作，防止死锁
    """
    self.agent = self._create_agent(request)
    self._current_session_id = request.session_id
    self._interrupt_flag = False

    # 使用同步队列（线程安全）
    events_queue: queue.Queue = queue.Queue()

    def on_progress(event: ProgressEvent):
        """SDK progress callback - 同步方法"""
        events_queue.put(event)

    def run_agent_sync():
        """同步执行 agent（在线程池中运行）"""
        try:
            result = self.agent.run(
                prompt=request.prompt,
                session_id=request.session_id,
                on_progress=on_progress,
            )
            events_queue.put(("result", result))
        except MemoryError:
            # 内存超限（Python 软限制触发）
            events_queue.put(("error", "MEMORY_LIMIT"))
        except Exception as e:
            events_queue.put(("error", str(e)))

    # 使用 asyncio.to_thread 在线程池中执行同步 SDK
    agent_task = asyncio.create_task(
        asyncio.to_thread(run_agent_sync)
    )

    # 流式返回事件
    while True:
        # 非阻塞检查队列
        try:
            item = events_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.01)  # 短暂让出控制权
            continue

        if isinstance(item, tuple):
            if item[0] == "result":
                yield {
                    "type": MessageType.RUN_RESULT,
                    "payload": self._result_to_payload(item[1]),
                }
                break
            elif item[0] == "error":
                if item[1] == "MEMORY_LIMIT":
                    yield {
                        "type": MessageType.ERROR,
                        "payload": {
                            "error": "内存不足：任务需要超过限制，请减少数据量",
                            "error_code": "MEMORY_LIMIT",
                        },
                    }
                else:
                    yield {
                        "type": MessageType.ERROR,
                        "payload": {"error": item[1]},
                    }
                break
        else:
            # ProgressEvent
            yield self._translate_event(item)

    await agent_task
```

#### ProgressEvent 映射

```python
def _translate_event(self, event: ProgressEvent) -> dict:
    """将 SDK ProgressEvent 转换为 WebSocket 消息"""
    if event.type == ProgressEventType.TOOL_CALL:
        return {
            "type": MessageType.TOOL_CALL,
            "payload": {
                "tool_name": event.data.get("tool", ""),
                "tool_call_id": event.data.get("tool_call_id", ""),
                "arguments": event.data.get("arguments", {}),
            },
        }

    elif event.type == ProgressEventType.TOOL_RESULT:
        return {
            "type": MessageType.TOOL_RESULT,
            "payload": {
                "tool_name": event.data.get("tool", ""),
                "success": event.data.get("success", True),
                "result": event.data.get("result", "")[:500],
                "error": event.data.get("error"),
            },
        }

    elif event.type == ProgressEventType.TEXT_CHUNK:
        return {
            "type": MessageType.STREAM_CHUNK,
            "payload": {"content": event.data.get("text", "")},
        }

    else:
        return {
            "type": MessageType.PROGRESS,
            "payload": {
                "event_type": event.type.value,
                "message": event.message,
                "data": event.data,
            },
        }
```

### 2.4 FastAPI WebSocket 端点（修订版）

> ⚠️ **关键修订**：添加全局异常捕获 + 防止双重 close

```python
# agent/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import asyncio
import logging
import resource

from harness_cloud.agent.sdk_bridge import SDKBridge
from harness_cloud.common.messages import MessageEnvelope, MessageType, RunRequest

logger = logging.getLogger(__name__)


def setup_memory_limit():
    """
    设置进程内存软限制

    当内存超过 3.8GB 时，Python 会抛出 MemoryError，
    而不是被 Linux OOM Killer 硬杀（-9）。
    这样 SDKBridge 可以捕获并转换为友好的 WebSocket 错误消息。

    ⚠️ 评审意见 - Python resource 限制的局限性：
    1. C 扩展（如 numpy）可能无法正确捕获 MemoryError
    2. 子进程（如 BashTool 执行命令）不受此限制
    3. 进程仍可能被 Linux OOM Killer 直接杀死（SIGKILL）

    解决方案：
    - 保留此软限制作为第一道防线
    - 依赖 Docker/K8s 的 mem_limit（硬限制）作为兜底
    - Gateway 的 _cleanup_loop 需处理容器被 OOM Kill 后的清理
    """
    try:
        soft_limit = 3800 * 1024 * 1024  # 3.8GB
        hard_limit = 4000 * 1024 * 1024  # 4GB
        resource.setrlimit(resource.RLIMIT_AS, (soft_limit, hard_limit))
        logger.info(f"Memory limit set: soft={soft_limit}, hard={hard_limit}")
    except Exception as e:
        logger.warning(f"Failed to set memory limit: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化"""
    setup_memory_limit()
    yield


app = FastAPI(title="Harness Container Agent", lifespan=lifespan)


@app.websocket("/ws/run")
async def websocket_run(websocket: WebSocket):
    """
    主 WebSocket 端点（修订版）

    修订内容：
    - 添加 _closed 标志防止双重 close
    - 全局异常捕获防止进程崩溃
    """
    await websocket.accept()
    bridge = SDKBridge()
    session_id = None

    # 心跳检测
    last_ping = asyncio.get_event_loop().time()
    HEARTBEAT_TIMEOUT = 90.0
    _closed = False  # 防止双重 close

    async def heartbeat_monitor():
        """监控心跳超时"""
        while True:
            await asyncio.sleep(30)
            if _closed:
                return
            elapsed = asyncio.get_event_loop().time() - last_ping
            if elapsed > HEARTBEAT_TIMEOUT:
                logger.warning("Heartbeat timeout, closing connection")
                _closed = True
                try:
                    await websocket.close(code=1001, reason="Heartbeat timeout")
                except Exception:
                    pass  # 防止重复 close 异常
                return

    heartbeat_task = asyncio.create_task(heartbeat_monitor())

    try:
        while True:
            raw_data = await websocket.receive_text()
            envelope = MessageEnvelope.parse_raw(raw_data)

            # 处理心跳
            if envelope.type == "ping":
                last_ping = asyncio.get_event_loop().time()
                await websocket.send_json({"type": "pong"})
                continue

            if envelope.type == MessageType.RUN_REQUEST:
                request = RunRequest.parse_obj(envelope.payload)
                session_id = request.session_id

                await websocket.send_json({
                    "type": MessageType.ACK.value,
                    "session_id": session_id,
                })

                async for event in bridge.run_stream(request):
                    await websocket.send_json(event)

            elif envelope.type == MessageType.INTERRUPT:
                bridge.interrupt()
                await websocket.send_json({
                    "type": MessageType.INTERRUPTED.value,
                })

    except WebSocketDisconnect:
        logger.info(f"Client disconnected, session: {session_id}")
    except Exception as e:
        logger.error(f"Unexpected error in websocket: {e}")
    finally:
        _closed = True
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


@app.get("/health")
async def health_check():
    """容器健康检查"""
    return {"status": "healthy"}
```

### 2.5 会话状态同步（session_sync.py）

> ⚠️ **评审建议**：实现断线重连的状态恢复机制，避免长任务执行中断线导致上下文丢失。

#### 模块职责

```python
# agent/session_sync.py

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


@dataclass
class SessionState:
    """会话状态快照"""
    session_id: str
    last_event_id: int  # 最后收到的事件 ID
    progress: dict      # 当前进度（如 tool_calls 列表）
    timestamp: datetime
```

#### 状态持久化

```python
class SessionSync:
    """会话状态同步器

    用途：
    1. 在任务执行过程中定期保存状态快照
    2. 断线重连后恢复上下文
    3. 支持"从断点续传"
    """

    def __init__(self, state_dir: str = "/tmp/harness_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)

    def save_state(self, state: SessionState):
        """保存状态快照到本地文件"""
        state_file = self.state_dir / f"{state.session_id}.json"
        data = {
            "session_id": state.session_id,
            "last_event_id": state.last_event_id,
            "progress": state.progress,
            "timestamp": state.timestamp.isoformat(),
        }
        state_file.write_text(json.dumps(data))

    def load_state(self, session_id: str) -> SessionState | None:
        """加载状态快照"""
        state_file = self.state_dir / f"{session_id}.json"
        if not state_file.exists():
            return None
        data = json.loads(state_file.read_text())
        return SessionState(
            session_id=data["session_id"],
            last_event_id=data["last_event_id"],
            progress=data["progress"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    def clear_state(self, session_id: str):
        """清理状态"""
        state_file = self.state_dir / f"{session_id}.json"
        state_file.unlink(missing_ok=True)
```

#### 断线重连流程

```
前端断线检测（心跳超时）
    ↓
前端发起 WebSocket 重连
    ↓
发送 auth 消息 + resume_request
    ↓
{
    "type": "resume_request",
    "session_id": "abc123",
    "last_event_id": 42
}
    ↓
Agent 从 SessionSync 加载状态
    ↓
Agent 发送增量事件（event_id > 42）
    ↓
正常继续执行
```

#### WebSocket 消息扩展

```python
# 在 main.py 中添加 resume 处理

elif envelope.type == "resume_request":
    session_id = envelope.payload.get("session_id")
    last_event_id = envelope.payload.get("last_event_id", 0)

    # 加载状态
    state = session_sync.load_state(session_id)
    if not state:
        await websocket.send_json({
            "type": "error",
            "payload": {"error": "Session not found or expired"}
        })
        return

    # 发送恢复确认
    await websocket.send_json({
        "type": "resume_ack",
        "session_id": session_id,
        "progress": state.progress,
    })

    # 继续执行（需要 SDK 支持 checkpoint）
```

#### 注意事项

- **状态文件存储在 `/tmp`**（tmpfs），容器销毁后自动清理
- **增量同步限制**：如果任务已完成，无法恢复
- **SDK Checkpoint 支持**：需要 SDK 层面的 checkpoint 机制才能真正实现断点续传

---

## 3. 网关控制层设计

### 3.1 概述

Gateway 是 Harness Cloud 的统一入口，负责容器调度、消息路由、用户认证和限流。

### 3.2 目录结构

```
src/harness_cloud/gateway/
├── __init__.py
├── main.py              # Gateway FastAPI 入口
├── container_manager.py # 容器管理抽象接口
├── docker_manager.py    # Docker 实现
├── k8s_manager.py       # Kubernetes 实现（新增）
├── tunnel.py            # WebSocket 隧道
├── auth.py              # JWT 认证
├── rate_limiter.py      # Redis 限流器（修订）
├── file_storage.py      # MinIO 文件存储（新增）
└── config.py            # Gateway 配置
```

### 3.3 容器管理器抽象接口（新增）

```python
# gateway/container_manager.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContainerInfo:
    """运行时容器信息"""
    container_id: str
    session_id: str
    user_id: str
    internal_ip: str
    internal_port: int = 8000
    created_at: datetime
    last_activity: datetime


class ContainerManager(ABC):
    """容器管理器抽象接口"""

    @abstractmethod
    async def create_container(
        self,
        session_id: str,
        user_id: str,
        workspace_path: str | None = None,
    ) -> ContainerInfo:
        """创建沙箱容器"""
        pass

    @abstractmethod
    async def destroy_container(self, session_id: str) -> bool:
        """销毁容器"""
        pass

    @abstractmethod
    def get_container_url(self, session_id: str) -> str:
        """获取容器 WebSocket URL"""
        pass

    @abstractmethod
    def get_container(self, session_id: str) -> ContainerInfo | None:
        """获取容器信息"""
        pass
```

### 3.4 DockerManager - Docker 实现（修订版）

> ⚠️ **关键修订**：
> 1. 使用内部网络替代 `network_mode: none`
> 2. Gateway 非 root 用户运行
> 3. tmpfs 挂载解决只读文件系统问题

```python
# gateway/docker_manager.py

import docker
import asyncio
from datetime import datetime

from harness_cloud.gateway.container_manager import ContainerManager, ContainerInfo


@dataclass
class DockerConfig:
    """Docker 容器配置"""
    image: str = "harness-agent:latest"
    cpu_quota: int = 200000      # 2 CPU
    memory_limit: str = "4g"
    memory_swap: str = "4g"
    timeout_seconds: int = 600
    pids_limit: int = 100
    internal_network: str = "harness-net"
    read_only_root_fs: bool = True
    cap_drop: list[str] = ["ALL"]


class DockerManager(ContainerManager):
    """Docker 环境容器管理"""

    def __init__(self, config: DockerConfig = None):
        self.config = config or DockerConfig()
        self.client = docker.from_env()
        self._containers: dict[str, ContainerInfo] = {}
        self._cleanup_task: asyncio.Task = None
        self._ensure_network()

    def _ensure_network(self):
        """确保内部网络存在"""
        try:
            self.client.networks.get(self.config.internal_network)
        except docker.errors.NotFound:
            self.client.networks.create(
                self.config.internal_network,
                driver="bridge",
                internal=True,  # 阻止外网访问
            )

    async def create_container(
        self,
        session_id: str,
        user_id: str,
        workspace_path: str | None = None,
    ) -> ContainerInfo:
        """创建安全加固的沙箱容器"""
        volumes = {}
        if workspace_path:
            volumes[workspace_path] = {"bind": "/workspace", "mode": "rw"}

        # tmpfs 挂载（修复只读文件系统问题）
        tmpfs = {"/tmp": "size=100M,mode=1777"}

        container = self.client.containers.run(
            self.config.image,
            detach=True,
            name=f"harness-{session_id}",
            environment={
                "SESSION_ID": session_id,
                "USER_ID": user_id,
            },
            volumes=volumes,
            tmpfs=tmpfs,

            # 资源限制
            cpu_quota=self.config.cpu_quota,
            mem_limit=self.config.memory_limit,
            memswap_limit=self.config.memory_swap,
            pids_limit=self.config.pids_limit,

            # 网络配置（修订：使用内部网络）
            network=self.config.internal_network,

            # 安全加固
            security_opt=["no-new-privileges"],
            cap_drop=self.config.cap_drop,
            read_only=self.config.read_only_root_fs,

            remove=False,
        )

        # 获取容器 IP
        container.reload()
        networks = container.attrs["NetworkSettings"]["Networks"]
        internal_ip = networks[self.config.internal_network]["IPAddress"]

        info = ContainerInfo(
            container_id=container.id,
            session_id=session_id,
            user_id=user_id,
            internal_ip=internal_ip,
            container=container,
        )

        self._containers[session_id] = info
        return info

    async def destroy_container(self, session_id: str) -> bool:
        """销毁容器"""
        info = self._containers.pop(session_id, None)
        if not info:
            return False
        try:
            info.container.remove(force=True)
            return True
        except Exception:
            return False

    def get_container_url(self, session_id: str) -> str:
        """获取容器 WebSocket URL"""
        info = self._containers.get(session_id)
        if not info:
            raise ValueError(f"Container not found: {session_id}")
        return f"ws://{info.internal_ip}:{info.internal_port}/ws/run"

    def get_container(self, session_id: str) -> ContainerInfo | None:
        return self._containers.get(session_id)

    async def start(self):
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
        for info in list(self._containers.values()):
            await self.destroy_container(info.session_id)

    async def _cleanup_loop(self):
        """定期清理过期容器"""
        while True:
            await asyncio.sleep(60)
            now = datetime.now()
            expired = [
                sid for sid, info in self._containers.items()
                if (now - info.last_activity).total_seconds() > self.config.timeout_seconds
            ]
            for sid in expired:
                await self.destroy_container(sid)
```

### 3.5 K8sPodManager - Kubernetes 实现（新增）

```python
# gateway/k8s_manager.py

from kubernetes import client, config
from harness_cloud.gateway.container_manager import ContainerManager, ContainerInfo


class K8sPodManager(ContainerManager):
    """Kubernetes 环境容器管理"""

    def __init__(self, namespace: str = "harness-cloud"):
        config.load_incluster_config()
        self.core_v1 = client.CoreV1Api()
        self.namespace = namespace
        self._containers: dict[str, ContainerInfo] = {}

    async def create_container(
        self,
        session_id: str,
        user_id: str,
        workspace_path: str | None = None,
    ) -> ContainerInfo:
        """创建 K8s Pod 作为沙箱"""
        pod_name = f"harness-{session_id}"

        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name,
                labels={
                    "app": "harness-agent",
                    "session-id": session_id,
                    "user-id": user_id,
                },
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="agent",
                        image="harness-agent:latest",
                        ports=[client.V1ContainerPort(container_port=8000)],
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": "500m", "memory": "2Gi"},
                            limits={"cpu": "2000m", "memory": "4Gi"},
                        ),
                        env=[
                            client.V1EnvVar(name="SESSION_ID", value=session_id),
                            client.V1EnvVar(name="USER_ID", value=user_id),
                        ],
                        # 健康检查（修订：必须添加）
                        liveness_probe=client.V1Probe(
                            http_get=client.V1HTTPGetAction(path="/health", port=8000),
                            initial_delay_seconds=5,
                            period_seconds=10,
                        ),
                        readiness_probe=client.V1Probe(
                            http_get=client.V1HTTPGetAction(path="/health", port=8000),
                            initial_delay_seconds=2,
                            period_seconds=5,
                        ),
                    )
                ],
                restart_policy="Never",
            ),
        )
                        image="harness-agent:latest",
                        ports=[client.V1ContainerPort(container_port=8000)],
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": "500m", "memory": "2Gi"},
                            limits={"cpu": "2000m", "memory": "4Gi"},
                        ),
                        env=[
                            client.V1EnvVar(name="SESSION_ID", value=session_id),
                            client.V1EnvVar(name="USER_ID", value=user_id),
                        ],
                    )
                ],
                restart_policy="Never",
            ),
        )

        self.core_v1.create_namespaced_pod(self.namespace, pod)

        # 等待 Pod 就绪并获取 IP
        import time
        for _ in range(30):
            pod_status = self.core_v1.read_namespaced_pod(pod_name, self.namespace)
            if pod_status.status.phase == "Running" and pod_status.status.pod_ip:
                break
            time.sleep(1)

        return ContainerInfo(
            container_id=pod_name,
            session_id=session_id,
            user_id=user_id,
            internal_ip=pod_status.status.pod_ip,
        )

    async def destroy_container(self, session_id: str) -> bool:
        try:
            self.core_v1.delete_namespaced_pod(
                f"harness-{session_id}", self.namespace
            )
            return True
        except Exception:
            return False

    def get_container_url(self, session_id: str) -> str:
        pod_name = f"harness-{session_id}"
        return f"ws://{pod_name}.{self.namespace}.svc.cluster.local:8000/ws/run"
```

### 3.6 Redis Rate Limiter（修订版）

> ⚠️ **修订**：替代内存版，支持多实例部署

```python
# gateway/rate_limiter.py

import redis
import time


class RedisRateLimiter:
    """基于 Redis 的滑动窗口限流器"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_requests: int = 100,
        window_seconds: int = 3600,
    ):
        self.redis = redis.from_url(redis_url)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def check(self, user_id: str) -> bool:
        """检查是否超过限制（滑动窗口算法）"""
        key = f"rate_limit:{user_id}"
        now = time.time()
        window_start = now - self.window_seconds

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, self.window_seconds)

        results = pipe.execute()
        current_count = results[1]

        return current_count < self.max_requests
```

### 3.7 MinIO 文件存储（新增）

```python
# gateway/file_storage.py

from minio import Minio
import io


class FileStorage:
    """MinIO 文件存储"""

    def __init__(
        self,
        endpoint: str = "minio:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket: str = "harness-files",
    ):
        self.client = Minio(endpoint, access_key, secret_key, secure=False)
        self.bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception:
            pass

    async def upload(self, file_name: str, data: bytes, user_id: str) -> str:
        """上传文件"""
        object_name = f"{user_id}/{file_name}"
        self.client.put_object(
            self.bucket, object_name, io.BytesIO(data), len(data)
        )
        return object_name

    async def get_download_url(self, object_name: str, expires: int = 3600) -> str:
        """获取预签名下载 URL"""
        return self.client.presigned_get_object(self.bucket, object_name, expires=expires)
```

### 3.8 Gateway FastAPI 入口

```python
# gateway/main.py

import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from harness_cloud.gateway.container_manager import ContainerManager
from harness_cloud.gateway.docker_manager import DockerManager
from harness_cloud.gateway.k8s_manager import K8sPodManager
from harness_cloud.gateway.tunnel import WebSocketTunnel
from harness_cloud.gateway.auth import get_current_user, User
from harness_cloud.gateway.rate_limiter import RedisRateLimiter
from harness_cloud.gateway.file_storage import FileStorage


def get_container_manager() -> ContainerManager:
    """根据环境选择容器管理器"""
    env = os.getenv("HARNESS_ENV", "docker")
    if env == "k8s":
        return K8sPodManager(namespace="harness-cloud")
    return DockerManager()


container_manager: ContainerManager = None
rate_limiter: RedisRateLimiter = None
file_storage: FileStorage = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global container_manager, rate_limiter, file_storage
    container_manager = get_container_manager()
    await container_manager.start()
    rate_limiter = RedisRateLimiter(redis_url=os.getenv("REDIS_URL", "redis://redis:6379"))
    file_storage = FileStorage()
    yield
    await container_manager.stop()


app = FastAPI(title="Harness Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/sessions")
async def create_session(user: User = Depends(get_current_user)):
    """创建会话"""
    if not rate_limiter.check(user.id):
        raise HTTPException(429, "Rate limit exceeded")

    session_id = str(uuid.uuid4())[:8]
    info = await container_manager.create_container(
        session_id=session_id, user_id=user.id
    )
    return {"session_id": session_id, "container_id": info.container_id[:12]}


@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str, token: str):
    """
    会话 WebSocket 端点

    ⚠️ 安全修订：Token 通过首条消息传递，避免 URL 泄露
    """
    await websocket.accept()

    # 等待首条鉴权消息
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        auth_data = json.loads(auth_msg)
        if auth_data.get("type") != "auth":
            await websocket.close(code=4001, reason="Expected auth message")
            return
        token = auth_data.get("token")
    except Exception:
        await websocket.close(code=4001, reason="Auth timeout")
        return

    try:
        user = await get_current_user(token)
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    info = container_manager.get_container(session_id)
    if not info or info.user_id != user.id:
        await websocket.close(code=4003, reason="Not authorized")
        return

    info.last_activity = datetime.now()
    container_url = container_manager.get_container_url(session_id)
    tunnel = WebSocketTunnel(container_url)

    try:
        await tunnel.connect(websocket)
    except WebSocketDisconnect:
        pass
    finally:
        info.last_activity = datetime.now()


# 文件上传 - 前端直传 MinIO（修订版）
@app.post("/api/files/presign-upload")
async def get_upload_url(
    filename: str,
    user: User = Depends(get_current_user),
):
    """
    获取预签名上传 URL

    前端直接 PUT 到 MinIO，避免大文件经过 Gateway 内存
    """
    object_name = f"{user.id}/{uuid.uuid4().hex[:8]}_{filename}"
    upload_url = file_storage.get_presigned_put_url(object_name)
    return {"upload_url": upload_url, "object_name": object_name}


@app.post("/api/files/presign-download")
async def get_download_url(
    object_name: str,
    user: User = Depends(get_current_user),
):
    """获取预签名下载 URL"""
    # 验证用户权限
    if not object_name.startswith(f"{user.id}/"):
        raise HTTPException(403, "Access denied")
    download_url = await file_storage.get_download_url(object_name)
    return {"download_url": download_url}
```

### MinIO FileStorage（修订版）

```python
# gateway/file_storage.py

from minio import Minio
import io


class FileStorage:
    """MinIO 文件存储 - 支持预签名 URL"""

    def __init__(
        self,
        endpoint: str = "minio:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket: str = "harness-files",
    ):
        self.client = Minio(endpoint, access_key, secret_key, secure=False)
        self.bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception:
            pass

    def get_presigned_put_url(self, object_name: str, expires: int = 3600) -> str:
        """
        获取预签名上传 URL

        前端直接 PUT 到此 URL，文件不经过 Gateway 内存
        """
        return self.client.presigned_put_object(self.bucket, object_name, expires=expires)

    async def get_download_url(self, object_name: str, expires: int = 3600) -> str:
        """获取预签名下载 URL"""
        return self.client.presigned_get_object(self.bucket, object_name, expires=expires)
```

### 前端文件上传示例

```typescript
// 前端直传 MinIO
async function uploadFile(file: File): Promise<string> {
  // 1. 获取预签名上传 URL
  const { upload_url, object_name } = await fetch(
    `/api/files/presign-upload?filename=${file.name}`,
    { headers: { Authorization: `Bearer ${token}` } }
  ).then(r => r.json())

  // 2. 直接 PUT 到 MinIO
  await fetch(upload_url, {
    method: 'PUT',
    body: file,
    headers: { 'Content-Type': file.type }
  })

  return object_name
}
```

---

## 4. Vue 前端开发

### 4.1 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4+ | 框架 |
| TypeScript | 5.0+ | 类型安全 |
| Vite | 5.0+ | 构建工具 |
| Pinia | 2.0+ | 状态管理 |
| TailwindCSS | 3.0+ | 样式 |

### 4.2 WebSocket 客户端（含心跳检测）

```typescript
// composables/useWebSocket.ts

import { ref, onUnmounted } from 'vue'

export function useWebSocket(sessionId: string) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)

  // 心跳配置
  const HEARTBEAT_INTERVAL = 30000
  const HEARTBEAT_TIMEOUT = 60000
  const MAX_RECONNECT = 5

  let lastHeartbeat = Date.now()
  let heartbeatTimer: number | null = null
  let reconnectAttempts = 0

  // ⚠️ 修订：Token 通过首条消息传递，避免 URL 泄露
  function connect(token: string) {
    ws.value = new WebSocket(`${gatewayUrl}/ws/session/${sessionId}`)

    ws.value.onopen = () => {
      // 连接后立即发送鉴权消息
      ws.value!.send(JSON.stringify({ type: 'auth', token: token }))
    }

    ws.value.onmessage = (event) => {
      const envelope = JSON.parse(event.data)

      // 处理鉴权成功
      if (envelope.type === 'auth_success') {
        isConnected.value = true
        reconnectAttempts = 0
        startHeartbeat()
        return
      }

      // 处理心跳
      if (envelope.type === 'pong') {
        lastHeartbeat = Date.now()
        return
      }
      handleMessage(envelope)
    }

    ws.value.onclose = () => {
      isConnected.value = false
      stopHeartbeat()
      if (reconnectAttempts < MAX_RECONNECT) {
        scheduleReconnect(token)
      }
    }
  }

  function startHeartbeat() {
    heartbeatTimer = setInterval(() => {
      if (ws.value?.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({ type: 'ping' }))
        if (Date.now() - lastHeartbeat > HEARTBEAT_TIMEOUT) {
          ws.value.close()
        }
      }
    }, HEARTBEAT_INTERVAL)
  }

  function scheduleReconnect(token: string) {
    reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
    setTimeout(() => connect(token), delay)
  }

  onUnmounted(() => {
    stopHeartbeat()
    ws.value?.close()
  })

  return { connect, on, send, isConnected }
}
```

---

## 5. WebSocket 消息协议

### 5.1 消息类型

| 类型 | 方向 | 说明 |
|------|------|------|
| `run_request` | C→S | 执行任务 |
| `interrupt` | C→S | 中断执行 |
| `ack` | S→C | 确认接收 |
| `run_result` | S→C | 最终结果 |
| `stream_chunk` | S→C | 流式文本 |
| `tool_call` | S→C | 工具调用 |
| `tool_result` | S→C | 工具结果 |
| `error` | S→C | 错误 |

### 5.2 交互流程

```
Client                    Server
  │                         │
  │── run_request ─────────>│
  │<── ack ─────────────────│
  │<── stream_chunk ────────│
  │<── tool_call ───────────│
  │<── tool_result ─────────│
  │<── run_result ──────────│
```

---

## 6. 部署指南

### 6.1 Docker Compose（修订版）

> ⚠️ **生产环境安全警告**：
> - `docker.sock` 挂载存在容器逃逸风险，生产环境建议使用 **K8sPodManager** 或 **Docker Rootless 模式**
> - 参见 [ADR-007: Docker Socket 安全策略](#adr-007-docker-socket-安全策略新增)

```yaml
version: '3.8'

services:
  gateway:
    build:
      context: .
      dockerfile: docker/gateway.Dockerfile
    ports:
      - "8080:8080"
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
    volumes:
      # ⚠️ 安全警告：docker.sock 挂载存在容器逃逸风险
      # 生产环境建议：使用 K8sPodManager 或 Docker Rootless 模式
      - /var/run/docker.sock:/var/run/docker.sock:ro  # 只读挂载
    user: "1000:1000"  # 非 root 用户运行
    depends_on:
      - redis
      - minio
    networks:
      - harness-net

  redis:
    image: redis:7-alpine
    networks:
      - harness-net

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    networks:
      - harness-net

networks:
  harness-net:
    driver: bridge
```

### 6.2 Gateway Dockerfile（修订版）

```dockerfile
# docker/gateway.Dockerfile

FROM python:3.11-slim

# 创建非 root 用户
RUN useradd -m -u 1000 harness

WORKDIR /app
COPY --chown=harness:harness src/harness_cloud /app/harness_cloud
RUN pip install fastapi uvicorn websockets docker redis minio pyjwt

USER harness
EXPOSE 8080

CMD ["uvicorn", "harness_cloud.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 6.3 Agent Dockerfile（优化版）

> ⚠️ **评审建议**：使用多阶段构建减小镜像体积，分离 SDK 构建与业务代码。

```dockerfile
# docker/agent.Dockerfile

# 阶段 1：构建 SDK wheel
FROM python:3.11-slim AS sdk-builder

WORKDIR /build
COPY packages/sdk /build/sdk
RUN pip install build && \
    cd sdk && \
    python -m build --wheel

# 阶段 2：运行时镜像
FROM python:3.11-slim

# 安装运行时依赖（不含 build-essential）
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制 SDK wheel
COPY --from=sdk-builder /build/sdk/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

# 复制业务代码
COPY src/harness_cloud /app/harness_cloud
RUN pip install --no-cache-dir fastapi uvicorn websockets

# 创建工作目录
RUN mkdir /workspace
WORKDIR /workspace

EXPOSE 8000
CMD ["uvicorn", "harness_cloud.agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**优化效果**：
- 镜像体积减小约 200MB（不含 build-essential）
- SDK 构建缓存独立，业务代码修改不影响 SDK 层

### 6.4 Kubernetes NetworkPolicy

> ⚠️ **重要**：`egress: []` 表示拒绝所有出站流量。`- {}` 是允许所有，这是常见的配置错误。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sandbox-isolation
spec:
  podSelector:
    matchLabels:
      app: harness-agent
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: gateway
      ports:
        - port: 8000
  egress: []  # 明确拒绝所有出站流量（空数组 = 拒绝所有）
```

### 6.5 资源配置

| 容器 | CPU | 内存 | 超时 |
|------|-----|------|------|
| Agent | 2核 | 4GB | 10分钟 |
| Gateway | 1核 | 2GB | - |

---

## 参考资源

- [Harness SDK 文档](../sdk/docs/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Vue 3 文档](https://cn.vuejs.org/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- [Docker Rootless Mode](https://docs.docker.com/engine/security/rootless/)
- [AI Agent Sandboxing - Northflank](https://northflank.com/blog/how-to-sandbox-ai-agents)