# 05 - WebSocket 消息协议

## 概述

本文档定义了前端与后端之间的 WebSocket 消息协议，包括消息类型、数据格式和交互流程。

**协议版本**: v2 (Auth-First Protocol)

**核心原则**: 客户端首次连接后必须先认证，认证成功后可发送多次执行请求，无需重复提供 API Key。

## 消息格式

### 消息包装（MessageEnvelope）

所有 WebSocket 消息都使用统一的包装格式：

```typescript
interface MessageEnvelope {
  type: MessageType;        // 消息类型
  payload: Record<string, any>;  // 消息载荷
  timestamp?: string;       // 可选时间戳
}
```

### 示例

```json
{
  "type": "auth",
  "payload": {
    "api_key": "sk-ant-xxx",
    "provider": "anthropic"
  }
}
```

## 消息类型

### 客户端 → 服务端（请求类）

| 类型 | 说明 | payload |
|------|------|---------|
| `auth` | 认证请求（首次连接必发） | `AuthRequest` |
| `run_request` | 执行任务（需先认证） | `RunRequest` |
| `interrupt` | 中断执行 | `{}` |

### 服务端 → 客户端（响应类）

| 类型 | 说明 | payload |
|------|------|---------|
| `auth_success` | 认证成功 | `AuthSuccess` |
| `auth_failed` | 认证失败 | `AuthFailed` |
| `ack` | 确认接收 | `{session_id}` |
| `run_result` | 最终结果 | `RunResult` |
| `stream_chunk` | 流式文本块 | `{content}` |
| `tool_call` | 工具调用开始 | `ToolCallEvent` |
| `tool_result` | 工具执行结果 | `ToolResultEvent` |
| `progress` | 进度事件 | `ProgressEvent` |
| `error` | 错误 | `{error}` |
| `interrupted` | 已中断 | `{}` |

## 详细定义

### AuthRequest - 认证请求（首次连接必发）

```typescript
interface AuthRequest {
  api_key: string;             // API Key（必填）
  provider?: string;           // 提供商（默认 "anthropic"）
  base_url?: string;           // 自定义 API URL（OpenAI 兼容 API）
  model?: string;              // 默认模型（默认 "claude-sonnet-4-6"）
  max_iterations?: number;     // 最大迭代次数（默认 10）
  temperature?: number;        // 温度参数（默认 1.0）
  system_prompt?: string;      // 系统提示
  tool_result_role?: string;   // 工具结果角色（默认 "tool"）
}
```

**示例**：
```json
{
  "type": "auth",
  "payload": {
    "api_key": "sk-ant-xxx",
    "provider": "anthropic"
  }
}
```

**OpenAI 兼容 API 示例**：
```json
{
  "type": "auth",
  "payload": {
    "api_key": "your-key",
    "provider": "openai",
    "base_url": "https://api.your-provider.com/v1",
    "model": "gpt-4o"
  }
}
```

### AuthSuccess - 认证成功

```typescript
interface AuthSuccess {
  provider: string;  // 确认的提供商
  model: string;     // 确认的默认模型
}
```

**示例**：
```json
{
  "type": "auth_success",
  "payload": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-6"
  }
}
```

### AuthFailed - 认证失败

```typescript
interface AuthFailed {
  error: string;       // 错误信息
  error_code: string;  // 错误码：INVALID_API_KEY, UNSUPPORTED_PROVIDER 等
}
```

**示例**：
```json
{
  "type": "auth_failed",
  "payload": {
    "error": "API key is required",
    "error_code": "INVALID_API_KEY"
  }
}
```

### RunRequest - 执行请求（需先认证）

```typescript
interface RunRequest {
  prompt: string;              // 用户输入（必填）
  session_id?: string;         // 会话 ID（可选）
  // 以下可选，未设置时使用 auth 时的配置
  model?: string;              // 覆盖默认模型
  max_iterations?: number;     // 覆盖默认迭代次数
  temperature?: number;        // 覆盖默认温度
  system_prompt?: string;      // 覆盖默认系统提示
}
```

**注意**: `api_key`、`provider`、`base_url` 等敏感信息仅在 `auth` 消息中提供，`run_request` 不再包含这些字段。

**示例**：
```json
{
  "type": "run_request",
  "payload": {
    "prompt": "读取 main.py 文件",
    "session_id": "abc123"
  }
}
```

