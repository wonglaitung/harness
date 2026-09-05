# 01 - 项目概述与架构总览

## 项目背景

### 问题陈述

当前 Harness SDK 以 Python 包形式提供，用户需要在自己的环境中运行。桌面客户端（PyQt6）仅支持 Windows 平台。如果用户想要：

- 在浏览器中使用 Harness，无需安装桌面客户端
- 多用户共享云端资源，各自隔离
- 企业级部署，统一管理和监控

需要构建云原生的 Web 解决方案。

### 解决方案

构建 **Harness Cloud**：将 SDK 包装在 Docker 沙箱容器中，通过 Web 网关提供服务，前端使用 Vue + TypeScript。

## 架构总览

### 系统架构图

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
│  │ Docker Manager  │  │ WebSocket Tunnel│  │ Auth Manager    │          │
│  │ (容器生命周期)   │  │ (消息转发)      │  │ (JWT 认证)      │          │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘          │
│                                    ↓                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                                    │ Docker Network                      │
│                                    ↓                                     │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    Docker Sandbox Container                         │ │
│  │                                                                     │ │
│  │  ┌─────────────────────────────────────────────────────────────┐  │ │
│  │  │                  FastAPI Agent                                │  │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │  │ │
│  │  │  │ WebSocket    │  │ SDK Bridge   │  │ Session Sync │       │  │ │
│  │  │  │ Handler      │  │ (调用 SDK)   │  │ (状态同步)   │       │  │ │
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

### 核心组件关系

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
│  │ Docker  │    │ Tunnel  │    │  Auth   │         │
│  │Manager  │    │   WS    │    │  JWT    │         │
│  └────┬────┘    └────┬────┘    └─────────┘         │
│       │              │                               │
│       ↓              ↓                               │
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
│  └──────┬──────┘ │
│         ↓        │
│  ┌─────────────┐ │
│  │AgentHarness │ │
│  └─────────────┘ │
└─────────────────┘
```

## 核心概念

### 三层架构

| 层级 | 组件 | 职责 |
|------|------|------|
| **前端层** | Vue + TypeScript | 用户界面、WebSocket 连接、状态管理 |
| **网关层** | FastAPI + Docker | 容器调度、消息路由、用户认证 |
| **容器层** | FastAPI Agent + SDK | SDK 执行、会话管理、进度事件 |

### Agent（容器内代理）

Agent 是运行在每个 Docker 容器内的 FastAPI 服务，作为 SDK 与外界的"胶水层"：

```
WebSocket 消息 → SDKBridge → AgentHarness.run() → ProgressEvent → WebSocket 消息
```

**核心职责**：
1. 接收 WebSocket 消息
2. 转换为 SDK 调用参数
3. 执行 SDK 并捕获 ProgressEvent
4. 将事件转换为 WebSocket 消息返回

### Gateway（网关控制层）

Gateway 是统一入口，负责：

| 功能 | 说明 |
|------|------|
| **容器管理** | 动态创建/销毁用户沙箱容器 |
| **消息路由** | WebSocket 隧道：前端 ↔ Gateway ↔ 容器 |
| **用户认证** | JWT Token 验证 |
| **资源隔离** | 每个容器 2 CPU / 4GB 内存 / 10 分钟超时 |

### SDK Bridge（SDK 桥接器）

连接 WebSocket 与 Harness SDK 的核心组件：

```python
class SDKBridge:
    async def run_stream(request: MergedRequest) -> AsyncIterator[dict]:
        """
        1. 创建 AgentHarness 实例
        2. 调用 agent.run_sync(prompt, session_id, on_progress)
        3. 将 ProgressEvent 转换为 WebSocket 消息
        4. 流式返回给前端

        注意：使用 run_sync() 因为 asyncio.to_thread() 需要同步函数。
        """
```

**认证流程**: 客户端首次连接必须发送 `auth` 消息（包含 API Key），认证成功后可发送多次 `run_request`，无需重复提供 API Key。

## 数据流

### 请求处理流程

```
用户输入（Vue 组件）
    │
    ↓
WebSocket 发送 Auth（首次连接）
    │
    ↓
Container Agent 验证 API Key
    │
    ↓
返回 auth_success
    │
    ↓
WebSocket 发送 RunRequest（无需 API Key）
    │
    ↓
Gateway 创建/获取容器
    │
    ↓
