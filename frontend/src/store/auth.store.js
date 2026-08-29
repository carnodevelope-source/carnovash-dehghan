import { defineStore } from 'pinia'
import api from '../services/api'

const AUTH_CACHE_KEY = 'carvash.auth.user'

const readCachedUser = () => {
  if (typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(AUTH_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

const writeCachedUser = (user) => {
  if (typeof sessionStorage === 'undefined') return
  try {
    if (user) sessionStorage.setItem(AUTH_CACHE_KEY, JSON.stringify(user))
    else sessionStorage.removeItem(AUTH_CACHE_KEY)
  } catch {
    // Private mode / quota — auth still works in memory.
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: readCachedUser(),
    meInFlight: null,
    lastMeAt: 0
  }),
  getters: {
    role: (state) => state.user?.role || '',
    platformRole: (state) => state.user?.platform_role || '',
    isHq: (state) => state.user?.is_hq === true || ['hq_admin', 'hq_support', 'hq_project_manager', 'hq_finance'].includes(state.user?.platform_role),
    isHqAdmin: (state) => state.user?.is_hq_admin === true || state.user?.platform_role === 'hq_admin',
    isHqFinance: (state) => state.user?.platform_role === 'hq_finance',
    isHqProjectManager: (state) => state.user?.platform_role === 'hq_project_manager',
    isAccountant: (state) => state.user?.role === 'accountant',
    licenseStatus: (state) => state.user?.license_status || {},
    isLicenseLocked: (state) => state.user?.license_status?.is_locked === true,
    canAccessManagerSettings: (state) => ['manager', 'admin'].includes(state.user?.role),
    canAccessWallet: (state) => ['accountant', 'manager', 'admin', 'operator'].includes(state.user?.role),
    canAccessReports: (state) => ['manager', 'admin'].includes(state.user?.role),
    canAccessSupport: (state) => ['accountant', 'admin', 'owner', 'manager', 'operator', 'worker'].includes(state.user?.role),
    canAccessDashboard: (state) => ['admin', 'owner', 'manager', 'operator', 'worker'].includes(state.user?.role)
  },
  actions: {
    setUser(user) {
      this.user = user || null
      writeCachedUser(this.user)
    },
    async fetchMe(options = {}) {
      const force = options.force === true
      const maxAgeMs = Number.isFinite(Number(options.maxAgeMs)) ? Number(options.maxAgeMs) : 0
      if (!force && this.meInFlight) return this.meInFlight
      if (!force && maxAgeMs > 0 && this.user && this.lastMeAt && (Date.now() - this.lastMeAt) < maxAgeMs) {
        return this.user
      }

      this.meInFlight = (async () => {
        try {
          const { data } = await api.get('/auth/me/', {
            meta: { trackLoading: false, showErrorToast: false, timeoutMs: 12000 }
          })
          this.setUser(data)
          this.lastMeAt = Date.now()
          return data
        } catch {
          this.setUser(null)
          this.lastMeAt = 0
          return null
        } finally {
          this.meInFlight = null
        }
      })()

      return this.meInFlight
    },
    refreshMeInBackground(maxAgeMs = 60_000) {
      if (this.meInFlight) return this.meInFlight
      if (this.user && this.lastMeAt && (Date.now() - this.lastMeAt) < maxAgeMs) return Promise.resolve(this.user)
      return this.fetchMe({ maxAgeMs })
    },
    async logout() {
      try {
        await api.post('/auth/logout/')
      } finally {
        this.setUser(null)
        this.lastMeAt = 0
      }
    }
  }
})