**覆盖默认模型示例**：
```json
{
  "type": "run_request",
  "payload": {
    "prompt": "分析这个文件",
    "model": "claude-opus-4-6"
  }
}
```

### RunResult - 执行结果

```typescript
interface RunResult {
  status: string;              // 状态: "completed" | "interrupted" | "error"
  content: string;             // 最终内容
  iterations: number;          // 迭代次数
  token_usage: {
    input: number;
    output: number;
  };
  error?: string;              // 错误信息（如果有）
}
```

**示例**：
```json
{
  "type": "run_result",
  "payload": {
    "status": "completed",
    "content": "我已经读取了 main.py 文件...",
    "iterations": 2,
    "token_usage": {
      "input": 1500,
      "output": 300
    }
  }
}
```

### StreamChunk - 流式文本块

```typescript
interface StreamChunk {
  content: string;  // 文本内容
}
```

**示例**：
```json
{
  "type": "stream_chunk",
  "payload": {
    "content": "Hello"
  }
}
```

### ToolCallEvent - 工具调用

```typescript
interface ToolCallEvent {
  tool_name: string;           // 工具名称
  tool_call_id: string;        // 调用 ID
  arguments: Record<string, any>;  // 参数
}
```

**示例**：
```json
{
  "type": "tool_call",
  "payload": {
    "tool_name": "read",
    "tool_call_id": "toolu_123",
    "arguments": {
      "file_path": "/workspace/main.py"
    }
  }
}
```

### ToolResultEvent - 工具结果

```typescript
interface ToolResultEvent {
  tool_name: string;    // 工具名称
  success: boolean;     // 是否成功
  result: string;       // 结果（截断）
  error?: string;       // 错误信息
}
```

**示例**：
```json
{
  "type": "tool_result",
  "payload": {
    "tool_name": "read",
    "success": true,
    "result": "def main():\n    print('Hello')"
  }
}
```

### ProgressEvent - 进度事件

```typescript
interface ProgressEvent {
  event_type: string;          // 事件类型
  message: string;             // 消息
  data?: Record<string, any>;  // 附加数据
}
```

**event_type 取值**：

| event_type | 说明 | data |
|------------|------|------|
| `loop_start` | 循环开始 | `{}` |
| `loop_end` | 循环结束 | `{iterations}` |
| `llm_call` | LLM 调用开始 | `{}` |
| `llm_response` | LLM 响应 | `{token_usage}` |
| `iteration` | 迭代计数 | `{iteration}` |

**示例**：
```json
{
  "type": "progress",
  "payload": {
    "event_type": "iteration",
    "message": "思考中... (第 2 步)",
    "data": {
      "iteration": 2
    }
  }
}
```

## SDK ProgressEvent 映射

Harness SDK 的 `ProgressEvent` 与 WebSocket 消息的映射关系：

| SDK ProgressEventType | WebSocket MessageType | payload 字段 |
|----------------------|----------------------|-------------|
| `TOOL_CALL` | `tool_call` | `tool_name`, `tool_call_id`, `arguments` |
| `TOOL_RESULT` | `tool_result` | `tool_name`, `success`, `result`, `error` |
| `TEXT_CHUNK` | `stream_chunk` | `content` |
| `LLM_CALL` | `progress` | `event_type: "llm_call"` |
| `LLM_RESPONSE` | `progress` | `event_type: "llm_response"`, `token_usage` |
| `ITERATION` | `progress` | `event_type: "iteration"`, `iteration` |
| `LOOP_START` | `progress` | `event_type: "loop_start"` |
| `LOOP_END` | `progress` | `event_type: "loop_end"` |
| `ERROR` | `error` | `error` |

## 交互流程

### 认证流程（首次连接必须执行）

```
Client                                Server
  │                                     │
  │──── auth ──────────────────────────>│
  │     {api_key, provider, model}      │
  │                                     │
  │<──── auth_success ──────────────────│
  │     {provider, model}               │
  │                                     │
  │  ───── 或 ─────                     │
  │                                     │
  │<──── auth_failed ───────────────────│
  │     {error, error_code}             │
  │                                     │
```

### 正常执行流程（认证后）

