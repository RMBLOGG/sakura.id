from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import time
import threading
import os
import json
from collections import deque

app = Flask(__name__)
app.secret_key = 'sakura-id-secret'

# Supabase & Web Push Config
SUPABASE_URL      = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY      = os.environ.get('SUPABASE_KEY', '')
VAPID_PUBLIC_KEY  = "BGJLPB6bAtAMW05nqxt_LywHfEbsD85W2QZLGYlpjgVMNxqiEwfzMlow3fxdDtmq_iQQ6rjvLno2JKc0aDhPopw"
VAPID_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgy/2ZqvB152EOc8My\npt2iXlCsUo49MwDGhSJMj9zs3e6hRANCAARiSzwemwLQDFtOZ6sbfy8sB3xG7A/O\nVtkGSxmJaY4FTDcaohMH8zJaMN38XQ7Zqv4kEOq47y56NiSnNGg4T6Kc\n-----END PRIVATE KEY-----"
VAPID_CLAIMS      = {"sub": "mailto:admin@sakura-id.vercel.app"}

def supabase_req(method, path, body=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        resp = requests.request(method, url, headers=headers,
                                json=body, params=params, timeout=10)
        if resp.text:
            try: return resp.json()
            except: return {}
        return {}
    except Exception as e:
        print(f"[Supabase] Error: {e}")
        return {}

API_BASE = "https://www.sankavollerei.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.sankavollerei.com/',
    'Origin': 'https://www.sankavollerei.com',
    'Connection': 'keep-alive',
}

cache_store = {}
CACHE_DURATION = {
    'short':  600,
    'medium': 1800,
    'long':   3600,
}

_request_lock = threading.Lock()
_request_times = []
MAX_REQUESTS_PER_MINUTE = 60

def _wait_for_rate_limit():
    with _request_lock:
        now = time.time()
        while _request_times and now - _request_times[0] > 60:
            _request_times.pop(0)
        if len(_request_times) >= MAX_REQUESTS_PER_MINUTE:
            wait = 60 - (now - _request_times[0]) + 0.5
            time.sleep(max(wait, 0))
        _request_times.append(time.time())

def get_cached_or_fetch(url, cache_key, timeout=15, cache_type='short'):
    now = time.time()
    duration = CACHE_DURATION.get(cache_type, CACHE_DURATION['short'])
    if cache_key in cache_store:
        cached_data, timestamp = cache_store[cache_key]
        if now - timestamp < duration:
            return cached_data
    _wait_for_rate_limit()
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            if response.status_code in (403, 429):
                time.sleep((attempt + 1) * 5)
                continue
            response.raise_for_status()
            data = response.json()
            cache_store[cache_key] = (data, now)
            return data
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(2)
    if cache_key in cache_store:
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
    return render_template("browse.html", data=data, page=page, title="Anime Ongoing", active="ongoing")

@app.route("/completed")
def completed():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/completed?page={page}", f"completed_{page}", cache_type='short')
    return render_template("browse.html", data=data, page=page, title="Anime Completed", active="completed")

@app.route("/latest")
def latest():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/latest?page={page}", f"latest_{page}", cache_type='short')
    return render_template("browse.html", data=data, page=page, title="Update Terbaru", active="latest")

@app.route("/popular")
def popular():
    page = request.args.get("page", 1, type=int)
    data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/popular?page={page}", f"popular_{page}", cache_type='short')
    return render_template("browse.html", data=data, page=page, title="Anime Populer", active="popular")

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
        try:
            response = requests.get(f"{API_BASE}/anime/animasu/search/{keyword}?page={page}", headers=HEADERS, timeout=10)
            data = response.json()
        except Exception as e:
            data = {"status": "error", "message": str(e)}
    return render_template("search.html", data=data, keyword=keyword, page=page, active="search")

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
            data.get("animeId") or data.get("anime_id") or data.get("anime_slug") or
            (data.get("detail", {}) or {}).get("animeId", "") or ""
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
                           anime_slug=anime_slug, anime_poster=anime_poster,
                           anime_title=anime_title, active="")

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


# ─── Helper ──────────────────────────────────────────────

def extract_schedule(d):
    if not isinstance(d, dict):
        return {}
    for key in ["schedule", "data"]:
        val = d.get(key)
        if isinstance(val, dict):
            if any(k in val for k in ["senin","selasa","rabu","kamis","jumat","sabtu","minggu"]):
                return val
            inner = val.get("schedule") or val.get("data")
            if isinstance(inner, dict):
                return inner
    return {}


# ─── API Endpoints ───────────────────────────────────────

@app.route("/api/schedule-notif")
def api_schedule_notif():
    subs_raw = request.args.get("subs", "[]")
    try:
        subs = json.loads(subs_raw)
    except Exception:
        subs = []
    schedule_data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/schedule", "schedule", cache_type='long')
    return jsonify({"subs": subs, "schedule": extract_schedule(schedule_data)})


