// ═══════════════════════════════════════════════════════
//   SAKURA.ID — Features: Watchlist, History, Notifikasi
// ═══════════════════════════════════════════════════════

// ══════════════════════════════════
//  STORAGE HELPERS
// ══════════════════════════════════
const SK = {
  WATCHLIST: 'sakura_watchlist',
  HISTORY:   'sakura_history',
  NOTIF_SUBS:'sakura_notif_subs',
  NOTIF_PERM:'sakura_notif_perm',
};

function storageGet(key) {
  try { return JSON.parse(localStorage.getItem(key)) || []; }
  catch { return []; }
}
function storageSet(key, val) {
  try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
}

// ══════════════════════════════════
//  WATCHLIST
// ══════════════════════════════════
const Watchlist = {
  getAll() { return storageGet(SK.WATCHLIST); },

  has(slug) { return this.getAll().some(a => a.slug === slug); },

  add(anime) {
    const list = this.getAll().filter(a => a.slug !== anime.slug);
    list.unshift({ ...anime, addedAt: Date.now() });
    storageSet(SK.WATCHLIST, list);
  },

  remove(slug) {
    storageSet(SK.WATCHLIST, this.getAll().filter(a => a.slug !== slug));
  },

  toggle(anime) {
    if (this.has(anime.slug)) { this.remove(anime.slug); return false; }
    else { this.add(anime); return true; }
  }
};

// ══════════════════════════════════
//  HISTORY / CONTINUE WATCHING
// ══════════════════════════════════
const History = {
  getAll() { return storageGet(SK.HISTORY); },

  // Ambil entri untuk anime tertentu
  getAnime(animeSlug) {
    return this.getAll().find(h => h.animeSlug === animeSlug) || null;
  },

  // Simpan progres nonton episode
  save({ animeSlug, animeTitle, animePoster, episodeSlug, episodeName }) {
    const list = this.getAll().filter(h => h.animeSlug !== animeSlug);
    list.unshift({
      animeSlug, animeTitle, animePoster,
      episodeSlug, episodeName,
      watchedAt: Date.now()
    });
    // Simpan max 30 entri
    storageSet(SK.HISTORY, list.slice(0, 30));
  },

  remove(animeSlug) {
    storageSet(SK.HISTORY, this.getAll().filter(h => h.animeSlug !== animeSlug));
  },

  clear() { storageSet(SK.HISTORY, []); }
};

// ══════════════════════════════════
//  NOTIFIKASI JADWAL
// ══════════════════════════════════
const Notif = {
  getSubs() { return storageGet(SK.NOTIF_SUBS); },

  hasSub(animeSlug) { return this.getSubs().some(s => s.slug === animeSlug); },

  subscribe(anime) {
    const subs = this.getSubs().filter(s => s.slug !== anime.slug);
    subs.push({ ...anime, subscribedAt: Date.now() });
    storageSet(SK.NOTIF_SUBS, subs);
  },

  unsubscribe(slug) {
    storageSet(SK.NOTIF_SUBS, this.getSubs().filter(s => s.slug !== slug));
  },

  toggle(anime) {
    if (this.hasSub(anime.slug)) { this.unsubscribe(anime.slug); return false; }
    else { this.subscribe(anime); return true; }
  },

  async requestPermission() {
    if (!('Notification' in window)) return 'unsupported';
    if (Notification.permission === 'granted') return 'granted';
    if (Notification.permission === 'denied') return 'denied';
    const result = await Notification.requestPermission();
    return result;
  },

  send(title, body, icon, url) {
    if (Notification.permission !== 'granted') return;
    // Kirim lewat Service Worker kalau tersedia (agar bisa muncul di background)
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'SEND_NOTIF', title, body, icon, url });
    } else {
      const n = new Notification(title, {
        body, icon: icon || '/static/img/sakura-icon.png',
        badge: '/static/img/sakura-icon.png',
        tag: 'sakura-notif'
      });
      if (url) n.onclick = () => { window.focus(); window.location.href = url; n.close(); };
      setTimeout(() => n.close(), 8000);
    }
  },

  // Cek jadwal dan kirim notif untuk anime yang disubscribe
  checkSchedule(scheduleData) {
    if (Notification.permission !== 'granted') return;
    const subs = this.getSubs();
    if (!subs.length || !scheduleData) return;

    const today = new Date().toLocaleDateString('id-ID', { weekday: 'long' }).toLowerCase();

    Object.entries(scheduleData).forEach(([day, animes]) => {
      if (!day.toLowerCase().includes(today.slice(0, 3))) return;
      animes.forEach(anime => {
        const sub = subs.find(s => s.slug === anime.slug || s.title === anime.title);
        if (sub) {
          this.send(
            `🌸 Episode Baru: ${anime.title}`,
            `Tayang hari ini! Klik untuk nonton sekarang.`,
            anime.poster,
            `/anime/${anime.slug}`
          );
        }
      });
    });
  },

  // Register Service Worker untuk notifikasi background
  async registerSW() {
    if (!('serviceWorker' in navigator)) return;
    try {
      const reg = await navigator.serviceWorker.register('/sw.js');
      console.log('[SW] Registered:', reg.scope);

      // Kirim data subs ke SW saat diminta
      navigator.serviceWorker.addEventListener('message', e => {
        if (e.data?.type === 'GET_SUBS_FOR_SW') {
          const subs = this.getSubs();
          e.source?.postMessage({ type: 'SUBS_DATA', subs });
        }
      });

      // Minta SW mulai background check
      navigator.serviceWorker.ready.then(sw => {
        sw.active?.postMessage({ type: 'START_NOTIF_CHECK' });
      });
    } catch (err) {
      console.log('[SW] Register failed:', err);
    }
  }
};

