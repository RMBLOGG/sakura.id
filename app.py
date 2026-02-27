from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import time
import threading
import os
from collections import deque

app = Flask(__name__)
app.secret_key = 'sakura-id-secret'

API_BASE = "https://www.sankavollerei.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.sankavollerei.com/',
    'Origin': 'https://www.sankavollerei.com',
    'Connection': 'keep-alive',
}

# ============================================================
# CACHE SYSTEM
# Durasi cache berbeda tiap jenis konten:
#   - List/home/ongoing : 10 menit (konten sering update)
#   - Detail anime      : 30 menit (jarang berubah)
#   - Episode detail    : 60 menit (hampir tidak berubah)
#   - Schedule/genres   : 60 menit
# ============================================================
cache_store = {}
CACHE_DURATION = {
    'short':  600,   # 10 menit  - list, home, recent
    'medium': 1800,  # 30 menit  - detail anime
    'long':   3600,  # 60 menit  - episode, schedule, genres
}

# Rate limiter: maks 60 req/menit (aman di bawah limit 70)
_request_lock = threading.Lock()
_request_times = []
MAX_REQUESTS_PER_MINUTE = 60

def _wait_for_rate_limit():
    """Pastikan tidak melebihi 60 request per menit"""
    with _request_lock:
        now = time.time()
        while _request_times and now - _request_times[0] > 60:
            _request_times.pop(0)
        if len(_request_times) >= MAX_REQUESTS_PER_MINUTE:
            wait = 60 - (now - _request_times[0]) + 0.5
            print(f"⏳ Rate limit: tunggu {wait:.1f}s")
            time.sleep(max(wait, 0))
        _request_times.append(time.time())

def get_cached_or_fetch(url, cache_key, timeout=15, cache_type='short'):
    """Ambil dari cache atau fetch dari API dengan rate limit protection"""
    now = time.time()
    duration = CACHE_DURATION.get(cache_type, CACHE_DURATION['short'])

    # Cek cache dulu
    if cache_key in cache_store:
        cached_data, timestamp = cache_store[cache_key]
        if now - timestamp < duration:
            print(f"✅ Cache HIT: {cache_key}")
            return cached_data

    print(f"🌐 API Request: {cache_key}")
    _wait_for_rate_limit()

    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            if response.status_code in (403, 429):
                wait = (attempt + 1) * 5
                print(f"⚠️ Rate limited ({response.status_code}), retry {attempt+1}/3 dalam {wait}s")
                time.sleep(wait)
                continue
            response.raise_for_status()
            data = response.json()
            cache_store[cache_key] = (data, now)  # hanya cache kalau sukses
            return data
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(2)

    # Semua retry gagal - coba pakai stale cache
    if cache_key in cache_store:
        print(f"⚠️ Pakai stale cache: {cache_key}")
        return cache_store[cache_key][0]

    return {"status": "error", "message": str(last_error)}


# ─── Routes ─────────────────────────────────────────────

@app.route("/")
def home():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/home?page={page}", f"home_{page}", cache_type='short')
    popular_data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/popular", "popular", cache_type='short')
    movies_data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/movies", "movies", cache_type='short')
    return render_template("home.html", data=data, page=page, active="home",
                           popular_data=popular_data, movies_data=movies_data)


@app.route("/ongoing")
def ongoing():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/ongoing?page={page}", f"ongoing_{page}", cache_type='short')
    return render_template("browse.html", data=data, page=page,
                           title="Anime Ongoing", active="ongoing")


@app.route("/completed")
def completed():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/completed?page={page}", f"completed_{page}", cache_type='short')
    return render_template("browse.html", data=data, page=page,
                           title="Anime Completed", active="completed")


@app.route("/latest")
def latest():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/latest?page={page}", f"latest_{page}", cache_type='short')
    return render_template("browse.html", data=data, page=page,
                           title="Update Terbaru", active="latest")


@app.route("/popular")
def popular():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/popular?page={page}", f"popular_{page}", cache_type='short')
    return render_template("browse.html", data=data, page=page,
                           title="Anime Populer", active="popular")


@app.route("/movies")
def movies():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/movies?page={page}", f"movies_{page}", cache_type='short')
    return render_template("movies.html", data=data, page=page, active="movies")


