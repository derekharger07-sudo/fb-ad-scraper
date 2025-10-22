# Product Research Tool — Thin Slice Starter

A fast, no-BS starter to build an ad discovery + SKU/angle intelligence slice.

## What's included
- **FastAPI** (`/health`, `/opportunities`) with SQLModel  
- **SQLite** by default (flip to Postgres via env vars later)  
- **Playwright scraper** stub for TikTok Creative Center (replace selectors)  
- **Angle tagger** (rules) → easy to swap for ML  
- **Product fingerprint** (perceptual image hash + landing key)  
- **Cold-start scoring** boilerplate  
- Simple **opportunity seeding** so the UI shows something day 1  

## Quick start (local or Replit)
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (One-time) install Playwright browsers (optional until you run scraper)
python -m playwright install chromium

# Run the API
uvicorn app.api.main:app --reload --port 8000
