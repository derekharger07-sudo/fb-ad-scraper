# ✅ How to Verify Your Scraper is Working Correctly

## 🎯 What the Scraper Extracts

When working properly, the scraper collects:

### Basic Data (from Facebook Ads Library):
- ✅ Advertiser name
- ✅ Ad caption/text
- ✅ Image/video URL
- ✅ Landing page URL
- ✅ CTA button text
- ✅ Date started running
- ✅ Advertiser profile picture

### Enriched Data (from landing pages):
- ✅ **Product Name** - Extracted from page title, meta tags, or Shopify
- ✅ **Product Price** - Extracted with currency detection ($, €, £, etc.)
- ✅ **Platform Type** - Detected (Shopify, Wix, WooCommerce, etc.)

### Traffic Data (from SpyFu API):
- ✅ **Monthly Visits** - Estimated traffic from SpyFu
- ✅ Domain caching - Avoids duplicate API calls

### Analysis:
- ✅ **Is Spark Ad** - Detects Instagram UGC ads
- ✅ **Scoring** - Weighted score based on traffic, age, variants
- ✅ **Creative Hash** - For duplicate detection

---

## 🧪 Test Your Setup

### Quick Test (3 ads):
```bash
python test_scraper_full.py
```

This will:
1. Scrape 3 ads for "leggings"
2. Show what data was extracted
3. Report any missing fields

### Expected Output:
```
✅ Scraped 3 ads

--- Ad 1 ---
  Advertiser: Example Store
  Caption: Get 50% off our leggings...
  Landing URL: https://example.com/products/leggings
  🏷️  Product Name: Premium Fleece Lined Leggings
  💰 Product Price: $29.99
  🛒 Platform Type: shopify
  📈 Monthly Visits: 125000
  ✨ Is Spark Ad: False
  📊 Total Score: 72

✅ ALL CRITICAL FIELDS EXTRACTED!
```

---

## 🔍 What to Check

### 1. **Product Names Missing?**

**Possible causes:**
- Landing page blocked/redirected
- Unusual page structure
- Page requires JavaScript

**Fix:** The scraper already handles this with multiple fallback methods:
- Meta tags (og:title)
- H1 headings
- Shopify JavaScript
- Page title

### 2. **Prices Missing?**

**Possible causes:**
- Price hidden behind "Add to Cart"
- Dynamic pricing
- No price displayed

**Fix:** Scraper tries multiple price formats:
- $29.99, €45, £23.50
- data-price attributes
- Shopify price variables
- Currency detection from meta tags

### 3. **Platform Type = "custom"?**

This is **normal** for:
- Custom-built websites
- Unknown platforms
- Sites with no clear platform markers

Detected platforms:
- Shopify
- Wix
- WooCommerce
- Squarespace
- BigCommerce
- Magento
- WordPress
- PrestaShop
- Webflow

### 4. **Monthly Visits = null?**

**Possible causes:**
- SpyFu API key not set
- Domain too new/small for SpyFu
- Instagram Spark ad (intentionally skipped)

**Fix:** Make sure SPYFU_API_KEY is in your .env file

---

## 📊 View Your Data

### Check Database:
```bash
python -c "from app.db.repo import get_session; from app.db.models import AdCreative; s = next(get_session()); ads = s.query(AdCreative).limit(5).all(); print(f'Total: {s.query(AdCreative).count()}'); [print(f'{a.product_name} - ${a.product_price} - {a.platform_type}') for a in ads]"
```

### Via API:
```bash
curl http://localhost:5000/ads?limit=5
```

### Expected API Response:
```json
{
  "id": 1,
  "account_name": "Store Name",
  "caption": "Ad text...",
  "landing_url": "https://...",
  "product_name": "Product Name",      // ✅ Should have value
  "product_price": 29.99,              // ✅ Should have value
  "platform_type": "shopify",          // ✅ Should have value
  "monthly_visits": 125000,            // ✅ Should have value (if SpyFu key set)
  "is_spark_ad": false,
  "total_score": 72,
  "stars": 4
}
```

---

## ✅ Verification Checklist

Run through this before scraping large batches:

- [ ] Python 3.10+ installed
- [ ] All packages installed: `pip install -r requirements.txt`
- [ ] Playwright installed: `playwright install chromium`
- [ ] SpyFu API key in .env file
- [ ] config.py uses `CHROMIUM_BIN = None` (for local)
- [ ] Test scraper works: `python test_scraper_full.py`
- [ ] Product names extracted ✅
- [ ] Prices extracted ✅
- [ ] Platforms detected ✅
- [ ] Traffic data present ✅ (if SpyFu key set)

---

## 🐛 Troubleshooting

### "No product name found"
The scraper **skips ads** where it can't extract product names. This is intentional to keep database clean.

**Fix:** These ads usually:
- Have no landing page URL
- Redirect to login pages
- Block automated access

This is working as designed!

### "Product extraction failed"
Temporary network issues or page timeouts.

**Fix:** The scraper continues with other ads automatically.

### All fields null in database
You might be looking at **sample ads** I created for testing.

**Fix:** Run the actual scraper to get real data:
```bash
python distributed_scraper.py
```

---

## 🚀 Ready to Scrape

Once verification passes:

```bash
# Full scrape with all 50 keywords
python distributed_scraper.py

# Or with 246 keywords (edit distributed_scraper.py first)
# Set: KEYWORDS_FILE = "keywords_246_full.txt"
python distributed_scraper.py
```

Your scraper will extract **complete product intelligence** for every ad! 📊
