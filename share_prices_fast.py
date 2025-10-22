#!/usr/bin/env python3
"""
Fast price sharing using efficient SQL UPDATE.
"""

import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

print("🔄 Sharing product prices across ads with same landing_url...\n")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Use a single UPDATE query with a subquery
print("📊 Updating ads with prices from same landing_url...")

cur.execute("""
    UPDATE adcreative a1
    SET product_price = (
        SELECT a2.product_price
        FROM adcreative a2
        WHERE a2.landing_url = a1.landing_url
          AND a2.product_price IS NOT NULL
          AND a2.product_price != ''
        LIMIT 1
    )
    WHERE (a1.product_price IS NULL OR a1.product_price = '')
      AND a1.landing_url IS NOT NULL
      AND EXISTS (
        SELECT 1
        FROM adcreative a3
        WHERE a3.landing_url = a1.landing_url
          AND a3.product_price IS NOT NULL
          AND a3.product_price != ''
      )
""")

updated_count = cur.rowcount
conn.commit()

# Final stats
cur.execute("SELECT COUNT(*) FROM adcreative WHERE product_price IS NOT NULL AND product_price != ''")
total_with_prices = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM adcreative WHERE product_price IS NULL OR product_price = ''")
total_without_prices = cur.fetchone()[0]

print(f"\n✅ Updated {updated_count:,} ads with shared prices!")
print(f"📊 Total ads with prices: {total_with_prices:,}")
print(f"⚠️  Total ads still missing prices: {total_without_prices:,}")

cur.close()
conn.close()
