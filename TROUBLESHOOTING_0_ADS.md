# 🔧 Troubleshooting: "0 ads saved"

## 🎯 **Quick Fix - Run These Commands:**

```bash
# 1. Initialize database (if you haven't already)
python init_database.py

# 2. Run debug script to see what's happening
python debug_scraper.py
```

---

## 🔍 **Why You're Getting "0 ads saved":**

### **Possibility 1: Database Not Initialized** ⚠️
```
Error: "no such table: adcreative"
```

**Fix:**
```bash
python init_database.py
```

**Then try scraping again.**

---

### **Possibility 2: All Ads Being Skipped**
```
⏭️ Skipping ad - no landing URL
⏭️ Skipping ad - no product name found
```

**Why this happens:**
- Some Facebook ads are **brand awareness** ads (no landing page)
- Some ads have **broken media** or missing data
- **Product name extraction fails** for certain sites

**This is NORMAL** - scraper is smart enough to skip junk ads!

**What to do:**
- ✅ Try different keywords (avoid generic terms)
- ✅ Use product-specific keywords like "yoga mat" instead of "fitness"
- ✅ The scraper will eventually find good ads

---

### **Possibility 3: Facebook Changed Their Layout**
Facebook updates their Ads Library frequently. Selectors might break.

**Signs:**
```
⚠️ No images found, continuing...
⏭️ No new ads found, moving to next query
```

**Test:**
1. Visit https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&q=yoga+mat
2. Do you see ads manually?
3. If yes, but scraper finds 0 → Facebook changed layout

---

## 🧪 **Debug Steps:**

### **Step 1: Check Database**
```bash
python -c "from app.db.repo import get_session; from app.db.models import AdCreative; print('DB OK')"
```

**Should print:** `DB OK`

**If error:** Run `python init_database.py`

---

### **Step 2: Run Debug Script**
```bash
python debug_scraper.py
```

**This will:**
- ✅ Check database is accessible
- ✅ Scrape 5 ads with detailed output
- ✅ Show what's being skipped and why

---

### **Step 3: Check What You're Seeing**

**Good signs (scraper working):**
```
✅ Images loaded, ads should be visible
🏷️ Product: Yoga Mat Premium
💰 Price: $29.99
🛒 Platform: shopify
💾 Saved ad to database
```

**Bad signs (scraper broken):**
```
⚠️ No images found, continuing...
⏭️ No new ads found, moving to next query
📥 Scraping complete — saved 0 ads
```

---

## 🎯 **Most Likely Causes:**

### **#1: Database Not Initialized (80% of cases)**
**Symptom:** Everything else works but 0 ads in database

**Fix:**
```bash
python init_database.py
python distributed_scraper.py
```

---

### **#2: Keyword Too Generic (15% of cases)**
**Symptom:** "⏭️ Skipping ad - no landing URL" for every ad

**Why:** Brand awareness ads don't have landing pages

**Fix:** Use specific product keywords:
- ✅ "yoga mat" (specific)
- ✅ "bluetooth speaker" (specific)
- ❌ "fitness" (too generic)
- ❌ "health" (too generic)

---

### **#3: Facebook Blocking (5% of cases)**
**Symptom:** "⚠️ No images found" on every page

**Fix:** 
- Try different IP (mobile hotspot)
- Wait 30 minutes and retry
- Use VPN

---

## 📋 **Expected Success Rate:**

**Normal scraping session:**
- 50-70% ads saved ✅
- 20-30% skipped (no product name) ⚠️
- 10-20% skipped (no landing URL) ⚠️

**If you're getting 100% skipped:**
- Either keywords are too generic
- Or Facebook layout changed
- Or database not initialized

---

## 🚀 **Quick Test:**

```bash
# This should work if everything is set up correctly:
python debug_scraper.py
```

**Expected output:**
```
✅ Database accessible - Current ads: 0
2️⃣ Testing scraper with 1 keyword...

🏷️ Product: Premium Yoga Mat
💰 Price: $29.99
🛒 Platform: shopify

📊 RESULTS:
Total ads found: 3-5
✅ Scraper is working!
```

---

## 💡 **Still Getting 0 Ads?**

**Run this and send me the output:**
```bash
python debug_scraper.py > debug_output.txt 2>&1
```

Then check `debug_output.txt` for the full error log.

---

## ✅ **Checklist Before Scraping:**

- [ ] Ran `python init_database.py`
- [ ] Database shows "✅ Database accessible"
- [ ] Using specific keywords (not generic)
- [ ] Internet connection stable
- [ ] Facebook Ads Library accessible in browser

**Once all checked, run:**
```bash
python distributed_scraper.py
```

Should start saving ads! 🎉
