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
      const nextItems = Array.isArray(nextVehicles) ? nextVehicles : []
      const currentById = new Map(this.vehicles.map((item) => [Number(item.id), item]))
      const nextIds = new Set(nextItems.map((item) => Number(item.id)))

      for (let index = this.vehicles.length - 1; index >= 0; index -= 1) {
        if (!nextIds.has(Number(this.vehicles[index]?.id))) {
          this.vehicles.splice(index, 1)
        }
      }

      nextItems.forEach((nextItem, index) => {
        const existing = currentById.get(Number(nextItem.id))
        if (existing) {
          Object.assign(existing, nextItem)
          const currentIndex = this.vehicles.findIndex((item) => Number(item.id) === Number(nextItem.id))
          if (currentIndex !== index && currentIndex >= 0) {
            this.vehicles.splice(index, 0, this.vehicles.splice(currentIndex, 1)[0])
          }
          return
        }
        this.vehicles.splice(index, 0, nextItem)
      })
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
