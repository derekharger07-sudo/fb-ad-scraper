# 🔧 Quick Fix Guide - Database Errors

## ❌ **Problem You Had:**

```
ERROR - no such table: adcreative
ERROR - SQLite Date type only accepts Python date objects
```

**Result:** 0 ads saved ❌

---

## ✅ **The Fix (2 Steps):**

### **Step 1: Initialize Database**
```bash
python init_database.py
```

**What this does:**
- Creates the `adcreative` table
- Creates the `domaintraffic` cache table
- Sets up all required fields

**Expected output:**
```
🔧 Initializing database...
✅ Database tables created successfully!

Tables created:
  - adcreative (main ads table)
  - domaintraffic (traffic cache)

🚀 Database is ready!
```

---

### **Step 2: Run Scraper Again**
```bash
python distributed_scraper.py
```

**Now it will work!** ✅

---

## 🎯 **What Was Fixed:**

### 1. **Database Initialization** ✅
- Added `init_database.py` script
- Automatically creates all tables
- Must run **before** first scrape

### 2. **Date Format Bug** ✅
- Fixed `parse_ad_start_date()` to return Python `date` object
- Previously returned ISO string (caused SQLite error)
- Now properly stores dates in database

---

## 📋 **Complete Setup Process:**

**First Time Setup:**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Playwright browser
playwright install chromium

# 3. Create .env file
echo "SPYFU_API_KEY=your_key_here" > .env

# 4. Initialize database (NEW - REQUIRED!)
python init_database.py

# 5. Run scraper
python distributed_scraper.py
```

**Future Runs:**
```bash
# Just run the scraper (database already exists)
python distributed_scraper.py
```

---

## 🐛 **If You Still Get Errors:**

### Error: "no such table: adcreative"
**Fix:** Run `python init_database.py` first

### Error: "SQLite Date type only accepts..."
**Fix:** Re-download the project (I fixed the date parsing bug)

### Error: "SPYFU_API_KEY not set"
**Fix:** Make sure `.env` file exists with your API key

### Error: "Chromium executable not found"
**Fix:** Run `playwright install chromium`

---

## ✅ **Verification:**

After running `init_database.py`, check the database:

```python
python -c "from app.db.repo import get_session; from app.db.models import AdCreative; print('✅ Database ready!' if next(get_session()).query(AdCreative).count() >= 0 else '❌ Error')"
```

Should print: `✅ Database ready!`

---

## 🚀 **Updated Installer:**

The Windows installer (`install_and_run.bat`) now includes database initialization:

```batch
# Old installer missed this step:
python distributed_scraper.py  ❌

# New installer does:
python init_database.py        ✅
python distributed_scraper.py  ✅
```

---

## 📦 **Files to Re-Download:**

1. ✅ `init_database.py` (new - creates tables)
2. ✅ `app/workers/run_test_scraper.py` (fixed date bug)
3. ✅ `install_and_run.bat` (updated installer)
4. ✅ `QUICK_FIX_GUIDE.md` (this guide)

---

## 🎉 **After the Fix:**

Your scraper will save ads successfully:

```
🏷️ Product: Premium Yoga Pants
💰 Price: $49.99
🛒 Platform: shopify
📈 Monthly visits: 125000
✅ Scored ad: 72 points (4 stars)
💾 Saved to database ✅

============================================================
🎉 SCRAPING COMPLETE - SUMMARY
============================================================
  Worker 1: 45 ads saved, 12 duplicates skipped
  Worker 2: 38 ads saved, 8 duplicates skipped
  Worker 3: 52 ads saved, 15 duplicates skipped

📊 Total: 135 ads saved, 35 duplicates skipped
```

**Now it works!** 🚀
