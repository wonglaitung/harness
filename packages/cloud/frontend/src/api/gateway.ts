/**
 * Gateway REST API client
 */

const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || ''

export interface SessionResponse {
  session_id: string
  container_id: string
}

export interface HealthResponse {
  status: string
  containers?: number
}

/**
 * Create a new session
 */
export async function createSession(): Promise<SessionResponse> {
  const response = await fetch(`${GATEWAY_URL}/api/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to create session: ${response.status}`)
  }

  return response.json()
}

/**
 * Check gateway health
 */
export async function healthCheck(): Promise<HealthResponse> {
  const response = await fetch(`${GATEWAY_URL}/health`)
  return response.json()
}

/**
 * Destroy a session
 */
export async function destroySession(sessionId: string): Promise<void> {
  const response = await fetch(`${GATEWAY_URL}/api/sessions/${sessionId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error(`Failed to destroy session: ${response.status}`)
  }
}