/**
 * WebSocket message types - mapped from packages/cloud/src/harness_cloud/common/messages.py
 */

// Message type enum
export enum MessageType {
  // Client → Server (request types)
  AUTH = 'auth',
  RUN_REQUEST = 'run_request',
  INTERRUPT = 'interrupt',

  // Server → Client (response types)
  ACK = 'ack',
  AUTH_SUCCESS = 'auth_success',
  AUTH_FAILED = 'auth_failed',
  RUN_RESULT = 'run_result',
  STREAM_CHUNK = 'stream_chunk',
  TOOL_CALL = 'tool_call',
  TOOL_RESULT = 'tool_result',
  PROGRESS = 'progress',
  ERROR = 'error',
  INTERRUPTED = 'interrupted',
}

// Message envelope
export interface MessageEnvelope {
  type: MessageType | string
  payload: Record<string, unknown>
  timestamp?: string
}

// Auth request
export interface AuthRequest {
  api_key: string
  provider?: 'anthropic' | 'openai'
  base_url?: string
  model?: string
  max_iterations?: number
  temperature?: number
  system_prompt?: string
}

// Auth response
export interface AuthSuccess {
  provider: string
  model: string
}

export interface AuthFailed {
  error: string
  error_code: string
}

// Run request
export interface RunRequest {
  prompt: string
  session_id?: string
  model?: string
  max_iterations?: number
  temperature?: number
  system_prompt?: string
}

// Run result
export interface RunResult {
  status: 'completed' | 'interrupted' | 'error'
  content: string
  iterations: number
  token_usage: {
    input: number
    output: number
  }
  error?: string
}

// Stream chunk
export interface StreamChunk {
  content: string
}

// Tool call event
export interface ToolCallEvent {
  tool_name: string
  tool_call_id: string
  arguments: Record<string, unknown>
}

// Tool result event
export interface ToolResultEvent {
  tool_name: string
  success: boolean
  result: string
  error?: string
}

// Progress event
export interface ProgressEvent {
  event_type: string
  message: string
  data: Record<string, unknown>
}

// Error event
export interface ErrorEvent {
  error: string
  error_code?: string
}

// Message for UI
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  toolCalls?: ToolCallEvent[]
  isStreaming?: boolean
}
