# 🚀 PC Scraper Setup Guide - Windows

## Your Current Setup

You're using the **Distributed Scraper** with the auto-installer batch script.

---

## ✅ What's Ready to Use

### 1. **Main Scraper Script**
- **File:** `install_and_run.bat`
- **What it does:** 
  - Installs dependencies
  - Lets you choose keyword file
  - Configures workers/threads
  - Runs the distributed scraper

### 2. **Keyword Files Available**
- `keywords.txt` - 50 test keywords (~30 min)
- `keywords_246_full.txt` - 246 keywords (~2-4 hours)
- `keywords_leggings_only.txt` - Just "leggings" (quick test for advertiser scraping)

### 3. **New Features Included**
- ✅ Survey/Quiz page detection (fixed)
- ✅ `page_type` saving to database (fixed)
- ✅ Advertiser deep scraping (optional, see below)

---

## 🏃 How to Run (Quick Start)

### Standard Scraping (No Advertiser Scraping)

1. **Download & Extract ZIP**
2. **Double-click:** `install_and_run.bat`
3. **Follow prompts:**
   - Enter SpyFu API key (if not set)
   - Choose keyword file
   - Choose worker/thread configuration
4. **Wait for results!**

---

## 🎯 Advertiser Deep Scraping (ENABLED BY DEFAULT)

### What It Does
For each ad found, it **automatically scrapes ALL ads** from that advertiser's Facebook page.

**Example:**
1. Searches for "leggings"
2. Finds ad from "Ninepine"
3. Saves that ad
4. **Goes to Ninepine's Ad Library profile**
5. **Scrapes ALL 26 ads from Ninepine**
6. Continues with next "leggings" ad

### How to Disable (If Needed)

Open `distributed_scraper.py` in Notepad and change **line 39**:

```python
# Change from:
ENABLE_ADVERTISER_SCRAPING = True

# To:
ENABLE_ADVERTISER_SCRAPING = False
```

### Performance Impact

⚠️ **This feature is ON by default** and increases scrape time:

**Without feature:**
- "leggings" = ~10 ads in 30 seconds

**With feature (current default):**
- "leggings" = ~10 ads + (5-20 ads per advertiser × 8 advertisers) = ~100-200 ads in 5-10 minutes

---

## 📁 Database Connection

Your scraper saves to **Replit's PostgreSQL database** using:
- `DATABASE_URL` environment variable (from `.env` file)

All ads save automatically - no setup needed!

---

## 🔧 Recommended Configurations

### Your System (i5 + 16GB RAM):
```
Workers: 3
Threads: 10
Total browsers: 30
```

### If You Want Faster (with advertiser scraping):
```
Workers: 2
Threads: 5
Total browsers: 10
(Less browsers = more stable with advertiser scraping)
```

---

## 📊 Check Results

### Via Database Query:
```bash
python -c "from app.db.repo import get_session; from app.db.models import AdCreative; from sqlmodel import select, func; print(f'Total ads: {next(get_session()).exec(select(func.count()).select_from(AdCreative)).one()}')"
```

### Via API (open in browser):
```bash
# Start server
uvicorn app.api.main:app --host 0.0.0.0 --port 5000

# Then visit:
http://localhost:5000/api/opportunity-cards
```

---

## 🐛 Troubleshooting

### "No ads scraped"
- Check your internet connection
- Make sure Facebook Ad Library is accessible
- Try with `keywords_leggings_only.txt` first

### "Database errors"
- Run: `python init_database.py`
- Make sure `.env` has `DATABASE_URL`

### "Chromium not found"
- The installer should handle this
- Manual fix: `python -m playwright install chromium`

---

## 📝 Current Configuration

**Distributed Scraper Settings** (`distributed_scraper.py`):
- Workers: 1 (will be updated by installer)
- Threads: 5 (will be updated by installer)
- Keywords File: Will be selected during install
- Advertiser Scraping: **ON** (change line 39 to disable)

**Test Scraper Settings** (`app/workers/run_test_scraper.py`):
- Advertiser Scraping: **ON** (change line 102 to disable)

---

## ✅ You're All Set!

Just run `install_and_run.bat` and you're good to go! 🚀
