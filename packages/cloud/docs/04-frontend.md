# 04 - 前端开发

## 概述

前端使用 Vue 3 + TypeScript + Vite 构建，通过 WebSocket 与后端通信，提供与桌面客户端类似的交互体验。

## 目录结构

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
│
└── src/
    ├── main.ts              # 入口
    ├── App.vue              # 根组件
    │
    ├── api/                 # API 层
    │   ├── websocket.ts     # WebSocket 客户端
    │   ├── gateway.ts       # Gateway REST API
    │   └── types.ts         # TypeScript 类型
    │
    ├── components/          # Vue 组件
    │   ├── ChatPanel.vue    # 对话面板
    │   ├── MessageList.vue  # 消息列表
    │   ├── MessageBubble.vue # 单条消息
    │   ├── InputArea.vue    # 输入框
    │   ├── ToolCallDisplay.vue # 工具调用
    │   └── SettingsPanel.vue # 设置
    │
    ├── stores/              # Pinia 状态管理
    │   ├── sessionStore.ts  # 会话状态
    │   └── settingsStore.ts # 设置状态
    │
    ├── composables/         # Vue Composition API
    │   ├── useWebSocket.ts  # WebSocket Hook
    │   └── useAgent.ts      # Agent 控制 Hook
    │
    └── styles/
        └── main.css         # 全局样式
```

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4+ | 框架 |
| TypeScript | 5.0+ | 类型安全 |
| Vite | 5.0+ | 构建工具 |
| Pinia | 2.0+ | 状态管理 |
| Vue Router | 4.0+ | 路由 |
| TailwindCSS | 3.0+ | 样式 |

## TypeScript 类型定义

### api/types.ts

```typescript
/**
 * WebSocket 消息类型
 */
export enum MessageType {
  // 请求类
  RUN_REQUEST = "run_request",
  INTERRUPT = "interrupt",
  
  // 响应类
  ACK = "ack",
  RUN_RESULT = "run_result",
  STREAM_CHUNK = "stream_chunk",
  TOOL_CALL = "tool_call",
  TOOL_RESULT = "tool_result",
  PROGRESS = "progress",
  ERROR = "error",
}

/**
 * 消息包装格式
 */
export interface MessageEnvelope {
  type: MessageType;
  payload: Record<string, any>;
  timestamp?: string;
}

/**
 * 执行请求
 */
export interface RunRequest {
  prompt: string;
  session_id?: string;
  model: string;
  max_iterations: number;
  temperature: number;
  system_prompt?: string;
}

/**
 * 执行结果
 */
export interface RunResult {
  status: string;
  content: string;
  iterations: number;
  token_usage: {
    input: number;
    output: number;
  };
}

/**
 * 工具调用事件
 */
export interface ToolCallEvent {
  tool_name: string;
  tool_call_id: string;
  arguments: Record<string, any>;
}

/**
 * 工具执行结果
 */
export interface ToolResultEvent {
  tool_name: string;
  success: boolean;
  result: string;
  error?: string;
}

/**
 * 消息
 */
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}
```

## WebSocket 客户端（含心跳检测）

### composables/useWebSocket.ts

> ⚠️ **修订**：Token 通过首条消息传递，避免 URL 参数泄露。

```typescript
import { ref, onUnmounted } from 'vue'
import { MessageType, MessageEnvelope } from '@/api/types'

