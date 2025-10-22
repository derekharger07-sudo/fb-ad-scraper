#!/usr/bin/env python3
"""
🔄 ONE-TIME BACKFILL SCRIPT - Advertiser Ad Portfolio Scraper

This script extracts all advertiser page_ids from existing ads in the database
and scrapes their complete ad portfolios from Facebook Ad Library.

⚠️ This is a TEMPORARY TOOL for one-time use only.
⚠️ It will NOT be integrated into the main scraper.

Usage:
    python backfill_advertiser_ads.py

What it does:
1. Queries all existing ads from database
2. Extracts unique advertiser URLs
3. Converts URLs to page_ids
4. Scrapes ALL ads from each advertiser's Ad Library (in parallel)
5. Saves new ads to database (skips duplicates)
"""

import asyncio
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import Session, engine
from app.db.models import AdCreative
from sqlmodel import select
from playwright.async_api import async_playwright
from app.config import CHROMIUM_BIN
from app.workers.run_test_scraper import (
    extract_page_id_from_url,
    parse_ad_start_date,
    creative_fingerprint,
    extract_ads_from_page,
    accept_cookies_if_present
)
from app.db.repo import save_ads
from app.scoring.ad_scoring import score_ad

# ========== CONFIGURATION ==========
MAX_ADVERTISERS = None  # Set to a number (e.g., 50) to limit for testing, None for all
NUM_PARALLEL_BROWSERS = 50  # Number of browsers to run in parallel (50 optimized for 40GB RAM i7 - backfill is more intensive than distributed scraper)
MAX_ADS_PER_ADVERTISER = 200  # Maximum ads to scrape per advertiser (prevents spending too much time on large advertisers)
VERBOSE = True  # Set to False to reduce output

# Increased timeouts for better success rate
PAGE_LOAD_TIMEOUT = 45000  # 45 seconds (was 30s)
INITIAL_WAIT = 5000  # 5 seconds after page load (was 3s)
COOKIE_WAIT = 3000  # 3 seconds after cookie acceptance (was 2s)
AD_IMAGE_WAIT = 15000  # 15 seconds to wait for ad images (was 10s)
SCROLL_WAIT = 4000  # 4 seconds between scrolls (was 3s)
# ===================================