WebSocket Tunnel 转发消息
    │
    ↓
Container Agent 接收消息
    │
    ↓
SDKBridge 调用 AgentHarness.run_sync()
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

## 模块依赖关系

```
                    ┌─────────────┐
                    │  Frontend   │
                    │  (Vue + TS) │
                    └──────┬──────┘
                           │ WebSocket
                           ↓
                    ┌─────────────┐
                    │   Gateway   │
                    │  (FastAPI)  │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ↓                 ↓                 ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Container  │    │  Container  │    │  Container  │
│    Agent    │    │    Agent    │    │    Agent    │
│      #1     │    │      #2     │    │      #3     │
└──────┬──────┘    └─────────────┘    └─────────────┘
       │
       ↓
┌─────────────┐
│ Harness SDK │
└─────────────┘
```

## 设计决策记录 (ADR)

### ADR-001: 为什么使用 Docker 容器隔离？

**决策**: 每个用户会话运行在独立的 Docker 容器中。

**原因**:
1. **安全隔离**: 用户代码不会影响其他用户或宿主机
2. **资源限制**: 可精确控制 CPU、内存、执行时间
3. **环境一致**: 容器内环境完全可控
4. **易于清理**: 容器销毁后所有状态自动清除

**权衡**:
- 容器启动有一定延迟（可通过预热池优化）
- 需要额外的容器管理开销

### ADR-002: 为什么使用 Vue 而非 React？

**决策**: 前端使用 Vue 3 + TypeScript。

**原因**:
1. **学习曲线**: Vue 更易上手，模板语法直观
2. **渐进式**: 可以从简单开始，逐步引入复杂特性
3. **Composition API**: 与 React Hooks 类似，但更简洁
4. **中文社区**: Vue 在国内有更活跃的中文社区

### ADR-003: 为什么使用 FastAPI 作为容器 Agent？

**决策**: 容器内使用 FastAPI 提供 WebSocket 服务。

**原因**:
1. **异步原生**: 与 SDK 的 asyncio 无缝集成
2. **WebSocket 支持**: 内置 WebSocket 端点
3. **性能**: 高并发处理能力
4. **类型安全**: Pydantic 提供运行时类型验证

### ADR-004: 容器隔离级别选择

**背景**: Docker 容器共享宿主机内核，存在容器逃逸风险。2025年11月发现3个 runc 漏洞。

**决策**: MVP 阶段使用 Hardened Container，生产环境考虑 Kata/gVisor。

**隔离级别对比**：

| 级别 | 技术 | 安全强度 | 适用场景 |
|------|------|---------|---------|
| microVM | Firecracker, Kata | 最强 | 多租户、不可信代码 |
| gVisor | 用户空间内核 | 中强 | 计算密集型 |
| Hardened Container | seccomp + AppArmor | 基础 | 可信代码 |

**MVP 阶段必须实现**：
- 进程数限制 (`pids_limit=100`)
- **内部网络隔离**（使用 Docker 内部桥接网络 `harness-net`）
- CPU/Memory 限制
- 只读文件系统 + tmpfs 挂载

**生产阶段建议**：
- 配置 seccomp profile
- 配置 AppArmor profile
- 考虑 Kata Containers 或 gVisor

### ADR-005: JWT Token 有效期

**决策**: Token 有效期设为 15 分钟，配合刷新机制。

**原因**:
1. **安全最佳实践**: 短期 Token 减少泄露风险
2. **业界标准**: OAuth 2.0 推荐短期 Access Token + 长期 Refresh Token
3. **平衡用户体验**: 15 分钟内无需重新登录

**实现**：
```python
def create_token(user_id: str) -> str:
    return jwt.encode({
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }, secret)
```

### ADR-006: WebSocket 心跳检测

**决策**: 客户端每 30 秒发送心跳，90 秒无响应视为断线。

**原因**:
1. **检测僵尸连接**: 网络中断后 TCP 可能不会立即感知
2. **及时清理资源**: 断线后快速释放容器资源
3. **保持连接活跃**: 防止中间代理（如 Nginx）超时断开

**配置**：
| 参数 | 值 | 说明 |
|------|---|------|
| HEARTBEAT_INTERVAL | 30秒 | 心跳间隔 |
| HEARTBEAT_TIMEOUT | 90秒 | 超时阈值（`AgentConfig.heartbeat_timeout`，默认 90.0） |
| MAX_RECONNECT | 5 | 最大重连次数 |
| 重连策略 | 指数退避 | 1s, 2s, 4s, 8s, 16s |

