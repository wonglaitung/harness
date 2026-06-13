<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  message: string
  isUser?: boolean
}>()

const bgClass = computed(() =>
  props.isUser ? 'message-user ml-auto' : 'message-assistant'
)

const textClass = computed(() =>
  props.isUser ? 'text-white' : 'text-gray-100'
)
</script>

<template>
  <div
    :class="[bgClass, textClass]"
    class="p-4 max-w-[80%] whitespace-pre-wrap break-words"
  >
    <slot>
      {{ message }}
    </slot>
  </div>
</template>