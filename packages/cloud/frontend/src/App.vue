<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settingsStore'
import AuthForm from '@/components/AuthForm.vue'
import ChatPanel from '@/components/ChatPanel.vue'

const settingsStore = useSettingsStore()

// Check if user has configured API key
const isConfigured = computed(() => settingsStore.hasApiKey)

// Session ID (generated on mount or from route)
const sessionId = ref<string>('')
const isSessionReady = ref(false)

onMounted(async () => {
  // Generate session ID
  sessionId.value = await generateSessionId()
  isSessionReady.value = true
})

async function generateSessionId(): Promise<string> {
  try {
    const response = await fetch('/api/sessions', { method: 'POST' })
    const data = await response.json()
    return data.session_id
  } catch (e) {
    // Fallback: generate locally
    return Math.random().toString(36).substring(2, 10)
  }
}

async function handleConfigured() {
  sessionId.value = await generateSessionId()
  isSessionReady.value = true
}
</script>

<template>
  <div class="min-h-screen bg-dark-bg flex flex-col">
    <!-- Header -->
    <header class="bg-dark-surface border-b border-dark-border px-4 py-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <img src="/icon.svg" alt="Harness" class="w-8 h-8" />
          <h1 class="text-xl font-semibold">Harness Cloud</h1>
        </div>
        <button
          @click="settingsStore.clearSettings()"
          class="text-sm text-gray-400 hover:text-white"
          v-if="isConfigured"
        >
          Reset Settings
        </button>
      </div>
    </header>

    <!-- Main content -->
    <main class="flex-1 flex items-center justify-center p-4">
      <!-- Loading state -->
      <div v-if="isConfigured && !isSessionReady" class="text-gray-500">
        Creating session...
      </div>

      <!-- Auth form if not configured -->
      <AuthForm v-else-if="!isConfigured" @configured="handleConfigured" />

      <!-- Chat panel if configured and session ready -->
      <ChatPanel v-else :session-id="sessionId" class="w-full max-w-4xl h-full" @new-session="sessionId = ''" />
    </main>

    <!-- Footer -->
    <footer class="bg-dark-surface border-t border-dark-border px-4 py-2 text-center text-sm text-gray-500">
      Session: {{ sessionId || 'connecting...' }}
    </footer>
  </div>
</template>