// ══════════════════════════════════
//  UI: TOMBOL WATCHLIST DI DETAIL
// ══════════════════════════════════
function initWatchlistButton() {
  const btn = document.getElementById('watchlistBtn');
  if (!btn) return;

  const slug    = btn.dataset.slug;
  const title   = btn.dataset.title;
  const poster  = btn.dataset.poster;
  const type    = btn.dataset.type || '';
  const status  = btn.dataset.status || '';

  function updateBtn(inList) {
    btn.classList.toggle('active', inList);
    btn.innerHTML = inList
      ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3h14a2 2 0 012 2v16l-8-3-8 3V5a2 2 0 012-2z"/></svg> Tersimpan`
      : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg> Simpan`;
  }

  updateBtn(Watchlist.has(slug));

  btn.addEventListener('click', () => {
    const added = Watchlist.toggle({ slug, title, poster, type, status });
    updateBtn(added);
    showToast(added ? '✅ Ditambahkan ke Watchlist' : '🗑️ Dihapus dari Watchlist');
  });
}

// ══════════════════════════════════
//  UI: TOMBOL NOTIF DI DETAIL
// ══════════════════════════════════
function initNotifButton() {
  const btn = document.getElementById('notifBtn');
  if (!btn) return;

  const slug   = btn.dataset.slug;
  const title  = btn.dataset.title;
  const poster = btn.dataset.poster;

  function updateBtn(subbed) {
    btn.classList.toggle('active', subbed);
    btn.innerHTML = subbed
      ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"/></svg> Notif Aktif`
      : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"/></svg> Ingatkan Saya`;
  }

  updateBtn(Notif.hasSub(slug));

  btn.addEventListener('click', async () => {
    if (!('Notification' in window)) {
      showToast('⚠️ Browser kamu tidak mendukung notifikasi', 'warn');
      return;
    }
    const perm = await Notif.requestPermission();
    if (perm !== 'granted') {
      showToast('❌ Izin notifikasi ditolak. Aktifkan di pengaturan browser.', 'warn');
      return;
    }
    const subbed = Notif.toggle({ slug, title, poster });
    updateBtn(subbed);
    showToast(subbed
      ? `🔔 Notifikasi aktif untuk "${title}"`
      : `🔕 Notifikasi dimatikan untuk "${title}"`
    );
  });
}

// ══════════════════════════════════
//  UI: CONTINUE WATCHING DI HOME
// ══════════════════════════════════
function renderContinueWatching() {
  const container = document.getElementById('continueWatchingSection');
  if (!container) return;

  const history = History.getAll();
  if (!history.length) {
    container.style.display = 'none';
    return;
  }

  container.style.display = '';
  const row = container.querySelector('.continue-row');
  if (!row) return;

  row.innerHTML = history.slice(0, 12).map(h => {
    const timeAgo = formatTimeAgo(h.watchedAt);
    const posterSrc = h.animePoster && h.animePoster.trim() ? h.animePoster : '/static/img/no-poster.svg';
    return `
    <a href="/watch/${h.episodeSlug}" class="continue-card">
      <div class="continue-poster-wrap">
        <img src="${posterSrc}" alt="${h.animeTitle}" loading="lazy"
             onerror="this.src='/static/img/no-poster.svg'">
        <div class="continue-overlay">
          <div class="continue-play">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg>
          </div>
        </div>
        <button class="continue-remove" data-slug="${h.animeSlug}" title="Hapus dari riwayat"
                onclick="event.preventDefault(); event.stopPropagation(); removeContinue('${h.animeSlug}', this.closest('.continue-card'))">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="continue-info">
        <div class="continue-title">${h.animeTitle}</div>
        <div class="continue-ep">${h.episodeName}</div>
        <div class="continue-time">${timeAgo}</div>
      </div>
    </a>`;
  }).join('');
}

