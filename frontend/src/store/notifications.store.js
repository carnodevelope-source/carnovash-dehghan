import { defineStore } from 'pinia'

let nextId = 1

const normalizeDuration = (value, fallback = 4200) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) return fallback
  return numeric
}

export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    items: []
  }),
  actions: {
    push(message, type = 'error', options = {}) {
      const text = String(message || '').trim()
      if (!text) return null

      const item = {
        id: nextId += 1,
        type,
        message: text,
        title: String(options.title || '').trim(),
        duration: normalizeDuration(options.duration, type === 'error' ? 4800 : 3200)
      }

      this.items.push(item)
      return item.id
    },
    remove(id) {
      this.items = this.items.filter((item) => item.id !== id)
    },
    clear() {
      this.items = []
    }
  }
})
