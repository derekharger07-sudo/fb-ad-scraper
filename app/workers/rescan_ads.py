"""
Daily Rescan Worker for Ad Status Tracking

This script:
1. Scrapes all currently active ads from Facebook Ad Library
2. Updates last_seen_ts and resets missing_count for ads found
3. Increments missing_count for ads not found in the scrape
4. Marks ads as inactive after 3 consecutive misses
5. Processes in batches for large datasets (200k+ ads)
"""

import asyncio
from datetime import datetime, date
from typing import List, Set
from sqlmodel import Session, select, col, func
from sqlalchemy import text
from app.db.repo import get_session, engine
from app.db.models import AdCreative
from app.workers.run_test_scraper import run_test_scrape


BATCH_SIZE = 20000  # Process 20k ads per batch
INACTIVE_THRESHOLD = 3  # Mark inactive after 3 consecutive misses


async def perform_daily_rescan():
    """
    Main rescan process:
    1. Scrape all currently active ads
    2. Update existing ads (reset missing_count, update last_seen)
    3. Insert new ads
    4. Mark missing ads (increment missing_count, mark inactive if >= 3)
    """
    print("🔄 Starting daily rescan process...")
    print(f"⚙️  Batch size: {BATCH_SIZE}, Inactive threshold: {INACTIVE_THRESHOLD} misses\n")
    
    # Step 1: Scrape all currently active ads
    print("📡 Scraping currently active ads from Facebook Ad Library...")
    scraped_ads = await run_test_scrape()
    
    if not scraped_ads:
        print("⚠️  No ads scraped, aborting rescan")
        return
    
    print(f"✅ Scraped {len(scraped_ads)} active ads\n")
    
    # Extract creative hashes from scraped ads
    from app.db.repo import make_creative_hash
    scraped_hashes: Set[str] = set()
    scraped_ads_by_hash = {}
    
    for ad in scraped_ads:
        creative_hash = make_creative_hash(ad)
        if creative_hash:
            scraped_hashes.add(creative_hash)
            scraped_ads_by_hash[creative_hash] = ad
    
    print(f"🔑 {len(scraped_hashes)} unique creative hashes in today's scrape\n")
    
    # Step 2: Process database updates in batches
    with get_session() as session:
        # Use count query instead of loading all IDs into memory
        total_count = session.exec(select(func.count()).select_from(AdCreative)).one()
        # Extract scalar value from tuple result
        if isinstance(total_count, tuple):
            total_count = total_count[0]
        print(f"📊 Total ads in database: {total_count}")
        
        # Process in batches
        for batch_start in range(0, total_count, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_count)
            print(f"\n🔄 Processing batch {batch_start}-{batch_end}...")
            
            # Get batch of ads
            batch_ads = session.exec(
                select(AdCreative)
                .offset(batch_start)
                .limit(BATCH_SIZE)
            ).all()
            
            found_in_batch = 0
            missing_in_batch = 0
            newly_inactive = 0
            
            for ad in batch_ads:
                if not ad.creative_hash:
                    continue
                
                # Check if ad was found in today's scrape
                scraped_ad_data = scraped_ads_by_hash.get(ad.creative_hash)
                
                if ad.creative_hash in scraped_hashes:
                    # Ad found in scrape - update status
                    ad.last_seen_ts = datetime.utcnow()
                    ad.missing_count = 0
                    found_in_batch += 1
                    
                    # 🔄 Layer 1: Check Facebook's delivery status (if available)
                    if scraped_ad_data and scraped_ad_data.get('fb_delivery_status'):
                        fb_status = scraped_ad_data['fb_delivery_status']
                        ad.fb_delivery_status = fb_status
                        
                        if fb_status == 'INACTIVE':
                            # Facebook says inactive - mark it immediately
                            ad.is_active = False
                            ad.detection_method = 'facebook_status'
                            if scraped_ad_data.get('fb_delivery_stop_time'):
                                from datetime import datetime as dt
                                try:
                                    ad.fb_delivery_stop_time = dt.strptime(scraped_ad_data['fb_delivery_stop_time'], '%B %d, %Y').date()
                                except:
                                    pass
                        else:
                            # Facebook says active
                            ad.is_active = True
                            ad.detection_method = 'facebook_status'
                    else:
                        # No Facebook status - ad is active since we found it
                        ad.is_active = True
                        ad.detection_method = '3_miss_detection'
                else:
                    # Ad not found - increment missing_count
                    ad.missing_count += 1
                    missing_in_batch += 1
                    
                    # 🔄 Layer 2: Use 3-miss detection as fallback
                    if ad.missing_count >= INACTIVE_THRESHOLD and ad.is_active:
                        ad.is_active = False
                        newly_inactive += 1
                        
                        # Determine detection method
                        if ad.fb_delivery_status == 'ACTIVE':
                            # Facebook said active but we haven't seen it in 3 scans
                            ad.detection_method = 'hybrid'
                            print(f"  ⛔ Marking inactive (hybrid): {ad.account_name} (FB says active but missed {ad.missing_count} times)")
                        else:
                            ad.detection_method = '3_miss_detection'
                            print(f"  ⛔ Marking inactive (3-miss): {ad.account_name} (missed {ad.missing_count} times)")
            
            session.commit()
            print(f"  ✅ Batch complete: {found_in_batch} found, {missing_in_batch} missing, {newly_inactive} newly inactive")
    
    # Step 3: Save new ads from scrape (not in database)
    from app.db.repo import save_ads
    print(f"\n💾 Saving new ads from scrape...")
    new_ads_saved = save_ads(scraped_ads)
    print(f"✅ Saved {new_ads_saved} new ads")
    
    # Step 4: Print summary statistics
    with get_session() as session:
        active_count = session.exec(
            select(col(AdCreative.id)).where(AdCreative.is_active == True)
        ).all()
        inactive_count = session.exec(
            select(col(AdCreative.id)).where(AdCreative.is_active == False)
        ).all()
        
        print(f"\n📈 Rescan Summary:")
        print(f"  • Total ads: {len(active_count) + len(inactive_count)}")
        print(f"  • Active ads: {len(active_count)}")
        print(f"  • Inactive ads: {len(inactive_count)}")
        print(f"  • New ads added: {new_ads_saved}")
        print(f"\n✅ Daily rescan complete!")


