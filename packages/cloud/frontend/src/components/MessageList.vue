<script setup lang="ts">
import type { ToolCallWithResult } from '@/stores/sessionStore'
import type { ToolCallEvent } from '@/api/types'
import MessageBubble from './MessageBubble.vue'

defineProps<{
  messages: Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
  }>
  streamingText?: string
  currentToolCall?: ToolCallEvent | null
  toolCallHistory?: ToolCallWithResult[]
}>()

// Format timestamp
function formatTime(date: Date): string {
  return new Date(date).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Truncate result for display
function truncateResult(result: string, maxLength: number = 300): string {
  if (result.length <= maxLength) return result
  return result.slice(0, maxLength) + '...'
}

// Check if we're in a running state (has tool calls or streaming)
function isRunning(toolCallHistory?: ToolCallWithResult[], streamingText?: string, currentToolCall?: ToolCallEvent | null): boolean {
  return (toolCallHistory && toolCallHistory.length > 0) || !!streamingText || !!currentToolCall
}
</script>

<template>
  <div class="space-y-4">
    <!-- Render all messages -->
    <template v-for="(msg, index) in messages" :key="msg.id">
      <!-- User message -->
      <MessageBubble v-if="msg.role === 'user'" :message="msg.content" is-user />

      <!-- Assistant message with timestamp -->
      <div v-else class="flex flex-col gap-2">
        <MessageBubble :message="msg.content" />
        <span class="text-xs text-gray-500 ml-4">{{ formatTime(msg.timestamp) }}</span>
      </div>

      <!-- After the LAST user message, show tool calls and streaming (if running) -->
      <!-- This ensures tools appear BEFORE the AI response -->
      <template v-if="msg.role === 'user' && index === messages.length - 1 && isRunning(toolCallHistory, streamingText, currentToolCall)">
        <!-- Tool call history (all completed tool calls) -->
        <div v-if="toolCallHistory && toolCallHistory.length > 0" class="tool-history">
          <div
            v-for="(toolCall, idx) in toolCallHistory"
            :key="idx"
            class="tool-item"
          >
            <!-- Tool call (running or completed) -->
            <div v-if="!toolCall.result" class="tool-call-card">
              <div class="flex items-center gap-2">
                <span class="tool-icon running">▶</span>
                <span class="tool-name">{{ toolCall.call.tool_name }}</span>
                <span class="tool-status running">执行中...</span>
              </div>
              <pre v-if="Object.keys(toolCall.call.arguments).length > 0" class="tool-args">
{{ JSON.stringify(toolCall.call.arguments, null, 2) }}</pre>
            </div>

            <!-- Tool result -->
            <div v-else :class="['tool-result-card', toolCall.result.success ? 'success' : 'failure']">
              <div class="flex items-center gap-2">
                <span :class="['result-icon', toolCall.result.success ? 'success' : 'failure']">
                  {{ toolCall.result.success ? '✓' : '✗' }}
                </span>
                <span class="tool-name">{{ toolCall.call.tool_name }}</span>
                <span :class="['tool-status', toolCall.result.success ? 'success' : 'failure']">
                  {{ toolCall.result.success ? '成功' : '失败' }}
                </span>
              </div>
              <pre v-if="toolCall.result.result" class="tool-result-text">
{{ truncateResult(toolCall.result.result) }}</pre>
              <p v-if="toolCall.result.error" class="tool-error">{{ toolCall.result.error }}</p>
            </div>
          </div>
        </div>

        <!-- Current running tool call (if not in history yet) -->
        <div v-if="currentToolCall && toolCallHistory && !toolCallHistory.some(t => t.call.tool_call_id === currentToolCall?.tool_call_id)" class="tool-indicator">
          <div class="tool-call-card">
            <div class="flex items-center gap-2">
              <span class="tool-icon running">▶</span>
              <span class="tool-name">{{ currentToolCall.tool_name }}</span>
              <span class="tool-status running">执行中...</span>
            </div>
            <pre v-if="Object.keys(currentToolCall.arguments).length > 0" class="tool-args">
{{ JSON.stringify(currentToolCall.arguments, null, 2) }}</pre>
          </div>
        </div>

        <!-- Streaming text (AI response) - appears AFTER tool calls -->
        <MessageBubble v-if="streamingText" :message="streamingText" />
      </template>
    </template>

    <!-- Edge case: streaming without any messages (first interaction) -->
    <template v-if="messages.length === 0 && isRunning(toolCallHistory, streamingText, currentToolCall)">
      <!-- Tool calls -->
      <div v-if="toolCallHistory && toolCallHistory.length > 0" class="tool-history">
        <div
          v-for="(toolCall, idx) in toolCallHistory"
          :key="idx"
          class="tool-item"
        >
          <div v-if="!toolCall.result" class="tool-call-card">
            <div class="flex items-center gap-2">
              <span class="tool-icon running">▶</span>
              <span class="tool-name">{{ toolCall.call.tool_name }}</span>
              <span class="tool-status running">执行中...</span>
            </div>
            <pre v-if="Object.keys(toolCall.call.arguments).length > 0" class="tool-args">
{{ JSON.stringify(toolCall.call.arguments, null, 2) }}</pre>
          </div>
          <div v-else :class="['tool-result-card', toolCall.result.success ? 'success' : 'failure']">
            <div class="flex items-center gap-2">
              <span :class="['result-icon', toolCall.result.success ? 'success' : 'failure']">
                {{ toolCall.result.success ? '✓' : '✗' }}
              </span>
              <span class="tool-name">{{ toolCall.call.tool_name }}</span>
              <span :class="['tool-status', toolCall.result.success ? 'success' : 'failure']">
                {{ toolCall.result.success ? '成功' : '失败' }}
              </span>
            </div>
            <pre v-if="toolCall.result.result" class="tool-result-text">
{{ truncateResult(toolCall.result.result) }}</pre>
            <p v-if="toolCall.result.error" class="tool-error">{{ toolCall.result.error }}</p>
          </div>
        </div>
      </div>

      <!-- Current tool call -->
      <div v-if="currentToolCall && toolCallHistory && !toolCallHistory.some(t => t.call.tool_call_id === currentToolCall?.tool_call_id)" class="tool-indicator">
        <div class="tool-call-card">
          <div class="flex items-center gap-2">
            <span class="tool-icon running">▶</span>
            <span class="tool-name">{{ currentToolCall.tool_name }}</span>
            <span class="tool-status running">执行中...</span>
          </div>
          <pre v-if="Object.keys(currentToolCall.arguments).length > 0" class="tool-args">
{{ JSON.stringify(currentToolCall.arguments, null, 2) }}</pre>
        </div>
      </div>

      <!-- Streaming -->
      <MessageBubble v-if="streamingText" :message="streamingText" />
    </template>
  </div>
</template>

<style scoped>
.tool-history {
  margin-left: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tool-item {
  max-width: 400px;
}

.tool-call-card {
  background-color: #1e3a5f;
  border-left: 3px solid #3b82f6;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
}

.tool-icon {
  font-size: 0.75rem;
}

.tool-icon.running {
  color: #60a5fa;
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.tool-name {
  color: #e2e8f0;
  font-weight: 500;
  font-size: 0.8125rem;
}

.tool-status {
  font-size: 0.6875rem;
  margin-left: auto;
}

.tool-status.running {
  color: #60a5fa;
}

.tool-status.success {
  color: #22c55e;
}

.tool-status.failure {
  color: #ef4444;
}

.tool-args {
  color: #94a3b8;
  font-size: 0.6875rem;
  margin-top: 0.375rem;
  overflow-x: auto;
  max-height: 6rem;
}

.tool-result-card {
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
}

.tool-result-card.success {
  background-color: transparent;
  border-left: 3px solid #22c55e;
}

.tool-result-card.failure {
  background-color: #3f1f1f;
  border-left: 3px solid #ef4444;
}

.result-icon {
  font-size: 0.75rem;
}

.result-icon.success {
  color: #22c55e;
}

.result-icon.failure {
  color: #ef4444;
}

.tool-result-text {
  color: #94a3b8;
  font-size: 0.6875rem;
  margin-top: 0.375rem;
  overflow-x: auto;
  max-height: 6rem;
}

.tool-error {
  color: #f87171;
  font-size: 0.6875rem;
  margin-top: 0.25rem;
}
</style>