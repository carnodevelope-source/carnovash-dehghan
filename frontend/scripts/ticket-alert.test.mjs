import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'
import assert from 'node:assert/strict'

const source = readFileSync(new URL('../src/utils/ticketAlert.js', import.meta.url), 'utf8')
  .replace(/^import .*$/gm, '').replace(/export /g, '')

function setup({ hidden = false, notifications = true, clock = null } = {}) {
  const calls = { sounds: 0, toasts: 0, banners: 0 }
  class Audio {
    play() { calls.sounds++; return Promise.resolve() }
    pause() {}
  }
  class Notification {
    static permission = 'granted'
    constructor() { calls.banners++ }
  }
  const context = vm.createContext({
    Audio, Notification: notifications ? Notification : undefined,
    window: notifications ? { Notification } : {},
    document: { visibilityState: hidden ? 'hidden' : 'visible' },
    notifyInfo() { calls.toasts++ }, Date: clock ? class extends Date { static now() { return clock.now } } : Date, encodeURI,
  })
  vm.runInContext(source + ';globalThis.alertMessage=notifyIncomingSupportMessage;globalThis.permission=ensureTicketBrowserPermission;globalThis.alertTickets=notifyNewSupportTickets', context)
  return { calls, context }
}

const event = (id, actor = 2) => ({ type: 'support.message.created', data: { id, ticket_id: 10, actor_user_id: actor } })

test('each incoming message gets a toast and sound; replay and own messages do not', () => {
  const { calls, context } = setup()
  context.alertMessage(event(1), 1)
  context.alertMessage(event(1), 1)
  context.alertMessage(event(2, 1), 1)
  context.alertMessage(event(3), 1)
  assert.deepEqual(calls, { sounds: 2, toasts: 2, banners: 0 })
})

test('hidden tab gets browser notification as well as sound', () => {
  const { calls, context } = setup({ hidden: true })
  context.alertMessage(event(1), 1)
  assert.deepEqual(calls, { sounds: 1, toasts: 1, banners: 1 })
})

test('old replay messages are silent', () => {
  const { calls, context } = setup()
  context.alertMessage({ ...event(1), occurred_at: new Date(Date.now() - 60000).toISOString() }, 1)
  assert.equal(calls.sounds, 0)
  assert.equal(calls.toasts, 0)
})

test('unsupported browser notifications do not break in-app alerts', async () => {
  const { calls, context } = setup({ notifications: false })
  assert.equal(await context.permission(), 'unsupported')
  context.alertMessage(event(1), 1)
  assert.equal(calls.toasts, 1)
  assert.equal(calls.sounds, 1)
})


test('a new ticket shows one OS banner while minimized, even with duplicate live/poll delivery', () => {
  const { calls, context } = setup({ hidden: true })
  context.alertTickets([{ id: 700, subject: 'new ticket' }])
  context.alertTickets([{ id: 700, subject: 'new ticket' }])
  context.alertTickets([{ id: 701, subject: 'another ticket' }])
  assert.deepEqual(calls, { sounds: 2, toasts: 2, banners: 2 })
})

test('minimized HQ still checks alerts without loading or rendering the ticket panel', async () => {
  const hq = readFileSync(new URL('../src/views/hq/HqPanelView.vue', import.meta.url), 'utf8')
  const start = hq.indexOf('const refreshTicketsQuietly = async () => {')
  const end = hq.indexOf('const stopHqTicketLive', start)
  let polls = 0, loads = 0
  const context = vm.createContext({
    document: { visibilityState: 'hidden' },
    pollTicketAlerts: async () => { polls++ },
    loadTickets: async () => { loads++ }
  })
  vm.runInContext('let hqTicketPollingInFlight = false;'+hq.slice(start, end)+';globalThis.refresh=refreshTicketsQuietly', context)
  await context.refresh()
  await context.refresh()
  assert.equal(polls, 2)
  assert.equal(loads, 0)
})


test('a message delayed for 90 seconds is still announced if created during this session', () => {
  const clock = { now: Date.now() }
  const { calls, context } = setup({ hidden: true, clock })
  const created = new Date(clock.now + 1000).toISOString()
  clock.now += 90000
  context.alertMessage({ ...event(800), occurred_at: created }, 1)
  assert.equal(calls.banners, 1)
})

test('live and polling copies of the same message have one stable notification identity', () => {
  const { calls, context } = setup({ hidden: true })
  context.alertMessage({ ...event(801), id: 'random-live-event-id' }, 1)
  context.alertMessage(event(801), 1)
  assert.equal(calls.banners, 1)
})

test('polling recovers missed replies and retries failed detail requests without notifying old history', async () => {
  const hq = readFileSync(new URL('../src/views/hq/HqPanelView.vue', import.meta.url), 'utf8')
  const start = hq.indexOf('const pollTicketAlerts = async () => {')
  const end = hq.indexOf('const ensureSelectedTicket', start)
  const oldTime = '2026-11-01T10:00:00Z', newTime = '2026-11-01T10:02:00Z'
  let changed = false, fail = false, details = 0, alerts = []
  const context = vm.createContext({
    api: { get: async (path) => {
      if (path.endsWith('/9/')) {
        details++
        if (fail) throw new Error('temporary disconnect')
        return { data: { messages: [
          { id: 11, sender: 2, created_at: oldTime },
          { id: 12, sender: 2, created_at: newTime }
        ] } }
      }
      return { data: [{ id: 9, status: 'open', last_message_at: changed ? newTime : oldTime }] }
    } },
    notifyNewSupportTickets: () => {},
    notifyIncomingSupportMessage: (payload) => alerts.push(payload.data.id),
    authStore: { user: { id: 1 } }, Date, Map, Set
  })
  vm.runInContext('let ticketAlertsInitialized=false; let alertKnownTicketIds=new Set(); let alertKnownMessageTimes=new Map();'+hq.slice(start,end)+';globalThis.poll=pollTicketAlerts',context)
  await context.poll()
  assert.equal(details, 0)
  changed = true; fail = true
  await context.poll()
  assert.deepEqual(alerts, [])
  fail = false
  await context.poll()
  assert.deepEqual(alerts, [12])
  await context.poll()
  assert.equal(details, 2)
  assert.deepEqual(alerts, [12])
})

test('persistent notification is delivered through the service worker when available', async () => {
  const { calls, context } = setup({ hidden: true })
  let persistent = 0
  context.window.isSecureContext = true
  context.navigator = { serviceWorker: {
    register: async () => ({ active: {}, showNotification: async () => { persistent++ } })
  } }
  context.alertMessage(event(803), 1)
  await new Promise((resolve) => setImmediate(resolve))
  assert.equal(persistent, 1)
  assert.equal(calls.banners, 0)
})
