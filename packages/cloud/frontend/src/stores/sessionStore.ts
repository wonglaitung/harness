import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ToolCallEvent, ToolResultEvent } from '@/api/types'

// Tool call with result
export interface ToolCallWithResult {
  call: ToolCallEvent
  result?: ToolResultEvent
}

// Extended message with tool calls
export interface MessageWithTools {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  toolCalls?: ToolCallWithResult[]
  isStreaming?: boolean
}

export const useSessionStore = defineStore('session', () => {
  // State
  const sessionId = ref<string | null>(null)
  const messages = ref<MessageWithTools[]>([])
  const tokenUsage = ref({ input: 0, output: 0 })
  const isRunning = ref(false)
  const streamingText = ref('')
  const currentToolCall = ref<ToolCallEvent | null>(null)
  // All tool calls in current run (cleared when run starts)
  const toolCallHistory = ref<ToolCallWithResult[]>([])

  // Computed
  const messageCount = computed(() => messages.value.length)

  // Actions
  function setSessionId(id: string) {
    sessionId.value = id
  }

  function addMessage(role: 'user' | 'assistant', content: string): MessageWithTools {
    const msg: MessageWithTools = {
      id: crypto.randomUUID(),
      role,
      content,
      timestamp: new Date(),
    }
    messages.value.push(msg)
    return msg
  }

  function updateLastAssistantMessage(content: string) {
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.content = content
    }
  }

  function appendStreamingText(text: string) {
    streamingText.value += text
  }

  function clearStreamingText() {
    streamingText.value = ''
  }

  function finalizeStreamingText() {
    if (streamingText.value) {
      addMessage('assistant', streamingText.value)
      streamingText.value = ''
    }
  }

  function setCurrentToolCall(toolCall: ToolCallEvent | null) {
    currentToolCall.value = toolCall
    if (toolCall) {
      // Add new tool call to history
      toolCallHistory.value.push({ call: toolCall })
    }
  }

  function setToolResult(result: ToolResultEvent) {
    // Update the last tool call in history with its result
    const lastToolCall = toolCallHistory.value[toolCallHistory.value.length - 1]
    if (lastToolCall && lastToolCall.call.tool_name === result.tool_name) {
      lastToolCall.result = result
    }
    // Clear current tool call indicator
    currentToolCall.value = null
  }

  function updateTokenUsage(input: number, output: number) {
    tokenUsage.value.input += input
    tokenUsage.value.output += output
  }

  function setRunning(running: boolean) {
    isRunning.value = running
    // Clear tool call history when starting a new run
    if (running) {
      toolCallHistory.value = []
    }
  }

  function clearMessages() {
    messages.value = []
    tokenUsage.value = { input: 0, output: 0 }
    streamingText.value = ''
    currentToolCall.value = null
    toolCallHistory.value = []
  }

  function reset() {
    sessionId.value = null
    messages.value = []
    tokenUsage.value = { input: 0, output: 0 }
    isRunning.value = false
    streamingText.value = ''
    currentToolCall.value = null
    toolCallHistory.value = []
  }

  return {
    // State
    sessionId,
    messages,
    tokenUsage,
    isRunning,
    streamingText,
    currentToolCall,
    toolCallHistory,
    // Computed
    messageCount,
    // Actions
    setSessionId,
    addMessage,
    updateLastAssistantMessage,
    appendStreamingText,
    clearStreamingText,
    finalizeStreamingText,
    setCurrentToolCall,
    setToolResult,
    updateTokenUsage,
    setRunning,
    clearMessages,
    reset,
  }
})