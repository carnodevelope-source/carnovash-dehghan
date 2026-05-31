import { defineStore } from 'pinia'
import api from '../services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null }),
  getters: {
    role: (state) => state.user?.role || '',
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
