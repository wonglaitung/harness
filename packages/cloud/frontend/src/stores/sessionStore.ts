import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, ToolCallEvent } from '@/api/types'

export const useSessionStore = defineStore('session', () => {
  // State
  const sessionId = ref<string | null>(null)
  const messages = ref<Message[]>([])
  const tokenUsage = ref({ input: 0, output: 0 })
  const isRunning = ref(false)
  const streamingText = ref('')
  const currentToolCall = ref<ToolCallEvent | null>(null)

  // Computed
  const messageCount = computed(() => messages.value.length)

  // Actions
  function setSessionId(id: string) {
    sessionId.value = id
  }

  function addMessage(role: 'user' | 'assistant', content: string): Message {
    const msg: Message = {
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
  }

  function updateTokenUsage(input: number, output: number) {
    tokenUsage.value.input += input
    tokenUsage.value.output += output
  }

  function setRunning(running: boolean) {
    isRunning.value = running
  }

  function clearMessages() {
    messages.value = []
    tokenUsage.value = { input: 0, output: 0 }
    streamingText.value = ''
    currentToolCall.value = null
  }

  function reset() {
    sessionId.value = null
    messages.value = []
    tokenUsage.value = { input: 0, output: 0 }
    isRunning.value = false
    streamingText.value = ''
    currentToolCall.value = null
  }

  return {
    // State
    sessionId,
    messages,
    tokenUsage,
    isRunning,
    streamingText,
    currentToolCall,
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
    updateTokenUsage,
    setRunning,
    clearMessages,
    reset,
  }
})