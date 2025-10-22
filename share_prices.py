#!/usr/bin/env python3
"""
Share product_price across ads with the same landing_url.
Similar to traffic sharing - if one ad has a price, copy it to all ads with same URL.
"""

import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

print("🔄 Sharing product prices across ads with same landing_url...\n")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Find landing URLs that have at least one ad with a price
print("📊 Step 1: Finding landing URLs with price data...")
cur.execute("""
    SELECT landing_url, product_price
    FROM adcreative
    WHERE product_price IS NOT NULL 
      AND product_price != ''
      AND landing_url IS NOT NULL
""")

# Build URL → price mapping
url_to_price = {}
for landing_url, product_price in cur.fetchall():
    if landing_url and product_price:
        # Use the first non-null price for each URL
        if landing_url not in url_to_price:
            url_to_price[landing_url] = product_price

print(f"✅ Found {len(url_to_price)} unique landing URLs with price data\n")

# For each URL, check how many ads are missing prices
print("📊 Step 2: Checking which URLs need price updates...")
urls_to_process = []

for url, price in url_to_price.items():
    # Count ads without product_price for this exact URL
    cur.execute("""
        SELECT COUNT(*)
        FROM adcreative
        WHERE landing_url = %s
          AND (product_price IS NULL OR product_price = '')
    """, (url,))
    
    count = cur.fetchone()[0]
    if count > 0:
        urls_to_process.append((url, price, count))

print(f"✅ Found {len(urls_to_process)} URLs with ads needing price updates\n")

if not urls_to_process:
    print("🎉 All URLs are already complete! Nothing to do.")
    cur.close()
    conn.close()
    exit(0)

# Update ads that need prices
print("📊 Step 3: Updating ads...")
updated_total = 0
batch_count = 0

for url, price, count_missing in urls_to_process:
    # Update all ads missing product_price for this URL
    cur.execute("""
        UPDATE adcreative
        SET product_price = %s
        WHERE landing_url = %s
          AND (product_price IS NULL OR product_price = '')
    """, (price, url))
    
    updated = cur.rowcount
    if updated > 0:
        updated_total += updated
        # Show first 20 examples
        if batch_count < 20:
            url_short = url[:60] + '...' if len(url) > 60 else url
            print(f"  {price} → {updated} ads ({url_short})")
        batch_count += 1
    
    # Commit every 50 URLs to avoid timeout
    if batch_count % 50 == 0:
        conn.commit()

# Final commit
conn.commit()

# Final stats
cur.execute("SELECT COUNT(*) FROM adcreative WHERE product_price IS NOT NULL AND product_price != ''")
total_with_prices = cur.fetchone()[0]

print(f"\n✅ Updated {updated_total} ads!")
print(f"📊 Total ads with prices: {total_with_prices:,}")
print(f"📊 Processed {len(urls_to_process)} unique URLs")

cur.close()
conn.close()