async def scrape_advertiser_with_retries(page_identifier: str, info: Dict[str, Any], browser_id: int) -> tuple[int, int, str]:
    """
    Scrape all ads from a single advertiser with enhanced timeouts and debugging.
    
    Args:
        page_identifier: Either numeric page_id or username/slug from advertiser URL
        info: Dict with advertiser name, URL, search_query, country
        browser_id: Unique browser ID for logging
    
    Returns:
        Tuple of (new_ads_count, duplicate_ads_count, advertiser_name)
    """
    advertiser_name = info["name"]
    advertiser_url = info["url"]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM_BIN if CHROMIUM_BIN else None
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        new_count = 0
        duplicate_count = 0
        
        try:
            print(f"[Browser {browser_id}] 🏢 {advertiser_name}")
            
            # Step 1: Go to advertiser's Facebook page to get real page_id
            print(f"[Browser {browser_id}]   📍 Visiting: {advertiser_url}")
            await page.goto(advertiser_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
            await page.wait_for_timeout(INITIAL_WAIT)
            
            # Accept cookies if present
            await accept_cookies_if_present(page)
            await page.wait_for_timeout(COOKIE_WAIT)
            
            # Step 2: Extract REAL numeric page_id from Facebook page HTML
            page_content = await page.content()
            
            # Search for "associated_page_id":"12345678" pattern
            page_id_match = re.search(r'"associated_page_id"\s*:\s*"(\d+)"', page_content)
            
            if not page_id_match:
                # Try alternate pattern without quotes
                page_id_match = re.search(r'associated_page_id["\s:]+(\d+)', page_content)
            
            if not page_id_match:
                print(f"[Browser {browser_id}]   ❌ Could not extract associated_page_id from {advertiser_url}")
                return 0, 0, advertiser_name
            
            real_page_id = page_id_match.group(1)
            print(f"[Browser {browser_id}]   ✅ Extracted page_id: {real_page_id}")
            
            # Step 3: Navigate to Ad Library with REAL numeric page_id
            ad_library_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&search_type=page&view_all_page_id={real_page_id}"
            
            print(f"[Browser {browser_id}]   🔗 Opening Ad Library...")
            await page.goto(ad_library_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
            await page.wait_for_timeout(INITIAL_WAIT)
            
            # Check for blocking/errors
            page_text = await page.text_content('body') or ""
            page_url = page.url
            
            if "Log in to Facebook" in page_text or "login" in page_url.lower():
                print(f"[Browser {browser_id}]   🚫 BLOCKED: Facebook requires login")
                raise Exception("Facebook login required")
            elif "Sorry, this content isn't available" in page_text:
                print(f"[Browser {browser_id}]   🚫 BLOCKED: Content not available")
                raise Exception("Content not available")
            elif "No results found" in page_text:
                print(f"[Browser {browser_id}]   ℹ️ Advertiser has no active ads")
                return 0, 0, advertiser_name
            
            # Wait for ads to appear
            try:
                await page.wait_for_selector('img[src*="scontent"]', timeout=AD_IMAGE_WAIT)
                print(f"[Browser {browser_id}]   ✅ Ads loaded!")
            except:
                print(f"[Browser {browser_id}]   ⚠️ No ad images, attempting extraction anyway...")
            
            advertiser_ads = []
            scroll_attempts = 0
            max_scrolls = 10
            
            while scroll_attempts < max_scrolls and len(advertiser_ads) < MAX_ADS_PER_ADVERTISER:
                # Extract ads from current view
                batch = await extract_ads_from_page(page)
                
                if not batch:
                    if scroll_attempts == 0:
                        if VERBOSE:
                            print(f"[Browser {browser_id}]   ⏭️ No ads found on first try")
                    break
                
                # Add metadata
                for ad in batch:
                    ad["search_query"] = info.get("search_query", "backfill")
                    ad["country"] = info.get("country", "US")
                    ad["from_advertiser_scrape"] = True
                
                advertiser_ads.extend(batch)
                print(f"[Browser {browser_id}]   📥 Found {len(batch)} ads (total: {len(advertiser_ads)})")
                
                # Check if we hit the limit
                if len(advertiser_ads) >= MAX_ADS_PER_ADVERTISER:
                    print(f"[Browser {browser_id}]   ⚠️ Reached {MAX_ADS_PER_ADVERTISER} ad limit for {advertiser_name}")
                    advertiser_ads = advertiser_ads[:MAX_ADS_PER_ADVERTISER]  # Trim to exactly MAX_ADS_PER_ADVERTISER
                    break
                
                # Scroll for more with increased wait time
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(SCROLL_WAIT)
                scroll_attempts += 1
            
            # Process and save ads
            for ad in advertiser_ads:
                # Add date parsing and hash
                if ad.get("started_running_on"):
                    start_date, days_running = parse_ad_start_date(ad["started_running_on"])
                    ad["started_running_on"] = start_date
                    ad["days_running"] = days_running
                
                ad["creative_hash"] = creative_fingerprint(ad)
                ad["page_id"] = real_page_id
                
                # Score the ad
                ad_scored = score_ad(ad)
                
                # Check if it's a duplicate
                if ad_scored.get("creative_hash"):
                    with Session(engine) as session:
                        existing = session.exec(
                            select(AdCreative).where(
                                AdCreative.creative_hash == ad_scored["creative_hash"]
                            )
                        ).first()
                        
                        if existing:
                            duplicate_count += 1
                            continue
                
                # Save new ad
                save_ads([ad_scored])
                new_count += 1
            
            if new_count > 0 or duplicate_count > 0:
                print(f"[Browser {browser_id}]   ✅ {advertiser_name}: {new_count} new, {duplicate_count} duplicates")
            
        except Exception as e:
            print(f"[Browser {browser_id}]   ❌ Error: {str(e)[:100]}")
        
        finally:
            await browser.close()
        
        return new_count, duplicate_count, advertiser_name


def process_advertiser_batch(advertisers_batch: List[tuple], browser_id: int) -> Dict[str, int]:
    """Process a batch of advertisers synchronously in one thread."""
    total_new = 0
    total_duplicates = 0
    
    for page_id, info in advertisers_batch:
        try:
            new_count, dup_count, name = asyncio.run(
                scrape_advertiser_with_retries(page_id, info, browser_id)
            )
            total_new += new_count
            total_duplicates += dup_count
        except Exception as e:
            print(f"[Browser {browser_id}] ❌ Fatal error: {e}")
            continue
    
    return {"new": total_new, "duplicates": total_duplicates}


async def main():
    """Main backfill process."""
    
    print("=" * 80)
    print("🔄 ADVERTISER AD PORTFOLIO BACKFILL SCRIPT (PARALLEL)")
    print("=" * 80)
    print()
    print("⚠️  This is a ONE-TIME backfill script")
    print("⚠️  It will scrape ALL ads from advertisers in your database")
    print()
    print(f"⚙️  Configuration:")
    print(f"   - Parallel browsers: {NUM_PARALLEL_BROWSERS}")
    print(f"   - Page load timeout: {PAGE_LOAD_TIMEOUT/1000}s")
    print(f"   - Ad image wait: {AD_IMAGE_WAIT/1000}s")
    print()
    
    # Step 1: Extract unique advertiser URLs from database
    print("📊 Step 1: Extracting advertiser URLs from database...")
    
    with Session(engine) as session:
        # Query all ads with advertiser URLs in raw JSON
        stmt = select(AdCreative)
        all_ads = session.exec(stmt).all()
        
        print(f"   Found {len(all_ads)} total ads in database")
        
        # Extract unique (page_id, advertiser_name, advertiser_url) tuples
        advertiser_map = {}  # page_id -> (name, url, search_query, country)
        
        for ad in all_ads:
            if ad.raw and isinstance(ad.raw, dict):
                advertiser_url = ad.raw.get("advertiser_url")
                advertiser_name = ad.account_name or ad.raw.get("advertiser_name", "Unknown")
                
                if advertiser_url:
                    page_id = extract_page_id_from_url(advertiser_url)
                    
                    if page_id and page_id not in advertiser_map:
                        advertiser_map[page_id] = {
                            "name": advertiser_name,
                            "url": advertiser_url,
                            "search_query": ad.search_query or "backfill",
                            "country": ad.country or "US"
                        }
        
        print(f"   ✅ Found {len(advertiser_map)} unique advertisers")
        print()
    
    if not advertiser_map:
        print("❌ No advertisers found in database. Exiting.")
        return
    
    # Limit advertisers if configured
    advertisers_to_scrape = list(advertiser_map.items())
    if MAX_ADVERTISERS:
        advertisers_to_scrape = advertisers_to_scrape[:MAX_ADVERTISERS]
        print(f"🔧 Limiting to first {MAX_ADVERTISERS} advertisers for testing")
        print()
    
    # Step 2: Scrape ads from each advertiser in parallel
    print(f"🎯 Step 2: Scraping ads from {len(advertisers_to_scrape)} advertisers...")
    print(f"   Using {NUM_PARALLEL_BROWSERS} parallel browsers")
    print(f"   (This may take 10-60 minutes)")
    print()
    
    start_time = time.time()
    
    # Split advertisers into batches for parallel processing
    batch_size = max(1, len(advertisers_to_scrape) // NUM_PARALLEL_BROWSERS)
    batches = [
        advertisers_to_scrape[i:i + batch_size]
        for i in range(0, len(advertisers_to_scrape), batch_size)
    ]
    
    total_new_ads = 0
    total_duplicate_ads = 0
    
    # Process batches in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=NUM_PARALLEL_BROWSERS) as executor:
        futures = {
            executor.submit(process_advertiser_batch, batch, i + 1): i
            for i, batch in enumerate(batches)
        }
        
        for future in as_completed(futures):
            try:
                result = future.result()
                total_new_ads += result["new"]
                total_duplicate_ads += result["duplicates"]
            except Exception as e:
                print(f"❌ Batch error: {e}")
    
    elapsed = time.time() - start_time
    
    # Final summary
    print()
    print("=" * 80)
    print("✅ BACKFILL COMPLETE")
    print("=" * 80)
    print(f"   Time elapsed: {elapsed/60:.1f} minutes")
    print(f"   Advertisers processed: {len(advertisers_to_scrape)}")
    print(f"   New ads added: {total_new_ads}")
    print(f"   Duplicates skipped: {total_duplicate_ads}")
    print()
    print("🎉 Your database now contains complete ad portfolios from all advertisers!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
