#!/usr/bin/env python3
"""
Smart traffic sharing - only processes domains that still need updates.
"""

import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

print("🔄 Smart traffic sharing (skips already-completed domains)...\n")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Find domains that:
# 1. Have at least one ad WITH monthly_visits
# 2. Have at least one ad WITHOUT monthly_visits
print("📊 Finding domains that need processing...")
cur.execute("""
    SELECT landing_url, monthly_visits
    FROM adcreative
    WHERE monthly_visits IS NOT NULL AND monthly_visits > 0
""")

# Build domain mapping
domain_to_visits = {}
domain_total_ads = {}
domain_ads_without_visits = {}

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

print(f"✅ Found {len(domain_to_visits)} domains with traffic data\n")

# For each domain, check how many ads are missing monthly_visits
print("📊 Checking which domains need updates...")
domains_to_process = []

for domain in domain_to_visits.keys():
    # Count ads without monthly_visits for this domain
    cur.execute("""
        SELECT COUNT(*)
        FROM adcreative
        WHERE (monthly_visits IS NULL OR monthly_visits = 0)
          AND (landing_url LIKE %s OR landing_url LIKE %s)
    """, (f'%://{domain}%', f'%://www.{domain}%'))
    
    count = cur.fetchone()[0]
    if count > 0:
        domains_to_process.append((domain, domain_to_visits[domain], count))

print(f"✅ Found {len(domains_to_process)} domains with ads needing updates\n")

if not domains_to_process:
    print("🎉 All domains are already complete! Nothing to do.")
    cur.close()
    conn.close()
    exit(0)

# Process domains that need updates
print("📊 Updating ads...")
updated_total = 0

for domain, visits, count_missing in domains_to_process:
    # Update all ads missing monthly_visits for this domain
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
    
    # Commit every 10 domains to avoid timeout
    if updated_total % 10 == 0:
        conn.commit()

# Final commit
conn.commit()

# Final stats
cur.execute("SELECT COUNT(*) FROM adcreative WHERE monthly_visits IS NOT NULL AND monthly_visits > 0")
total_with_visits = cur.fetchone()[0]

print(f"\n✅ Updated {updated_total} ads!")
print(f"📊 Total ads with monthly_visits: {total_with_visits:,}")

cur.close()
conn.close()
