#!/usr/bin/env python3
"""
🚀 DISTRIBUTED FACEBOOK AD SCRAPER
⚡ FAST MODE: 10 workers × 10 threads each (100 total browsers)
- 246 keywords for maximum product coverage
- URL-only extraction (10x faster, no page loading)
- Deduplication: skips duplicate ads and SpyFu lookups
- Thread-safe database access
- Saves logs for each worker
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from datetime import datetime
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.workers.run_test_scraper import main as run_test_scraper
from app.db.repo import db_get_ad_by_hash, db_insert_ad, db_domain_exists, db_insert_domain, make_creative_hash
from app.workers.spyfu_api import get_seo_clicks
from sqlmodel import Session, select
from app.db.repo import engine
from app.db.models import AdCreative
import re

# Configuration
NUM_WORKERS = 10  # 10 workers for aggressive scraping (100 total browsers with 10 threads each)
THREADS_PER_WORKER = 10  # 10 parallel threads per worker
KEYWORDS_FILE = "keywords_246_full.txt"  # Using full 246-keyword list for maximum coverage
LOGS_DIR = "logs"
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds

# 🆕 ADVERTISER SCRAPING: Automatically scrapes ALL ads from each advertiser's page
ENABLE_ADVERTISER_SCRAPING = True  # ⚡ ENABLED - Scrapes all ads from each advertiser (set False to disable)

# 🆕 POST-PROCESSING: Automatically run after scraping
ENABLE_AUTO_CLASSIFICATION = True  # Classify ads into categories
ENABLE_AUTO_TRAFFIC_SHARING = True  # Share traffic across same domains
ENABLE_AUTO_PRICE_SHARING = True  # Share prices across same URLs

def retry_on_db_locked(func, *args, max_retries=MAX_RETRIES, delay=RETRY_DELAY, **kwargs):
    """Retry a database operation if it fails due to database lock."""
    import sqlite3
    from sqlalchemy.exc import OperationalError
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except (OperationalError, sqlite3.OperationalError) as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
                continue
            raise
    return None

def setup_logging(worker_id: int) -> logging.Logger:
    """Setup logging for a worker."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    logger = logging.getLogger(f"worker_{worker_id}")
    logger.setLevel(logging.INFO)
    
    # File handler with UTF-8 encoding (fixes Windows emoji errors)
    log_file = os.path.join(LOGS_DIR, f"worker_{worker_id}.log")
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(logging.INFO)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

