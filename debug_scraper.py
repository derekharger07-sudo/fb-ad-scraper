#!/usr/bin/env python3
"""
Debug script to see exactly what's happening with the scraper
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.workers.run_test_scraper import run_test_scrape

async def debug_scrape():
    print("=" * 60)
    print("🐛 DEBUG MODE - Let's see what's happening")
    print("=" * 60)
    print()
    
    # Check database first
    print("1️⃣ Checking database...")
    try:
        from app.db.repo import get_session
        from app.db.models import AdCreative
        session = next(get_session())
        count = session.query(AdCreative).count()
        print(f"✅ Database accessible - Current ads: {count}")
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("\n🔧 Fix: Run 'python init_database.py' first!")
        return
    
    print()
    print("2️⃣ Testing scraper with 1 keyword (limit 5 ads)...")
    print()
    
    # Test with single keyword
    try:
        ads = await run_test_scrape(
            keyword='yoga mat',  # Simple product
            limit=5,  # Just 5 ads
            country='US'
        )
        
        print()
        print("=" * 60)
        print("📊 RESULTS:")
        print("=" * 60)
        print(f"Total ads found: {len(ads)}")
        
        if ads:
            print("\n✅ Scraper is working!")
            for i, ad in enumerate(ads, 1):
                print(f"\n--- Ad {i} ---")
                print(f"  Product: {ad.get('product_name', 'N/A')}")
                print(f"  Price: {ad.get('product_price', 'N/A')}")
                print(f"  Platform: {ad.get('platform_type', 'N/A')}")
                print(f"  Traffic: {ad.get('monthly_visits', 'N/A')}")
        else:
            print("\n❌ 0 ads saved - possible issues:")
            print("  1. No ads found on Facebook (try different keyword)")
            print("  2. All ads skipped (no landing URLs / no product names)")
            print("  3. Database not saving (check errors above)")
            
    except Exception as e:
        print(f"\n❌ Scraper crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_scrape())
