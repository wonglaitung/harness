# 02 - Agent 胶水层

## 概述

Agent 是运行在每个 Docker 沙箱容器内的 FastAPI 服务，负责连接 WebSocket 与 Harness SDK。

**协议版本**: v2 (Auth-First Protocol)

**核心原则**: 客户端首次连接后必须先认证，认证成功后可发送多次执行请求，无需重复提供 API Key。

## 目录结构

```
src/harness_cloud/agent/
├── __init__.py
├── main.py           # FastAPI 入口
├── sdk_bridge.py     # SDK 集成层
├── session_sync.py   # 会话状态同步
└── config.py         # Agent 配置
```

## SDKBridge - 核心组件

### 类定义

```python
from harness import (
    AgentHarness,
    HarnessConfig,
    ProgressEvent,
    ProgressEventType,
    ReadTool,
    WriteTool,
    GlobTool,
    GrepTool,
    BashTool,
    WebSearchTool,
    WebFetchTool,
    WebToMarkdownTool,
)
from harness_cloud.agent.config import AgentConfig


class SDKBridge:
    """
    连接 WebSocket 与 Harness SDK
    
    核心职责：
    1. 接收 WebSocket 消息
    2. 转换为 SDK 调用参数
    3. 执行 SDK 并捕获 ProgressEvent
    4. 将事件转换为 WebSocket 消息返回
    """
    
    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()
        self.workspace = Path(self.config.workspace)
        self.agent: AgentHarness | None = None
        self._interrupt_flag = False
        self._current_session_id: str | None = None
```

### 创建 Agent

```python
def _create_agent(self, request: MergedRequest) -> AgentHarness:
    """根据合并后的请求配置创建 AgentHarness"""
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
        WebSearchTool(),
        WebFetchTool(),
        WebToMarkdownTool(),
    ]

    return AgentHarness(config=config, tools=tools)
```

### 流式执行

```python
async def run_stream(self, request: MergedRequest) -> AsyncIterator[dict]:
    """
    执行任务并流式返回事件

    这是核心方法：
    1. 创建 AgentHarness
    2. 设置 on_progress 回调
    3. 执行 agent.run_sync()
    4. 将 ProgressEvent 转换为 WebSocket 消息

    ⚠️ 注意：使用 run_sync() 而非 run()，因为 asyncio.to_thread() 需要同步函数。
    """
    self.agent = self._create_agent(request)
    self._current_session_id = request.session_id
    self._interrupt_flag = False

    # 使用同步队列（线程安全）
    import queue
    events_queue: queue.Queue = queue.Queue()

    def on_progress(event: ProgressEvent):
        """SDK progress callback - 同步方法"""
        events_queue.put(event)

    def run_agent_sync():
        """同步执行 agent（在线程池中运行）"""
        try:
            result = self.agent.run_sync(
                prompt=request.prompt,
                session_id=request.session_id,
                on_progress=on_progress,
            )
            events_queue.put(("result", result))
        except Exception as e:
            events_queue.put(("error", str(e)))

    # 使用 asyncio.to_thread 在线程池中执行同步 SDK
    agent_task = asyncio.create_task(asyncio.to_thread(run_agent_sync))
    
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

### ProgressEvent 映射

```python
def _translate_event(self, event: ProgressEvent) -> dict:
    """
    将 SDK ProgressEvent 转换为 WebSocket 消息
    
    映射规则：
    - TOOL_CALL → tool_call
    - TOOL_RESULT → tool_result
    - TEXT_CHUNK → stream_chunk
    - 其他 → progress
    """
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

## FastAPI WebSocket 端点

### main.py

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import asyncio

from harness_cloud.agent.config import AgentConfig
from harness_cloud.agent.sdk_bridge import SDKBridge
from harness_cloud.common.messages import (
    AuthFailed,
    AuthRequest,
    AuthSuccess,
    MessageEnvelope,
    MessageType,
    RunRequest,
    create_message,
)


