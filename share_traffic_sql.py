#!/usr/bin/env python3
"""
Share monthly_visits across ads with same domain using efficient SQL.
"""

import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

print("🔄 Sharing monthly_visits across ads with same domain using SQL...\n")

# Connect to database
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Get domains with traffic data
print("📊 Step 1: Analyzing domains with traffic data...")
cur.execute("""
    SELECT landing_url, monthly_visits
    FROM adcreative
    WHERE monthly_visits IS NOT NULL AND monthly_visits > 0
""")

# Build domain → visits mapping
domain_to_visits = {}
for landing_url, monthly_visits in cur.fetchall():
    if not landing_url:
        continue
    try:
        parsed = urlparse(landing_url)
        domain = (parsed.netloc or parsed.path).replace('www.', '')
        if domain:
            domain_to_visits[domain] = monthly_visits
    except:
        continue

print(f"✅ Found {len(domain_to_visits)} unique domains with traffic data\n")

# Update ads by domain
print("📊 Step 2: Updating ads...")
updated_total = 0

for domain, visits in domain_to_visits.items():
    # Update all ads matching this domain
    cur.execute("""
        UPDATE adcreative
        SET monthly_visits = %s
        WHERE (monthly_visits IS NULL OR monthly_visits = 0)
          AND (landing_url LIKE %s OR landing_url LIKE %s)
    """, (visits, f'%://{domain}%', f'%://www.{domain}%'))
    
    updated = cur.rowcount
    if updated > 0:
        updated_total += updated
        print(f"  {domain}: {visits:,} visits → {updated} ads")

# Commit changes
conn.commit()

# Final stats
cur.execute("SELECT COUNT(*) FROM adcreative WHERE monthly_visits IS NOT NULL")
total_with_visits = cur.fetchone()[0]

print(f"\n✅ Updated {updated_total} ads with shared monthly_visits!")
print(f"📊 Final: {total_with_visits:,} ads now have monthly_visits")

cur.close()
conn.close()
