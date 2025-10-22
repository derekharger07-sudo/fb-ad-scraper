#!/usr/bin/env python3
"""
Test script to verify scraper extracts ALL data correctly
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.workers.run_test_scraper import main as scraper

async def test_full_extraction():
    print("=" * 60)
    print("🧪 TESTING FULL DATA EXTRACTION")
    print("=" * 60)
    print()
    
    # Test with a real keyword
    print("Testing scraper with keyword: 'leggings'")
    print("Limit: 3 ads (quick test)")
    print()
    
    ads = await scraper(keyword='leggings', limit=3, country='US')
    
    print(f"\n✅ Scraped {len(ads)} ads")
    print()
    
    if not ads:
        print("❌ No ads found - scraper might have issues")
        return
    
    # Check what data was extracted
    for i, ad in enumerate(ads, 1):
        print(f"--- Ad {i} ---")
        print(f"  Advertiser: {ad.get('advertiser_name', 'N/A')}")
        print(f"  Caption: {ad.get('caption', 'N/A')[:60]}...")
        print(f"  Landing URL: {ad.get('landing_url', 'N/A')[:60]}...")
        print(f"  🏷️  Product Name: {ad.get('product_name', 'N/A')}")
        print(f"  💰 Product Price: {ad.get('product_price', 'N/A')}")
        print(f"  🛒 Platform Type: {ad.get('platform_type', 'N/A')}")
        print(f"  📈 Monthly Visits: {ad.get('monthly_visits', 'N/A')}")
        print(f"  ✨ Is Spark Ad: {ad.get('is_spark_ad', False)}")
        print(f"  📊 Total Score: {ad.get('total_score', 'N/A')}")
        print()
    
    # Verify critical fields
    issues = []
    for i, ad in enumerate(ads, 1):
        if not ad.get('product_name'):
            issues.append(f"Ad {i}: Missing product_name")
        if ad.get('product_price') is None and not ad.get('is_spark_ad'):
            issues.append(f"Ad {i}: Missing product_price (not Spark ad)")
        if not ad.get('platform_type'):
            issues.append(f"Ad {i}: Missing platform_type")
    
    if issues:
        print("⚠️  ISSUES FOUND:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ ALL CRITICAL FIELDS EXTRACTED!")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_full_extraction())