@app.route("/api/debug/schedule")
def debug_schedule():
    import datetime
    schedule_data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/schedule", "schedule", cache_type="long")
    schedule = extract_schedule(schedule_data)
    now_wib = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    today = now_wib.strftime("%A").lower()
    day_map = {"monday":"senin","tuesday":"selasa","wednesday":"rabu",
               "thursday":"kamis","friday":"jumat","saturday":"sabtu","sunday":"minggu"}
    today_id = day_map.get(today, today)
    return jsonify({
        "utc_time": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "wib_time": now_wib.strftime("%Y-%m-%d %H:%M:%S"),
        "today_id": today_id,
        "schedule_keys": list(schedule.keys()),
        "todays_anime_count": len([a for day, animes in schedule.items()
                                   if isinstance(animes, list) and today_id in day.lower()
                                   for a in animes])
    })


@app.route("/api/push/vapid-public-key")
def push_vapid_key():
    return jsonify({"key": VAPID_PUBLIC_KEY})


@app.route("/api/push/subscribe", methods=["POST"])
def push_subscribe():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    endpoint = data.get("endpoint")
    p256dh   = data.get("keys", {}).get("p256dh")
    auth     = data.get("keys", {}).get("auth")
    if not all([endpoint, p256dh, auth]):
        return jsonify({"error": "Missing fields"}), 400
    supabase_req("DELETE", "push_subscriptions", params={"endpoint": f"eq.{endpoint}"})
    supabase_req("POST", "push_subscriptions", body={"endpoint": endpoint, "p256dh": p256dh, "auth": auth})
    return jsonify({"status": "ok"})


@app.route("/api/push/unsubscribe", methods=["POST"])
def push_unsubscribe():
    data = request.get_json()
    endpoint = data.get("endpoint") if data else None
    if endpoint:
        supabase_req("DELETE", "push_subscriptions", params={"endpoint": f"eq.{endpoint}"})
    return jsonify({"status": "ok"})


@app.route("/api/push/send-schedule", methods=["GET", "POST"])
def push_send_schedule():
    try:
        from pywebpush import webpush, WebPushException
        import datetime

        subs = supabase_req("GET", "push_subscriptions", params={"select": "*"})
        if not subs or not isinstance(subs, list):
            return jsonify({"status": "no subscribers"})

        schedule_data = get_cached_or_fetch(f"{API_BASE}/anime/animasu/schedule", "schedule", cache_type="long")
        schedule = extract_schedule(schedule_data)

        # Pakai waktu WIB (UTC+7)
        now_wib = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        today = now_wib.strftime("%A").lower()
        today_date = now_wib.date().isoformat()

        day_map = {
            "monday": "senin", "tuesday": "selasa", "wednesday": "rabu",
            "thursday": "kamis", "friday": "jumat", "saturday": "sabtu", "sunday": "minggu"
        }
        today_id = day_map.get(today, today)

        todays_anime = []
        for day, animes in schedule.items():
            if isinstance(animes, list) and today_id in day.lower():
                todays_anime.extend(animes)

        if not todays_anime:
            return jsonify({"status": "no anime today", "today_wib": today_id, "schedule_keys": list(schedule.keys())})

        already_sent_raw = supabase_req("GET", "notif_sent", params={
            "select": "anime_slug",
            "sent_date": f"eq.{today_date}"
        })
        already_sent = set()
        if isinstance(already_sent_raw, list):
            already_sent = {r["anime_slug"] for r in already_sent_raw}

        new_anime = [a for a in todays_anime if a.get("slug") not in already_sent]
        if not new_anime:
            return jsonify({"status": "already sent today", "sent": 0})

        sent = 0
        failed = 0
        errors = []
        newly_sent_slugs = []

        for sub in subs:
            for anime in new_anime:
                try:
                    payload = json.dumps({
                        "title": f"🌸 Episode Baru: {anime.get('title', '')}",
                        "body": "Tayang hari ini! Klik untuk nonton sekarang.",
                        "icon": anime.get("poster", "/static/img/sakura-icon.png"),
                        "url": f"/anime/{anime.get('slug', '')}"
                    })
                    webpush(
                        subscription_info={
                            "endpoint": sub["endpoint"],
                            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}
                        },
                        data=payload,
                        vapid_private_key=VAPID_PRIVATE_KEY,
                        vapid_claims=VAPID_CLAIMS
                    )
                    sent += 1
                    slug = anime.get("slug")
                    if slug and slug not in newly_sent_slugs:
                        newly_sent_slugs.append(slug)
                except WebPushException as e:
                    err_msg = str(e)
                    errors.append(f"WebPushException [{anime.get('slug')}]: {err_msg}")
                    if "410" in err_msg or "404" in err_msg:
                        supabase_req("DELETE", "push_subscriptions",
                                     params={"endpoint": f"eq.{sub['endpoint']}"})
                    failed += 1
                except Exception as e:
                    errors.append(f"Exception [{anime.get('slug')}]: {str(e)}")
                    failed += 1

        for slug in newly_sent_slugs:
            try:
                supabase_req("POST", "notif_sent", body={"anime_slug": slug, "sent_date": today_date})
            except Exception:
                pass

        return jsonify({
            "status": "ok",
            "sent": sent,
            "failed": failed,
            "new_anime": len(new_anime),
            "errors": errors[:5]  # tampilkan max 5 error pertama
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── AJAX ────────────────────────────────────────────────

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
