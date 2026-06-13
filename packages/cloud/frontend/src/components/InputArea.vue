<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  modelValue: string
  disabled?: boolean
  isRunning?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'send': []
  'interrupt': []
}>()

const textareaRef = ref<HTMLTextAreaElement | null>(null)

function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (!props.disabled && !props.isRunning) {
      emit('send')
    }
  }
}

function focus() {
  textareaRef.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="p-4 border-t border-dark-border bg-dark-surface">
    <div class="flex gap-3">
      <textarea
        ref="textareaRef"
        :value="modelValue"
        :disabled="disabled"
        :placeholder="disabled ? 'Connecting...' : 'Type a message... (Enter to send, Shift+Enter for new line)'"
        @input="handleInput"
        @keydown="handleKeydown"
        class="flex-1 px-4 py-3 bg-dark-bg border border-dark-border rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary text-gray-100 placeholder-gray-500"
        rows="2"
      />
      <div class="flex flex-col gap-2">
        <!-- Send button (when not running) -->
        <button
          v-if="!isRunning"
          @click="emit('send')"
          :disabled="disabled || !modelValue.trim()"
          class="w-12 h-12 bg-primary hover:bg-primary-hover disabled:bg-gray-600 text-white rounded-xl flex items-center justify-center transition-colors"
          title="Send"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>

        <!-- Stop button (when running) -->
        <button
          v-else
          @click="emit('interrupt')"
          class="w-12 h-12 bg-red-500 hover:bg-red-600 text-white rounded-xl flex items-center justify-center transition-colors"
          title="Stop"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="6" width="12" height="12" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>