# 🏠 Running the Distributed Scraper Locally

This guide shows you how to run the Facebook Ad Scraper on your local computer or server, where it will work MUCH faster without resource limits.

## 📋 Prerequisites

Before you start, make sure you have:

- **Python 3.10+** installed ([Download](https://www.python.org/downloads/))
- **Git** installed ([Download](https://git-scm.com/downloads))
- **4GB+ RAM** (8GB recommended)
- **SpyFu API Key** ([Get one here](https://www.spyfu.com/api))

---

## 🚀 Step 1: Download the Project

### Option A: Clone from Replit (if you have Git set up)
```bash
git clone <your-replit-repo-url>
cd product-research-tool-starter
```

### Option B: Download Manually from Replit
1. Click the **3-dot menu** in Replit
2. Select **Download as ZIP**
3. Extract the ZIP file
4. Open terminal/command prompt in the extracted folder

---

## 🔧 Step 2: Install Dependencies

### Install Python packages:
```bash
pip install -r requirements.txt
```

### Install Playwright browsers:
```bash
playwright install chromium
```

This downloads the Chromium browser Playwright needs (takes ~200MB).

---

## 🔑 Step 3: Set Up API Keys

### Create a `.env` file in the project root:

```bash
# On Mac/Linux:
touch .env

# On Windows:
type nul > .env
```

### Add your API keys to `.env`:

```env
# SpyFu API Key (REQUIRED)
SPYFU_API_KEY=your_spyfu_api_key_here

# Database (OPTIONAL - uses SQLite by default)
# DATABASE_URL=postgresql://user:pass@localhost/dbname

# OpenAI API Key (OPTIONAL - only for video analysis)
# OPENAI_API_KEY=your_openai_key_here
```

**Get SpyFu API Key:**
1. Sign up at [spyfu.com/api](https://www.spyfu.com/api)
2. Copy your API key
3. Paste it in the `.env` file

---

## 🏃 Step 4: Run the Scraper

### Quick Start (50 keywords):
```bash
python3 distributed_scraper.py
```

### Custom Configuration:
Edit `distributed_scraper.py` to adjust settings:

```python
# Configuration (line ~30)
NUM_WORKERS = 3        # More workers = faster (try 3-5)
THREADS_PER_WORKER = 10  # Parallel threads per worker
KEYWORDS_FILE = "keywords.txt"  # Or use keywords_246_full.txt
```

### For all 246 keywords:
```python
KEYWORDS_FILE = "keywords_246_full.txt"
```

---

## 📊 Step 5: Monitor Progress

### Watch the logs:
```bash
# Main scraper log
tail -f scraper_main.log

# Worker logs
tail -f logs/worker_1.log
```

### Check database:
```bash
# Quick stats
python3 -c "
from app.db.repo import get_session
from app.db.models import AdCreative
session = next(get_session())
total = session.query(AdCreative).count()
print(f'📊 Total ads: {total}')
"
```

---

## ⚙️ Performance Recommendations

### For Best Performance:

| Your System | Recommended Config |
|------------|-------------------|
| **Laptop** (8GB RAM) | 2 workers × 5 threads = 10 browsers |
| **Desktop** (16GB RAM) | 3 workers × 10 threads = 30 browsers |
| **Server** (32GB+ RAM) | 5 workers × 20 threads = 100 browsers |

### Adjust in `distributed_scraper.py`:
```python
# For laptop (stable & safe):
NUM_WORKERS = 2
THREADS_PER_WORKER = 5

# For desktop (fast):
NUM_WORKERS = 3
THREADS_PER_WORKER = 10

# For server (blazing fast):
NUM_WORKERS = 5
THREADS_PER_WORKER = 20
```

---

## 🗄️ Database Options

### SQLite (Default - No Setup Required)
- Automatically creates `ads.db` file
- Works out of the box
- May have lock errors with 30+ threads

### PostgreSQL (Recommended for Heavy Use)
1. Install PostgreSQL locally
2. Create a database: `createdb facebook_ads`
3. Add to `.env`:
   ```env
   DATABASE_URL=postgresql://localhost/facebook_ads
   ```

---

## 🐛 Troubleshooting

### Issue: "playwright not found"
```bash
pip install playwright
playwright install chromium
```

### Issue: "SPYFU_API_KEY not set"
- Make sure `.env` file exists in project root
- Check the API key is correct
- Try loading manually:
  ```bash
  export SPYFU_API_KEY=your_key_here
  python3 distributed_scraper.py
  ```

### Issue: Database lock errors
- Use PostgreSQL instead of SQLite
- Or reduce threads: `THREADS_PER_WORKER = 5`

### Issue: Too slow
- Increase workers and threads (see Performance table above)
- Make sure you have good internet speed
- Consider using faster DNS (8.8.8.8)

---

## 📈 Expected Performance

### Local Machine vs Replit:

| Environment | Speed | Max Keywords/Hour |
|------------|-------|------------------|
| **Replit** | ❌ Gets killed | ~10 |
| **Laptop** (10 browsers) | ✅ Stable | ~50-100 |
| **Desktop** (30 browsers) | ✅✅ Fast | ~150-300 |
| **Server** (100 browsers) | 🚀 Blazing | ~500-1000 |

**50 keywords:**
- Replit: Won't complete ❌
- Laptop: ~30-60 minutes ✅
- Desktop: ~10-20 minutes ✅✅
- Server: ~5-10 minutes 🚀

**246 keywords:**
- Laptop: 2-5 hours
- Desktop: 1-2 hours
- Server: 20-45 minutes

---

## ✅ Verification

After scraping completes, verify your data:

```bash
# Check ad count
python3 -c "
from app.db.repo import get_session
from app.db.models import AdCreative
from sqlalchemy import func

session = next(get_session())
total = session.query(AdCreative).count()
with_product = session.query(AdCreative).filter(AdCreative.product_name.isnot(None)).count()
with_price = session.query(AdCreative).filter(AdCreative.product_price.isnot(None)).count()
with_traffic = session.query(AdCreative).filter(AdCreative.est_total_visits > 0).count()

print(f'📊 Total ads: {total}')
print(f'📦 With product name: {with_product}')
print(f'💰 With price: {with_price}')
print(f'📈 With traffic data: {with_traffic}')
"
```

---

## 🎯 Next Steps

After scraping locally:

1. **Start the API server:**
   ```bash
   cd product-research-tool-starter
   uvicorn app.api.main:app --host 0.0.0.0 --port 5000
   ```

2. **View your data:**
   - API: http://localhost:5000/ads
   - Opportunities: http://localhost:5000/opportunities

3. **Analyze with AI:**
   ```bash
   python3 -c "
   from app.api.analyze_ad import analyze_video
   result = analyze_video('https://video-url.mp4')
   print(result)
   "
   ```

---

## 💡 Pro Tips

1. **Run overnight:** Set it up before bed, wake up to thousands of ads
2. **Use PostgreSQL:** Much faster and no lock errors
3. **Monitor logs:** Keep `tail -f scraper_main.log` running
4. **Backup data:** Copy the database file before experimenting
5. **Use keywords_246_full.txt:** Get comprehensive market coverage

---

## 🆘 Need Help?

- Check `DISTRIBUTED_SCRAPER_README.md` for technical details
- Review logs in `scraper_main.log` and `logs/worker_*.log`
- Verify API keys are set correctly in `.env`

**Common Issues:**
- Memory errors → Reduce workers/threads
- Slow speed → Increase workers/threads
- DB locks → Switch to PostgreSQL
- Missing data → Check SpyFu API key
