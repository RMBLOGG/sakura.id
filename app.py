from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import time
import threading
from collections import deque

app = Flask(__name__)
app.secret_key = 'sakura-id-secret'

API_BASE = "https://www.sankavollerei.com"
CACHE_TTL = 300  # 5 menit

_cache = {}
_cache_lock = threading.Lock()
_req_times = deque()
_rate_lock = threading.Lock()


def rate_limit_wait():
    with _rate_lock:
        now = time.time()
        while _req_times and _req_times[0] < now - 60:
            _req_times.popleft()
        if len(_req_times) >= 68:
            sleep_time = 60 - (now - _req_times[0]) + 0.1
            time.sleep(max(0, sleep_time))
        _req_times.append(time.time())


def api_get(path):
    with _cache_lock:
        if path in _cache:
            data, ts = _cache[path]
            if time.time() - ts < CACHE_TTL:
                return data

    rate_limit_wait()
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        with _cache_lock:
            _cache[path] = (data, time.time())
        return data
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── Routes ─────────────────────────────────────────────

@app.route("/")
def home():
    page = request.args.get("page", 1, type=int)
    data = api_get(f"/anime/animasu/home?page={page}")
    popular_data = api_get("/anime/animasu/popular")
    movies_data = api_get("/anime/animasu/movies")
    return render_template("home.html", data=data, page=page, active="home",
                           popular_data=popular_data, movies_data=movies_data)


@app.route("/ongoing")
def ongoing():
    page = request.args.get("page", 1, type=int)
    data = api_get(f"/anime/animasu/ongoing?page={page}")
    return render_template("browse.html", data=data, page=page,
                           title="Anime Ongoing", active="ongoing")


@app.route("/completed")
def completed():
    page = request.args.get("page", 1, type=int)
    data = api_get(f"/anime/animasu/completed?page={page}")
    return render_template("browse.html", data=data, page=page,
                           title="Anime Completed", active="completed")


@app.route("/latest")
def latest():
    page = request.args.get("page", 1, type=int)
    data = api_get(f"/anime/animasu/latest?page={page}")
    return render_template("browse.html", data=data, page=page,
                           title="Update Terbaru", active="latest")


@app.route("/popular")
def popular():
    page = request.args.get("page", 1, type=int)
    data = api_get(f"/anime/animasu/popular?page={page}")
    return render_template("browse.html", data=data, page=page,
                           title="Anime Populer", active="popular")


@app.route("/movies")
def movies():
    page = request.args.get("page", 1, type=int)
    data = api_get(f"/anime/animasu/movies?page={page}")
    return render_template("movies.html", data=data, page=page, active="movies")


@app.route("/animelist")
def animelist():
    page = request.args.get("page", 1, type=int)
    data = api_get(f"/anime/animasu/animelist?page={page}")
    return render_template("animelist.html", data=data, page=page, active="animelist")


@app.route("/genre")
def genres():
    data = api_get("/anime/animasu/genres")
    return render_template("genres.html", data=data, active="genre")


@app.route("/genre/<slug>")
def genre_detail(slug):
    page = request.args.get("page", 1, type=int)
    data = api_get(f"/anime/animasu/genre/{slug}?page={page}")
    return render_template("browse.html", data=data, page=page,
                           title=f"Genre: {slug.replace('-', ' ').title()}", active="genre")


@app.route("/schedule")
def schedule():
    data = api_get("/anime/animasu/schedule")
    return render_template("schedule.html", data=data, active="schedule")


@app.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    data = None
    if keyword:
        data = api_get(f"/anime/animasu/search/{keyword}?page={page}")
    return render_template("search.html", data=data, keyword=keyword,
                           page=page, active="search")


@app.route("/anime/<slug>")
def anime_detail(slug):
    data = api_get(f"/anime/animasu/detail/{slug}")
    return render_template("detail.html", data=data, slug=slug, active="")


@app.route("/watch/<slug>")
def watch(slug):
    import re
    data = api_get(f"/anime/animasu/episode/{slug}")

    # ── Cari anime_slug ──────────────────────────────────────
    # Prioritas 1: ambil dari field animeId / anime_id di response episode
    anime_slug = ""
    if data and isinstance(data, dict):
        anime_slug = (
            data.get("animeId") or
            data.get("anime_id") or
            data.get("anime_slug") or
            (data.get("detail", {}) or {}).get("animeId", "") or
            ""
        )

    # Prioritas 2: regex dari episode slug sebagai fallback
    if not anime_slug:
        anime_slug = re.sub(r"^nonton-", "", slug)
        anime_slug = re.sub(r"-episode-\d+.*$", "", anime_slug)

    # ── Ambil poster & judul anime untuk history ─────────────
    anime_poster = ""
    anime_title  = ""
    try:
        detail = api_get(f"/anime/animasu/detail/{anime_slug}")
        if detail:
            # Coba berbagai struktur response
            d = None
            if detail.get("status") == "success":
                d = detail.get("detail") or detail.get("data", {}).get("detail")
            elif detail.get("data"):
                d = detail["data"].get("detail") or detail["data"]
            if d:
                anime_poster = d.get("poster") or d.get("image") or ""
                anime_title  = d.get("title") or ""
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

# ─── AJAX Endpoints ─────────────────────────────────────

@app.route("/api/search")
def api_search():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"animes": [], "status": "success"})
    data = api_get(f"/anime/animasu/search/{keyword}")
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
