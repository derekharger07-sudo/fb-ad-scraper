# Two-Layer Ad Inactive Detection System

This guide documents the **two-layer detection system** that intelligently determines when Facebook ads stop running.

## Overview

The system uses a hybrid approach combining two detection methods for maximum accuracy:

1. **Layer 1 - Facebook Delivery Status** (Primary)  
   Uses Facebook's own ad delivery status indicators extracted from the Ads Library HTML

2. **Layer 2 - 3-Miss Detection** (Fallback)  
   Tracks ad disappearances over consecutive daily scans (marks inactive after 3 misses)

## How It Works

### Detection Logic Flow

```
┌─────────────────────────────────────┐
│  Daily Rescan Scrapes Active Ads   │
└──────────────┬──────────────────────┘
               │
               ▼
       ┌───────────────┐
       │ Ad Found?     │
       └───┬───────┬───┘
          YES     NO
           │       │
           ▼       ▼
    ┌──────────┐  ┌──────────────────┐
    │Layer 1:  │  │Increment         │
    │Check FB  │  │missing_count     │
    │Status    │  │                  │
    └────┬─────┘  │If >= 3: inactive │
         │        └──────────────────┘
    ┌────▼─────────────────┐
    │FB Status Available?  │
    └────┬────────────┬────┘
        YES          NO
         │            │
         ▼            ▼
    ┌────────┐    ┌─────────────┐
    │INACTIVE?│    │Mark Active  │
    │        │    │(3-miss only)│
    └─┬───┬──┘    └─────────────┘
     YES  NO
      │    │
      ▼    ▼
   Inactive Active
   (FB)     (FB)
```

### Database Fields

#### New Columns (Two-Layer Detection)

```sql
fb_delivery_status      VARCHAR   -- Facebook's status: "ACTIVE", "INACTIVE", or NULL
fb_delivery_stop_time   DATE      -- When Facebook says ad stopped (parsed from "Stopped on...")  
detection_method        VARCHAR   -- How status was determined: 
                                  -- "facebook_status"  = Layer 1 (FB provided status)
                                  -- "3_miss_detection" = Layer 2 (fallback 3-miss)
                                  -- "hybrid"          = Layer 2 override (FB said active, but missing 3x)
```

#### Existing Columns (Enhanced)

```sql
is_active       BOOLEAN  -- Current status (true/false)
missing_count   INTEGER  -- Consecutive scans where ad wasn't found
last_seen_ts    TIMESTAMP -- Last time ad was seen in scrape
```

## Detection Methods

### Method 1: Facebook Delivery Status (Primary)

**When:** Facebook provides delivery status indicators in the Ads Library HTML

**How it works:**
1. Scraper looks for patterns like:
   - "Stopped running on [date]" or "Ended running on [date]" → `INACTIVE`
   - "Active" or "Currently running" → `ACTIVE`

2. During rescan:
   - If `fb_delivery_status = "INACTIVE"` → mark `is_active = false` immediately
   - If `fb_delivery_status = "ACTIVE"` → mark `is_active = true`
   - Set `detection_method = "facebook_status"`

