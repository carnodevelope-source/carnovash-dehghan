import { defineStore } from 'pinia'
import api from '../services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null }),
  getters: {
    role: (state) => state.user?.role || '',
    platformRole: (state) => state.user?.platform_role || '',
    isHq: (state) => state.user?.is_hq === true || ['hq_admin', 'hq_support'].includes(state.user?.platform_role),
    isHqAdmin: (state) => state.user?.is_hq_admin === true || state.user?.platform_role === 'hq_admin',
    isAccountant: (state) => state.user?.role === 'accountant',
    canAccessManagerSettings: (state) => ['manager', 'admin'].includes(state.user?.role),
    canAccessWallet: (state) => ['accountant', 'manager', 'admin'].includes(state.user?.role),
    canAccessReports: (state) => ['manager', 'admin'].includes(state.user?.role),
    canAccessSupport: (state) => ['accountant', 'admin', 'owner', 'manager', 'operator', 'worker'].includes(state.user?.role),
    canAccessDashboard: (state) => ['admin', 'owner', 'manager', 'operator', 'worker'].includes(state.user?.role)
  },
  actions: {
    async fetchMe() {
      try {
        const { data } = await api.get('/auth/me/')
        this.user = data
      } catch {
        this.user = null
      }
    },
    async logout() {
      try {
        await api.post('/auth/logout/')
      } finally {
        this.user = null
      }
    }
  }
})
