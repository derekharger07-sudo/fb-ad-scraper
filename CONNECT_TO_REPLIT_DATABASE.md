# 🔌 Connect Local Scraper to Replit Database

This guide shows how to run the scraper on your PC and save data directly to Replit's PostgreSQL database.

## ✅ Benefits
- ✅ Scraper runs fast on your PC
- ✅ Data saves to Replit cloud database
- ✅ React frontend shows real scraped ads instantly
- ✅ No manual data uploads needed

---

## 🔧 Setup (One-Time)

### Step 1: Get Your Database Connection String

1. **In Replit**, open the Shell/Console
2. Run this command:
   ```bash
   echo $DATABASE_URL
   ```
3. Copy the entire output - it looks like:
   ```
   postgresql://username:password@host:5432/database
   ```

### Step 2: Configure Your Local Scraper

1. **On your PC**, open the folder where you extracted the scraper
2. Create a new file called `.env` (yes, starts with a dot!)
3. Paste this into the file:
   ```
   DATABASE_URL=postgresql://username:password@host:5432/database
   ```
4. Replace the URL with the one you copied from Replit

**Example `.env` file:**
```
DATABASE_URL=postgresql://neondb_owner:npg_abc123xyz@ep-something.us-east-2.aws.neon.tech/neondb?sslmode=require
```

### Step 3: Install PostgreSQL Driver

Your local scraper needs the PostgreSQL driver. Run:

```bash
pip install psycopg2-binary
```

Or if you're using the installer, it will handle this automatically.

---

## 🚀 Run the Scraper

Now just run normally:

```bash
python distributed_scraper.py
```

**What happens:**
1. ✅ Scraper runs on your PC (uses your RAM/CPU)
2. ✅ Connects to Replit's PostgreSQL database
3. ✅ Saves ads directly to the cloud
4. ✅ Your React app shows new ads in real-time!

---

## 🔍 Verify Connection

### Check from Replit:
```bash
python check_database.py
```

You'll see the ad count increasing as your PC scraper runs!

### Check from your PC:
After scraping completes, the terminal will show:
```
✅ Worker 1 finished: 127 ads saved
✅ Worker 2 finished: 143 ads saved
Total: 270 ads saved to database
```

---

## 🛡️ Security Notes

- ✅ `.env` file is in `.gitignore` (won't be committed)
- ✅ Never share your DATABASE_URL publicly
- ✅ This is your development database (safe to experiment)

---

## ❓ Troubleshooting

### "Could not connect to database"
- Check that DATABASE_URL is correct (no typos)
- Make sure you have internet connection
- Verify psycopg2-binary is installed

### "SSL connection required"
- Make sure your DATABASE_URL ends with `?sslmode=require`

### Still having issues?
Run this test from your PC:
```bash
python test_db_connection.py
```

---

## 🎯 Next Steps

Once scraper completes:
1. Check Replit database: `python check_database.py`
2. View in React app: Your frontend will show the real ads!
3. Scrape more: Run `python distributed_scraper.py` anytime

**Your PC becomes a powerful scraping machine that feeds your Replit frontend!** 🚀
