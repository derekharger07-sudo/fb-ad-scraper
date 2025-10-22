# 🔄 Advertiser Ad Portfolio Backfill Guide

## What Is This?

The backfill script extracts **all advertiser page_ids** from your existing 1,300 ads and scrapes their **complete ad portfolios** from Facebook Ad Library.

This is a **one-time operation** to enrich your database with historical data.

---

## 🎯 What It Does

1. **Queries your database** → Finds all existing ads (e.g., 1,457 ads)
2. **Extracts advertiser URLs** → Gets unique advertisers (e.g., ~624 unique brands)
3. **Visits Facebook pages** → Navigates to each advertiser's Facebook page
4. **Extracts real page_id** → Finds the numeric `associated_page_id` from page HTML
5. **Scrapes Ad Library** → Uses the real page_id to access Ad Library
6. **Extracts all their ads** → Scrapes 5-30 ads per advertiser
7. **Saves to database** → Adds new ads, skips duplicates

**Expected result:** 1,457 ads → 3,000-8,000 ads

---

## 📋 Prerequisites

**Before running:**
1. ✅ Scraper is working (you've tested it successfully)
2. ✅ Database has ~1,300 ads (from previous scrapes)
3. ✅ Python environment is set up (Playwright installed)

---

## 🚀 How to Run

### Step 1: Review Configuration (Optional)

Open `backfill_advertiser_ads.py` and check lines 52-54:

```python
MAX_ADVERTISERS = None  # Set to 50 for testing, None for all
NUM_PARALLEL_BROWSERS = 5  # Number of browsers (5 = stable for 2-step navigation)
VERBOSE = True          # Set to False to reduce output
```

**For testing:**
- Set `MAX_ADVERTISERS = 50` → Scrapes only 50 advertisers (~250 ads, 5-10 mins)

**For full backfill:**
- Set `MAX_ADVERTISERS = None` → Scrapes all 624 advertisers (~3,000+ ads, 45-90 mins)

---

### Step 2: Run the Backfill Script

**On Windows:**
```bash
python backfill_advertiser_ads.py
```

**On Mac/Linux:**
```bash
python3 backfill_advertiser_ads.py
```

---

## 📊 Expected Output

```
================================================================================
🔄 ADVERTISER AD PORTFOLIO BACKFILL SCRIPT (PARALLEL)
================================================================================

⚠️  This is a ONE-TIME backfill script
⚠️  It will scrape ALL ads from advertisers in your database

⚙️  Configuration:
   - Parallel browsers: 5
   - Page load timeout: 45.0s
   - Ad image wait: 15.0s

📊 Step 1: Extracting advertiser URLs from database...
   Found 1457 total ads in database
   ✅ Found 624 unique advertisers

🎯 Step 2: Scraping ads from 624 advertisers...
   Using 5 parallel browsers
   (This may take 10-60 minutes)

[Browser 1] 🏢 Cleanse Esthetics Wellness Yoga
[Browser 1]   📍 Visiting: https://www.facebook.com/people/Cleanse-Esthetics-Wellness-Yoga/61551985450123/
[Browser 1]   ✅ Extracted page_id: 158357214016794
[Browser 1]   🔗 Opening Ad Library...
[Browser 1]   ✅ Ads loaded!
[Browser 1]   📥 Found 5 ads (total: 5)
[Browser 1]   ✅ Cleanse Esthetics Wellness Yoga: 5 new, 0 duplicates

[Browser 2] 🏢 GOVEE
[Browser 2]   📍 Visiting: https://www.facebook.com/GoveeOfficial/
[Browser 2]   ✅ Extracted page_id: 102837007868128
[Browser 2]   🔗 Opening Ad Library...
[Browser 2]   ✅ Ads loaded!
[Browser 2]   📥 Found 8 ads (total: 8)
[Browser 2]   ✅ GOVEE: 6 new, 2 duplicates
...
```

---

## ⏱️ How Long Will It Take?

| Advertisers | Estimated Time | Estimated Ads |
|-------------|----------------|---------------|
| 50 | 5-10 minutes | 250-500 |
| 100 | 10-20 minutes | 500-1,000 |
| 200+ | 30-60 minutes | 2,000-5,000 |

**Note:** Facebook may rate-limit if you scrape too fast. The script includes delays to prevent this.

---

## ✅ After Completion

Check your database:

```python
# Count total ads
SELECT COUNT(*) FROM adcreative;

# Count ads by advertiser
SELECT account_name, COUNT(*) as ad_count
FROM adcreative
GROUP BY account_name
ORDER BY ad_count DESC
LIMIT 20;
```

You should see:
- ✅ 2x-5x more ads than before
- ✅ Multiple ads per advertiser (5-30 each)
- ✅ Complete ad portfolios for each brand

---

## 🔧 Troubleshooting

### Issue: "No advertisers found in database"
**Fix:** Your database is empty or advertiser URLs are missing. Run the main scraper first.

### Issue: "Timeout errors"
**Fix:** Normal if Facebook is slow. Script will continue with next advertiser.

### Issue: "Too slow"
**Fix:** Set `MAX_ADVERTISERS = 50` to test on a smaller subset first.

---

## ⚠️ Important Notes

1. **This is a ONE-TIME script** → Not integrated into main scraper
2. **Duplicates are skipped** → Won't create duplicate ads in database
3. **Can be stopped/restarted** → Just run again, it will skip duplicates
4. **Delete after use** → This is temporary, delete `backfill_advertiser_ads.py` when done

---

## 🗑️ After Completion

**Recommended:** Delete the backfill script to avoid confusion:

```bash
# Windows
del backfill_advertiser_ads.py

# Mac/Linux
rm backfill_advertiser_ads.py
```

The main scraper (`distributed_scraper.py`) already has advertiser scraping built-in, so you won't need this script again.

---

## 📈 Expected Database Growth

**Before backfill:** 1,357 ads  
**After backfill:** 3,000-5,000 ads

**Breakdown:**
- Original ads: 1,357
- New ads from backfill: ~2,000-4,000
- Duplicates skipped: ~500-1,000

---

**Ready to run? Just execute:**
```bash
python backfill_advertiser_ads.py
```

🚀 **Happy backfilling!**
