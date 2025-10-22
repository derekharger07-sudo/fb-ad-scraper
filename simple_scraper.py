#!/usr/bin/env python3
"""
Simple Sequential Facebook Ad Scraper
Processes keywords one at a time (1 browser) - STABLE & RELIABLE
"""
import sys
import os
from datetime import datetime

# Add to path
sys.path.insert(0, os.path.dirname(__file__))

from app.workers.run_test_scraper import main as scraper

def main():
    # Read keywords
    with open('keywords.txt', 'r') as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    print("=" * 60)
    print("🚀 SIMPLE SEQUENTIAL FACEBOOK AD SCRAPER")
    print("=" * 60)
    print(f"\n📋 Loaded {len(keywords)} keywords")
    print("⚙️  Mode: Sequential (1 browser at a time)")
    print("🕐 Started:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("\n" + "-" * 60 + "\n")
    
    total_ads = 0
    for i, keyword in enumerate(keywords, 1):
        print(f"[{i}/{len(keywords)}] Scraping: '{keyword}'")
        
        try:
            ads = scraper(keyword=keyword, limit=20, country='US')
            total_ads += len(ads)
            print(f"  ✅ Found {len(ads)} ads (total: {total_ads})")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()
    
    print("-" * 60)
    print(f"\n🎯 COMPLETE!")
    print(f"📊 Total ads scraped: {total_ads}")
    print(f"🕐 Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
