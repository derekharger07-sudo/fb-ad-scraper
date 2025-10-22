#!/usr/bin/env python3
"""
🛒 PLATFORM SHARING BACKFILL SCRIPT
Shares detected platform types across existing ads by domain and advertiser.
Optimized for Windows PC with 40GB RAM - processes 11k+ ads efficiently.

NO RE-SCANNING - Just shares existing platform data!

Run this on your Windows PC:
    python backfill_share_platforms.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, select
from app.db.repo import engine
from app.db.models import AdCreative
from urllib.parse import urlparse
from collections import Counter
import time

# Configuration
BATCH_SIZE = 500  # Process 500 ads per batch (adjust based on your RAM)
SOCIAL_PLATFORMS = ['instagram', 'facebook', 'tiktok', 'twitter', 'snapchat']
PLATFORM_PRIORITY = ['shopify', 'wix', 'woocommerce', 'squarespace', 'bigcommerce', 'magento', 'prestashop', 'webflow', 'wordpress']

def extract_domain(url: str) -> str | None:
    """Extract root domain from URL."""
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        return domain if domain else None
    except:
        return None

def main():
    print("=" * 80)
    print("🛒 PLATFORM SHARING BACKFILL")
    print("Shares detected platforms across existing ads (no re-scanning)")
    print("=" * 80)
    
    start_time = time.time()
    
    with Session(engine) as session:
        # ========================================
        # LAYER 1: DOMAIN-LEVEL SHARING
        # ========================================
        print("\n" + "=" * 80)
        print("📊 LAYER 1: Domain-Level Platform Sharing")
        print("=" * 80)
        
        # Build domain -> platform mapping
        print("\n🔍 Building domain → platform mapping...")
        stmt = select(AdCreative.landing_url, AdCreative.platform_type).where(
            AdCreative.platform_type.is_not(None),
            AdCreative.platform_type != '',
            AdCreative.platform_type != 'custom',
            AdCreative.landing_url.is_not(None),
            AdCreative.landing_url != ''
        )
        
        rows = session.exec(stmt).all()
        print(f"   Found {len(rows)} ads with detected platforms")
        
        domain_platform_map = {}
        for url, platform in rows:
            if platform in SOCIAL_PLATFORMS:
                continue  # Skip social platforms (Instagram, Facebook, etc.)
            
            domain = extract_domain(url)
            if domain:
                # Prioritize specific platforms (e.g., Shopify > WordPress)
                if domain not in domain_platform_map:
                    domain_platform_map[domain] = platform
                elif platform in PLATFORM_PRIORITY:
                    current_priority = PLATFORM_PRIORITY.index(domain_platform_map[domain]) if domain_platform_map[domain] in PLATFORM_PRIORITY else 999
                    new_priority = PLATFORM_PRIORITY.index(platform)
                    if new_priority < current_priority:
                        domain_platform_map[domain] = platform
        
        print(f"   ✅ Mapped {len(domain_platform_map)} unique domains to platforms")
        
        # Show top domains
        print("\n   🏆 Top 10 domains:")
        domain_counts = Counter()
        for url, _ in rows:
            domain = extract_domain(url)
            if domain and domain in domain_platform_map:
                domain_counts[domain] += 1
        
        for domain, count in domain_counts.most_common(10):
            print(f"      • {domain}: {count} ads → {domain_platform_map[domain]}")
        
        # Share platforms by domain (batched processing)
        print(f"\n🔄 Sharing platforms across same domains (batches of {BATCH_SIZE})...")
        
        stmt = select(AdCreative).where(
            AdCreative.landing_url.is_not(None),
            AdCreative.landing_url != ''
        ).where(
            (AdCreative.platform_type.is_(None)) | 
            (AdCreative.platform_type == '') | 
            (AdCreative.platform_type == 'custom')
        )
        
        domain_shared_count = 0
        offset = 0
        
        while True:
            batch_stmt = stmt.offset(offset).limit(BATCH_SIZE)
            batch = session.exec(batch_stmt).all()
            
            if not batch:
                break
            
            batch_updates = 0
            for ad in batch:
                domain = extract_domain(ad.landing_url)
                if domain and domain in domain_platform_map:
                    ad.platform_type = domain_platform_map[domain]
                    session.add(ad)
                    batch_updates += 1
                    domain_shared_count += 1
            
            session.commit()
            offset += len(batch)
            print(f"   Processed {offset} ads | Updated {domain_shared_count} so far...")
        
        print(f"\n   ✅ Domain-level: Shared platforms to {domain_shared_count} ads from {len(domain_platform_map)} domains")
        
        # ========================================
        # LAYER 2: ADVERTISER-LEVEL SHARING
        # ========================================
        print("\n" + "=" * 80)
        print("📊 LAYER 2: Advertiser-Level Platform Sharing (with 80% consensus)")
        print("=" * 80)
        
        # Build advertiser -> platforms mapping
        print("\n🔍 Building advertiser → platform mapping...")
        stmt = select(AdCreative.page_id, AdCreative.platform_type).where(
            AdCreative.platform_type.is_not(None),
            AdCreative.platform_type != '',
            AdCreative.platform_type != 'custom',
            AdCreative.page_id.is_not(None),
            AdCreative.page_id != ''
        )
        
        rows = session.exec(stmt).all()
        print(f"   Found {len(rows)} ads with page_id and platforms")
        
        advertiser_platforms = {}
        for page_id, platform in rows:
            if platform in SOCIAL_PLATFORMS:
                continue  # Skip social platforms
            
            if page_id not in advertiser_platforms:
                advertiser_platforms[page_id] = []
            advertiser_platforms[page_id].append(platform)
        
        # Only share if advertiser has 80%+ consensus
        advertiser_platform_map = {}
        for page_id, platforms in advertiser_platforms.items():
            counter = Counter(platforms)
            most_common_platform, count = counter.most_common(1)[0]
            consensus_pct = (count / len(platforms)) * 100
            
            if consensus_pct >= 80:  # Require 80% consensus
                advertiser_platform_map[page_id] = most_common_platform
        
        print(f"   ✅ Found {len(advertiser_platform_map)} advertisers with 80%+ platform consensus")
        
        # Show advertiser examples
        print("\n   🏆 Sample advertisers with consensus:")
        sample_count = 0
        for page_id, platform in list(advertiser_platform_map.items())[:5]:
            ad_count = len(advertiser_platforms[page_id])
            print(f"      • page_id {page_id}: {ad_count} ads → {platform}")
            sample_count += 1
        
        if len(advertiser_platform_map) > 5:
            print(f"      ... and {len(advertiser_platform_map) - 5} more advertisers")
        
        # Share platforms by advertiser (batched processing)
        print(f"\n🔄 Sharing platforms across same advertisers (batches of {BATCH_SIZE})...")
        
        stmt = select(AdCreative).where(
            AdCreative.page_id.is_not(None),
            AdCreative.page_id != ''
        ).where(
            (AdCreative.platform_type.is_(None)) | 
            (AdCreative.platform_type == '') | 
            (AdCreative.platform_type == 'custom')
        )
        
        advertiser_shared_count = 0
        offset = 0
        
        while True:
            batch_stmt = stmt.offset(offset).limit(BATCH_SIZE)
            batch = session.exec(batch_stmt).all()
            
            if not batch:
                break
            
            batch_updates = 0
            for ad in batch:
                if ad.page_id and ad.page_id in advertiser_platform_map:
                    ad.platform_type = advertiser_platform_map[ad.page_id]
                    session.add(ad)
                    batch_updates += 1
                    advertiser_shared_count += 1
            
            session.commit()
            offset += len(batch)
            print(f"   Processed {offset} ads | Updated {advertiser_shared_count} so far...")
        
        print(f"\n   ✅ Advertiser-level: Shared platforms to {advertiser_shared_count} ads from {len(advertiser_platform_map)} advertisers")
        
        # ========================================
        # FINAL STATISTICS
        # ========================================
        print("\n" + "=" * 80)
        print("📊 FINAL PLATFORM DISTRIBUTION")
        print("=" * 80)
        
        stmt = select(AdCreative.platform_type)
        all_platforms = session.exec(stmt).all()
        total_ads = len(all_platforms)
        
        platform_counts = Counter([p for p in all_platforms if p])
        total_with_platform = sum(platform_counts.values())
        
        print(f"\n🎯 Coverage: {total_with_platform}/{total_ads} ads ({(total_with_platform/total_ads)*100:.1f}%) have platform types\n")
        
        for platform, count in sorted(platform_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_ads) * 100
            bar = "█" * int(pct / 2)
            print(f"   {platform:15} │ {bar} {count:5} ads ({pct:5.1f}%)")
        
        null_count = total_ads - total_with_platform
        if null_count > 0:
            pct = (null_count / total_ads) * 100
            bar = "░" * int(pct / 2)
            print(f"   {'(null)':15} │ {bar} {null_count:5} ads ({pct:5.1f}%)")
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"✅ BACKFILL COMPLETE in {elapsed:.1f} seconds")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   • Domain-level sharing: {domain_shared_count} ads updated")
    print(f"   • Advertiser-level sharing: {advertiser_shared_count} ads updated")
    print(f"   • Total updates: {domain_shared_count + advertiser_shared_count}")
    print(f"\n💡 Future scrapes will automatically share platforms via post-processing!")

if __name__ == "__main__":
    main()
