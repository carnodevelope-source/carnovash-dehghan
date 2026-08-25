import { defineStore } from 'pinia'

export const useLoadingStore = defineStore('loading', {
  state: () => ({
    pendingRequests: 0,
    pendingByKey: {}
  }),
  getters: {
    isLoading: (state) => state.pendingRequests > 0
  },
  actions: {
    start(key = '') {
      this.pendingRequests += 1
      if (key) this.pendingByKey[key] = (this.pendingByKey[key] || 0) + 1
    },
    stop(key = '') {
      this.pendingRequests = Math.max(0, this.pendingRequests - 1)
      if (!key || !this.pendingByKey[key]) return
      const next = this.pendingByKey[key] - 1
      if (next > 0) this.pendingByKey[key] = next
      else delete this.pendingByKey[key]
    },
    isPending(key) {
      return (this.pendingByKey[key] || 0) > 0
    }
  }
})
