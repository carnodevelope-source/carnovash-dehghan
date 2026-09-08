import axios from 'axios'
import { getActivePinia } from 'pinia'
import { useLoadingStore } from '../store/loading.store'
import { resolveApiErrorMessage, getApiErrorStatus } from '../utils/apiError'
import { notifyError } from '../utils/notify'

const resolveBaseURL = () => {
  const configured = import.meta.env.VITE_API_BASE_URL || ''
  if (!configured) return '/api'

  try {
    const current = new URL(window.location.href)
    const target = new URL(configured)
    const isLocalTarget = ['localhost', '127.0.0.1'].includes(target.hostname)
    const isViteDevServer = current.port === '5173'
    if (isLocalTarget && isViteDevServer) return '/api'
  } catch (_error) {
    return configured || '/api'
  }

  return configured
}

// Requests must always have a finite deadline. Heavier reports/uploads opt in
// to a documented endpoint-specific timeout through meta.timeoutMs.
const REQUEST_TIMEOUT_MS = 20000
const IDEMPOTENCY_KEY_TTL_MS = 5 * 60 * 1000

const api = axios.create({
  baseURL: resolveBaseURL(),
  withCredentials: true,
  timeout: REQUEST_TIMEOUT_MS,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken'
})

export const getCookie = (name) => {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) {
    return parts.pop().split(';').shift()
  }
  return ''
}

export const ensureCsrfToken = async () => {
  await api.get('/auth/csrf/', { meta: { mode: 'prefetch', showErrorToast: false } })
  return getCookie('csrftoken')
}

// Upper bound on how long one request may hold the full-screen overlay.
const LOADER_WATCHDOG_MS = 20000

let loaderSeq = 0
const loaderWatchdogs = new Map()
const mutationKeys = new Map()

const startGlobalLoading = (config) => {
  if (!getActivePinia()) return
  const id = ++loaderSeq
  config.meta = { ...(config.meta || {}), _loaderId: id }
  useLoadingStore().start(config.meta?.loadingKey)
  // Aborted requests and redirects can skip the response interceptors, and a
  // single unmatched start would otherwise block the UI for the whole session.
  loaderWatchdogs.set(id, window.setTimeout(() => stopGlobalLoading(config), LOADER_WATCHDOG_MS))
}

const stopGlobalLoading = (config) => {
  const id = config?.meta?._loaderId
  if (!id || !loaderWatchdogs.has(id)) return
  window.clearTimeout(loaderWatchdogs.get(id))
  loaderWatchdogs.delete(id)
  if (!getActivePinia()) return
  useLoadingStore().stop(config.meta?.loadingKey)
}

const shouldSkipErrorToast = (config = {}) => config?.meta?.showErrorToast === false

const isCancelled = (error) => axios.isCancel(error) || error?.code === 'ERR_CANCELED'
const isTimeout = (error) => error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT'

const shouldAutoNotifyError = (error) => {
  const config = error?.config || {}
  if (isCancelled(error)) return false
  if (shouldSkipErrorToast(config)) return false
  if (config?.meta?.showErrorToast === true) return true

  const url = String(config?.url || '')
  const status = getApiErrorStatus(error)

  if (!error?.response) return true
  if (status >= 500) return true
  if ((status === 401 || status === 403) && !url.includes('/auth/me/') && !url.includes('/auth/csrf/')) return true
  return false
}

