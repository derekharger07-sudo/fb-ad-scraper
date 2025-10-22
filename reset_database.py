"""
Reset database - Delete all ads
Use this before running a fresh scrape
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

# Connect to database
engine = create_engine(DATABASE_URL)

print("🗑️  DATABASE RESET")
print("=" * 80)

with engine.connect() as conn:
    # Count current ads
    try:
        result = conn.execute(text("SELECT COUNT(*) FROM ad_creatives"))
        current_count = result.scalar()
        print(f"📊 Current ads in database: {current_count}")
    except:
        print("⚠️  No ads table found or database is empty")
        exit(0)
    
    if current_count == 0:
        print("✅ Database is already empty!")
        exit(0)
    
    # Ask for confirmation
    print(f"\n⚠️  WARNING: This will permanently delete all {current_count} ads!")
    confirm = input("Type 'DELETE ALL' to confirm: ")
    
    if confirm != 'DELETE ALL':
        print("❌ Reset cancelled")
        exit(0)
    
    # Delete all ads
    print("\n🗑️  Deleting all ads...")
    conn.execute(text("DELETE FROM ad_creatives"))
    conn.commit()
    
    # Verify deletion
    result = conn.execute(text("SELECT COUNT(*) FROM ad_creatives"))
    remaining = result.scalar()
    
    if remaining == 0:
        print(f"✅ Successfully deleted {current_count} ads")
        print("📊 Database is now empty and ready for fresh scraping!")
    else:
        print(f"⚠️  Warning: {remaining} ads still remain")
    
print("\n" + "=" * 80)
print("🚀 You can now run: python distributed_scraper.py")
