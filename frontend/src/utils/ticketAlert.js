import { notifyInfo } from './notify'

export const TICKET_ALERT_SOUND_URL = encodeURI(
  '/ElevenLabs_Soft_chime_new_message_notification,_single_bright_tone.mp3'
)

let alertAudio = null
let audioUnlocked = false
let permissionRequest = null
let workerRegistration = null
const alertSessionStartedAt = Date.now()

const canUseNotifications = () => typeof window !== 'undefined' && 'Notification' in window

export const unlockTicketAlertAudio = () => {
  if (typeof window === 'undefined' || audioUnlocked) return
  try {
    alertAudio = alertAudio || new Audio(TICKET_ALERT_SOUND_URL)
    alertAudio.preload = 'auto'
    alertAudio.volume = 0.9
    // Play muted once so browsers allow later unmuted playback (including background tabs).
    alertAudio.muted = true
    const playPromise = alertAudio.play()
    if (playPromise?.then) {
      playPromise
        .then(() => {
          alertAudio.pause()
          alertAudio.currentTime = 0
          alertAudio.muted = false
          audioUnlocked = true
        })
        .catch(() => {
          if (alertAudio) alertAudio.muted = false
        })
    } else {
      alertAudio.muted = false
      audioUnlocked = true
    }
  } catch (_error) {
    // Autoplay policies can block until a real user gesture.
  }
}

export const prepareTicketNotificationWorker = () => {
  const worker = typeof navigator !== 'undefined' ? navigator.serviceWorker : null
  if (!worker || !window.isSecureContext) return Promise.resolve(null)
  if (!workerRegistration) {
    workerRegistration = worker.register('/ticket-alert-sw.js', { scope: '/' })
      .then(async (registration) => {
        if (registration.active) return registration
        return Promise.race([
          worker.ready,
          new Promise((resolve) => window.setTimeout(() => resolve(null), 5000))
        ])
      })
      .catch(() => { workerRegistration = null; return null })
  }
  return workerRegistration
}

export const ensureTicketBrowserPermission = async () => {
  if (!canUseNotifications()) return 'unsupported'
  if (Notification.permission === 'default') {
    if (!permissionRequest) {
      permissionRequest = Notification.requestPermission().catch(() => Notification.permission)
        .finally(() => { permissionRequest = null })
    }
    await permissionRequest
  }
  if (Notification.permission === 'granted') void prepareTicketNotificationWorker()
  return Notification.permission
}

export const unlockTicketAlerts = () => {
  unlockTicketAlertAudio()
  ensureTicketBrowserPermission()
}

export const playTicketAlertSound = () => {
  if (typeof window === 'undefined') return
  try {
    if (!alertAudio) {
      alertAudio = new Audio(TICKET_ALERT_SOUND_URL)
      alertAudio.preload = 'auto'
    }
    alertAudio.muted = false
    alertAudio.volume = 0.9
    alertAudio.currentTime = 0
    const playPromise = alertAudio.play()
    if (playPromise?.then) {
      playPromise
        .then(() => {
          audioUnlocked = true
        })
        .catch(() => {})
    } else {
      audioUnlocked = true
    }
  } catch (_error) {
    // Browser autoplay policies can still block in some cases.
  }
}

const showBrowserNotification = async ({ title, body, tag }) => {
  if (!canUseNotifications() || Notification.permission !== 'granted') return
  const options = { body, tag, renotify: true, silent: false, dir: 'rtl', lang: 'fa',
    data: { url: '/hq?tab=tickets' } }
  const hasWorker = typeof navigator !== 'undefined' && navigator.serviceWorker && window.isSecureContext
  if (hasWorker) {
    try {
      const registration = await prepareTicketNotificationWorker()
      if (registration?.active) {
        await registration.showNotification(title, options)
        return
      }
    } catch (_error) { /* Fall back to desktop Notification if worker delivery fails. */ }
  }
  try {
    const notification = new Notification(title, options)
    notification.onclick = () => { window.focus?.(); notification.close() }
  } catch (_error) { /* Permission/OS settings are outside page control. */ }
}

const seenSupportMessages = new Set()

export const notifyIncomingSupportMessage = (payload, userId) => {
  if (payload?.type !== 'support.message.created') return false
  const data = payload.data || {}
  if (data.actor_user_id && String(data.actor_user_id) === String(userId)) return false
  const occurredAt = Date.parse(payload.occurred_at || payload.created_at || '')
  if (Number.isFinite(occurredAt) && occurredAt < alertSessionStartedAt - 5000) return false
  const key = data.id ? `message:${data.id}` : payload.event_id || payload.id || null
  if (key && seenSupportMessages.has(key)) return false
  if (key) {
    seenSupportMessages.add(key)
    if (seenSupportMessages.size > 500) seenSupportMessages.delete(seenSupportMessages.values().next().value)
  }
  const title = 'پیام جدید پشتیبانی'
  const body = data.ticket_id ? `پیام جدید برای تیکت #${data.ticket_id} دریافت شد.` : 'یک پیام جدید در بخش پشتیبانی دریافت شد.'
  notifyInfo(body, { title, duration: 7000 })
  playTicketAlertSound()
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
    showBrowserNotification({ title, body, tag: `support-message-${data.id || data.ticket_id}` })
  }
  return true
}

const seenNewTicketIds = new Set()

export const notifyNewSupportTickets = (tickets = []) => {
  const items = (Array.isArray(tickets) ? tickets : []).filter((item) => item && item.id && !seenNewTicketIds.has(String(item.id)))
  if (!items.length) return
  for (const item of items) seenNewTicketIds.add(String(item.id))
  while (seenNewTicketIds.size > 500) seenNewTicketIds.delete(seenNewTicketIds.values().next().value)

  playTicketAlertSound()

  const first = items[0]
  const count = items.length
  const title = count === 1 ? 'تیکت جدید' : `${count} تیکت جدید`
  const tenant = first.tenant_name ? ` — ${first.tenant_name}` : ''
  const message = count === 1
    ? `#${first.id} ${first.subject || 'درخواست جدید'}${tenant}`
    : `آخرین مورد: #${first.id} ${first.subject || 'درخواست جدید'}${tenant}`

  notifyInfo(message, { title, duration: 7000 })

  // OS banner when the HQ page is in another browser tab / minimized.
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
    showBrowserNotification({
      title: `کارواش | ${title}`,
      body: message,
      tag: `hq-ticket-${first.id}`
    })
  }
}
