import { formatJalaliDate, formatJalaliDateTime } from '../../../utils/date'
import { formatThousandsToman } from '../../../utils/money'

export { formatJalaliDate, formatJalaliDateTime }

export function formatMoney(value) {
  if (value === null || value === undefined || value === '') return '—'
  return formatThousandsToman(value)
}

export function formatFaNumber(value) {
  if (value === null || value === undefined || value === '') return '—'
  return Number(value || 0).toLocaleString('fa-IR')
}

export function formatPercent(value, { digits = 1 } = {}) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${Number(value).toLocaleString('fa-IR', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0
  })}٪`
}

export function formatPercentChange(value) {
  if (value === null || value === undefined) return 'بدون داده مقایسه'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return 'بدون داده مقایسه'
  const sign = numeric > 0 ? '+' : ''
  return `${sign}${numeric.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪`
}

export function formatRelativeDate(value) {
  if (!value) return '—'
  const target = new Date(value)
  if (Number.isNaN(target.getTime())) return '—'
  const now = new Date()
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startTarget = new Date(target.getFullYear(), target.getMonth(), target.getDate())
  const dayDiff = Math.round((startTarget - startToday) / 86400000)
  if (dayDiff === 0) return 'امروز'
  if (dayDiff === -1) return 'دیروز'
  if (dayDiff === 1) return 'فردا'
  if (dayDiff < 0) return `${formatFaNumber(Math.abs(dayDiff))} روز پیش`
  return `${formatFaNumber(dayDiff)} روز دیگر`
}

export function formatDaysRemaining(endsAt) {
  if (!endsAt) return ''
  const end = new Date(endsAt)
  if (Number.isNaN(end.getTime())) return ''
  const today = new Date()
  const startToday = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const startEnd = new Date(end.getFullYear(), end.getMonth(), end.getDate())
  const days = Math.round((startEnd - startToday) / 86400000)
  if (days > 0) return `${formatFaNumber(days)} روز مانده`
  if (days === 0) return 'امروز منقضی می‌شود'
  return `${formatFaNumber(Math.abs(days))} روز گذشته`
}

export function deltaTone(value) {
  if (value === null || value === undefined || Number(value) === 0) return 'neutral'
  return Number(value) > 0 ? 'up' : 'down'
}

export function signedMoney(value, direction) {
  const amount = formatMoney(value)
  if (amount === '—') return amount
  if (direction === 'in') return `+${amount}`
  if (direction === 'out') return `−${amount}`
  return amount
}
