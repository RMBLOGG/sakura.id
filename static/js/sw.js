// ═══════════════════════════════════════════════════════
//   SAKURA.ID — Service Worker (Web Push Notifications)
// ═══════════════════════════════════════════════════════

const SW_VERSION = 'sakura-sw-v2';

// ── Install & Activate ──────────────────────────────────
self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(clients.claim());
});

// ── Terima Push dari Server (Web Push Protocol) ─────────
self.addEventListener('push', e => {
  if (!e.data) return;

  let payload = {};
  try { payload = e.data.json(); } catch { payload = { title: e.data.text() }; }

  const title   = payload.title  || '🌸 SAKURA.ID';
  const options = {
    body:    payload.body  || 'Ada update baru!',
    icon:    payload.icon  || '/static/img/sakura-icon.png',
    badge:   '/static/img/sakura-icon.png',
    tag:     payload.tag   || 'sakura-notif',
    data:    { url: payload.url || '/' },
    vibrate: [200, 100, 200],
    requireInteraction: false,
  };

  e.waitUntil(self.registration.showNotification(title, options));
});

// ── Klik notifikasi → buka halaman ─────────────────────
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || '/';

  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.focus();
          client.navigate(url);
          return;
        }
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});

// ── Terima pesan manual dari halaman ───────────────────
self.addEventListener('message', e => {
  if (e.data?.type === 'SEND_NOTIF') {
    const { title, body, icon, url } = e.data;
    self.registration.showNotification(title, {
      body,
      icon: icon || '/static/img/sakura-icon.png',
      badge: '/static/img/sakura-icon.png',
      tag: 'sakura-manual-' + Date.now(),
      data: { url }
    });
  }
});
