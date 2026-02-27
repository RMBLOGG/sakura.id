// ═══════════════════════════════════════════════════════
//   SAKURA.ID — Service Worker (Background Notifications)
// ═══════════════════════════════════════════════════════

const SW_VERSION = 'sakura-sw-v1';
const CHECK_INTERVAL = 60 * 60 * 1000; // cek jadwal tiap 1 jam

// ── Install & Activate ──────────────────────────────────
self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(clients.claim());
  // Mulai background check setelah SW aktif
  scheduleCheck();
});

// ── Terima pesan dari halaman ───────────────────────────
self.addEventListener('message', e => {
  if (e.data?.type === 'START_NOTIF_CHECK') {
    scheduleCheck();
  }
  if (e.data?.type === 'SEND_NOTIF') {
    const { title, body, icon, url } = e.data;
    self.registration.showNotification(title, {
      body,
      icon: icon || '/static/img/sakura-icon.png',
      badge: '/static/img/sakura-icon.png',
      tag: 'sakura-notif-' + Date.now(),
      data: { url }
    });
  }
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

// ── Background Schedule Check ───────────────────────────
function scheduleCheck() {
  // Jalankan cek pertama setelah 5 detik
  setTimeout(() => checkAndNotify(), 5000);
  // Ulangi tiap 1 jam
  setInterval(() => checkAndNotify(), CHECK_INTERVAL);
}

async function checkAndNotify() {
  try {
    // Ambil data subscripsi dari semua client yang terbuka
    const clientList = await clients.matchAll({ includeUncontrolled: true });
    
    // Kirim pesan ke client untuk minta data subs
    // Kalau tidak ada client (browser tutup), ambil dari API langsung
    if (clientList.length > 0) {
      clientList[0].postMessage({ type: 'GET_SUBS_FOR_SW' });
    } else {
      // Background check: fetch jadwal dari API langsung
      await fetchAndCheckSchedule();
    }
  } catch (err) {
    console.log('[SW] checkAndNotify error:', err);
  }
}

async function fetchAndCheckSchedule() {
  try {
    const resp = await fetch('/api/schedule-notif', { credentials: 'same-origin' });
    if (!resp.ok) return;
    const data = await resp.json();

    if (!data.subs?.length || !data.schedule) return;

    const today = new Date().toLocaleDateString('id-ID', { weekday: 'long' }).toLowerCase();

    Object.entries(data.schedule).forEach(([day, animes]) => {
      if (!day.toLowerCase().includes(today.slice(0, 3))) return;
      animes.forEach(anime => {
        const sub = data.subs.find(s => s.slug === anime.slug || s.title === anime.title);
        if (sub) {
          self.registration.showNotification(`🌸 Episode Baru: ${anime.title}`, {
            body: 'Tayang hari ini! Klik untuk nonton sekarang.',
            icon: anime.poster || '/static/img/sakura-icon.png',
            badge: '/static/img/sakura-icon.png',
            tag: `sakura-${anime.slug}`,
            data: { url: `/anime/${anime.slug}` }
          });
        }
      });
    });
  } catch (err) {
    console.log('[SW] fetchAndCheckSchedule error:', err);
  }
}
