import { notifyInfo } from './notify'

export const TICKET_ALERT_SOUND_URL = encodeURI(
  '/ElevenLabs_Soft_chime_new_message_notification,_single_bright_tone.mp3'
)

let alertAudio = null
let audioUnlocked = false
let browserPermissionRequested = false

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

export const ensureTicketBrowserPermission = async () => {
  if (!canUseNotifications()) return 'unsupported'
  if (browserPermissionRequested) return Notification.permission
  browserPermissionRequested = true
  if (Notification.permission === 'default') {
    try {
      await Notification.requestPermission()
    } catch (_error) {
      // Ignore permission errors; in-app toast + sound still work.
    }
  }
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

const showBrowserNotification = ({ title, body, tag }) => {
  if (!canUseNotifications() || Notification.permission !== 'granted') return
  try {
    const notification = new Notification(title, {
      body,
      tag,
      renotify: true,
      // Keep OS sound as fallback when the tab is backgrounded and HTMLAudio may be blocked.
      silent: false,
      dir: 'rtl',
      lang: 'fa'
    })
    notification.onclick = () => {
      window.focus?.()
      notification.close()
    }
  } catch (_error) {
    // Some browsers block Notification construction outside secure contexts.
  }
}

const seenSupportMessages = new Set()

export const notifyIncomingSupportMessage = (payload, userId) => {
  if (payload?.type !== 'support.message.created') return false
  const data = payload.data || {}
  if (data.actor_user_id && String(data.actor_user_id) === String(userId)) return false
  const occurredAt = Date.parse(payload.occurred_at || payload.created_at || '')
  if (Number.isFinite(occurredAt) && Date.now() - occurredAt > 30_000) return false
  const key = payload.event_id || payload.id || (data.id ? `message:${data.id}` : null)
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

export const notifyNewSupportTickets = (tickets = []) => {
  const items = (Array.isArray(tickets) ? tickets : []).filter((item) => item && item.id)
  if (!items.length) return

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
