import { defineStore } from 'pinia'
import api, { mutationMeta } from '../services/api'

export const useVehicleStore = defineStore('vehicle', {
  state: () => ({
    vehicles: [],
    selectedVehicle: null,
    loading: false
  }),
  actions: {
    async ensureCsrf(options = {}) {
      const trackLoading = options.trackLoading === true
      await api.get('/auth/csrf/', {
        meta: { trackLoading, showErrorToast: options.showErrorToast }
      })
    },
    applyVehicleList(nextVehicles = []) {
      // Full board replace is cheaper than per-row splice/findIndex thrashing
      // once the day gets busy — Vue 3 handles the array swap fine.
      this.vehicles = Array.isArray(nextVehicles) ? nextVehicles : []
    },
    upsertVehicle(vehicle) {
      if (!vehicle?.id) return vehicle
      const idx = this.vehicles.findIndex((item) => Number(item.id) === Number(vehicle.id))
      if (idx >= 0) {
        this.vehicles[idx] = { ...this.vehicles[idx], ...vehicle }
      } else {
        this.vehicles.unshift(vehicle)
      }
      if (this.selectedVehicle && Number(this.selectedVehicle.id) === Number(vehicle.id)) {
        this.selectedVehicle = { ...this.selectedVehicle, ...vehicle }
      }
      return vehicle
    },
    async fetchVehicles(params = {}, options = {}) {
      const trackLoading = options.trackLoading === true
      if (trackLoading) this.loading = true
      try {
        const { data } = await api.get('/vehicles/', {
          params,
          meta: { trackLoading, showErrorToast: options.showErrorToast }
        })
        this.applyVehicleList(data)
      } finally {
        if (trackLoading) this.loading = false
      }
    },
    async createVehicle(payload) {
      await this.ensureCsrf()
      const { data } = await api.post('/vehicles/', payload, {
        meta: mutationMeta('vehicle:create')
      })
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
