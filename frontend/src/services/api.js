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

const api = axios.create({
  baseURL: resolveBaseURL(),
  withCredentials: true,
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

const startGlobalLoading = () => {
  if (!getActivePinia()) return
  useLoadingStore().start()
}

const stopGlobalLoading = () => {
  if (!getActivePinia()) return
  useLoadingStore().stop()
}

const shouldSkipErrorToast = (config = {}) => config?.meta?.showErrorToast === false

const shouldAutoNotifyError = (error) => {
  const config = error?.config || {}
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

  const shouldTrack = config?.meta?.trackLoading !== false
  if (shouldTrack) {
    config.meta = { ...(config.meta || {}), _trackedByGlobalLoader: true }
    startGlobalLoading()
  }

  return config
}, (error) => {
  stopGlobalLoading()
  return Promise.reject(error)
})

api.interceptors.response.use((response) => {
  if (response?.config?.meta?._trackedByGlobalLoader) {
    stopGlobalLoading()
  }
  return response
}, (error) => {
  if (error?.config?.meta?._trackedByGlobalLoader) {
    stopGlobalLoading()
  }

  if (shouldAutoNotifyError(error)) {
    notifyError(resolveApiErrorMessage(error, 'عملیات ناموفق بود.'), {
      title: 'خطا در ارتباط با سامانه'
    })
  }

  return Promise.reject(error)
})

export default api
