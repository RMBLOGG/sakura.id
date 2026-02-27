// ═══════════════════════════════════
//   SAKURA.ID — Main JS
// ═══════════════════════════════════

// ── Theme ──────────────────────────
const themeToggle = document.getElementById('themeToggle');
const iconMoon = themeToggle?.querySelector('.icon-moon');
const iconSun  = themeToggle?.querySelector('.icon-sun');
const html = document.documentElement;

function applyTheme(theme) {
  html.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  if (iconMoon && iconSun) {
    iconMoon.style.display = theme === 'dark' ? '' : 'none';
    iconSun.style.display  = theme === 'light' ? '' : 'none';
  }
}

const savedTheme = localStorage.getItem('theme') || 'dark';
applyTheme(savedTheme);

themeToggle?.addEventListener('click', () => {
  const current = html.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
});

// ── Navbar Scroll ──────────────────
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  if (navbar) {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
  }
}, { passive: true });

// ── Hamburger ──────────────────────
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('navLinks');

hamburger?.addEventListener('click', () => {
  navLinks?.classList.toggle('open');
});

// Close menu on link click
navLinks?.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => navLinks.classList.remove('open'));
});

// ── Search ─────────────────────────
const searchToggle  = document.getElementById('searchToggle');
const searchBox     = document.getElementById('searchBox');
const searchInput   = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');

let searchTimeout;

searchToggle?.addEventListener('click', (e) => {
  e.stopPropagation();
  searchBox?.classList.toggle('open');
  if (searchBox?.classList.contains('open')) {
    searchInput?.focus();
  }
});

document.addEventListener('click', (e) => {
  if (!e.target.closest('#searchWrap')) {
    searchBox?.classList.remove('open');
  }
});

searchInput?.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  const q = searchInput.value.trim();
  if (!q) {
    if (searchResults) searchResults.innerHTML = '';
    return;
  }
  if (searchResults) searchResults.innerHTML = '<div class="search-loading">Mencari...</div>';
  searchTimeout = setTimeout(() => doSearch(q), 350);
});

async function doSearch(q) {
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!searchResults) return;
    const animes = data.animes || [];
    if (!animes.length) {
      searchResults.innerHTML = '<div class="search-empty">Tidak ada hasil</div>';
      return;
    }
    searchResults.innerHTML = animes.slice(0, 8).map(a => `
      <div class="search-item" onclick="location.href='/anime/${a.slug}'">
        <img src="${a.poster}" alt="${a.title}" loading="lazy" onerror="this.src='/static/img/no-poster.jpg'">
        <div class="search-item-info">
          <div class="search-item-title">${a.title}</div>
          <div class="search-item-sub">${a.episode || ''} · ${a.type || ''}</div>
        </div>
      </div>
    `).join('');
  } catch {
    if (searchResults) searchResults.innerHTML = '<div class="search-empty">Error mencari</div>';
  }
}

// ── Hero Slideshow ─────────────────
const slides = document.querySelectorAll('.hero-slide');
const dots   = document.querySelectorAll('.hero-dot');
let currentSlide = 0;
let slideInterval;

function goToSlide(index) {
  slides.forEach((s, i) => s.classList.toggle('active', i === index));
  dots.forEach((d, i) => d.classList.toggle('active', i === index));
  currentSlide = index;
}

function nextSlide() {
  goToSlide((currentSlide + 1) % slides.length);
}

if (slides.length > 0) {
  goToSlide(0);
  slideInterval = setInterval(nextSlide, 6000);

  dots.forEach((dot, i) => {
    dot.addEventListener('click', () => {
      clearInterval(slideInterval);
      goToSlide(i);
      slideInterval = setInterval(nextSlide, 6000);
    });
  });

  // Pause on hover
  const hero = document.querySelector('.hero');
  hero?.addEventListener('mouseenter', () => clearInterval(slideInterval));
  hero?.addEventListener('mouseleave', () => {
    slideInterval = setInterval(nextSlide, 6000);
  });
}

// ── Watch Page — Server Selector ───
const serverBtns = document.querySelectorAll('.server-btn');
const playerFrame = document.getElementById('playerFrame');
const playerPlaceholder = document.getElementById('playerPlaceholder');

serverBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    serverBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const url = btn.dataset.url;
    if (playerFrame) {
      playerFrame.src = url;
      playerFrame.style.display = 'block';
    }
    if (playerPlaceholder) playerPlaceholder.style.display = 'none';
  });
});

// Auto-select first server
if (serverBtns.length > 0) {
  serverBtns[0].click();
}

// ── Episode Filter (Detail Page) ──
const episodeSearch = document.getElementById('episodeSearch');
const episodeItems  = document.querySelectorAll('.episode-item');

episodeSearch?.addEventListener('input', () => {
  const q = episodeSearch.value.toLowerCase();
  episodeItems.forEach(item => {
    item.style.display = item.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
});

// ── Lazy Load Images ───────────────
if ('IntersectionObserver' in window) {
  const imgs = document.querySelectorAll('img[data-src]');
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.src = e.target.dataset.src;
        io.unobserve(e.target);
      }
    });
  }, { rootMargin: '200px' });
  imgs.forEach(img => io.observe(img));
}

// ── Search Page ────────────────────
const searchPageInput = document.getElementById('searchPageInput');
if (searchPageInput) {
  let pageSearchTimeout;
  searchPageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = searchPageInput.value.trim();
      if (q) window.location.href = `/search?q=${encodeURIComponent(q)}`;
    }
  });
}
