import axios from 'axios'
import { getActivePinia } from 'pinia'
import { useLoadingStore } from '../store/loading.store'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
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
  return Promise.reject(error)
})

export default api