config = AgentConfig()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化"""
    setup_memory_limit()
    yield


app = FastAPI(title="Harness Container Agent", lifespan=lifespan)


@app.websocket("/ws/run")
async def websocket_run(websocket: WebSocket):
    """
    主 WebSocket 端点

    协议流程（Auth-First Protocol）：
    1. Client 发送 auth 消息（包含 API Key）
    2. Agent 验证后响应 auth_success 或 auth_failed
    3. Client 发送 run_request（无需 API Key）
    4. Agent 流式发送 ProgressEvent，返回 run_result

    心跳机制：
    - Client 发送 ping
    - Agent 响应 pong
    - 检测超时断线
    """
    await websocket.accept()
    bridge = SDKBridge(config)
    session_id = None
    authenticated = False
    auth_config: AuthRequest | None = None

    # 心跳检测
    last_ping = asyncio.get_event_loop().time()
    HEARTBEAT_TIMEOUT = config.heartbeat_timeout
    _closed = False

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
                    pass
                return

    heartbeat_task = asyncio.create_task(heartbeat_monitor())

    try:
        while True:
            raw_data = await websocket.receive_text()
            envelope = MessageEnvelope.model_validate_json(raw_data)

            # 处理心跳
            if envelope.type == MessageType.PING:
                last_ping = asyncio.get_event_loop().time()
                await websocket.send_json({"type": "pong"})
                continue

            # 处理认证
            if envelope.type == MessageType.AUTH:
                if authenticated:
                    logger.warning("Received auth while already authenticated")
                    continue

                try:
                    auth_request = AuthRequest.model_validate(envelope.payload)
                    if not auth_request.api_key:
                        await websocket.send_json(
                            create_message(
                                MessageType.AUTH_FAILED,
                                AuthFailed(
                                    error="API key is required",
                                    error_code="INVALID_API_KEY",
                                ),
                            )
                        )
                        continue

                    # 存储 auth 配置
                    auth_config = auth_request
                    authenticated = True

                    await websocket.send_json(
                        create_message(
                            MessageType.AUTH_SUCCESS,
                            AuthSuccess(
                                provider=auth_config.provider,
                                model=auth_config.model,
                            ),
                        )
                    )
                    logger.info(f"Authenticated: provider={auth_config.provider}")

                except Exception as e:
                    logger.error(f"Auth validation error: {e}")
                    await websocket.send_json(
                        create_message(
                            MessageType.AUTH_FAILED,
                            AuthFailed(
                                error=str(e),
                                error_code="INVALID_AUTH_PAYLOAD",
                            ),
                        )
                    )
                continue

            # 处理 run_request（需要先认证）
            if envelope.type == MessageType.RUN_REQUEST:
                if not authenticated or not auth_config:
                    await websocket.send_json(
                        create_message(
                            MessageType.ERROR,
                            {"error": "Not authenticated. Send auth message first.", "error_code": "NOT_AUTHENTICATED"},
                        )
                    )
                    continue

                try:
                    request = RunRequest.model_validate(envelope.payload)
                    session_id = request.session_id

                    # 合并 auth 配置与 run request
                    merged_request = auth_config.merge_with_request(request)

                    # 发送确认
                    await websocket.send_json(
                        create_message(MessageType.ACK, {"session_id": session_id})
                    )

                    # 流式执行
                    async for event in bridge.run_stream(merged_request):
                        await websocket.send_json(event)

                except Exception as e:
                    logger.error(f"Run request error: {e}")
                    await websocket.send_json(
                        create_message(
                            MessageType.ERROR,
                            {"error": str(e), "error_code": "INVALID_RUN_REQUEST"},
                        )
                    )
                continue

            # 处理中断
            if envelope.type == MessageType.INTERRUPT:
                bridge.interrupt()
                await websocket.send_json(create_message(MessageType.INTERRUPTED, {}))
                continue

            # 未知消息类型
            logger.warning(f"Unknown message type: {envelope.type}")
            await websocket.send_json(
                create_message(
                    MessageType.ERROR,
                    {"error": f"Unknown message type: {envelope.type}", "error_code": "UNKNOWN_MESSAGE_TYPE"},
                )
            )

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

## 内存软限制配置（修订）

> ⚠️ **评审意见**：防止 OOM Killer 硬杀进程导致前端无错误提示。
>
> **Python resource 限制的局限性**：
> 1. C 扩展（如 numpy）可能无法正确捕获 MemoryError
> 2. 子进程（如 BashTool 执行命令）不受此限制
> 3. 进程仍可能被 Linux OOM Killer 直接杀死（SIGKILL）
>
> **解决方案**：
> - 保留此软限制作为第一道防线
> - 依赖 Docker/K8s 的 mem_limit（硬限制）作为兜底
> - Gateway 的 _cleanup_loop 需处理容器被 OOM Kill 后的清理

```python
# agent/main.py 启动时设置内存软限制

import resource


def setup_memory_limit():
    """
    设置进程内存软限制

    当内存超过 3.8GB 时，Python 会抛出 MemoryError，
    而不是被 Linux OOM Killer 硬杀（-9）。
    这样 SDKBridge 可以捕获并转换为友好的 WebSocket 错误消息。
    """
    try:
        # 软限制 3.8GB，硬限制 4GB
        soft_limit = 3800 * 1024 * 1024  # 3.8GB
        hard_limit = 4000 * 1024 * 1024  # 4GB
        resource.setrlimit(resource.RLIMIT_AS, (soft_limit, hard_limit))
        logger.info(f"Memory limit set: soft={soft_limit}, hard={hard_limit}")
    except Exception as e:
        logger.warning(f"Failed to set memory limit: {e}")


# 在 lifespan 中调用
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_memory_limit()
    yield
```

### 内存超限时的错误处理

```python
# 在 SDKBridge.run_stream 中捕获 MemoryError

async def run_stream(self, request: MergedRequest) -> AsyncIterator[dict]:
    try:
        # ... agent 执行逻辑
    except MemoryError:
        yield {
            "type": MessageType.ERROR,
            "payload": {
                "error": "内存不足：任务需要超过 3.8GB 内存，请减少数据量或联系管理员",
                "error_code": "MEMORY_LIMIT",
            },
        }
    except Exception as e:
        yield {
            "type": MessageType.ERROR,
            "payload": {"error": str(e)},
        }
```

## 配置

### config.py

```python
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Agent 配置"""
    
    workspace: str = "/workspace"
    default_model: str = "claude-sonnet-4-6"
    default_max_iterations: int = 10
    default_temperature: float = 1.0
    
    # API Key 可通过环境变量设置
    # ANTHROPIC_API_KEY 或 OPENAI_API_KEY
