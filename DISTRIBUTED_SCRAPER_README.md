# 🚀 Distributed Facebook Ad Scraper

Parallel scraper using **5 workers × 10 threads** (50 total threads) for high-performance ad data collection.

## Features

✅ **Full Metric Extraction**: Product names, prices, platform detection, traffic data  
✅ **Deduplication**: Skips duplicate ads and SpyFu API lookups  
✅ **Thread-Safe**: Retry logic with exponential backoff for database writes  
✅ **SpyFu Integration**: Automatic traffic estimation for landing domains  
✅ **Detailed Logging**: Separate log file for each worker  

## Requirements

### Database
⚠️ **IMPORTANT**: For best results, use **PostgreSQL** instead of SQLite.

- **SQLite** (default): Works but may have "database locked" errors with 50 threads
- **PostgreSQL** (recommended): Handles concurrent writes perfectly

To use PostgreSQL:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"
```

### API Keys
Ensure you have:
- `SPYFU_API_KEY` - For traffic estimation
- `OPENAI_API_KEY` - For AI video analysis (optional)

## Quick Start

### 1. Configure Keywords
Edit `keywords.txt` and add one keyword per line:
```
leggings
fitness tracker
skincare
```

Currently loaded with **247 product keywords** across categories:
- Apparel / Fashion
- Beauty / Skincare
- Fitness / Wellness
- Home / Kitchen
- Electronics
- Pets, Baby, Outdoor, Gifts, etc.

### 2. Run the Scraper
```bash
cd product-research-tool-starter
python3 distributed_scraper.py
```

### 3. Monitor Progress
Check logs in real-time:
```bash
tail -f logs/worker_1.log
tail -f logs/worker_2.log
# ... etc
```

## Configuration

Edit `distributed_scraper.py` to adjust:

```python
NUM_WORKERS = 5              # Number of parallel workers
THREADS_PER_WORKER = 10      # Threads per worker (total = 50)
MAX_RETRIES = 3              # DB write retries on lock
RETRY_DELAY = 0.5            # Initial retry delay (exponential backoff)
```

## How It Works

1. **Keyword Distribution**: 247 keywords split into 5 batches (~49 keywords per worker)
2. **Parallel Processing**: Each worker processes keywords using 10 threads
3. **Ad Scraping**: `run_test_scraper()` fetches ads for each keyword
4. **Deduplication**: 
   - Checks if ad hash already exists in database
   - Checks if domain traffic data already cached
5. **Traffic Lookup**: SpyFu API called once per unique domain
6. **Database Storage**: Ads saved with retry logic for SQLite compatibility

## Output

### Console Summary
```
📊 SCRAPING COMPLETE - SUMMARY
Worker 1: 1,245 ads saved, 89 duplicates skipped
Worker 2: 1,103 ads saved, 112 duplicates skipped
...
🎯 Total: 5,892 ads saved, 421 duplicates skipped
⏱️  Duration: 847.3 seconds
📁 Logs saved to: ./logs/worker_*.log
```

### Database
All ads stored in `AdCreative` table with:
- Product name, price, platform type
- Traffic estimates (SpyFu)
- Lifetime metrics (days running, started date)
- Creative hash for variant tracking
- Scoring (demand, competition, angle, geo)

### Logs
Detailed logs per worker at `logs/worker_*.log`:
```
2025-10-13 11:30:15 - worker_1 - INFO - Processing keyword: 'leggings'
2025-10-13 11:30:23 - worker_1 - INFO - SpyFu: yeoreo.com → 45,230 SEO clicks
2025-10-13 11:30:25 - worker_1 - INFO - ✅ 'leggings' complete: 12 saved, 3 duplicates skipped
```

## Performance Tips

### For SQLite (Default)
- Reduce thread count: `THREADS_PER_WORKER = 5` (25 total threads)
- Increase retry delay: `RETRY_DELAY = 1.0`

### For PostgreSQL (Recommended)
- Use full parallelism: `THREADS_PER_WORKER = 10` (50 total threads)
- Faster scraping with no lock errors

### To Optimize
- Start with small batch (10-20 keywords) to test
- Monitor SpyFu API rate limits
- Check Playwright doesn't get blocked by Facebook

## Troubleshooting

### "database is locked" errors
- **Cause**: SQLite can't handle 50 concurrent writes
- **Fix**: Use PostgreSQL or reduce thread count

### Duplicate ads not being skipped
- **Cause**: Hash mismatch (fixed in current version)
- **Fix**: Uses `make_creative_hash()` from repo.py

### SpyFu API errors
- **Cause**: Invalid API key or rate limit
- **Fix**: Verify `SPYFU_API_KEY` env variable

### No ads found
- **Cause**: Facebook blocking Playwright
- **Fix**: Check single scraper works first: `python app/workers/run_test_scraper.py`

## Integration with Main App

The distributed scraper saves ads directly to the database. View them in the main app:

```bash
# Start the API server
uvicorn app.api.main:app --host 0.0.0.0 --port 5000

# Access in browser
http://localhost:5000/ads?limit=100
```

## Next Steps

After scraping completes:
1. **Review Data**: Check `/ads` API endpoint for scraped ads
2. **Run Rescanner**: `python app/workers/rescan_ads.py` to detect inactive ads
3. **Analyze Opportunities**: Use scoring system to find winning products
4. **AI Analysis**: Analyze top ads with GPT-5 video analyzer

---

**Happy Scraping!** 🎯