```
Client                                Server
  │                                     │
  │──── auth ──────────────────────────>│
  │<──── auth_success ──────────────────│
  │                                     │
  │──── run_request ───────────────────>│
  │                                     │
  │<──── ack ───────────────────────────│
  │                                     │
  │<──── progress (loop_start) ─────────│
  │                                     │
  │<──── progress (llm_call) ───────────│
  │                                     │
  │<──── stream_chunk ──────────────────│
  │<──── stream_chunk ──────────────────│
  │<──── stream_chunk ──────────────────│
  │                                     │
  │<──── tool_call ─────────────────────│
  │                                     │
  │<──── tool_result ───────────────────│
  │                                     │
  │<──── progress (iteration) ──────────│
  │                                     │
  │<──── progress (llm_call) ───────────│
  │                                     │
  │<──── stream_chunk ──────────────────│
  │<──── stream_chunk ──────────────────│
  │                                     │
  │<──── run_result ────────────────────│
  │                                     │
```

### 多次请求流程（无需重复认证）

```
Client                                Server
  │                                     │
  │──── auth ──────────────────────────>│
  │<──── auth_success ──────────────────│
  │                                     │
  │──── run_request #1 ────────────────>│
  │<──── ack ───────────────────────────│
  │<──── stream_chunk ──────────────────│
  │<──── run_result ────────────────────│
  │                                     │
  │──── run_request #2 ────────────────>│  (无需再发 auth)
  │<──── ack ───────────────────────────│
  │<──── stream_chunk ──────────────────│
  │<──── run_result ────────────────────│
  │                                     │
```

### 中断执行流程

```
Client                                Server
  │                                     │
  │──── run_request ───────────────────>│
  │                                     │
  │<──── ack ───────────────────────────│
  │                                     │
  │<──── stream_chunk ──────────────────│
  │                                     │
  │──── interrupt ─────────────────────>│
  │                                     │
  │<──── interrupted ───────────────────│
  │                                     │
```

### 错误处理流程

```
Client                                Server
  │                                     │
  │──── run_request ───────────────────>│
  │                                     │
  │<──── ack ───────────────────────────│
  │                                     │
  │<──── progress (llm_call) ───────────│
  │                                     │
  │<──── error ─────────────────────────│
  │     {error: "API key invalid"}      │
  │                                     │
```

## Python 实现

### messages.py

```python
from enum import Enum
from pydantic import BaseModel
from typing import Any, Optional


class MessageType(str, Enum):
    """WebSocket 消息类型"""
    
    # 请求类
    RUN_REQUEST = "run_request"
    INTERRUPT = "interrupt"
    
    # 响应类
    ACK = "ack"
    RUN_RESULT = "run_result"
    STREAM_CHUNK = "stream_chunk"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PROGRESS = "progress"
    ERROR = "error"
    INTERRUPTED = "interrupted"


class MessageEnvelope(BaseModel):
    """消息包装"""
    type: MessageType
    payload: dict[str, Any] = {}
    timestamp: Optional[str] = None


class RunRequest(BaseModel):
    """执行请求"""
    prompt: str
    session_id: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    api_key: Optional[str] = None
    provider: str = "anthropic"
    base_url: Optional[str] = None
    max_iterations: int = 10
    temperature: float = 1.0
    system_prompt: str = ""
    tool_result_role: str = "tool"


class RunResult(BaseModel):
    """执行结果"""
    status: str
    content: str
    iterations: int
    token_usage: dict[str, int]
    error: Optional[str] = None


class StreamChunk(BaseModel):
    """流式文本块"""
    content: str


class ToolCallEvent(BaseModel):
    """工具调用事件"""
    tool_name: str
    tool_call_id: str
    arguments: dict[str, Any]


class ToolResultEvent(BaseModel):
    """工具结果事件"""
    tool_name: str
    success: bool
    result: str
    error: Optional[str] = None
```

## 验证测试

### 使用 wscat 测试

```bash
# 连接
wscat -c ws://localhost:8000/ws/run

# 发送请求
> {"type": "run_request", "payload": {"prompt": "Hello"}}

# 接收响应
< {"type": "ack", "session_id": null}
< {"type": "progress", "payload": {"event_type": "loop_start", ...}}
< {"type": "stream_chunk", "payload": {"content": "Hello"}}
< {"type": "run_result", "payload": {"status": "completed", ...}}

# 发送中断
> {"type": "interrupt", "payload": {}}
< {"type": "interrupted", "payload": {}}
```