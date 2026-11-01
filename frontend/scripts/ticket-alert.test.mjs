import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'
import assert from 'node:assert/strict'

const source = readFileSync(new URL('../src/utils/ticketAlert.js', import.meta.url), 'utf8')
  .replace(/^import .*$/gm, '').replace(/export /g, '')

function setup({ hidden = false, notifications = true } = {}) {
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
    notifyInfo() { calls.toasts++ }, Date, encodeURI,
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