def process_keyword(keyword: str, worker_id: int, logger: logging.Logger) -> Dict[str, Any]:
    """Process a single keyword and save ads to database."""
    try:
        logger.info(f"Processing keyword: '{keyword}'")
        
        # 🆕 Set advertiser scraping flag before running scraper
        import app.workers.run_test_scraper as scraper_module
        scraper_module.SCRAPE_ADVERTISER_ADS = ENABLE_ADVERTISER_SCRAPING
        
        # Scrape ads for this keyword (no limit = get all available)
        ads = run_test_scraper(keyword=keyword, limit=None)
        
        saved_count = 0
        skipped_duplicates = 0
        
        for ad in ads:
            # Generate ad hash for deduplication using same method as repo.py
            ad_hash = make_creative_hash(ad)
            
            if not ad_hash:
                logger.warning(f"Skipping ad - no hash could be generated for '{keyword}'")
                continue
            
            # Skip duplicate ads (with retry for SQLite lock tolerance)
            existing_ad = retry_on_db_locked(db_get_ad_by_hash, ad_hash)
            if existing_ad:
                skipped_duplicates += 1
                continue
            
            domain = ad.get("domain")
            if not domain:
                logger.warning(f"Skipping ad - no domain for '{keyword}'")
                continue
            
            # Handle SpyFu lookup with deduplication
            domain_data = retry_on_db_locked(db_domain_exists, domain)
            
            if not domain_data:
                try:
                    spyfu_data = get_seo_clicks(domain)
                    seo_clicks = spyfu_data.get("seo_clicks", 0) if spyfu_data.get("status") == "ok" else 0
                    retry_on_db_locked(db_insert_domain, domain, seo_clicks=seo_clicks)
                    logger.info(f"SpyFu: {domain} → {seo_clicks:,} SEO clicks")
                except Exception as e:
                    logger.error(f"SpyFu error for {domain}: {e}")
                    retry_on_db_locked(db_insert_domain, domain, seo_clicks=0)
                    seo_clicks = 0
            else:
                seo_clicks = domain_data["seo_clicks"] if domain_data else 0
            
            # Attach SEO clicks and save ad with all metrics
            ad["seo_clicks"] = seo_clicks
            ad["monthly_visits"] = seo_clicks  # Already converted by run_test_scraper
            
            try:
                retry_on_db_locked(db_insert_ad, ad)
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save ad for '{keyword}' after {MAX_RETRIES} retries: {e}")
        
        logger.info(f"✅ '{keyword}' complete: {saved_count} saved, {skipped_duplicates} duplicates skipped")
        
        return {
            "keyword": keyword,
            "saved": saved_count,
            "duplicates": skipped_duplicates,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing '{keyword}': {e}")
        return {
            "keyword": keyword,
            "saved": 0,
            "duplicates": 0,
            "success": False,
            "error": str(e)
        }

def run_worker(worker_id: int, keywords: List[str], threads_per_worker: int) -> Dict[str, Any]:
    """Run a worker that processes keywords using thread pool."""
    logger = setup_logging(worker_id)
    logger.info(f"👷 Worker {worker_id} starting with {len(keywords)} keywords...")
    
    results = []
    total_saved = 0
    total_duplicates = 0
    
    # Process keywords in parallel using thread pool
    with ThreadPoolExecutor(max_workers=threads_per_worker) as executor:
        futures = {
            executor.submit(process_keyword, kw, worker_id, logger): kw 
            for kw in keywords
        }
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result["success"]:
                total_saved += result["saved"]
                total_duplicates += result["duplicates"]
    
    logger.info(f"✅ Worker {worker_id} finished: {total_saved} ads saved, {total_duplicates} duplicates skipped")
    
    return {
        "worker_id": worker_id,
        "total_saved": total_saved,
        "total_duplicates": total_duplicates,
        "results": results
    }

def split_keywords(keywords: List[str], num_batches: int) -> List[List[str]]:
    """Split keywords into roughly equal batches."""
    batch_size = len(keywords) // num_batches
    remainder = len(keywords) % num_batches
    
    batches = []
    start = 0
    
    for i in range(num_batches):
        # Add 1 extra keyword to first 'remainder' batches
        extra = 1 if i < remainder else 0
        end = start + batch_size + extra
        batches.append(keywords[start:end])
        start = end
    
    return batches


def classify_ad_text(caption: str, product_name: str, account_name: str, landing_url: str) -> str:
    """
    Lightweight category classification using keyword matching.
    Returns category name or 'Other' if no match found.
    """
    # Import category keywords (simplified version)
    CATEGORIES = {
        "Beauty & Health": ["skincare", "makeup", "beauty", "cosmetic", "serum", "cream", "wellness", "vitamin", "supplement"],
        "Women's Clothing": ["dress", "blouse", "skirt", "women's", "ladies", "gown", "leggings", "cardigan"],
        "Sports & Entertainment": ["fitness", "exercise", "workout", "gym", "sports", "yoga", "athletic"],
        "Pet Products": ["pet", "dog", "cat", "puppy", "kitten", "pet food", "pet toy"],
        "Jewelry & Accessories": ["jewelry", "necklace", "bracelet", "earring", "ring", "accessory"],
        "Food": ["snack", "chocolate", "candy", "coffee", "tea", "nutrition", "meal"],
        "Mother & Kids": ["baby", "infant", "toddler", "children", "maternity", "diaper", "stroller"],
        "Shoes": ["shoes", "sneakers", "boots", "sandals", "heels", "flats", "footwear"],
        "Home & Garden": ["plant", "garden", "outdoor", "patio", "lawn", "flower"],
        "Furniture": ["sofa", "couch", "chair", "table", "desk", "bed", "mattress"],
    }
    
    # Combine all text
    text_parts = [caption or "", product_name or "", account_name or "", landing_url or ""]
    combined = " ".join(text_parts).lower()
    
    # Score categories
    best_category = "Other"
    best_score = 0
    
    for category, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_category = category
    
    return best_category


def run_post_processing():
    """
    Run post-processing tasks after scraping:
    1. Classify ads into categories
    2. Share traffic data across same domains
    3. Share prices across same landing URLs
    4. Share platform types across same advertisers
    """
    print("\n" + "=" * 80)
    print("🔄 POST-PROCESSING - Starting automated data enhancement")
    print("=" * 80)
    
    with Session(engine) as session:
        # 1. CATEGORY CLASSIFICATION
        if ENABLE_AUTO_CLASSIFICATION:
            print("\n📊 Step 1/4: Classifying ads into product categories...")
            stmt = select(AdCreative).where((AdCreative.category.is_(None)) | (AdCreative.category == ''))
            unclassified = session.exec(stmt).all()
            
            if unclassified:
                classified_count = 0
                for ad in unclassified:
                    category = classify_ad_text(
                        ad.caption or "",
                        ad.product_name or "",
                        ad.account_name or "",
                        ad.landing_url or ""
                    )
                    ad.category = category
                    session.add(ad)
                    classified_count += 1
                    
                    if classified_count % 500 == 0:
                        session.commit()
                        print(f"  ✅ Classified {classified_count}/{len(unclassified)} ads...")
                
                session.commit()
                print(f"  ✅ Classified {classified_count} ads into categories")
            else:
                print("  ✅ All ads already classified")
        
        # 2. TRAFFIC SHARING (share across same domains)
        if ENABLE_AUTO_TRAFFIC_SHARING:
            print("\n🌐 Step 2/4: Sharing traffic data across same domains...")
            
            # Get all ads with traffic data
            stmt = select(AdCreative).where(AdCreative.monthly_visits.is_not(None), AdCreative.monthly_visits > 0)
            ads_with_traffic = session.exec(stmt).all()
            
            # Build domain -> traffic mapping
            domain_traffic_map = {}
            for ad in ads_with_traffic:
                if ad.landing_url:
                    from urllib.parse import urlparse
                    try:
                        domain = urlparse(ad.landing_url).netloc.replace("www.", "")
                        if domain and ad.monthly_visits:
                            if domain not in domain_traffic_map or ad.monthly_visits > domain_traffic_map[domain]:
                                domain_traffic_map[domain] = ad.monthly_visits
                    except:
                        pass
            
            # Share traffic to ads without it
            stmt = select(AdCreative).where((AdCreative.monthly_visits.is_(None)) | (AdCreative.monthly_visits == 0))
            ads_without_traffic = session.exec(stmt).all()
            
            shared_count = 0
            for ad in ads_without_traffic:
                if ad.landing_url:
                    from urllib.parse import urlparse
                    try:
                        domain = urlparse(ad.landing_url).netloc.replace("www.", "")
                        if domain in domain_traffic_map:
                            ad.monthly_visits = domain_traffic_map[domain]
                            session.add(ad)
                            shared_count += 1
                    except:
                        pass
            
            session.commit()
            print(f"  ✅ Shared traffic to {shared_count} ads from {len(domain_traffic_map)} domains")
        
        # 3. PRICE SHARING (share across same landing URLs)
        if ENABLE_AUTO_PRICE_SHARING:
            print("\n💰 Step 3/4: Sharing prices across same landing URLs...")
            
            # Get all ads with prices
            stmt = select(AdCreative).where(AdCreative.product_price.is_not(None), AdCreative.product_price != '')
            ads_with_prices = session.exec(stmt).all()
            
            # Build URL -> price mapping
            url_price_map = {}
            for ad in ads_with_prices:
                if ad.landing_url and ad.product_price:
                    url_price_map[ad.landing_url] = ad.product_price
            
            # Share prices to ads without them
            stmt = select(AdCreative).where((AdCreative.product_price.is_(None)) | (AdCreative.product_price == ''))
            ads_without_prices = session.exec(stmt).all()
            
            shared_count = 0
            for ad in ads_without_prices:
                if ad.landing_url and ad.landing_url in url_price_map:
                    ad.product_price = url_price_map[ad.landing_url]
                    session.add(ad)
                    shared_count += 1
            
            session.commit()
            print(f"  ✅ Shared prices to {shared_count} ads from {len(url_price_map)} unique URLs")
        
        # 4. PLATFORM SHARING (share across same domains, then advertisers)
        print("\n🛒 Step 4/4: Sharing platform types across same domains and advertisers...")
        
        # LAYER 1: Domain-level sharing (most accurate)
        from urllib.parse import urlparse
        
        # Get all ads with platform_type detected (exclude 'custom', social platforms, and None)
        SOCIAL_PLATFORMS = ['instagram', 'facebook', 'tiktok', 'twitter', 'snapchat']
        stmt = select(AdCreative).where(
            AdCreative.platform_type.is_not(None),
            AdCreative.platform_type != '',
            AdCreative.platform_type != 'custom',
            AdCreative.landing_url.is_not(None),
            AdCreative.landing_url != ''
        )
        ads_with_platform = session.exec(stmt).all()
        
        # Build domain -> platform mapping (prioritize specific platforms over generic)
        domain_platform_map = {}
        PLATFORM_PRIORITY = ['shopify', 'wix', 'woocommerce', 'squarespace', 'bigcommerce', 'magento', 'prestashop', 'webflow', 'wordpress']
        
        for ad in ads_with_platform:
            if ad.landing_url and ad.platform_type and ad.platform_type not in SOCIAL_PLATFORMS:
                try:
                    domain = urlparse(ad.landing_url).netloc.replace("www.", "")
                    if domain:
                        # Keep the most specific platform (e.g., shopify > wordpress)
                        if domain not in domain_platform_map:
                            domain_platform_map[domain] = ad.platform_type
                        elif ad.platform_type in PLATFORM_PRIORITY:
                            current_priority = PLATFORM_PRIORITY.index(domain_platform_map[domain]) if domain_platform_map[domain] in PLATFORM_PRIORITY else 999
                            new_priority = PLATFORM_PRIORITY.index(ad.platform_type)
                            if new_priority < current_priority:
                                domain_platform_map[domain] = ad.platform_type
                except:
                    pass
        
        # Share platform by domain to ads without it (or with 'custom')
        stmt = select(AdCreative).where(
            AdCreative.landing_url.is_not(None),
            AdCreative.landing_url != ''
        ).where(
            (AdCreative.platform_type.is_(None)) | 
            (AdCreative.platform_type == '') | 
            (AdCreative.platform_type == 'custom')
        )
        ads_needing_platform = session.exec(stmt).all()
        
        domain_shared_count = 0
        for ad in ads_needing_platform:
            if ad.landing_url:
                try:
                    domain = urlparse(ad.landing_url).netloc.replace("www.", "")
                    if domain and domain in domain_platform_map:
                        ad.platform_type = domain_platform_map[domain]
                        session.add(ad)
                        domain_shared_count += 1
                except:
                    pass
        
        session.commit()
        print(f"  ✅ Domain-level: Shared platforms to {domain_shared_count} ads from {len(domain_platform_map)} domains")
        
        # LAYER 2: Advertiser-level sharing (for ads from same advertiser with consensus)
        # Re-query ads still needing platforms after domain sharing
        stmt = select(AdCreative).where(
            AdCreative.platform_type.is_not(None),
            AdCreative.platform_type != '',
            AdCreative.platform_type != 'custom',
            AdCreative.page_id.is_not(None),
            AdCreative.page_id != ''
        )
        ads_with_platform = session.exec(stmt).all()
        
        # Build advertiser -> platforms mapping (with consensus check)
        from collections import Counter
        advertiser_platforms = {}
        for ad in ads_with_platform:
            if ad.page_id and ad.platform_type and ad.platform_type not in SOCIAL_PLATFORMS:
                if ad.page_id not in advertiser_platforms:
                    advertiser_platforms[ad.page_id] = []
                advertiser_platforms[ad.page_id].append(ad.platform_type)
        
        # Only share if advertiser has consensus (80%+ same platform)
        advertiser_platform_map = {}
        for page_id, platforms in advertiser_platforms.items():
            counter = Counter(platforms)
            most_common_platform, count = counter.most_common(1)[0]
            if count / len(platforms) >= 0.8:  # 80% consensus
                advertiser_platform_map[page_id] = most_common_platform
        
        # Share platform by advertiser
        stmt = select(AdCreative).where(
            AdCreative.page_id.is_not(None),
            AdCreative.page_id != ''
        ).where(
            (AdCreative.platform_type.is_(None)) | 
            (AdCreative.platform_type == '') | 
            (AdCreative.platform_type == 'custom')
        )
        ads_needing_platform = session.exec(stmt).all()
        
        advertiser_shared_count = 0
        for ad in ads_needing_platform:
            if ad.page_id and ad.page_id in advertiser_platform_map:
                ad.platform_type = advertiser_platform_map[ad.page_id]
                session.add(ad)
                advertiser_shared_count += 1
        
        session.commit()
        print(f"  ✅ Advertiser-level: Shared platforms to {advertiser_shared_count} ads from {len(advertiser_platform_map)} advertisers (with 80% consensus)")
    
    print("\n" + "=" * 80)
    print("✅ POST-PROCESSING COMPLETE")
    print("=" * 80)

def main():
    """Main orchestrator for distributed scraping."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="🚀 Distributed Facebook Ad Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults (10 workers × 10 threads = 100 browsers)
  python distributed_scraper.py
  
  # Custom configuration (5 workers × 20 threads = 100 browsers)
  python distributed_scraper.py --workers 5 --threads 20
  
  # More aggressive (15 workers × 15 threads = 225 browsers)
  python distributed_scraper.py --workers 15 --threads 15
        """
    )
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=NUM_WORKERS,
        help=f'Number of workers (default: {NUM_WORKERS})'
    )
    parser.add_argument(
        '--threads', '-t',
        type=int,
        default=THREADS_PER_WORKER,
        help=f'Threads per worker (default: {THREADS_PER_WORKER})'
    )
    
    args = parser.parse_args()
    
    # Use command-line values or defaults
    num_workers = args.workers
    threads_per_worker = args.threads
    total_browsers = num_workers * threads_per_worker
    
    print("=" * 60)
    print("🚀 DISTRIBUTED FACEBOOK AD SCRAPER LAUNCHER")
    print(f"Configuration: {num_workers} workers × {threads_per_worker} threads = {total_browsers} browsers")
    print("=" * 60)
    
    # Check for keywords file
    if not os.path.exists(KEYWORDS_FILE):
        print(f"❌ {KEYWORDS_FILE} not found!")
        print("Please create keywords.txt with one keyword per line.")
        print("Example:")
        print("  skincare")
        print("  fitness tracker")
        print("  pet supplies")
        sys.exit(1)
    
    # Load keywords
    with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    if not keywords:
        print(f"❌ {KEYWORDS_FILE} is empty!")
        sys.exit(1)
    
    print(f"\n📋 Loaded {len(keywords)} keywords from {KEYWORDS_FILE}")
    
    # Split keywords into batches for workers
    batches = split_keywords(keywords, num_workers)
    
    for i, batch in enumerate(batches, 1):
        print(f"   Worker {i}: {len(batch)} keywords")
    
    # Create logs directory
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    print(f"\n🚀 Launching {num_workers} workers...\n")
    start_time = datetime.now()
    
    # Run workers in parallel
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(run_worker, i+1, batch, threads_per_worker): i+1 
            for i, batch in enumerate(batches)
        }
        
        worker_results = []
        for future in as_completed(futures):
            result = future.result()
            worker_results.append(result)
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("📊 SCRAPING COMPLETE - SUMMARY")
    print("=" * 60)
    
    total_saved = sum(r["total_saved"] for r in worker_results)
    total_duplicates = sum(r["total_duplicates"] for r in worker_results)
    
    for result in sorted(worker_results, key=lambda x: x["worker_id"]):
        wid = result["worker_id"]
        saved = result["total_saved"]
        dupes = result["total_duplicates"]
        print(f"  Worker {wid}: {saved:,} ads saved, {dupes:,} duplicates skipped")
    
    print(f"\n🎯 Total: {total_saved:,} ads saved, {total_duplicates:,} duplicates skipped")
    print(f"⏱️  Duration: {duration:.1f} seconds")
    print(f"📁 Logs saved to: ./{LOGS_DIR}/worker_*.log")
    print("=" * 60)
    
    # 🆕 Run automatic post-processing
    if ENABLE_AUTO_CLASSIFICATION or ENABLE_AUTO_TRAFFIC_SHARING or ENABLE_AUTO_PRICE_SHARING:
        run_post_processing()

if __name__ == "__main__":
    main()