export function useWebSocket(sessionId: string) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const handlers = new Map<MessageType, Function[]>()

  // 心跳检测配置
  const HEARTBEAT_INTERVAL = 30000  // 30秒
  const HEARTBEAT_TIMEOUT = 60000   // 60秒超时
  const MAX_RECONNECT_ATTEMPTS = 5

  let lastHeartbeat = Date.now()
  let heartbeatTimer: number | null = null
  let reconnectAttempts = 0

  /**
   * 连接 WebSocket（修订：Token 通过首条消息传递）
   */
  function connect(token: string) {
    // 不在 URL 中传递 Token
    const url = `${import.meta.env.VITE_GATEWAY_URL}/ws/session/${sessionId}`
    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      // 连接后立即发送鉴权消息
      ws.value!.send(JSON.stringify({ type: 'auth', token: token }))
    }

    ws.value.onmessage = (event) => {
      try {
        const envelope: MessageEnvelope = JSON.parse(event.data)

        // 处理鉴权成功响应
        if (envelope.type === 'auth_success' as MessageType) {
          isConnected.value = true
          reconnectAttempts = 0
          startHeartbeat()
          console.log('WebSocket authenticated')
          return
        }

        // 处理鉴权失败
        if (envelope.type === 'error' as MessageType && envelope.payload?.error_code === 'AUTH_FAILED') {
          console.error('Authentication failed')
          ws.value?.close()
          return
        }

        // 处理心跳响应
        if (envelope.type === 'pong' as MessageType) {
          lastHeartbeat = Date.now()
          return
        }

        handleMessage(envelope)
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }

    ws.value.onclose = (event) => {
      isConnected.value = false
      stopHeartbeat()
      console.log('WebSocket closed:', event.code, event.reason)

      // 自动重连
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        scheduleReconnect(token)
      }
    }
  }
      try {
        const envelope: MessageEnvelope = JSON.parse(event.data)
        
        // 处理心跳响应
        if (envelope.type === 'pong' as MessageType) {
          lastHeartbeat = Date.now()
          return
        }
        
        handleMessage(envelope)
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }
    
    ws.value.onclose = (event) => {
      isConnected.value = false
      stopHeartbeat()
      console.log('WebSocket closed:', event.code, event.reason)
      
      // 自动重连
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        scheduleReconnect(token)
      }
    }
    
    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }
  
  /**
   * 启动心跳检测
   */
  function startHeartbeat() {
    heartbeatTimer = window.setInterval(() => {
      if (ws.value?.readyState === WebSocket.OPEN) {
        // 发送心跳
        ws.value.send(JSON.stringify({ type: 'ping', payload: {} }))
        
        // 检查超时
        if (Date.now() - lastHeartbeat > HEARTBEAT_TIMEOUT) {
          console.warn('Heartbeat timeout, reconnecting...')
          ws.value.close()
        }
      }
    }, HEARTBEAT_INTERVAL)
  }
  
  /**
   * 停止心跳检测
   */
  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }
  
  /**
   * 计划重连（指数退避）
   */
  function scheduleReconnect(token: string) {
    reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
    
    console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`)
    
    setTimeout(() => {
      connect(token)
    }, delay)
  }
  
  /**
   * 注册消息处理器
   */
  function on(type: MessageType, handler: Function) {
    const existing = handlers.get(type) || []
    handlers.set(type, [...existing, handler])
  }
  
  /**
   * 发送消息
   */
  function send(type: MessageType, payload: any) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, payload }))
    }
  }
  
  /**
   * 处理收到的消息
   */
  function handleMessage(envelope: MessageEnvelope) {
    const callbacks = handlers.get(envelope.type) || []
    callbacks.forEach(cb => cb(envelope.payload))
  }
  
  /**
   * 断开连接
   */
  function disconnect() {
    stopHeartbeat()
    ws.value?.close()
    ws.value = null
  }
  
  onUnmounted(() => {
    disconnect()
  })
  
  return {
    connect,
    disconnect,
    on,
    send,
    isConnected,
  }
}
```

### 心跳检测机制说明

| 配置项 | 值 | 说明 |
|-------|---|------|
| HEARTBEAT_INTERVAL | 30秒 | 每30秒发送一次心跳 |
| HEARTBEAT_TIMEOUT | 60秒 | 60秒无响应视为断线 |
| MAX_RECONNECT_ATTEMPTS | 5 | 最大重连次数 |
| 重连延迟 | 指数退避 | 1s, 2s, 4s, 8s, 16s |

**流程**：
```
客户端 ──ping──> 服务端
客户端 <──pong── 服务端
        ↓
更新 lastHeartbeat
        ↓
检查是否超时 (60秒无响应)
        ↓
超时则触发重连
```

## Pinia 状态管理

### stores/sessionStore.ts

```typescript
import { defineStore } from 'pinia'
import { Message } from '@/api/types'

export const useSessionStore = defineStore('session', {
  state: () => ({
    sessionId: null as string | null,
    messages: [] as Message[],
    tokenUsage: { input: 0, output: 0 },
    isRunning: false,
  }),
  
  getters: {
    messageCount: (state) => state.messages.length,
  },
  
  actions: {
    setSessionId(id: string) {
      this.sessionId = id
    },
    
    addMessage(role: 'user' | 'assistant', content: string) {
      this.messages.push({
        id: crypto.randomUUID(),
        role,
        content,
        timestamp: new Date(),
      })
    },
    
    updateTokenUsage(input: number, output: number) {
      this.tokenUsage.input += input
      this.tokenUsage.output += output
    },
    
    clearMessages() {
      this.messages = []
      this.tokenUsage = { input: 0, output: 0 }
    },
    
    setRunning(running: boolean) {
      this.isRunning = running
    },
  },
})
```

## Vue 组件

### ChatPanel.vue

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useSessionStore } from '@/stores/sessionStore'
import { MessageType } from '@/api/types'
import MessageList from './MessageList.vue'
import InputArea from './InputArea.vue'
import ToolCallDisplay from './ToolCallDisplay.vue'

