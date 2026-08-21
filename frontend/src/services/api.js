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

// Without this axios waits forever, so one stalled request could hold the
// full-screen overlay until gunicorn's own 120s timeout fired.
const REQUEST_TIMEOUT_MS = 45000

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
  await api.get('/auth/csrf/')
  return getCookie('csrftoken')
}

// Upper bound on how long one request may hold the full-screen overlay.
const LOADER_WATCHDOG_MS = 20000

let loaderSeq = 0
const loaderWatchdogs = new Map()

const startGlobalLoading = (config) => {
  if (!getActivePinia()) return
  const id = ++loaderSeq
  config.meta = { ...(config.meta || {}), _loaderId: id }
  useLoadingStore().start()
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
  useLoadingStore().stop()
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
  const csrfToken = getCookie('csrftoken')
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }

  if (config?.meta?.trackLoading !== false) {
    startGlobalLoading(config)
  }

  return config
}, (error) => {
  stopGlobalLoading(error?.config)
  return Promise.reject(error)
})

api.interceptors.response.use((response) => {
  stopGlobalLoading(response?.config)
  return response
}, (error) => {
  stopGlobalLoading(error?.config)

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

export default api
