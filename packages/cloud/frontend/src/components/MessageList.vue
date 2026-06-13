<script setup lang="ts">
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
}>()

// Format timestamp
function formatTime(date: Date): string {
  return new Date(date).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="space-y-4">
    <!-- Message bubbles -->
    <div
      v-for="msg in messages"
      :key="msg.id"
      class="flex flex-col gap-1"
    >
      <!-- User message -->
      <MessageBubble v-if="msg.role === 'user'" :message="msg.content" is-user />

      <!-- Assistant message -->
      <div v-else class="flex flex-col gap-2">
        <MessageBubble :message="msg.content" />
        <span class="text-xs text-gray-500">{{ formatTime(msg.timestamp) }}</span>
      </div>
    </div>

    <!-- Streaming text (during response generation) -->
    <MessageBubble v-if="streamingText" :message="streamingText" />

    <!-- Current tool call -->
    <div v-if="currentToolCall" class="tool-card p-3">
      <div class="flex items-center gap-2 text-sm">
        <span class="text-yellow-400">⚡</span>
        <span class="font-medium">Tool '{{ currentToolCall.tool_name }}' called</span>
      </div>
      <pre class="text-xs text-gray-300 mt-2 overflow-x-auto">{{ JSON.stringify(currentToolCall.arguments, null, 2) }}</pre>
    </div>
  </div>
</template>