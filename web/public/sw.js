// Offline shell service worker for VVV Token Watch (Phase 4).
//
// Strategy:
//   * API requests are never cached.
//   * Navigations are network-first with an offline fallback page.
//   * Next.js static chunks, icons, and the manifest are cache-first with
//     runtime population.

const CACHE_NAME = 'vvv-token-watch-v1'
const OFFLINE_URL = '/offline'
const PRECACHE_URLS = [OFFLINE_URL, '/manifest.webmanifest', '/icon-192.png', '/icon-512.png']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api/')) return

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match(OFFLINE_URL).then((cached) => cached || Response.error()),
      ),
    )
    return
  }

  const isStatic =
    url.pathname.startsWith('/_next/static/') ||
    url.pathname.startsWith('/icon-') ||
    url.pathname === '/manifest.webmanifest'

  if (isStatic) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            const copy = response.clone()
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy))
            return response
          }),
      ),
    )
  }
})

// Web Push delivery (Slice 2.4): show an OS notification for alert pushes.
self.addEventListener('push', (event) => {
  let payload = { title: 'VVV Token Watch', body: 'A new alert was triggered.' }
  if (event.data) {
    try {
      const parsed = event.data.json()
      payload = {
        title: parsed.title || payload.title,
        body: parsed.body || payload.body,
      }
    } catch {
      payload.body = event.data.text()
    }
  }
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      tag: 'vvv-token-watch-alert',
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if ('focus' in client) {
          client.navigate('/alerts')
          return client.focus()
        }
      }
      return clients.openWindow('/alerts')
    }),
  )
})
