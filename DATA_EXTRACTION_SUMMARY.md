# 📊 Complete Data Extraction Summary

## ✅ Everything the Scraper Extracts

### 1. **SEO/Traffic Data** ✅
- **`monthly_visits`** - Estimated monthly traffic from SpyFu API
- **`is_spark_ad`** - Instagram UGC ads (skips traffic lookup)
- Caches results per domain to save API calls

### 2. **Ad Status (Active/Inactive)** ✅
- **`is_active`** - Boolean: true/false
- **Two-Layer Detection:**
  - Layer 1: Facebook's own `fb_delivery_status` ("ACTIVE" / "INACTIVE")
  - Layer 2: 3-miss detection (`missing_count`)
  - `fb_delivery_stop_time` - When Facebook says ad stopped
  - `detection_method` - "facebook_status", "3_miss_detection", or "hybrid"

### 3. **Number of Duplicates** ✅
- **`creative_variant_count`** - How many times this creative was seen
- **`creative_hash`** - Unique hash for duplicate detection
- Automatically updates when variants are found

### 4. **When Ad Was Created** ✅
- **`started_running_on`** - Date ad began running (from Facebook)
- **`days_running`** - How many days ad has been active
- **`first_seen_ts`** - Timestamp when first scraped

### 5. **When Ad Was Last Seen** ✅
- **`last_seen_ts`** - Timestamp of last scrape where ad appeared
- Updates every time ad is found in rescan

### 6. **Advertiser's Name** ✅
- **`account_name`** - Advertiser/brand name
- **`advertiser_favicon`** - Advertiser profile picture URL
- **`page_id`** - Facebook page ID

### 7. **Product Name** ✅
- **`product_name`** - Extracted from landing page
- Methods: og:title meta tags, H1, Shopify JS, page title
- **Required field** - Ads without product names are skipped

### 8. **Product URL** ✅
- **`landing_url`** - Where the ad directs users
- Cleaned of tracking params (fbclid, utm_*)

### 9. **Product Price** ✅
- **`product_price`** - Price with currency symbol ($, €, £, etc.)
- Supports: $29.99, €45, £23.50, 1.099,00€
- Auto-detects currency from page

---

## 🎯 Additional Fields Extracted

### Ad Content:
- **`caption`** - Ad text/copy
- **`video_url`** - Ad video/image URL
- **`cta_text`** - Call-to-action button text
- **`platform`** - Always "meta" (Facebook/Instagram)

### Platform Intelligence:
- **`platform_type`** - E-commerce platform (shopify, wix, woocommerce, custom, etc.)

### Scraping Context:
- **`search_query`** - Keyword used to find ad
- **`country`** - Target country (US, CA, etc.)

### Scoring:
- **`total_score`** - Weighted score (0-100)
- **`stars`** - Star rating (1-5)
- Formula: 45% duplicates + 35% age + 20% traffic

### Raw Data:
- **`raw`** - Full unprocessed ad data (JSON)
- **`metrics`** - Additional metrics (JSON)

---

## 🤖 AI Video Analyzer (Separate Feature)

**Location:** `app/api/analyze_ad.py`

**What it does:**
- Extracts video frames (1 per 2 seconds)
- Performs OCR text extraction
- Analyzes with GPT-5 for:
  - Emotions portrayed
  - Scene types
  - Product focus
  - Creative structure
  - Selling angles

**How to use:**
```python
from app.api.analyze_ad import analyze_video
result = analyze_video(video_url='https://...')
```

**Backend vs Frontend:**
- ✅ **Backend Function** - Runs on server (requires OpenAI API key)
- ✅ **Frontend Trigger** - Can be called from UI via API endpoint
- ❌ **Not Frontend Code** - Can't run in browser (needs API keys, heavy processing)

**When to use:**
- Analyze top-performing ads after scraping
- Understand what makes ads successful
- Extract creative insights

---

## 📋 Complete Field List (40+ fields)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `monthly_visits` | Integer | SpyFu API | Estimated monthly traffic |
| `is_active` | Boolean | Detection | Active/inactive status |
| `creative_variant_count` | Integer | Dedup | Number of duplicates |
| `started_running_on` | Date | Facebook | When ad started |
| `last_seen_ts` | Timestamp | Scraper | Last time ad was seen |
| `account_name` | String | Facebook | Advertiser name |
| `product_name` | String | Landing page | Product name |
| `landing_url` | String | Facebook | Product URL |
| `product_price` | String | Landing page | Product price |
| `platform_type` | String | Landing page | E-commerce platform |
| `is_spark_ad` | Boolean | URL check | Instagram UGC ad |
| `advertiser_favicon` | String | Facebook | Profile picture |
| `caption` | String | Facebook | Ad text |
| `video_url` | String | Facebook | Media URL |
| `cta_text` | String | Facebook | CTA button |
| `fb_delivery_status` | String | Facebook | FB's status |
| `fb_delivery_stop_time` | Date | Facebook | When FB stopped ad |
| `detection_method` | String | System | Detection method used |
| `creative_hash` | String | System | Duplicate detection hash |
| `first_seen_ts` | Timestamp | Scraper | First scrape time |
| `days_running` | Integer | Calculated | Days active |
| `missing_count` | Integer | Rescan | Consecutive misses |
| `page_id` | String | Facebook | FB page ID |
| `search_query` | String | Scraper | Keyword used |
| `country` | String | Scraper | Target country |
| `total_score` | Integer | Scoring | Weighted score 0-100 |
| `stars` | Integer | Scoring | Star rating 1-5 |
| `raw` | JSON | Facebook | Full raw data |
| `metrics` | JSON | Facebook | Additional metrics |

---

## ✅ Everything You Asked For

Your requirements:
1. ✅ SEO → monthly visits (SpyFu)
2. ✅ Ad status (active/inactive) 
3. ✅ Number of duplicates (creative_variant_count)
4. ✅ When ad was created (started_running_on)
5. ✅ When last seen (last_seen_ts)
6. ✅ Advertiser name (account_name)
7. ✅ Product name (product_name)
8. ✅ Product URL (landing_url)
9. ✅ Product price (product_price)

**All fields are extracted and saved to database!** 🎉

---

## 🔍 How to Verify

### Check a single ad:
```python
from app.db.repo import get_session
from app.db.models import AdCreative

session = next(get_session())
ad = session.query(AdCreative).first()

print(f"Product: {ad.product_name}")
print(f"Price: {ad.product_price}")
print(f"Traffic: {ad.monthly_visits}")
print(f"Active: {ad.is_active}")
print(f"Duplicates: {ad.creative_variant_count}")
print(f"Started: {ad.started_running_on}")
print(f"Last Seen: {ad.last_seen_ts}")
```

### Via API:
```bash
curl http://localhost:5000/ads/1
```

All fields will be in the JSON response!
