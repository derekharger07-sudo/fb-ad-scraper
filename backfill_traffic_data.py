"""
Backfill Script: Update monthly_visits for existing ads with missing traffic data
Extracts root domain from landing_url and fetches SpyFu data
"""

import os
import sys
from urllib.parse import urlparse
from sqlmodel import Session, select
from app.db.models import AdCreative
from app.db.repo import engine
from app.workers.spyfu_api import get_seo_clicks
from app.workers.traffic_estimator import estimate_monthly_visits
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import requests

def get_tier_from_visits(seo_clicks: int) -> str:
    """Determine traffic tier based on SEO clicks."""
    if seo_clicks >= 1_500_000:
        return "high"
    elif seo_clicks >= 20_000:
        return "mid"
    else:
        return "low"

def follow_redirects(url: str, timeout: int = 5) -> str:
    """
    Follow redirects to get the final destination URL.
    Returns the final URL after all redirects, or original URL if it fails.
    """
    # List of redirect domains to follow
    redirect_domains = [
        'reploedge.com',
        'l.facebook.com',
        'fb.me',
        'bit.ly',
        'bitly.com',
        'tinyurl.com',
        'ow.ly',
        'short.link',
        'rebrand.ly'
    ]
    
    try:
        # Check if this is a redirect URL we should follow
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        
        if any(redirect in domain for redirect in redirect_domains):
            # Follow redirects
            response = requests.head(url, allow_redirects=True, timeout=timeout)
            final_url = response.url
            return final_url
        else:
            # Not a redirect URL, return as-is
            return url
    except Exception as e:
        # If redirect following fails, return original URL
        return url

