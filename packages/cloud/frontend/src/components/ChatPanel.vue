<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useSessionStore } from '@/stores/sessionStore'
import { useSettingsStore } from '@/stores/settingsStore'
import MessageList from './MessageList.vue'
import InputArea from './InputArea.vue'

const props = defineProps<{
  sessionId: string
}>()

const settingsStore = useSettingsStore()
const sessionStore = useSessionStore()

// Only initialize WebSocket when sessionId is non-empty
const sessionIdRef = ref(props.sessionId)
const { connect, on, send, isConnected } = useWebSocket(sessionIdRef.value)

const input = ref('')
const messagesContainer = ref<HTMLDivElement | null>(null)

// Auto-scroll to bottom
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Watch for new messages
watch(
  () => sessionStore.messages.length,
  () => scrollToBottom()
)

watch(
  () => sessionStore.streamingText,
  () => scrollToBottom()
)

// Watch sessionId changes
watch(
  () => props.sessionId,
  (newId) => {
    sessionIdRef.value = newId
  }
)

// Setup message handlers and connect only when sessionId is valid
onMounted(() => {
  // Don't connect if sessionId is empty
  if (!props.sessionId) {
    console.warn('[ChatPanel] sessionId is empty, waiting...')
    return
  }

  // Register WebSocket message handlers
  on('stream_chunk', (payload: unknown) => {
    const p = payload as { content: string }
    sessionStore.appendStreamingText(p.content)
  })

  on('tool_call', (payload: unknown) => {
    sessionStore.setCurrentToolCall(payload as any)
  })

  on('tool_result', (payload: unknown) => {
    const result = payload as { tool_name: string; success: boolean; result: string; error?: string }
    sessionStore.setToolResult(result)
  })

  on('progress', (payload: unknown) => {
    const p = payload as { event_type: string; data?: { content?: string } }
    const eventType = p.event_type
    // Handle LLM response from progress events
    if (eventType === 'llm_response' || eventType === 'loop_end') {
      const content = p.data?.content
      if (content) {
        sessionStore.appendStreamingText(content)
      }
    }
  })

  on('run_result', (payload: unknown) => {
    const p = payload as { token_usage?: { input: number; output: number } }
    sessionStore.setRunning(false)
    sessionStore.finalizeStreamingText()
    if (p.token_usage) {
      sessionStore.updateTokenUsage(p.token_usage.input, p.token_usage.output)
    }
  })

  on('error', (payload: unknown) => {
    const p = payload as { error: string }
    console.error('Error:', p)
    sessionStore.setRunning(false)
    sessionStore.addMessage('assistant', `❌ Error: ${p.error}`)
  })

  // Connect WebSocket with auth
  const token = 'test-token' // Gateway accepts any token in test mode
  console.log('[ChatPanel] Connecting with sessionId:', props.sessionId)
  connect(token, settingsStore.getAuthPayload())
})

// Send message
function handleSend() {
  if (!input.value.trim() || sessionStore.isRunning || !isConnected.value) return

  const userMessage = input.value.trim()
  sessionStore.addMessage('user', userMessage)
  sessionStore.setRunning(true)
  sessionStore.clearStreamingText()
  input.value = ''

  send('run_request', {
    prompt: userMessage,
    session_id: props.sessionId,
  })
}

// Interrupt
function handleInterrupt() {
  send('interrupt', {})
  sessionStore.setRunning(false)
}
</script>

<template>
  <div class="flex flex-col h-full bg-dark-bg rounded-xl border border-dark-border overflow-hidden">
    <!-- Messages area -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4"
    >
      <!-- Empty state -->
      <div
        v-if="sessionStore.messages.length === 0 && !sessionStore.streamingText"
        class="flex flex-col items-center justify-center h-full text-gray-500"
      >
        <p class="text-lg mb-2">Start a conversation</p>
        <p class="text-sm">Type a message below to begin</p>
      </div>

      <!-- Messages -->
      <MessageList
        v-else
        :messages="sessionStore.messages"
        :streaming-text="sessionStore.streamingText"
        :current-tool-call="sessionStore.currentToolCall"
        :tool-call-history="sessionStore.toolCallHistory"
      />
    </div>

    <!-- Token usage -->
    <div
      v-if="sessionStore.tokenUsage.input > 0 || sessionStore.tokenUsage.output > 0"
      class="px-4 py-2 text-xs text-gray-500 border-t border-dark-border bg-dark-surface"
    >
      Tokens: {{ sessionStore.tokenUsage.input }} in / {{ sessionStore.tokenUsage.output }} out
    </div>

    <!-- Input area -->
    <InputArea
      v-model="input"
      :disabled="!isConnected"
      :is-running="sessionStore.isRunning"
      @send="handleSend"
      @interrupt="handleInterrupt"
    />
  </div>
</template>