const props = defineProps<{
  sessionId: string
  token: string
}>()

const store = useSessionStore()
const { connect, on, send, isConnected } = useWebSocket(props.sessionId)

const input = ref('')
const streamingText = ref('')
const currentToolCall = ref<any>(null)

// 设置消息处理器
on(MessageType.STREAM_CHUNK, (payload) => {
  streamingText.value += payload.content
})

on(MessageType.TOOL_CALL, (payload) => {
  currentToolCall.value = payload
})

on(MessageType.TOOL_RESULT, () => {
  currentToolCall.value = null
})

on(MessageType.RUN_RESULT, (payload) => {
  store.addMessage('assistant', payload.content)
  store.setRunning(false)
  streamingText.value = ''
})

on(MessageType.ERROR, (payload) => {
  store.addMessage('assistant', `❌ 错误: ${payload.error}`)
  store.setRunning(false)
})

// 连接 WebSocket
onMounted(() => {
  connect(props.token)
})

// 发送消息
function handleSend() {
  if (!input.value.trim() || store.isRunning) return
  
  const userMessage = input.value.trim()
  store.addMessage('user', userMessage)
  store.setRunning(true)
  input.value = ''
  streamingText.value = ''
  
  send(MessageType.RUN_REQUEST, {
    prompt: userMessage,
    session_id: props.sessionId,
    model: 'claude-sonnet-4-6',
    max_iterations: 10,
    temperature: 1.0,
  })
}

// 中断执行
function handleInterrupt() {
  send(MessageType.INTERRUPT, {})
  store.setRunning(false)
}
</script>

<template>
  <div class="flex flex-col h-full bg-gray-50">
    <!-- 消息列表 -->
    <div class="flex-1 overflow-y-auto p-4">
      <MessageList :messages="store.messages" />
      
      <!-- 流式输出 -->
      <div v-if="streamingText" class="message assistant">
        {{ streamingText }}
      </div>
      
      <!-- 工具调用显示 -->
      <ToolCallDisplay v-if="currentToolCall" :tool-call="currentToolCall" />
    </div>
    
    <!-- Token 统计 -->
    <div class="px-4 py-2 text-sm text-gray-500 border-t bg-white">
      Tokens: {{ store.tokenUsage.input }} in / {{ store.tokenUsage.output }} out
    </div>
    
    <!-- 输入区域 -->
    <InputArea
      v-model="input"
      :disabled="store.isRunning || !isConnected"
      @send="handleSend"
      @interrupt="handleInterrupt"
    />
  </div>
</template>
```

### MessageList.vue

```vue
<script setup lang="ts">
import { Message } from '@/api/types'
import MessageBubble from './MessageBubble.vue'

defineProps<{
  messages: Message[]
}>()
</script>

<template>
  <div class="space-y-4">
    <MessageBubble
      v-for="msg in messages"
      :key="msg.id"
      :message="msg"
    />
  </div>
</template>
```

### InputArea.vue

```vue
<script setup lang="ts">
const props = defineProps<{
  modelValue: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'send': []
  'interrupt': []
}>()

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}
</script>

<template>
  <div class="p-4 border-t bg-white">
    <div class="flex gap-2">
      <textarea
        :value="modelValue"
        :disabled="disabled"
        @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
        @keydown="handleKeydown"
        placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
        class="flex-1 resize-none border rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
        rows="2"
      />
      <div class="flex flex-col gap-2">
        <button
          v-if="!disabled"
          @click="emit('send')"
          class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          发送
        </button>
        <button
          v-else
          @click="emit('interrupt')"
          class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
        >
          停止
        </button>
      </div>
    </div>
  </div>
</template>
```

## 项目配置

### package.json

```json
{
  "name": "harness-cloud-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "vue-tsc": "^2.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

### vite.config.ts

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
```

## 启动命令

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build
```