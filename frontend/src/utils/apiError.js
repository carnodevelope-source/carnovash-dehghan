const isHtmlErrorPayload = (value) => {
  const text = String(value || '').trim()
  if (!text) return false
  return /<!doctype html>|<html[\s>]|Server Error \(\d+\)/i.test(text)
}

const firstMessage = (value) => {
  if (!value) return ''
  if (typeof value === 'string') {
    const text = value.trim()
    return isHtmlErrorPayload(text) ? '' : text
  }
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

export const getApiErrorStatus = (error) => Number(error?.response?.status || 0)

export const resolveApiErrorMessage = (error, fallback = 'عملیات ناموفق بود.') => {
  const payload = error?.response?.data
  if (typeof payload === 'string' && isHtmlErrorPayload(payload)) {
    return getApiErrorStatus(error) >= 500
      ? 'در پردازش درخواست از سمت سرور خطا رخ داد. چند لحظه دیگر دوباره تلاش کنید.'
      : fallback
  }
  const message = firstMessage(payload?.detail) || firstMessage(payload)
  if (message) return message
  if (error?.request && !error?.response) return 'ارتباط با سرور برقرار نشد. اتصال شبکه و اجرای بک‌اند را بررسی کنید.'
  if (getApiErrorStatus(error) >= 500) return 'در پردازش درخواست از سمت سرور خطا رخ داد. چند لحظه دیگر دوباره تلاش کنید.'
  return fallback
}
