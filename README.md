# SAKURA.ID — Anime Streaming Website

Website nonton anime sub indo dengan desain Netflix-inspired.

## Stack
- **Backend:** Flask (Python)
- **API:** Sankavollerei API (animasu source)
- **Cache:** In-memory, TTL 5 menit (hemat rate limit 70 req/menit)

## Endpoints yang Digunakan
| Route | API Endpoint |
|---|---|
| `/` | `/anime/animasu/home` |
| `/ongoing` | `/anime/animasu/ongoing` |
| `/completed` | `/anime/animasu/completed` |
| `/latest` | `/anime/animasu/latest` |
| `/animelist` | `/anime/animasu/animelist` |
| `/genre` | `/anime/animasu/genres` |
| `/genre/<slug>` | `/anime/animasu/genre/:slug` |
| `/schedule` | `/anime/animasu/schedule` |
| `/search` | `/anime/animasu/search/:keyword` |
| `/anime/<slug>` | `/anime/animasu/detail/:slug` |
| `/watch/<slug>` | `/anime/animasu/episode/:slug` |

## Run Lokal
```bash
pip install -r requirements.txt
python app.py
# Buka http://localhost:5000
```

## Deploy ke Vercel
1. Install Vercel CLI: `npm i -g vercel`
2. Login: `vercel login`
3. Deploy: `vercel --prod`

Atau pakai Vercel Dashboard:
1. Upload/push ke GitHub
2. Import repo di vercel.com
3. Framework: **Other** (bukan Next.js)
4. Deploy!

## Fitur
- ✅ Hero banner slideshow otomatis
- ✅ Dark / Light mode (disimpan di localStorage)
- ✅ Search real-time dengan debounce
- ✅ Video player embedded + pilih server
- ✅ Halaman detail anime lengkap dengan daftar episode
- ✅ Filter episode
- ✅ Jadwal tayang per hari
- ✅ Browse per genre
- ✅ Pagination semua halaman
- ✅ Rate limit protection + caching 5 menit
- ✅ Mobile responsive
