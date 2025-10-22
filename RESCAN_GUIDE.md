# Automated Daily Rescan Guide

## Overview
The daily rescan system automatically detects when ads stop running and marks them as inactive. This helps track ad lifetime metrics and identify truly evergreen products.

## How It Works

### 1. **Daily Rescan Process**
- Scrapes all currently active ads from Facebook Ad Library
- Updates `last_seen_ts` for ads found in the scrape
- Increments `missing_count` for ads NOT found in the scrape
- Marks ads as **inactive** after 3 consecutive misses
- Resets `missing_count` to 0 when ad is seen again

### 2. **Database Fields**
```sql
missing_count INT DEFAULT 0     -- Tracks consecutive misses
first_seen_ts TIMESTAMP          -- When ad was first discovered
last_seen_ts TIMESTAMP           -- When ad was last seen
is_active BOOL DEFAULT TRUE      -- Active/Inactive status
```

### 3. **Batch Processing**
- Processes 20,000 ads per batch for efficiency
- Handles 200k+ ad databases without performance issues

## Usage

### Run Daily Rescan
```bash
cd product-research-tool-starter
PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 app/workers/rescan_ads.py
```

### Run Delta Scan (Mid-Day Refresh)
```bash
cd product-research-tool-starter
PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 app/workers/rescan_ads.py --delta
```

### Test Rescan Logic
```bash
cd product-research-tool-starter
PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 app/workers/test_rescan.py
```

## Cron Schedule Examples

### Daily at Midnight (Full Rescan)
```cron
0 0 * * * cd /path/to/product-research-tool-starter && PYTHONPATH=/path/to/product-research-tool-starter python3 app/workers/rescan_ads.py
```

### Twice Daily (Full at 00:00, Delta at 12:00)
```cron
0 0 * * * cd /path/to/product-research-tool-starter && PYTHONPATH=/path/to/product-research-tool-starter python3 app/workers/rescan_ads.py
0 12 * * * cd /path/to/product-research-tool-starter && PYTHONPATH=/path/to/product-research-tool-starter python3 app/workers/rescan_ads.py --delta
```

## Configuration

### Adjust Inactive Threshold
Edit `app/workers/rescan_ads.py`:
```python
INACTIVE_THRESHOLD = 3  # Mark inactive after 3 consecutive misses
```

### Adjust Batch Size
```python
BATCH_SIZE = 20000  # Process 20k ads per batch
```

## Example Output

```
🔄 Starting daily rescan process...
⚙️  Batch size: 20000, Inactive threshold: 3 misses

📡 Scraping currently active ads from Facebook Ad Library...
✅ Scraped 150 active ads

🔑 150 unique creative hashes in today's scrape

📊 Total ads in database: 200

🔄 Processing batch 0-200...
  ⛔ Marking inactive: OldBrandName (missed 3 times)
  ✅ Batch complete: 145 found, 55 missing, 5 newly inactive

💾 Saving new ads from scrape...
✅ Saved 8 new ads

📈 Rescan Summary:
  • Total ads: 208
  • Active ads: 150
  • Inactive ads: 58
  • New ads added: 8

✅ Daily rescan complete!
```

## Benefits

1. **Accurate Lifetime Tracking**: Know exactly when ads stop running
2. **Evergreen Detection**: Identify truly long-running successful ads
3. **Clean Data**: Automatically mark dead ads as inactive
4. **Scalable**: Handles 200k+ ads efficiently with batch processing
5. **Reliable**: 3-miss threshold prevents false positives from scraping glitches

## API Integration

Filter active ads in API queries:
```python
from sqlmodel import select
from app.db.models import AdCreative

# Get only active ads
active_ads = session.exec(
    select(AdCreative).where(AdCreative.is_active == True)
).all()

# Get inactive ads (stopped running)
inactive_ads = session.exec(
    select(AdCreative).where(AdCreative.is_active == False)
).all()
```

## Testing

### Unit Test (Logic Validation)
Tests the core missing_count increment and inactive detection logic:
```bash
cd product-research-tool-starter
PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 app/workers/test_rescan.py
```

### Integration Test (Workflow Validation)
Simulates full rescan workflow with database operations:
```bash
cd product-research-tool-starter
PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 app/workers/test_rescan_integration.py
```

**Note**: Integration test simulates the rescan logic without calling the actual scraper (to avoid triggering expensive API calls). For full end-to-end testing with real scraping, run the daily rescan manually in a staging environment.

## Monitoring

Check rescan status:
```bash
# Count active vs inactive ads
PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 << 'EOF'
from app.db.repo import get_session
from sqlmodel import select, func
from app.db.models import AdCreative

with get_session() as s:
    active = s.exec(select(func.count()).where(AdCreative.is_active == True)).one()
    inactive = s.exec(select(func.count()).where(AdCreative.is_active == False)).one()
    print(f"Active: {active}, Inactive: {inactive}")
EOF
```

## Production Deployment

1. **Initial Migration**: Run migration to add missing_count column
   ```bash
   cd product-research-tool-starter
   PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 -c "from app.workers.rescan_ads import add_missing_count_column; add_missing_count_column()"
   ```

2. **Setup Cron Job**: Schedule daily rescan (example for crontab)
   ```cron
   # Daily at midnight UTC
   0 0 * * * cd /path/to/product-research-tool-starter && PYTHONPATH=/path/to/product-research-tool-starter python3 app/workers/rescan_ads.py >> /var/log/rescan.log 2>&1
   ```

3. **Monitor Logs**: Check logs for errors and status updates
   ```bash
   tail -f /var/log/rescan.log
   ```
