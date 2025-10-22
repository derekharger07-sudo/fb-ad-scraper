# Advertiser Deep Scraping Feature

## What It Does

This feature allows your scraper to not only find ads by keyword, but also scrape **ALL ads** from each advertiser's Facebook Ad Library profile.

## How It Works

1. **Finds an ad** via keyword search (e.g., "leggings")
2. **Extracts page_id** from the advertiser's URL
3. **Navigates to advertiser's page**: `https://www.facebook.com/ads/library/?...&view_all_page_id={page_id}`
4. **Scrapes ALL their ads** (not just ones matching your keyword)
5. **Returns to search** and continues with next ad

## How to Enable

### Option 1: For Test Scraper (`run_test_scraper.py`)

Edit line 105 in `app/workers/run_test_scraper.py`:

```python
# Change from:
SCRAPE_ADVERTISER_ADS = False

# To:
SCRAPE_ADVERTISER_ADS = True
```

### Option 2: For Distributed Scraper (`distributed_scraper.py`)

Edit line 39 in `distributed_scraper.py`:

```python
# Change from:
ENABLE_ADVERTISER_SCRAPING = False

# To:
ENABLE_ADVERTISER_SCRAPING = True
```

## Example Output

```
📥 Found ad from "Ninepine" for keyword "leggings"
💾 Saved ad to database

🔍 Extracting page_id: ninepineofficial from Ninepine

🎯 Scraping ALL ads from advertiser: Ninepine (page_id: ninepineofficial)
  📥 Found 8 ads (total: 8)
  📥 Found 6 ads (total: 14)
  ⏭️ No more ads found for Ninepine
  ✅ Scraped 14 total ads from Ninepine
  💾 Saved 14 ads from Ninepine

🔙 Returning to search results...
```

## What Gets Saved

All advertiser ads get:
- ✅ Same processing as keyword ads (product extraction, pricing, scoring)
- ✅ `page_id` field populated
- ✅ `from_advertiser_scrape = True` flag
- ✅ Linked to original keyword via `search_query` field

## Performance Impact

⚠️ **WARNING**: This will **significantly increase scrape time!**

- **Without feature**: 1 keyword = ~10-20 ads (~30 seconds)
- **With feature**: 1 keyword = ~10-20 ads + (10-50 ads per advertiser × number of advertisers)

**Example:**
- Keyword "leggings" finds 10 ads from 8 different advertisers
- Each advertiser has ~15 ads on average
- Total scraped: 10 + (8 × 15) = **130 ads** (vs. 10 ads)
- Time: ~5 minutes (vs. ~30 seconds)

## When to Use

✅ **Use when:**
- You want complete advertiser portfolios
- You're researching specific brands
- You have limited keywords but want maximum ad coverage
- You have time and want comprehensive data

❌ **Don't use when:**
- You're scraping 100+ keywords
- You only care about specific products
- You need fast results
- You want to avoid duplicate advertisers across keywords

## Safety Features

- ✅ Deduplication still works (won't save duplicate ads)
- ✅ Navigates back to original search page after each advertiser
- ✅ Limited to 10 scrolls per advertiser (prevents infinite loops)
- ✅ Can be disabled anytime without breaking existing code

## Current Status

**Feature is DISABLED by default** to avoid breaking your existing workflow.

To enable, change the flag from `False` to `True` as shown above.
