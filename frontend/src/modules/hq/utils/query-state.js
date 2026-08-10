import { formatJalaliDate } from '../../../utils/date'

function toJalaliDate(date) {
  return formatJalaliDate(date).replace(/-/g, '/')
}

export function resolveReportRange(rangeKey) {
  if (rangeKey === 'all') return { start: '', end: '' }
  const now = new Date()
  const start = new Date(now)
  if (rangeKey === 'day') return { start: toJalaliDate(start), end: toJalaliDate(now) }
  if (rangeKey === 'week') {
    const day = now.getDay()
    const offset = day === 0 ? 6 : day - 1
    start.setDate(now.getDate() - offset)
    return { start: toJalaliDate(start), end: toJalaliDate(now) }
  }
  start.setDate(1)
  return { start: toJalaliDate(start), end: toJalaliDate(now) }
}

export function readQueryState(route, defaults = {}) {
  const query = route.query || {}
  const next = { ...defaults }
  Object.keys(defaults).forEach((key) => {
    if (query[key] !== undefined && query[key] !== null && String(query[key]) !== '') {
      next[key] = String(query[key])
    }
  })
  return next
}

export function buildQueryPatch(currentQuery, patch) {
  const next = { ...currentQuery }
  Object.entries(patch).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === false) {
      delete next[key]
    } else if (value === true) {
      next[key] = '1'
    } else {
      next[key] = String(value)
    }
  })
  return next
}
