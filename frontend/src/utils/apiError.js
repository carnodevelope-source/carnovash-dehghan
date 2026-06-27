const firstMessage = (value) => {
  if (!value) return ''
  if (typeof value === 'string') return value.trim()
  if (Array.isArray(value)) {
    for (const item of value) {
      const message = firstMessage(item)
      if (message) return message
    }
    return ''
  }
  if (typeof value === 'object') {
    for (const item of Object.values(value)) {
      const message = firstMessage(item)
      if (message) return message
    }
  }
  return ''
}

export const resolveApiErrorMessage = (error, fallback = 'عملیات ناموفق بود.') => {
  const payload = error?.response?.data
  const message = firstMessage(payload?.detail) || firstMessage(payload)
  if (message) return message
  if (error?.request && !error?.response) return 'ارتباط با سرور برقرار نشد. اتصال شبکه و اجرای بک‌اند را بررسی کنید.'
  return fallback
}