api.interceptors.request.use((config) => {
  const meta = { ...(config.meta || {}) }
  // User-facing requests show the global overlay by default. Opt out with
  // trackLoading:false / mode:'background-sync'|'prefetch' for live polls.
  if (!meta.mode) {
    if (meta.trackLoading === false) meta.mode = 'background-sync'
    else if (meta.trackLoading === true || meta.blocking === true) meta.mode = 'navigation'
    else meta.mode = 'navigation'
  }
  config.meta = meta
  if (Number.isFinite(Number(meta.timeoutMs)) && Number(meta.timeoutMs) > 0) {
    config.timeout = Number(meta.timeoutMs)
  }
  const csrfToken = getCookie('csrftoken')
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  const isUnsafeMutation = ['post', 'put', 'patch', 'delete'].includes(String(config.method || '').toLowerCase())
  if (isUnsafeMutation && meta.idempotency !== false) {
    const scope = meta.idempotencyScope || meta.loadingKey || mutationFingerprint(config)
    meta._idempotencyScope = scope
    meta.idempotencyKey = meta.idempotencyKey || getMutationKey(scope)
    config.headers['Idempotency-Key'] = meta.idempotencyKey
  }

  if (meta.mode === 'navigation' || meta.mode === 'mutation-user' || meta.blocking === true) {
    startGlobalLoading(config)
  }

  return config
}, (error) => {
  stopGlobalLoading(error?.config)
  return Promise.reject(error)
})

export const createIdempotencyKey = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(16).slice(2)}-${Math.random().toString(16).slice(2)}`
}

const mutationFingerprint = (config) => {
  const method = String(config.method || '').toLowerCase()
  const url = String(config.baseURL || '') + String(config.url || '')
  const payload = config.data instanceof FormData ? '[form-data]' : JSON.stringify(config.data ?? null)
  return `${method}:${url}:${payload}`
}

const getMutationKey = (scope) => {
  const now = Date.now()
  const existing = mutationKeys.get(scope)
  if (existing && existing.expiresAt > now) return existing.key
  const key = createIdempotencyKey()
  mutationKeys.set(scope, { key, expiresAt: now + IDEMPOTENCY_KEY_TTL_MS })
  return key
}

const releaseMutationKey = (config) => {
  const scope = config?.meta?._idempotencyScope
  const key = config?.meta?.idempotencyKey
  if (scope && mutationKeys.get(scope)?.key === key) mutationKeys.delete(scope)
}

// Use this for a user mutation that may be retried after an ambiguous timeout.
// The key is intentionally returned to the caller, which must reuse it only
// for the exact same method/path/body retry.
export const mutationMeta = (loadingKey, options = {}) => ({
  mode: 'mutation-user',
  loadingKey,
  timeoutMs: options.timeoutMs || 30000,
  idempotencyScope: options.idempotencyScope || loadingKey,
  idempotencyKey: options.idempotencyKey || getMutationKey(options.idempotencyScope || loadingKey),
  ...options
})

api.interceptors.response.use((response) => {
  stopGlobalLoading(response?.config)
  releaseMutationKey(response?.config)
  return response
}, (error) => {
  stopGlobalLoading(error?.config)

  // Retain a key for network/5xx ambiguity so a retry cannot create a second
  // mutation. A completed client-visible 4xx is safe to release for a newly
  // corrected user action.
  if (error?.response && error.response.status < 500) releaseMutationKey(error.config)

  if (shouldAutoNotifyError(error)) {
    const fallback = isTimeout(error)
      ? 'پاسخی از سرور دریافت نشد. لطفاً دوباره تلاش کنید.'
      : 'عملیات ناموفق بود.'
    notifyError(resolveApiErrorMessage(error, fallback), {
      title: 'خطا در ارتباط با سامانه'
    })
  }

  return Promise.reject(error)
})

// Identical in-flight GETs (board + shell + step-2 catalogs) share one network
// round-trip. Mutations stay unique because of idempotency keys.
const inflightGets = new Map()

const originalGet = api.get.bind(api)
api.get = (url, config = {}) => {
  const paramsKey = JSON.stringify(config?.params || null)
  const key = `${url}?${paramsKey}`
  const existing = inflightGets.get(key)
  if (existing) return existing
  const request = originalGet(url, config).finally(() => {
    if (inflightGets.get(key) === request) inflightGets.delete(key)
  })
  inflightGets.set(key, request)
  return request
}

export default api