**Advantages:**
- ✅ Real-time accuracy (Facebook's own data)
- ✅ Instant detection (no 3-day wait)
- ✅ Includes exact stop date

### Method 2: 3-Miss Detection (Fallback)

**When:** Facebook doesn't provide delivery status OR as a safety check

**How it works:**
1. Daily rescan compares scraped ads with database
2. Ads not found in scrape → increment `missing_count`
3. After 3 consecutive misses → mark `is_active = false`
4. Set `detection_method = "3_miss_detection"`

**Advantages:**
- ✅ Works even without Facebook status
- ✅ Prevents false positives (3-day buffer)
- ✅ Battle-tested reliability

### Method 3: Hybrid (Safety Override)

**When:** Facebook says "ACTIVE" but we haven't seen the ad in 3 scans

**How it works:**
- If `fb_delivery_status = "ACTIVE"` BUT `missing_count >= 3`
- Mark `is_active = false` anyway
- Set `detection_method = "hybrid"`

**Use case:** Facebook status may lag or be incorrect

## API Changes

### GET /ads Endpoint

#### New Query Parameter

```http
GET /ads?is_active=true   # Returns only active ads
GET /ads?is_active=false  # Returns only inactive ads  
GET /ads                  # Returns both (default)
```

#### New Response Fields

```json
{
  "id": 123,
  "account_name": "Example Store",
  "is_active": false,
  "fb_delivery_status": "INACTIVE",
  "fb_delivery_stop_time": "2025-01-15",
  "detection_method": "facebook_status",
  "missing_count": 0,
  "...": "..."
}
```

## Usage Examples

### 1. Run Daily Rescan with Two-Layer Detection

```bash
cd product-research-tool-starter
PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 app/workers/rescan_ads.py
```

**Expected Output:**
```
🔄 Starting daily rescan process...
📡 Scraping currently active ads from Facebook Ad Library...
✅ Scraped 150 active ads

📊 Total ads in database: 250

🔄 Processing batch 0-250...
  ⛔ Marking inactive (hybrid): "Product X" (FB says active but missed 3 times)
  ✅ Batch complete: 150 found, 100 missing, 25 newly inactive

📈 Rescan Summary:
  • Total ads: 250
  • Active ads: 175
  • Inactive ads: 75
  • New ads added: 5

✅ Daily rescan complete!
```

### 2. Query Active Ads Only

```bash
curl "http://localhost:5000/ads?is_active=true&limit=10"
```

### 3. Query Inactive Ads with Facebook Status

```bash
curl "http://localhost:5000/ads?is_active=false&limit=10"
```

Response includes `fb_delivery_status` and `detection_method`:
```json
[
  {
    "id": 456,
    "account_name": "Stopped Store",
    "is_active": false,
    "fb_delivery_status": "INACTIVE",
    "fb_delivery_stop_time": "2025-01-10",
    "detection_method": "facebook_status"
  }
]
```

### 4. Find Ads with Hybrid Detection

```sql
SELECT * FROM adcreative 
WHERE detection_method = 'hybrid';
-- These are ads Facebook said were active, but we haven't seen in 3 scans
```

## Migration & Setup

### Initial Setup (Run Once)

```bash
# Add detection columns to existing database
cd product-research-tool-starter
PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 app/workers/add_detection_columns.py
```

**Expected Output:**
```
🔄 Adding two-layer detection columns to AdCreative table...
  📝 Adding fb_delivery_status column...
  ✅ fb_delivery_status column added
  📝 Adding fb_delivery_stop_time column...
  ✅ fb_delivery_stop_time column added
  📝 Adding detection_method column...
  ✅ detection_method column added
✅ Migration complete!
```

## Monitoring & Analytics

### Check Detection Method Distribution

```sql
SELECT 
  detection_method,
  COUNT(*) as count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM adcreative
WHERE is_active = false
GROUP BY detection_method;
```

**Example Output:**
```
detection_method    | count | percentage
--------------------|-------|------------
facebook_status     | 45    | 60%
3_miss_detection    | 25    | 33%
hybrid              | 5     | 7%
```

### Find Discrepancies (FB says active, we say inactive)

```sql
SELECT * FROM adcreative
WHERE fb_delivery_status = 'ACTIVE' 
  AND is_active = false
  AND detection_method = 'hybrid';
```

## Benefits of Two-Layer System

### 🎯 Accuracy
- **Best of both worlds:** Facebook's real-time data + our 3-miss safety net
- **Hybrid override:** Catches cases where Facebook status lags

### ⚡ Speed
- **Instant detection:** No 3-day wait when Facebook provides status
- **Historical data:** Exact stop dates for trend analysis

### 🛡️ Reliability
- **Fallback protection:** Works even if Facebook doesn't provide status
- **False positive prevention:** 3-miss buffer prevents temporary glitches

### 📊 Analytics
- **Detection transparency:** Know which method marked each ad inactive
- **Trust scoring:** Analyze accuracy of each detection method

## Troubleshooting

### Issue: All ads showing `detection_method = "3_miss_detection"`

**Cause:** Facebook Ads Library HTML doesn't include delivery status indicators

**Solution:** This is normal for ads that never had Facebook status in HTML. The 3-miss method is working correctly.

### Issue: Ads marked inactive immediately after scraping

**Cause:** Facebook HTML shows "Stopped on [date]" status

**Solution:** Working as designed! These ads are genuinely stopped according to Facebook.

### Issue: `detection_method = "hybrid"` is common

**Cause:** Facebook's status lags behind actual ad delivery

**Solution:** Hybrid detection is catching real inactive ads that Facebook hasn't updated yet. This validates the two-layer approach!

## Next Steps

1. **Schedule Daily Rescan:**
   ```cron
   0 0 * * * cd /path/to/project && PYTHONPATH=/path/to/project python3 app/workers/rescan_ads.py
   ```

2. **Monitor Detection Accuracy:**
   - Track `hybrid` detection rate
   - Compare Facebook vs 3-miss results
   - Adjust `INACTIVE_THRESHOLD` if needed (currently 3 misses)

3. **Build Analytics:**
   - Trend analysis: When do most ads stop?
   - Platform comparison: Shopify vs custom sites
   - Lifetime analysis: Which ads run longest?

---

**Last Updated:** October 13, 2025  
**Version:** 2.0 (Two-Layer Detection System)