function removeContinue(animeSlug, cardEl) {
  History.remove(animeSlug);
  cardEl?.remove();
  const row = document.querySelector('.continue-row');
  if (row && !row.children.length) {
    document.getElementById('continueWatchingSection').style.display = 'none';
  }
  showToast('🗑️ Dihapus dari riwayat');
}
window.removeContinue = removeContinue;

// ══════════════════════════════════
//  UI: SAVE HISTORY DI WATCH PAGE
// ══════════════════════════════════
function initWatchHistory() {
  const meta = document.getElementById('watchMeta');
  if (!meta) return;

  let { animeSlug, animeTitle, animePoster, episodeSlug, episodeName } = meta.dataset;
  if (!animeSlug || !episodeSlug) return;

  // Fallback: kalau poster kosong, coba ambil dari gambar pertama yang ada di halaman
  function getPosterFallback() {
    if (animePoster && animePoster.trim()) return animePoster.trim();
    // Cari gambar anime di halaman (poster dari card atau img pertama yang bukan icon)
    const imgs = document.querySelectorAll('img[src]');
    for (const img of imgs) {
      const src = img.src || '';
      if (src && src.startsWith('http') && !src.includes('no-poster') && img.naturalWidth > 50) {
        return src;
      }
    }
    return '';
  }

  // Simpan ke history setelah 5 detik nonton
  setTimeout(() => {
    const poster = getPosterFallback();
    History.save({
      animeSlug,
      animeTitle: animeTitle || episodeName || '',
      animePoster: poster,
      episodeSlug,
      episodeName
    });
  }, 5000);
}

// ══════════════════════════════════
//  UI: WATCHLIST PAGE
// ══════════════════════════════════
function renderWatchlistPage() {
  const container = document.getElementById('watchlistPageContainer');
  if (!container) return;

  const list = Watchlist.getAll();
  if (!list.length) {
    container.innerHTML = `
      <div class="empty-state-big">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text3);margin:0 auto 1rem">
          <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/>
        </svg>
        <h3>Watchlist kamu kosong</h3>
        <p>Tambahkan anime dari halaman detail dengan klik tombol "Simpan"</p>
        <a href="/" class="btn-primary" style="display:inline-flex;margin-top:1.5rem">Jelajahi Anime</a>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="watchlist-grid">
      ${list.map(a => `
      <div class="watchlist-item" id="wl-${a.slug}">
        <a href="/anime/${a.slug}" class="watchlist-poster-wrap">
          <img src="${a.poster}" alt="${a.title}" loading="lazy" onerror="this.src='/static/img/no-poster.svg'">
          <div class="watchlist-overlay">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
            </svg>
          </div>
        </a>
        <div class="watchlist-info">
          <a href="/anime/${a.slug}" class="watchlist-title">${a.title}</a>
          <div class="watchlist-meta">
            ${a.type ? `<span class="badge badge-dark">${a.type}</span>` : ''}
            ${a.status ? `<span class="badge ${a.status === 'Ongoing' ? 'badge-red' : 'badge-green'}">${a.status}</span>` : ''}
          </div>
          <button class="watchlist-remove" onclick="removeFromWatchlist('${a.slug}')">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
              <path d="M10 11v6M14 11v6M9 6V4h6v2"/>
            </svg>
            Hapus
          </button>
        </div>
      </div>
      `).join('')}
    </div>`;
}

function removeFromWatchlist(slug) {
  Watchlist.remove(slug);
  document.getElementById(`wl-${slug}`)?.remove();
  const grid = document.querySelector('.watchlist-grid');
  if (grid && !grid.children.length) renderWatchlistPage();
  showToast('🗑️ Dihapus dari Watchlist');
}
window.removeFromWatchlist = removeFromWatchlist;

// ══════════════════════════════════
//  TOAST NOTIFICATION
// ══════════════════════════════════
function showToast(msg, type = 'info') {
  const existing = document.querySelector('.sakura-toast');
  existing?.remove();

  const toast = document.createElement('div');
  toast.className = `sakura-toast ${type}`;
  toast.textContent = msg;
  document.body.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}
window.showToast = showToast;

// ══════════════════════════════════
//  HELPER: FORMAT TIME AGO
// ══════════════════════════════════
function formatTimeAgo(ts) {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1)  return 'Baru saja';
  if (m < 60) return `${m} menit lalu`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} jam lalu`;
  const d = Math.floor(h / 24);
  if (d < 7)  return `${d} hari lalu`;
  return new Date(ts).toLocaleDateString('id-ID', { day:'numeric', month:'short' });
}

// ══════════════════════════════════
//  INIT SEMUA FITUR
// ══════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  initWatchlistButton();
  initNotifButton();
  initWatchHistory();
  renderContinueWatching();
  renderWatchlistPage();
  // Register Service Worker untuk notifikasi background
  Notif.registerSW();
});
