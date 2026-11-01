/* Notifications only: deliberately no fetch handler or offline cache. */
self.addEventListener('install', (event) => event.waitUntil(self.skipWaiting()))
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = new URL('/hq?tab=tickets', self.location.origin).href
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async (clients) => {
    const existing = clients.find((client) => new URL(client.url).pathname === '/hq')
    if (existing) { await existing.focus(); return }
    await self.clients.openWindow(target)
  }))
})