```

## 容器启动命令

```bash
uvicorn harness_cloud.agent.main:app --host 0.0.0.0 --port 8000
```

## 复用 SDK 模式

Agent 的设计参考了桌面客户端的 `ChatController`：

| ChatController | SDKBridge |
|----------------|-----------|
| `initialize()` | `_create_agent()` |
| `send_message()` | `run_stream()` |
| `on_progress` 回调 | `_translate_event()` |
| `session_manager` | 容器内 SessionManager |

**关键差异**：
- ChatController 连接 PyQt6 UI → SDKBridge 连接 WebSocket
- ChatController 使用 Qt 信号 → SDKBridge 使用 asyncio.Queue
- ChatController 在本地运行 → SDKBridge 在容器内运行

## 错误处理

```python
async def run_stream(self, request: MergedRequest) -> AsyncIterator[dict]:
    try:
        # ... agent execution
    except ValueError as e:
        yield {
            "type": MessageType.ERROR,
            "payload": {"error": f"配置错误: {str(e)}"},
        }
    except Exception as e:
        yield {
            "type": MessageType.ERROR,
            "payload": {"error": f"执行错误: {type(e).__name__}: {str(e)}"},
        }
```

## 中断支持

```python
def interrupt(self):
    """请求中断执行"""
    self._interrupt_flag = True
    if self.agent:
        self.agent.interrupt()
```

## 验证测试

### 本地测试

```bash
# 1. 直接运行 Agent（无需容器）
cd packages/cloud
uv run uvicorn harness_cloud.agent.main:app --reload --port 8000

# 2. WebSocket 测试
wscat -c ws://localhost:8000/ws/run

# 3. 认证（必须先执行）
> {"type": "auth", "payload": {"api_key": "sk-ant-xxx", "provider": "anthropic"}}
< {"type": "auth_success", "payload": {"provider": "anthropic", "model": "claude-sonnet-4-6"}}

# 4. 发送请求（无需再提供 API Key）
> {"type": "run_request", "payload": {"prompt": "Hello"}}
```

### 预期响应流程

```
→ {"type": "auth", "payload": {"api_key": "...", "provider": "anthropic"}}
← {"type": "auth_success", "payload": {"provider": "anthropic", "model": "claude-sonnet-4-6"}}
→ {"type": "run_request", "payload": {"prompt": "Hello"}}
← {"type": "ack", "payload": {"session_id": null}}
← {"type": "progress", "payload": {"event_type": "loop_start"}}
← {"type": "progress", "payload": {"event_type": "llm_call"}}
← {"type": "stream_chunk", "payload": {"content": "Hello"}}
← {"type": "stream_chunk", "payload": {"content": "!"}}
← {"type": "run_result", "payload": {"status": "completed", "content": "Hello!"}}
```

## 下一步

- [01-overview.md](./01-overview.md) - 了解 Cloud 整体架构
- [03-gateway.md](./03-gateway.md) - 了解 Gateway 控制层设计
- [05-messages.md](./05-messages.md) - 了解 WebSocket 消息协议