@app.route("/animelist")
def animelist():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/animelist?page={page}", f"animelist_{page}", cache_type='long')
    return render_template("animelist.html", data=data, page=page, active="animelist")


@app.route("/genre")
def genres():
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/genres", "genres", cache_type='long')
    return render_template("genres.html", data=data, active="genre")


@app.route("/genre/<slug>")
def genre_detail(slug):
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/genre/{slug}?page={page}", f"genre_{slug}_{page}", cache_type='medium')
    return render_template("browse.html", data=data, page=page,
                           title=f"Genre: {slug.replace('-', ' ').title()}", active="genre")


@app.route("/schedule")
def schedule():
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/schedule", "schedule", cache_type='long')
    return render_template("schedule.html", data=data, active="schedule")


@app.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    data = None
    if keyword:
        # Search tidak di-cache (query unik tiap user)
        try:
            response = requests.get(f"{API_BASE}/anime/animasu/search/{keyword}?page={page}", headers=HEADERS, timeout=10)
            data = response.json()
        except Exception as e:
            data = {"status": "error", "message": str(e)}
    return render_template("search.html", data=data, keyword=keyword,
                           page=page, active="search")


@app.route("/anime/<slug>")
def anime_detail(slug):
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/detail/{slug}", f"detail_{slug}", cache_type='medium')
    return render_template("detail.html", data=data, slug=slug, active="")


@app.route("/watch/<slug>")
def watch(slug):
    import re
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/episode/{slug}", f"episode_{slug}", cache_type='long')

    anime_slug = ""
    if data and isinstance(data, dict):
        anime_slug = (
            data.get("animeId") or
            data.get("anime_id") or
            data.get("anime_slug") or
            (data.get("detail", {}) or {}).get("animeId", "") or
            ""
        )

    if not anime_slug:
        anime_slug = re.sub(r"^nonton-", "", slug)
        anime_slug = re.sub(r"-episode-\d+.*$", "", anime_slug)

    anime_poster = ""
    anime_title = ""
    try:
        detail = get_cached_or_fetch(f"{API_BASE}/anime/animasu/detail/{anime_slug}", f"detail_{anime_slug}", cache_type='medium')
        if detail:
            d = None
            if detail.get("status") == "success":
                d = detail.get("detail") or detail.get("data", {}).get("detail")
            elif detail.get("data"):
                d = detail["data"].get("detail") or detail["data"]
            if d:
                anime_poster = d.get("poster") or d.get("image") or ""
                anime_title = d.get("title") or ""
    except Exception:
        pass

    return render_template("watch.html", data=data, slug=slug,
                           anime_slug=anime_slug,
                           anime_poster=anime_poster,
                           anime_title=anime_title,
                           active="")


@app.route("/watchlist")
def watchlist():
    return render_template("watchlist.html", active="watchlist")


# ─── Service Worker ──────────────────────────────────────

@app.route("/sw.js")
def service_worker():
    from flask import Response
    response = Response(
        open(os.path.join(app.static_folder, 'sw.js')).read(),
        mimetype='application/javascript'
    )
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response


# ─── API: Schedule untuk SW background check ────────────

@app.route("/api/schedule-notif")
def api_schedule_notif():
    """Endpoint untuk Service Worker cek jadwal di background"""
    subs_raw = request.args.get("subs", "[]")
    try:
        import json
        subs = json.loads(subs_raw)
    except Exception:
        subs = []

    schedule_data = get_cached_or_fetch(
        f"{API_BASE}/anime/animasu/schedule",
        "schedule",
        cache_type='long'
    )

    return jsonify({
        "subs": subs,
        "schedule": schedule_data.get("data", schedule_data) if isinstance(schedule_data, dict) else {}
    })


# ─── AJAX Endpoints ─────────────────────────────────────

@app.route("/api/search")
def api_search():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"animes": [], "status": "success"})
    try:
        response = requests.get(f"{API_BASE}/anime/animasu/search/{keyword}", headers=HEADERS, timeout=10)
        data = response.json()
    except Exception as e:
        data = {"status": "error", "message": str(e)}
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
