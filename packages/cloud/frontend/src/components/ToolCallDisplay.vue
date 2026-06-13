<script setup lang="ts">
import type { ToolCallEvent, ToolResultEvent } from '@/api/types'

const props = defineProps<{
  toolCall?: ToolCallEvent | null
  toolResult?: ToolResultEvent | null
}>()

const isSuccess = props.toolResult?.success ?? true
</script>

<template>
  <div
    v-if="toolCall"
    class="tool-card p-3 my-2"
  >
    <!-- Header -->
    <div class="flex items-center gap-2 text-sm">
      <span class="text-yellow-400">⚡</span>
      <span class="font-medium">Tool '{{ toolCall.tool_name }}' called</span>
    </div>

    <!-- Arguments preview -->
    <pre
      v-if="Object.keys(toolCall.arguments).length > 0"
      class="text-xs text-gray-300 mt-2 overflow-x-auto max-h-32"
    >
{{ JSON.stringify(toolCall.arguments, null, 2) }}</pre>

    <!-- Result (if available) -->
    <div v-if="toolResult" class="mt-3 pt-3 border-t border-dark-border">
      <div class="flex items-center gap-2 text-sm">
        <span :class="isSuccess ? 'text-green-400' : 'text-red-400'">
          {{ isSuccess ? '✓' : '✗' }}
        </span>
        <span :class="isSuccess ? 'text-green-400' : 'text-red-400'">
          {{ isSuccess ? 'Succeeded' : 'Failed' }}
        </span>
      </div>
      <pre
        v-if="toolResult.result"
        class="text-xs text-gray-400 mt-2 overflow-x-auto max-h-32"
      >
{{ toolResult.result.slice(0, 500) }}{{ toolResult.result.length > 500 ? '...' : '' }}</pre>
      <p v-if="toolResult.error" class="text-xs text-red-400 mt-1">
        {{ toolResult.error }}
      </p>
    </div>
  </div>
</template>