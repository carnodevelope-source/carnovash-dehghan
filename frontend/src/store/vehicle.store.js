import { defineStore } from 'pinia'
import api from '../services/api'

export const useVehicleStore = defineStore('vehicle', {
  state: () => ({
    vehicles: [],
    selectedVehicle: null,
    loading: false
  }),
  actions: {
    async ensureCsrf() {
      await api.get('/auth/csrf/')
    },
    async fetchVehicles() {
      this.loading = true
      try {
        await this.ensureCsrf()
        const { data } = await api.get('/vehicles/')
        this.vehicles = Array.isArray(data) ? data : []
      } finally {
        this.loading = false
      }
    },
    async createVehicle(payload) {
      await this.ensureCsrf()
      const { data } = await api.post('/vehicles/', payload)
      this.vehicles.unshift(data)
      return data
    },
    async fetchVehicleDetail(vehicleId) {
      const { data } = await api.get(`/vehicles/${vehicleId}/`)
      this.selectedVehicle = data
      return data
    }
  }
})
