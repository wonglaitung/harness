import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Settings {
  apiKey: string
  provider: 'anthropic' | 'openai'
  model: string
  baseUrl: string
}

const STORAGE_KEY = 'harness-settings'

export const useSettingsStore = defineStore('settings', () => {
  // State
  const apiKey = ref<string>('')
  const provider = ref<'anthropic' | 'openai'>('anthropic')
  const model = ref<string>('claude-sonnet-4-6')
  const baseUrl = ref<string>('')

  // Load from localStorage on init
  function loadFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored) as Settings
        apiKey.value = parsed.apiKey || ''
        provider.value = parsed.provider || 'anthropic'
        model.value = parsed.model || 'claude-sonnet-4-6'
        baseUrl.value = parsed.baseUrl || ''
      }
    } catch (e) {
      console.error('Failed to load settings from storage:', e)
    }
  }

  // Save to localStorage
  function saveToStorage() {
    try {
      const settings: Settings = {
        apiKey: apiKey.value,
        provider: provider.value,
        model: model.value,
        baseUrl: baseUrl.value,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    } catch (e) {
      console.error('Failed to save settings to storage:', e)
    }
  }

  // Computed
  const hasApiKey = computed(() => !!apiKey.value)

  // Actions
  function setApiKey(key: string) {
    apiKey.value = key
    saveToStorage()
  }

  function setProvider(p: 'anthropic' | 'openai') {
    provider.value = p
    // Update default model based on provider
    if (p === 'anthropic') {
      model.value = 'claude-sonnet-4-6'
    } else {
      model.value = 'gpt-4o'
    }
    saveToStorage()
  }

  function setModel(m: string) {
    model.value = m
    saveToStorage()
  }

  function setBaseUrl(url: string) {
    baseUrl.value = url
    saveToStorage()
  }

  function clearSettings() {
    apiKey.value = ''
    provider.value = 'anthropic'
    model.value = 'claude-sonnet-4-6'
    baseUrl.value = ''
    localStorage.removeItem(STORAGE_KEY)
  }

  // Get auth payload for WebSocket
  function getAuthPayload() {
    const payload: Record<string, unknown> = {
      api_key: apiKey.value,
      provider: provider.value,
      model: model.value,
    }
    if (baseUrl.value) {
      payload.base_url = baseUrl.value
    }
    return payload
  }

  // Initialize
  loadFromStorage()

  return {
    // State
    apiKey,
    provider,
    model,
    baseUrl,
    // Computed
    hasApiKey,
    // Actions
    setApiKey,
    setProvider,
    setModel,
    setBaseUrl,
    clearSettings,
    getAuthPayload,
  }
})