def extract_root_domain(url: str) -> str:
    """Extract root domain from URL (e.g., https://mutha.com/pages/product -> mutha.com)"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain if domain else None
    except:
        return None

def process_ad(ad_data, domain_cache, cache_lock, total_ads):
    """Process a single ad - fetch traffic data and return result."""
    ad_id, landing_url, index = ad_data
    
    # Follow redirects to get final destination URL
    final_url = follow_redirects(landing_url)
    
    # Extract domain from final URL
    domain = extract_root_domain(final_url)
    
    if not domain:
        print(f"[{index}/{total_ads}] ⚠️  No domain extractable from: {landing_url[:50]}...")
        return {"status": "skipped", "ad_id": ad_id, "reason": "no_domain"}
    
    # Show redirect info if URL changed
    if final_url != landing_url:
        original_domain = extract_root_domain(landing_url)
        print(f"[{index}/{total_ads}] 🔄 Redirect: {original_domain} → {domain}")
    
    # Skip major platform domains (these are not product websites)
    platform_domains = [
        'youtube.com', 'youtu.be',
        'facebook.com', 'fb.com', 'fb.me',
        'instagram.com',
        'amazon.com', 'amzn.to',
        'google.com', 'maps.app.goo.gl', 'goo.gl', 'docs.google.com',
        'tiktok.com',
        'twitter.com', 'x.com',
        'linkedin.com',
        'pinterest.com',
        'snapchat.com',
        'apple.com', 'apps.apple.com', 'itunes.apple.com',
        'play.google.com'
    ]
    
    if any(platform in domain for platform in platform_domains):
        print(f"[{index}/{total_ads}] ⏭️  Skipping platform domain: {domain}")
        return {"status": "skipped", "ad_id": ad_id, "reason": "platform_domain"}
    
    # Check cache first (thread-safe)
    with cache_lock:
        if domain in domain_cache:
            if domain_cache[domain] is not None:
                print(f"[{index}/{total_ads}] 💾 {domain} → {domain_cache[domain]:,} visits (cached)")
                return {"status": "updated", "ad_id": ad_id, "monthly_visits": domain_cache[domain], "cached": True}
            else:
                print(f"[{index}/{total_ads}] ⏭️  {domain} → No data (cached)")
                return {"status": "skipped", "ad_id": ad_id, "reason": "no_data_cached"}
    
    # Fetch from SpyFu API
    try:
        print(f"[{index}/{total_ads}] 🔍 Fetching: {domain}...", end=" ", flush=True)
        spyfu_data = get_seo_clicks(domain)
        
        if spyfu_data.get("status") == "ok" and spyfu_data.get("seo_clicks"):
            seo_clicks = spyfu_data["seo_clicks"]
            tier = get_tier_from_visits(seo_clicks)
            estimated_visits = estimate_monthly_visits(seo_clicks, tier)
            monthly_visits = int(estimated_visits)
            
            # Update cache (thread-safe)
            with cache_lock:
                domain_cache[domain] = monthly_visits
            
            print(f"✅ {seo_clicks:,} SEO clicks ({tier}) → {monthly_visits:,} visits")
            return {"status": "updated", "ad_id": ad_id, "monthly_visits": monthly_visits, "cached": False}
        else:
            # Update cache (thread-safe)
            with cache_lock:
                domain_cache[domain] = None
            
            print(f"⚠️  No SpyFu data")
            return {"status": "skipped", "ad_id": ad_id, "reason": "no_spyfu_data"}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        # Update cache (thread-safe)
        with cache_lock:
            domain_cache[domain] = None
        return {"status": "failed", "ad_id": ad_id, "error": str(e)}

def backfill_traffic_data(limit: int = None, delay: float = 1.0, workers: int = 10):
    """
    Backfill monthly_visits for ads with missing traffic data using parallel processing.
    
    Args:
        limit: Max number of ads to process (None = all)
        delay: Delay between SpyFu API calls in seconds (not used in parallel mode)
        workers: Number of parallel workers (default: 10)
    """
    
    print("=" * 80)
    print("🚀 TRAFFIC DATA BACKFILL - Starting (Parallel Mode)")
    print("=" * 80)
    
    with Session(engine) as session:
        # Find ads with missing traffic data AND landing URLs
        # Only process ads that don't have monthly_visits yet
        stmt = select(AdCreative.id, AdCreative.landing_url).where(
            AdCreative.monthly_visits.is_(None)
        ).where(
            AdCreative.landing_url.is_not(None)
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        ads = session.exec(stmt).all()
        
        if not ads:
            print("✅ No ads need traffic backfill!")
            return
        
        print(f"📊 Found {len(ads)} ads with missing traffic data")
        print(f"⚙️  Using {workers} parallel workers")
        print()
        
        # Track stats
        domain_cache = {}  # Cache to avoid duplicate API calls
        cache_lock = Lock()  # Thread-safe cache access
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        
        # Prepare data for parallel processing
        ad_data_list = [(ad.id, ad.landing_url, i+1) for i, ad in enumerate(ads)]
        
        # Process ads in parallel
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(process_ad, ad_data, domain_cache, cache_lock, len(ads)): ad_data 
                for ad_data in ad_data_list
            }
            
            for future in as_completed(futures):
                result = future.result()
                
                if result["status"] == "updated":
                    # Update ad in database
                    ad = session.get(AdCreative, result["ad_id"])
                    if ad:
                        ad.monthly_visits = result["monthly_visits"]
                        session.add(ad)
                    updated_count += 1
                elif result["status"] == "skipped":
                    skipped_count += 1
                elif result["status"] == "failed":
                    failed_count += 1
        
        # Commit all changes
        print("\n💾 Saving changes to database...")
        session.commit()
        
        print("\n" + "=" * 80)
        print("🎯 BACKFILL COMPLETE")
        print("=" * 80)
        print(f"✅ Updated: {updated_count} ads")
        print(f"⏭️  Skipped: {skipped_count} ads (no data)")
        print(f"❌ Failed: {failed_count} ads (errors)")
        print(f"📊 Unique domains processed: {len(domain_cache)}")
        print("=" * 80)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill traffic data for existing ads (parallel mode)")
    parser.add_argument("--limit", type=int, default=None, help="Max ads to process (default: all)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between API calls (not used in parallel mode)")
    parser.add_argument("--workers", type=int, default=10, help="Number of parallel workers (default: 10)")
    
    args = parser.parse_args()
    
    backfill_traffic_data(limit=args.limit, delay=args.delay, workers=args.workers)
