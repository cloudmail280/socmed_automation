# socmed_automation

Web app buat auto-post produk dari **Shopee / TikTok** ke **Threads** dan **X (Twitter)** secara batch & terjadwal.

## Fitur

- Input batch link produk (Shopee / TikTok) lewat web UI
- Auto-scrape metadata: judul, harga, gambar produk
- Jadwalkan posting ke Threads dan/atau X
- Dashboard status produk & log posting

## Stack

- **Backend**: FastAPI + SQLAlchemy (SQLite)
- **Scheduler**: APScheduler
- **Scraping**: httpx (Shopee), Playwright (TikTok)
- **Publisher**: Meta Threads Graph API, X API v2 (tweepy)
- **Frontend**: Jinja2 templates + vanilla CSS

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # untuk scraper TikTok

cp .env.example .env
# edit .env, isi API keys

uvicorn app.main:app --reload
```

Buka http://localhost:8000

## Konfigurasi API

### Threads (Meta)
1. Buat app di https://developers.facebook.com/
2. Tambahkan product "Threads API"
3. Hubungkan IG/FB Business account
4. Ambil long-lived access token → isi `THREADS_ACCESS_TOKEN` & `THREADS_USER_ID`

### X (Twitter)
1. Register di https://developer.twitter.com/ (Free tier = 500 post/bulan)
2. Bikin project + app dengan akses **Read and Write**
3. Generate API Key, API Secret, Access Token, Access Token Secret
4. Isi `X_*` di `.env`

## Catatan hukum & teknis

- Scraping Shopee/TikTok **melanggar ToS masing-masing platform**. Tool ini untuk pemakaian pribadi skala kecil. Untuk produksi, gunakan API resmi (Shopee Affiliate API / TikTok Shop Partner API).
- TikTok punya anti-bot ketat — scraping sering gagal / butuh proxy.
- X Free tier dibatasi 500 post/bulan.

## Struktur

```
app/
├── main.py              FastAPI entry
├── config.py            env loader
├── database.py          SQLAlchemy setup
├── models.py            Product, ScheduledPost, PostLog
├── scheduler.py         APScheduler
├── scrapers/            shopee.py, tiktok.py
├── publishers/          threads.py, twitter.py
├── services/            post_service.py (orchestration)
├── routers/             products.py, schedule.py
└── templates/           Jinja2 HTML
```
