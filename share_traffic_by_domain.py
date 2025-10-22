#!/usr/bin/env python3
"""
Share monthly_visits across all ads with the same domain.

This script:
1. Groups ads by domain (extracted from landing_url)
2. Finds ads that have monthly_visits for each domain
3. Copies that value to all ads from the same domain
"""

import os
from urllib.parse import urlparse
from sqlmodel import Session, create_engine, select
from app.db.models import AdCreative

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)


def extract_domain(url):
    """Extract root domain from URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www. prefix
        domain = domain.replace('www.', '')
        return domain if domain else None
    except:
        return None


def main():
    print("🔄 Sharing monthly_visits across ads with same domain...\n")
    
    with Session(engine) as session:
        # First pass: Build domain → monthly_visits mapping
        print("📊 Step 1: Finding domains with traffic data...")
        ads_with_traffic = session.exec(
            select(AdCreative).where(AdCreative.monthly_visits.is_not(None))
        ).all()
        
        domain_to_visits = {}
        for ad in ads_with_traffic:
            domain = extract_domain(ad.landing_url)
            if domain and ad.monthly_visits > 0:
                domain_to_visits[domain] = ad.monthly_visits
        
        print(f"✅ Found {len(domain_to_visits)} domains with traffic data\n")
        
        # Second pass: Update ads in batches
        print("📊 Step 2: Updating ads without traffic data...")
        ads_without_traffic = session.exec(
            select(AdCreative).where(
                (AdCreative.monthly_visits.is_(None)) | (AdCreative.monthly_visits == 0)
            )
        ).all()
        
        updated_count = 0
        batch_size = 500
        
        for i in range(0, len(ads_without_traffic), batch_size):
            batch = ads_without_traffic[i:i+batch_size]
            
            for ad in batch:
                domain = extract_domain(ad.landing_url)
                if domain and domain in domain_to_visits:
                    ad.monthly_visits = domain_to_visits[domain]
                    updated_count += 1
            
            # Commit this batch
            session.commit()
            print(f"  Processed {min(i+batch_size, len(ads_without_traffic))}/{len(ads_without_traffic)} ads...")
        
        print(f"\n✅ Updated {updated_count} ads with shared monthly_visits!")
        print(f"\n📈 Summary:")
        
        # Show some examples
        example_domains = list(domain_to_visits.items())[:5]
        for domain, visits in example_domains:
            print(f"  {domain}: {visits:,} visits")
        
        # Final stats
        total_with_visits = session.exec(
            select(AdCreative).where(AdCreative.monthly_visits.is_not(None))
        ).all()
        print(f"\n📊 Final: {len(total_with_visits)} ads now have monthly_visits")


if __name__ == "__main__":
    main()
