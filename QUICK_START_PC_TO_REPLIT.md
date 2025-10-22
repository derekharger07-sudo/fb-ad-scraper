# 🚀 Quick Start: Connect PC Scraper to Replit

**Goal:** Run scraper on your PC → Save to Replit database → View in React app

---

## ⚡ 3-Step Setup (5 minutes)

### Step 1: Download Fresh Code from Replit

1. In Replit, click the **3-dot menu** (⋮) → **Download as ZIP**
2. Extract to a new folder on your PC
3. Open Command Prompt in that folder

### Step 2: Get Your Database URL

**In Replit Shell**, run:
```bash
echo $DATABASE_URL
```

Copy the entire output (starts with `postgresql://`)

### Step 3: Configure Local Connection

**On your PC**, in the extracted folder:

1. Copy `.env.example` to `.env`
2. Open `.env` with Notepad
3. Replace the placeholder with your actual DATABASE_URL:

```
DATABASE_URL=postgresql://neondb_owner:npg_abc123...@ep-something.neon.tech/neondb?sslmode=require
```

Save and close.

---

## ✅ Test Connection

Run this to verify everything works:

```bash
pip install python-dotenv psycopg2-binary
python test_db_connection.py
```

**Expected output:**
```
✅ CONNECTION SUCCESSFUL!
📊 Database contains: 0 ads
🚀 Your local scraper is ready to save ads to Replit!
```

---

## 🚀 Run the Scraper

### First Time Setup:
```bash
install_and_run.bat
```

When asked, choose:
```
2) Desktop/16GB RAM: 3 workers × 10 threads = 30 browsers
```

### Subsequent Runs:
```bash
python distributed_scraper.py
```

---

## 📊 Watch It Work

### From Your PC:
Terminal will show:
```
🏷️ Product: Yoga Mat Pro
💰 Price: $34.95
🛒 Platform: Shopify
📈 Monthly visits: 125000
✅ Saved ad to database!
```

### From Replit:
While scraper runs, check in Replit Shell:
```bash
python check_database.py
```

You'll see the count increasing live! 📈

### In Your React App:
Open your Replit webview → Ads appear automatically! 🎉

---

## 🎯 What Happens

```
Your PC (Scraper)  →  Replit PostgreSQL  →  React Frontend
   [Fast]                 [Cloud Storage]        [Live Display]
```

1. ✅ Scraper runs on your 16GB PC (fast, stable)
2. ✅ Each ad saves directly to Replit database
3. ✅ React app reads from database and displays
4. ✅ No manual uploads needed!

---

## 💡 Performance

With 30 browsers (3 workers × 10 threads):
- **~50 ads/minute**
- **247 keywords in ~15-20 minutes**
- **Expected: 500-1000+ ads total**

---

## ❓ Troubleshooting

### "Could not connect to database"
- Check `.env` file exists and has correct DATABASE_URL
- Make sure you have internet connection
- Run `python test_db_connection.py` for detailed diagnosis

### "Package not found"
```bash
pip install -r requirements.txt
```

### Want to see detailed output?
Check the log files in the `logs/` folder:
```bash
type logs\worker_1.log
```

---

## 🎉 You're All Set!

**Your PC is now a cloud-connected scraping machine!** 🚀

Every time you run `python distributed_scraper.py`, new ads flow directly into your Replit database and appear in your React frontend.

**No uploads. No exports. Just seamless integration.** ✨
