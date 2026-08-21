import api from './api'

export const LIVE_EVENT_NAME = 'carvash-live-event'

const SEEN_EVENT_TTL_MS = 5 * 60 * 1000
const RETRY_BASE_MS = 5000
const RETRY_MAX_MS = 60000
const HIDDEN_DISCONNECT_MS = 2 * 60 * 1000

const seenEventIds = new Map()
const subscribers = new Set()

let sharedSource = null
let retryTimer = null
let retryAttempt = 0
let hiddenTimer = null
let lifecycleBound = false

const isSupported = () => typeof window !== 'undefined' && typeof EventSource !== 'undefined'

const liveUrl = () => {
  const baseURL = String(api.defaults.baseURL || '/api').replace(/\/$/, '')
  return new URL(`${baseURL}/live/events/`, window.location.origin).toString()
}

const isFirstSighting = (id) => {
  const now = Date.now()
  for (const [key, seenAt] of seenEventIds) {
    if (now - seenAt > SEEN_EVENT_TTL_MS) seenEventIds.delete(key)
  }
  if (seenEventIds.has(id)) return false
  seenEventIds.set(id, now)
  return true
}

const emit = (type, event) => {
  for (const subscriber of Array.from(subscribers)) {
    for (const handler of Array.from(subscriber.handlers[type])) {
      try {
        handler(event)
      } catch (error) {
        console.error('live event handler error:', error)
      }
    }
  }
}

const clearRetry = () => {
  if (!retryTimer) return
  window.clearTimeout(retryTimer)
  retryTimer = null
}

const scheduleReconnect = () => {
  if (retryTimer || !subscribers.size) return
  const delay = Math.min(RETRY_BASE_MS * 2 ** retryAttempt, RETRY_MAX_MS)
  retryAttempt += 1
  retryTimer = window.setTimeout(() => {
    retryTimer = null
    openSharedSource()
  }, delay)
}

const closeSharedSource = () => {
  clearRetry()
  sharedSource?.close()
  sharedSource = null
}

function openSharedSource() {
  if (sharedSource || !subscribers.size || !isSupported()) return
  if (document.visibilityState === 'hidden') return

  clearRetry()
  sharedSource = new EventSource(liveUrl(), { withCredentials: true })

  sharedSource.onopen = (event) => {
    retryAttempt = 0
    emit('open', event)
  }

  sharedSource.onmessage = (event) => {
    const payload = parseLiveEvent(event.data)
    if (payload?.id && !isFirstSighting(payload.id)) return
    emit('message', event)
  }

  sharedSource.onerror = (event) => {
    emit('error', event)
    // The server answers 503 once it is at capacity, which closes the stream
    // for good; only the browser's own transport hiccups auto-retry.
    if (sharedSource && sharedSource.readyState === EventSource.CLOSED) {
      sharedSource = null
      scheduleReconnect()
    }
  }
}

const onVisibilityChange = () => {
  if (document.visibilityState === 'hidden') {
    if (hiddenTimer) window.clearTimeout(hiddenTimer)
    // Background tabs would otherwise pin a server thread indefinitely.
    hiddenTimer = window.setTimeout(closeSharedSource, HIDDEN_DISCONNECT_MS)
    return
  }
  if (hiddenTimer) {
    window.clearTimeout(hiddenTimer)
    hiddenTimer = null
  }
  retryAttempt = 0
  openSharedSource()
}

const onPageHide = () => {
  if (hiddenTimer) {
    window.clearTimeout(hiddenTimer)
    hiddenTimer = null
  }
  // A full reload never runs Vue unmount hooks, so without this the previous
  // EventSource stays open on gunicorn until the next heartbeat. Three quick
  // reloads is enough to occupy every sync-sized worker and freeze /auth/me/.
  closeSharedSource()
}

const onPageShow = () => {
  retryAttempt = 0
  if (subscribers.size) openSharedSource()
}

const bindLifecycle = () => {
  if (lifecycleBound) return
  lifecycleBound = true
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('pagehide', onPageHide)
  window.addEventListener('pageshow', onPageShow)
}

export function createLiveEventSource() {
  if (!isSupported()) return null

  const subscriber = {
    closed: false,
    handlers: { open: new Set(), message: new Set(), error: new Set() }
  }
  subscribers.add(subscriber)
  bindLifecycle()
  openSharedSource()

  return {
    addEventListener(type, handler) {
      const bucket = subscriber.handlers[type]
      if (subscriber.closed || !bucket || typeof handler !== 'function') return
      bucket.add(handler)
      // A component mounting onto an already-live stream still needs the
      // initial refresh that its open handler performs.
      if (type === 'open' && sharedSource?.readyState === EventSource.OPEN) {
        handler(new Event('open'))
      }
    },
    removeEventListener(type, handler) {
      subscriber.handlers[type]?.delete(handler)
    },
    close() {
      if (subscriber.closed) return
      subscriber.closed = true
      subscribers.delete(subscriber)
      if (!subscribers.size) closeSharedSource()
    }
  }
}

export function parseLiveEvent(raw) {
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function dispatchLiveEvent(payload) {
  if (typeof window === 'undefined' || !payload?.type) return
  window.dispatchEvent(new CustomEvent(LIVE_EVENT_NAME, { detail: payload }))
}
