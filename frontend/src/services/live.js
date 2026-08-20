import api from './api'

export const LIVE_EVENT_NAME = 'carvash-live-event'
const seenEventIds = new Map()
const SEEN_EVENT_TTL_MS = 5 * 60 * 1000

export function createLiveEventSource() {
  if (typeof window === 'undefined' || typeof EventSource === 'undefined') return null

  const baseURL = String(api.defaults.baseURL || '/api').replace(/\/$/, '')
  const url = new URL(`${baseURL}/live/events/`, window.location.origin)
  return new EventSource(url.toString(), { withCredentials: true })
}

export function parseLiveEvent(raw) {
  try {
    const payload = JSON.parse(raw)
    if (!payload?.id) return payload
    const now = Date.now()
    for (const [id, seenAt] of seenEventIds) {
      if (now - seenAt > SEEN_EVENT_TTL_MS) seenEventIds.delete(id)
    }
    if (seenEventIds.has(payload.id)) return null
    seenEventIds.set(payload.id, now)
    return payload
  } catch {
    return null
  }
}

export function dispatchLiveEvent(payload) {
  if (typeof window === 'undefined' || !payload?.type) return
  window.dispatchEvent(new CustomEvent(LIVE_EVENT_NAME, { detail: payload }))
}
