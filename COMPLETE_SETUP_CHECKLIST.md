# ✅ Complete Setup Checklist

## Before You Start

### 1. Download Project from Replit
- [ ] Click 3-dot menu (⋮) → Download as ZIP
- [ ] Extract to your computer
- [ ] Open folder in terminal/command prompt

### 2. Install Python
- [ ] Python 3.10, 3.11, 3.12, or 3.13
- [ ] Check: `python --version` shows 3.10+
- [ ] Download from: https://python.org/downloads

### 3. Get SpyFu API Key
- [ ] Sign up at: https://www.spyfu.com/api
- [ ] Copy your API key
- [ ] Keep it ready for installer

---

## Installation

### Run the Installer

**Windows:**
```
install_and_run.bat
```

**Mac/Linux:**
```bash
chmod +x install_and_run.sh
./install_and_run.sh
```

The installer will:
- [x] Check Python version
- [x] Install all Python packages
- [x] Install Chromium browser
- [x] Ask for SpyFu API key
- [x] Configure workers/threads
- [x] Start scraping

---

## Manual Installation (if installer fails)

### Step 1: Install Packages
```bash
pip install -r requirements.txt
```

### Step 2: Install Playwright
```bash
playwright install chromium
```

### Step 3: Create .env file
```bash
# Windows:
type nul > .env

# Mac/Linux:
touch .env
```

Add to .env:
```
SPYFU_API_KEY=your_key_here
```

### Step 4: Fix config.py
Open `app/config.py` and change line 7 to:
```python
CHROMIUM_BIN = os.getenv("CHROMIUM_BIN", None)  # None = use Playwright default
```

---

## Verification

### Test the Scraper
```bash
python test_scraper_full.py
```

**Expected:** 3 ads with complete data (names, prices, platforms)

### Check What's Installed
```bash
pip list | grep -E "playwright|dateutil|opencv|requests"
```

**Should show:**
- playwright
- python-dateutil
- opencv-python
- requests
- openai

---

## Common Issues & Fixes

### Issue 1: "No module named 'dateutil'"
```bash
pip install python-dateutil opencv-python requests
```

### Issue 2: "Chromium executable not found"
```bash
playwright install chromium
```

### Issue 3: "SPYFU_API_KEY not set"
- Check .env file exists in project root
- Verify API key is correct
- Try setting manually:
  ```bash
  export SPYFU_API_KEY=your_key  # Mac/Linux
  set SPYFU_API_KEY=your_key     # Windows
  ```

### Issue 4: "/nix/store/... chromium not found"
Edit `app/config.py`:
```python
CHROMIUM_BIN = os.getenv("CHROMIUM_BIN", None)
```

---

## Run the Scraper

### Quick Test (50 keywords):
```bash
python distributed_scraper.py
```

### Full Scan (246 keywords):
Edit `distributed_scraper.py`:
```python
KEYWORDS_FILE = "keywords_246_full.txt"
```
Then run:
```bash
python distributed_scraper.py
```

---

## View Results

### Check Database:
```bash
python -c "from app.db.repo import get_session; from app.db.models import AdCreative; print(f'Total ads: {next(get_session()).query(AdCreative).count()}')"
```

### Start API Server:
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 5000
```

Then visit: http://localhost:5000/ads

---

## Performance Settings

Edit `distributed_scraper.py`:

**Laptop (8GB RAM):**
```python
NUM_WORKERS = 2
THREADS_PER_WORKER = 5
```

**Desktop (16GB RAM):**
```python
NUM_WORKERS = 3
THREADS_PER_WORKER = 10
```

**Server (32GB+ RAM):**
```python
NUM_WORKERS = 5
THREADS_PER_WORKER = 20
```

---

## What Gets Extracted

For each ad:
- ✅ Advertiser name & profile pic
- ✅ Ad caption & media
- ✅ Landing page URL
- ✅ **Product name** (from page)
- ✅ **Product price** (with currency)
- ✅ **Platform type** (Shopify, Wix, etc.)
- ✅ **Monthly traffic** (from SpyFu)
- ✅ Scoring & star rating

---

## Files Reference

| File | Purpose |
|------|---------|
| `install_and_run.bat` | Windows installer |
| `install_and_run.sh` | Mac/Linux installer |
| `test_scraper_full.py` | Test data extraction |
| `distributed_scraper.py` | Main parallel scraper |
| `VERIFY_SETUP.md` | Verification guide |
| `.env` | API keys (create this) |
| `app/config.py` | Configuration (fix Chromium path) |

---

## ✅ You're Ready!

Once all checkboxes are complete, you can scrape thousands of ads with full product intelligence! 🚀
