import api from './api'
import { compareNumericIds, createLiveProtocolState } from './liveProtocol'

export const LIVE_EVENT_NAME = 'carvash-live-event'

const RETRY_BASE_MS = 5000
const RETRY_MAX_MS = 60000
const HIDDEN_DISCONNECT_MS = 2 * 60 * 1000
const RECONCILE_INTERVAL_MS = 90 * 1000
const LIVE_CURSOR_STORAGE_KEY = 'carvash.live.lastEventId'
const LIVE_REPLAY_ENABLED = String(import.meta.env.VITE_LIVE_REPLAY_ENABLED || '').toLowerCase() === 'true'

const protocol = createLiveProtocolState({
  maxRecentIds: Number(import.meta.env.VITE_LIVE_RECENT_EVENT_LIMIT || 1000)
})
const subscribers = new Set()

let sharedSource = null
let retryTimer = null
let retryAttempt = 0
let hiddenTimer = null
let lifecycleBound = false
let reconcileTimer = null
let reconcileInFlight = false
let lastEventId = typeof sessionStorage === 'undefined' ? '' : sessionStorage.getItem(LIVE_CURSOR_STORAGE_KEY) || ''

const isSupported = () => typeof window !== 'undefined' && typeof EventSource !== 'undefined'

const liveUrl = () => {
  const baseURL = String(api.defaults.baseURL || '/api').replace(/\/$/, '')
  const url = new URL(`${baseURL}/live/events/`, window.location.origin)
  // A new EventSource instance (for example after a hidden-tab disconnect)
  // does not retain Last-Event-ID itself, so carry the durable cursor forward.
  if (LIVE_REPLAY_ENABLED && lastEventId) url.searchParams.set('after', lastEventId)
  return url.toString()
}

const rememberEventId = (event, payload) => {
  const id = String(payload?.event_id || payload?.id || event?.lastEventId || '')
  if (!/^\d+$/.test(id)) return
  if (lastEventId && compareNumericIds(id, lastEventId) <= 0) return
  lastEventId = id
  try { sessionStorage.setItem(LIVE_CURSOR_STORAGE_KEY, id) } catch (_error) {}
}

const resetReplayCursor = () => {
  lastEventId = ''
  try { sessionStorage.removeItem(LIVE_CURSOR_STORAGE_KEY) } catch (_error) {}
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

const emitPayloadAsMessage = (payload) => {
  const event = { data: JSON.stringify(payload), lastEventId: String(payload?.event_id || payload?.id || '') }
  if (!protocol.accept(payload, event.lastEventId).accepted) return
  if (payload?.type === 'system.full_resync_required') resetReplayCursor()
  rememberEventId(event, payload)
  emit('message', event)
}

const reconcile = async () => {
  if (!LIVE_REPLAY_ENABLED || reconcileInFlight || document.visibilityState !== 'visible' || !lastEventId) return
  reconcileInFlight = true
  try {
    const { data: revision } = await api.get('/live/revision/', {
      meta: { mode: 'background-sync', showErrorToast: false, timeoutMs: 15000 }
    })
    const latest = String(revision?.latest_event_id || '')
    if (!latest || latest === lastEventId) return
    const { data } = await api.get('/live/sync/', {
      params: { after: lastEventId },
      meta: { mode: 'background-sync', showErrorToast: false, timeoutMs: 15000 }
    })
    if (data?.full_resync_required) {
      emitPayloadAsMessage({ type: 'system.full_resync_required', data: {} })
      return
    }
    for (const payload of data?.events || []) emitPayloadAsMessage(payload)
  } catch (_error) {
    // Reconcile is a self-healing safety net. A live connection remains usable
    // and a transient 404 means V2 has not been enabled server-side yet.
  } finally {
    reconcileInFlight = false
  }
}

const startReconcile = () => {
  if (!LIVE_REPLAY_ENABLED || reconcileTimer || !subscribers.size) return
  reconcileTimer = window.setInterval(() => { void reconcile() }, RECONCILE_INTERVAL_MS)
}

const stopReconcile = () => {
  if (!reconcileTimer) return
  window.clearInterval(reconcileTimer)
  reconcileTimer = null
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
    if (!protocol.accept(payload, event.lastEventId).accepted) return
    if (payload?.type === 'system.full_resync_required') resetReplayCursor()
    rememberEventId(event, payload)
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
    // Background tabs pin a gunicorn thread for the whole SSE lifetime.
    // Always release them; on return we reopen and the open handler refreshes.
    // With replay enabled, reconcile() fills any gap after reconnect.
    const delay = LIVE_REPLAY_ENABLED ? HIDDEN_DISCONNECT_MS : 30_000
    hiddenTimer = window.setTimeout(closeSharedSource, delay)
    return
  }
  if (hiddenTimer) {
    window.clearTimeout(hiddenTimer)
    hiddenTimer = null
  }
  retryAttempt = 0
  openSharedSource()
  void reconcile()
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
  startReconcile()
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
      if (!subscribers.size) {
        closeSharedSource()
        stopReconcile()
      }
    }
  }
}

export const getLiveDiagnostics = () => ({
  connectionCount: sharedSource ? 1 : 0,
  subscriberCount: subscribers.size,
  lastEventId,
  reconnectAttempt: retryAttempt,
  pendingReconcile: reconcileInFlight,
  ...protocol.diagnostics()
})

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