async def perform_delta_scan():
    """
    Optional mid-day delta scan - only checks currently active ads
    to refresh last_seen for running ads (lighter weight).
    """
    print("🔄 Starting delta scan (active ads only)...")
    
    # Scrape currently active ads
    scraped_ads = await run_test_scrape()
    if not scraped_ads:
        print("⚠️  No ads scraped, aborting delta scan")
        return
    
    # Extract creative hashes
    from app.db.repo import make_creative_hash
    scraped_hashes: Set[str] = {make_creative_hash(ad) for ad in scraped_ads if make_creative_hash(ad)}
    
    print(f"✅ Scraped {len(scraped_ads)} ads ({len(scraped_hashes)} unique hashes)")
    
    # Only update active ads that were found
    with get_session() as session:
        active_ads = session.exec(
            select(AdCreative).where(AdCreative.is_active == True)
        ).all()
        
        updated = 0
        for ad in active_ads:
            if ad.creative_hash and ad.creative_hash in scraped_hashes:
                ad.last_seen_ts = datetime.utcnow()
                updated += 1
        
        session.commit()
        print(f"✅ Delta scan complete: Updated {updated} active ads")


def add_missing_count_column():
    """
    Migration helper: Add missing_count column to existing database.
    Safe to run multiple times (checks if column exists first).
    """
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('adcreative')]
    
    if 'missing_count' not in columns:
        print("🔧 Adding missing_count column to database...")
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE adcreative ADD COLUMN missing_count INTEGER DEFAULT 0"
            ))
            conn.commit()
        print("✅ missing_count column added")
    else:
        print("✅ missing_count column already exists")


if __name__ == "__main__":
    import sys
    
    # Add missing_count column if it doesn't exist
    add_missing_count_column()
    
    if "--delta" in sys.argv:
        # Run delta scan (mid-day refresh for active ads)
        asyncio.run(perform_delta_scan())
    else:
        # Run full daily rescan
        asyncio.run(perform_daily_rescan())
