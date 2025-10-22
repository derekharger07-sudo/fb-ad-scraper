# Product Research Tool — Thin Slice Starter

A fast, no‑BS starter to build an ad discovery + SKU/angle intelligence slice.

## What's included
- **FastAPI** (`/health`, `/opportunities`) with SQLModel
- **SQLite** by default (flip to Postgres via env vars later)
- **Playwright scraper** stub for TikTok Creative Center (replace selectors)
- **Angle tagger** (rules) → easy to swap for ML
- **Product fingerprint** (perceptual image hash + landing key)
- **Cold‑start scoring** boilerplate
- Simple **opportunity seeding** so the UI shows something day 1

## Quick start (local or Replit)
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (One-time) install Playwright browsers (optional until you run scraper)
python -m playwright install chromium

# Run the API
uvicorn app.api.main:app --reload --port 8000
```

Open http://localhost:8000/docs for Swagger.

## Project layout
```
app/
  api/main.py           # FastAPI routes
  workers/scrape_tiktok.py  # Playwright stub (replace selectors)
  models/fingerprint.py
  models/angles.py
  models/scoring.py
  db/models.py          # SQLModel entities
  db/repo.py            # DB session + queries
infra/
  docker-compose.dev.yml
requirements.txt
```

## Environment variables (optional)
- `DATABASE_URL` (defaults to SQLite file `sqlite:///./dev.db`)
  - For Postgres later: `postgresql+psycopg://user:pass@host:5432/dbname`

## Notes / TODO
- Replace the TikTok Creative Center selectors in `scrape_tiktok.py` to match the current DOM.
- Keep scraping **polite and legal**: target public pages, rate-limit, follow platform rules.
- When ready for Postgres, change `DATABASE_URL` and run `python app/db/repo.py --init`.
- Add your embedding model + HDBSCAN if you want deduping beyond perceptual hashing.
