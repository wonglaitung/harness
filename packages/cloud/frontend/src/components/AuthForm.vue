<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSettingsStore } from '@/stores/settingsStore'

const emit = defineEmits<{
  configured: []
}>()

const settingsStore = useSettingsStore()

// Form state
const apiKey = ref('')
const provider = ref<'anthropic' | 'openai'>('anthropic')
const model = ref('claude-sonnet-4-6')
const baseUrl = ref('')
const showAdvanced = ref(false)
const useCustomModel = ref(false)

// Model presets based on provider
const modelPresets = computed(() => {
  if (provider.value === 'anthropic') {
    return [
      { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
      { value: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
      { value: 'claude-haiku-4-5', label: 'Claude Haiku 4.5' },
    ]
  }
  return [
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
  ]
})

// Update model when provider changes (only if using preset)
function onProviderChange() {
  if (!useCustomModel.value) {
    if (provider.value === 'anthropic') {
      model.value = 'claude-sonnet-4-6'
    } else {
      model.value = 'gpt-4o'
    }
  }
}

// Toggle custom model input
function toggleCustomModel() {
  useCustomModel.value = !useCustomModel.value
  if (!useCustomModel.value) {
    // Reset to preset when switching back
    onProviderChange()
  }
}

// Save settings
function saveSettings() {
  if (!apiKey.value.trim()) {
    alert('Please enter your API key')
    return
  }

  if (!model.value.trim()) {
    alert('Please enter a model name')
    return
  }

  settingsStore.setApiKey(apiKey.value.trim())
  settingsStore.setProvider(provider.value)
  settingsStore.setModel(model.value.trim())
  if (baseUrl.value.trim()) {
    settingsStore.setBaseUrl(baseUrl.value.trim())
  }

  emit('configured')
}
</script>

<template>
  <div class="w-full max-w-md p-6 bg-dark-surface rounded-xl border border-dark-border">
    <h2 class="text-xl font-semibold mb-6 text-center">Configure Your Agent</h2>

    <form @submit.prevent="saveSettings" class="space-y-4">
      <!-- API Key -->
      <div>
        <label class="block text-sm font-medium mb-1">API Key</label>
        <input
          v-model="apiKey"
          type="password"
          placeholder="Enter your API key"
          class="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          required
        />
      </div>

      <!-- Provider -->
      <div>
        <label class="block text-sm font-medium mb-1">Provider</label>
        <select
          v-model="provider"
          @change="onProviderChange"
          class="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="anthropic">Anthropic (Claude)</option>
          <option value="openai">OpenAI / Compatible</option>
        </select>
      </div>

      <!-- Model -->
      <div>
        <label class="block text-sm font-medium mb-1">Model</label>

        <!-- Preset select -->
        <select
          v-if="!useCustomModel"
          v-model="model"
          class="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option v-for="opt in modelPresets" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>

        <!-- Custom input -->
        <input
          v-else
          v-model="model"
          type="text"
          placeholder="Enter model name (e.g., gpt-4o, claude-sonnet-4-6)"
          class="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          required
        />

        <!-- Toggle button -->
        <button
          type="button"
          @click="toggleCustomModel"
          class="text-xs text-gray-400 hover:text-white mt-1"
        >
          {{ useCustomModel ? '▼ Use preset model' : '▶ Enter custom model name' }}
        </button>
      </div>

      <!-- Advanced settings toggle -->
      <button
        type="button"
        @click="showAdvanced = !showAdvanced"
        class="text-sm text-gray-400 hover:text-white"
      >
        {{ showAdvanced ? '▼' : '▶' }} Advanced Settings
      </button>

      <!-- Advanced: Base URL -->
      <div v-if="showAdvanced">
        <label class="block text-sm font-medium mb-1">Custom Base URL (Optional)</label>
        <input
          v-model="baseUrl"
          type="url"
          placeholder="https://api.example.com/v1"
          class="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <p class="text-xs text-gray-500 mt-1">For OpenAI-compatible APIs</p>
      </div>

      <!-- Submit -->
      <button
        type="submit"
        class="w-full py-3 bg-primary hover:bg-primary-hover text-white rounded-lg font-medium transition-colors"
      >
        Start Chatting
      </button>
    </form>

    <p class="text-xs text-gray-500 mt-4 text-center">
      Your API key is stored locally in your browser and never sent to our servers.
    </p>
  </div>
</template>