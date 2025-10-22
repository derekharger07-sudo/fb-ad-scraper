"""
Backfill page_id for existing ads by extracting from advertiser_url in raw data.

Run: PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 app/workers/backfill_page_ids.py
"""

import os
import sys
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.repo import get_session
from app.db.models import AdCreative
from sqlmodel import select

def extract_page_id_from_url(url: str) -> str | None:
    """Extract page ID from Facebook advertiser URL."""
    if not url:
        return None
    
    # Format 1: /profile.php?id=PAGE_ID
    profile_match = re.search(r'profile\.php\?id=(\d+)', url)
    if profile_match:
        return profile_match.group(1)
    
    # Format 2: /pages/PAGE_NAME/PAGE_ID
    pages_match = re.search(r'/pages/[^/]+/(\d+)', url)
    if pages_match:
        return pages_match.group(1)
    
    # Format 3: /PAGE_ID/ or /PAGE_USERNAME
    username_match = re.search(r'facebook\.com/([^/\?]+)', url)
    if username_match and username_match.group(1) not in ['ads', 'pages', 'profile']:
        return username_match.group(1)
    
    return None

def backfill_page_ids():
    """Backfill page_id for all ads that have advertiser_url in raw data."""
    
    print("🔄 Starting page_id backfill from advertiser_url...")
    
    with get_session() as session:
        # Get all ads
        stmt = select(AdCreative)
        ads = session.exec(stmt).all()
        
        total = len(ads)
        updated = 0
        skipped = 0
        
        print(f"📊 Found {total} ads to process")
        
        for ad in ads:
            # Skip if page_id already set
            if ad.page_id:
                skipped += 1
                continue
            
            # Try to extract from raw.advertiser_url
            if ad.raw and isinstance(ad.raw, dict):
                advertiser_url = ad.raw.get('advertiser_url')
                if advertiser_url:
                    page_id = extract_page_id_from_url(advertiser_url)
                    if page_id:
                        ad.page_id = page_id
                        session.add(ad)
                        updated += 1
                        if updated % 10 == 0:
                            print(f"  ✅ Updated {updated} ads...")
        
        # Commit all changes
        session.commit()
        
        print(f"\n✅ Backfill complete!")
        print(f"  • Total ads: {total}")
        print(f"  • Updated: {updated}")
        print(f"  • Skipped (already had page_id): {skipped}")
        print(f"  • No advertiser_url: {total - updated - skipped}")

if __name__ == "__main__":
    backfill_page_ids()