### ADR-007: Docker Socket 安全策略（修订）

> ⚠️ **评审意见修复**：直接挂载 `docker.sock` 存在严重的提权风险。

**背景**: Gateway 通过挂载 `/var/run/docker.sock` 调用 Docker API。如果 Gateway 被攻破，攻击者可获取宿主机 root 权限。

**决策**: 分层安全策略

**MVP 阶段（短期）**：
1. Gateway 容器以**非 root 用户**运行
2. docker.sock 只读挂载
3. 严格限制外网对 Gateway API 的非鉴权访问
4. **用户 GID 映射**：容器用户加入 docker 组，匹配宿主机 docker 组 GID

**生产阶段（长期）**：
1. 引入轻量级容器编排代理层（如 Podman API）
2. 或升级为 Docker Rootless 模式
3. 考虑使用 Kubernetes 替代直接 Docker API

#### Docker.sock 权限配置实现

**原理**：docker.sock 的组权限是 `docker`（gid=1001），容器用户必须在该组内才能访问。

```dockerfile
# gateway.Dockerfile
# 创建 docker 组（gid 匹配宿主机）
RUN groupadd -g 1001 docker && \
    useradd -m -u 1000 -G docker marcowong

# 设置目录权限
RUN chown -R marcowong:marcowong /app

# 以非 root 用户运行
USER marcowong
```

**权限映射**：
```
宿主机                        容器内
─────────────────────────────────────────
docker.sock → gid=1001    →   docker 组 gid=1001
marcowong  → uid=1000     →   marcowong uid=1000
           → groups=1001  →   groups=1001 (docker)
```

**注意**：GID/UID 值需与宿主机匹配。不同部署环境可能需要调整：
- 开发环境：固定 gid=1001, uid=1000
- 生产环境：通过环境变量或构建参数动态配置

### ADR-008: 网络隔离策略（修订）

> ⚠️ **评审意见修复**：`network_mode: none` 会导致网关无法连接容器。

**背景**: 原设计使用 `network_mode="none"` 完全隔离网络，但这会导致网关无法通过 WebSocket 连接容器内的 FastAPI。

**决策**: 使用 Docker 内部桥接网络（不配置 `internal=True`，保留出站访问，因为 Agent 需要访问外部 LLM API）

**实现方案**：
```python
# 1. 创建专用内部网络（注意：不使用 internal=True，Agent 需要访问 LLM API）
network = client.networks.create("harness-net", driver="bridge")

# 2. 容器加入内部网络
container = client.containers.run(image, network="harness-net", ...)
```

### ADR-009: SDK 调用线程模型（修订）

> ⚠️ **评审意见修复**：`asyncio.run_coroutine_threadsafe` 在高并发下可能导致事件循环死锁。

**背景**: 原实现在 SDK 回调中使用 `asyncio.run_coroutine_threadsafe`，在多租户高并发时易导致死锁。

**决策**: 使用 `asyncio.to_thread()` + 同步队列

**实现方案**：
```python
# 使用同步队列（线程安全）
events_queue: queue.Queue = queue.Queue()

def on_progress(event):
    events_queue.put(event)  # 同步方法

# 在线程池中执行同步 SDK
await asyncio.to_thread(run_agent_sync)
```

### ADR-010: 多实例限流策略（新增）

**背景**: 内存版 Rate Limiter 在 K8s 多副本部署（`replicas: 2`）下会失效。

**决策**: 使用 Redis 滑动窗口限流

**实现方案**：
```python
class RedisRateLimiter:
    def check(self, user_id: str) -> bool:
        # Redis 滑动窗口算法
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        # ...
```

## 参考资源

- [Harness SDK 文档](../../sdk/docs/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Vue 3 文档](https://cn.vuejs.org/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [AI Agent Sandboxing - Northflank](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Security for AI Agents - Obsidian Security](https://www.obsidiansecurity.com/blog/security-for-ai-agents)

## 下一步

- [02-agent.md](./02-agent.md) - Agent 胶水层设计
- [03-gateway.md](./03-gateway.md) - Gateway 控制层设计
- [06-deployment.md](./06-deployment.md) - 部署指南
