#!/usr/bin/env python3
"""
Quick test - scrape ONE keyword with detailed output
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def quick_test():
    from app.workers.run_test_scraper import run_test_scrape
    
    print("🧪 Testing with 'yoga mat' keyword...")
    print("Looking for 3 ads with landing pages...")
    print()
    
    ads = await run_test_scrape(
        keyword='yoga mat',
        limit=3,
        country='US'
    )
    
    print()
    print("=" * 60)
    print(f"📊 RESULT: Found {len(ads)} ads")
    print("=" * 60)
    
    if ads:
        print("\n✅ SUCCESS! Ads were saved:")
        for i, ad in enumerate(ads, 1):
            print(f"\nAd {i}:")
            print(f"  Product: {ad.get('product_name', 'N/A')}")
            print(f"  Price: {ad.get('product_price', 'N/A')}")
            print(f"  URL: {ad.get('landing_url', 'N/A')[:60]}...")
    else:
        print("\n❌ 0 ads found. This means:")
        print("  1. All ads on Facebook were brand awareness ads (no landing page)")
        print("  2. Or Facebook blocked automated access")
        print("  3. Try different keyword or check Facebook Ads Library manually")

if __name__ == "__main__":
    asyncio.run(quick_test())
