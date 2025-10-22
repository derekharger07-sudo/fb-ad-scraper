"""
Delete ads from latest scrape only (by date)
Safe: Keeps all older ads, only removes recent ones
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

engine = create_engine(DATABASE_URL)

print("🗑️  DELETE LATEST SCRAPE")
print("=" * 80)

with engine.connect() as conn:
    # Show total ads
    result = conn.execute(text("SELECT COUNT(*) FROM adcreative"))
    total_count = result.scalar()
    print(f"📊 Total ads in database: {total_count}")
    
    # Show ads from today
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM adcreative 
        WHERE DATE(first_seen_ts) = CURRENT_DATE
    """))
    today_count = result.scalar()
    print(f"📅 Ads scraped today: {today_count}")
    
    # Show ads from last hour
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM adcreative 
        WHERE first_seen_ts >= NOW() - INTERVAL '1 hour'
    """))
    last_hour_count = result.scalar()
    print(f"⏰ Ads scraped in last hour: {last_hour_count}")
    
    # Show ads from last 30 minutes
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM adcreative 
        WHERE first_seen_ts >= NOW() - INTERVAL '30 minutes'
    """))
    last_30min_count = result.scalar()
    print(f"⏱️  Ads scraped in last 30 minutes: {last_30min_count}")
    
    # Show ads from last 24 hours
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM adcreative 
        WHERE first_seen_ts >= NOW() - INTERVAL '24 hours'
    """))
    last_24h_count = result.scalar()
    print(f"📆 Ads scraped in last 24 hours: {last_24h_count}")
    
    # Show ads from last 48 hours
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM adcreative 
        WHERE first_seen_ts >= NOW() - INTERVAL '48 hours'
    """))
    last_48h_count = result.scalar()
    print(f"📆 Ads scraped in last 48 hours: {last_48h_count}")
    
    print("\n" + "=" * 80)
    print("DELETE OPTIONS:")
    print("1. Last 30 minutes only")
    print("2. Last hour only")
    print("3. Last 24 hours only")
    print("4. Last 48 hours only")
    print("5. Today only")
    print("6. Cancel (don't delete anything)")
    print("=" * 80)
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == "1":
        delete_query = "DELETE FROM adcreative WHERE first_seen_ts >= NOW() - INTERVAL '30 minutes'"
        delete_count = last_30min_count
        timeframe = "last 30 minutes"
    elif choice == "2":
        delete_query = "DELETE FROM adcreative WHERE first_seen_ts >= NOW() - INTERVAL '1 hour'"
        delete_count = last_hour_count
        timeframe = "last hour"
    elif choice == "3":
        delete_query = "DELETE FROM adcreative WHERE first_seen_ts >= NOW() - INTERVAL '24 hours'"
        delete_count = last_24h_count
        timeframe = "last 24 hours"
    elif choice == "4":
        delete_query = "DELETE FROM adcreative WHERE first_seen_ts >= NOW() - INTERVAL '48 hours'"
        delete_count = last_48h_count
        timeframe = "last 48 hours"
    elif choice == "5":
        delete_query = "DELETE FROM adcreative WHERE DATE(first_seen_ts) = CURRENT_DATE"
        delete_count = today_count
        timeframe = "today"
    elif choice == "6":
        print("❌ Cancelled - no ads deleted")
        exit(0)
    else:
        print("❌ Invalid choice")
        exit(1)
    
    # Confirm deletion
    print(f"\n⚠️  WARNING: This will delete {delete_count} ads from {timeframe}")
    print(f"📊 {total_count - delete_count} older ads will be kept safe")
    confirm = input(f"\nType 'DELETE {timeframe.upper()}' to confirm: ")
    
    expected_confirm = f"DELETE {timeframe.upper()}"
    if confirm != expected_confirm:
        print("❌ Deletion cancelled")
        exit(0)
    
    # Delete ads
    print(f"\n🗑️  Deleting ads from {timeframe}...")
    conn.execute(text(delete_query))
    conn.commit()
    
    # Verify
    result = conn.execute(text("SELECT COUNT(*) FROM adcreative"))
    remaining = result.scalar()
    deleted = total_count - remaining
    
    print(f"\n✅ Successfully deleted {deleted} ads from {timeframe}")
    print(f"📊 Remaining ads in database: {remaining}")

print("\n" + "=" * 80)
print("✅ Done!")
