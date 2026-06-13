/**
 * WebSocket composable with heartbeat and reconnect
 */

import { ref, onUnmounted } from 'vue'
import type { MessageEnvelope } from '@/api/types'

// Configuration
const HEARTBEAT_INTERVAL = 30000 // 30 seconds
const HEARTBEAT_TIMEOUT = 60000 // 60 seconds timeout
const MAX_RECONNECT_ATTEMPTS = 5

export function useWebSocket(sessionId: string) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const isAuthSuccess = ref(false)
  const handlers = new Map<string, Function[]>()

  // Heartbeat state
  let lastHeartbeat = Date.now()
  let heartbeatTimer: number | null = null
  let reconnectAttempts = 0
  let reconnectTimer: number | null = null
  let currentToken = ''

  /**
   * Connect to WebSocket
   * Token is sent in first message (not URL) to prevent leakage
   */
  function connect(token: string, authPayload?: Record<string, unknown>) {
    currentToken = token
    const gatewayUrl = import.meta.env.VITE_GATEWAY_URL || ''
    const url = `${gatewayUrl}/ws/session/${sessionId}`

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      // Send gateway auth message first
      ws.value!.send(JSON.stringify({ type: 'auth', token: currentToken }))
    }

    ws.value.onmessage = (event) => {
      try {
        const envelope: MessageEnvelope = JSON.parse(event.data)
        const msgType = envelope.type as string

        // Handle gateway auth success (connection to container ready)
        if (msgType === 'auth_success' || envelope.payload?.provider) {
          // This is Agent auth_success, send agent auth if needed
          if (authPayload && !isAuthSuccess.value) {
            ws.value!.send(JSON.stringify({ type: 'auth', payload: authPayload }))
          }
          return
        }

        // Handle agent auth success
        if (msgType === 'auth_success') {
          isAuthSuccess.value = true
          isConnected.value = true
          reconnectAttempts = 0
          startHeartbeat()
          console.log('[WS] Authenticated successfully')
          return
        }

        // Handle auth failed
        if (msgType === 'auth_failed' || (msgType === 'error' && envelope.payload?.error_code === 'AUTH_FAILED')) {
          console.error('[WS] Authentication failed:', envelope.payload)
          disconnect()
          return
        }

        // Handle heartbeat response
        if (msgType === 'pong') {
          lastHeartbeat = Date.now()
          return
        }

        // Dispatch to registered handlers
        handleMessage(envelope)
      } catch (e) {
        console.error('[WS] Failed to parse message:', e)
      }
    }

    ws.value.onclose = (event) => {
      isConnected.value = false
      isAuthSuccess.value = false
      stopHeartbeat()
      console.log('[WS] Closed:', event.code, event.reason)

      // Auto reconnect
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        scheduleReconnect(currentToken, authPayload)
      }
    }

    ws.value.onerror = (error) => {
      console.error('[WS] Error:', error)
    }
  }

  /**
   * Start heartbeat timer
   */
  function startHeartbeat() {
    heartbeatTimer = window.setInterval(() => {
      if (ws.value?.readyState === WebSocket.OPEN) {
        // Send ping
        ws.value.send(JSON.stringify({ type: 'ping', payload: {} }))

        // Check timeout
        if (Date.now() - lastHeartbeat > HEARTBEAT_TIMEOUT) {
          console.warn('[WS] Heartbeat timeout, reconnecting...')
          ws.value.close()
        }
      }
    }, HEARTBEAT_INTERVAL)
  }

  /**
   * Stop heartbeat timer
   */
  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  /**
   * Schedule reconnect with exponential backoff
   */
  function scheduleReconnect(token: string, authPayload?: Record<string, unknown>) {
    reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)

    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`)

    reconnectTimer = window.setTimeout(() => {
      connect(token, authPayload)
    }, delay)
  }

  /**
   * Register message handler
   */
  function on(type: string, handler: Function) {
    const existing = handlers.get(type) || []
    handlers.set(type, [...existing, handler])
  }

  /**
   * Unregister message handler
   */
  function off(type: string, handler: Function) {
    const existing = handlers.get(type) || []
    handlers.set(type, existing.filter(h => h !== handler))
  }

  /**
   * Send message
   */
  function send(type: string, payload: Record<string, unknown>) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, payload }))
    } else {
      console.warn('[WS] Cannot send, connection not open')
    }
  }

  /**
   * Handle received message
   */
  function handleMessage(envelope: MessageEnvelope) {
    const callbacks = handlers.get(envelope.type as string) || []
    callbacks.forEach(cb => cb(envelope.payload))
  }

  /**
   * Disconnect
   */
  function disconnect() {
    stopHeartbeat()
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    ws.value?.close()
    ws.value = null
    isConnected.value = false
    isAuthSuccess.value = false
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    connect,
    disconnect,
    on,
    off,
    send,
    isConnected,
    isAuthSuccess,
  }
}