import { defineStore } from 'pinia'

let resolver = null

export const usePermissionPromptStore = defineStore('permissionPrompt', {
  state: () => ({
    open: false,
    kind: 'camera',
    title: '',
    message: '',
    detail: '',
    confirmLabel: 'تأیید و ادامه',
    cancelLabel: 'انصراف',
    secondaryLabel: '',
    busy: false
  }),
  actions: {
    ask(options = {}) {
      if (resolver) {
        resolver({ confirmed: false, secondary: false })
        resolver = null
      }
      this.open = true
      this.kind = String(options.kind || 'camera')
      this.title = String(options.title || 'نیاز به دسترسی')
      this.message = String(options.message || '')
      this.detail = String(options.detail || '')
      this.confirmLabel = String(options.confirmLabel || 'تأیید و ادامه')
      this.cancelLabel = String(options.cancelLabel || 'انصراف')
      this.secondaryLabel = String(options.secondaryLabel || '')
      this.busy = false
      return new Promise((resolve) => {
        resolver = resolve
      })
    },
    setBusy(value = true) {
      this.busy = Boolean(value)
    },
    confirm() {
      if (!this.open) return
      const done = resolver
      resolver = null
      this.open = false
      this.busy = false
      done?.({ confirmed: true, secondary: false })
    },
    secondary() {
      if (!this.open) return
      const done = resolver
      resolver = null
      this.open = false
      this.busy = false
      done?.({ confirmed: false, secondary: true })
    },
    cancel() {
      if (!this.open) return
      const done = resolver
      resolver = null
      this.open = false
      this.busy = false
      done?.({ confirmed: false, secondary: false })
    }
  }
})
