/**
 * API client for GAIA Agent backend.
 * Handles both standard JSON and Server-Sent Events (streaming).
 */

const BASE_URL = '/api'

// ── REST Helpers ─────────────────────────────────────────────────────────────

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body) opts.body = JSON.stringify(body)

  const res = await fetch(`${BASE_URL}${path}`, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── API functions ─────────────────────────────────────────────────────────────

export const api = {
  /** Health check */
  health: () => request('GET', '/health'),

  /** Send a chat message (non-streaming) */
  chat: (message, conversationId = null, files = []) =>
    request('POST', '/chat', { message, conversation_id: conversationId, files }),

  /** List all conversations */
  listConversations: () => request('GET', '/conversations'),

  /** Get messages for a conversation */
  getMessages: (conversationId) =>
    request('GET', `/conversations/${conversationId}/messages`),

  /** Delete a conversation */
  deleteConversation: (conversationId) =>
    request('DELETE', `/conversations/${conversationId}`),

  /** Upload a file */
  uploadFile: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE_URL}/files/upload`, { method: 'POST', body: form })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || `Upload failed: HTTP ${res.status}`)
    }
    return res.json()
  },
}

/**
 * Stream chat using Server-Sent Events.
 * Calls onEvent(event) for each received event.
 * Returns a cleanup function to abort the stream.
 */
export function streamChat(message, conversationId, files, onEvent) {
  const controller = new AbortController()

  const run = async () => {
    const res = await fetch(`${BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        files,
      }),
      signal: controller.signal,
    })

    if (!res.ok) {
      onEvent({ event: 'error', data: { error: `HTTP ${res.status}` } })
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // Parse SSE lines
      const lines = buffer.split('\n')
      buffer = lines.pop() // Keep incomplete last line

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const payload = JSON.parse(line.slice(6))
            onEvent(payload)
          } catch {
            // Ignore parse errors
          }
        }
      }
    }
  }

  run().catch((err) => {
    if (err.name !== 'AbortError') {
      onEvent({ event: 'error', data: { error: err.message } })
    }
  })

  return () => controller.abort()
}
