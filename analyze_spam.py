"""
Analyze spam in database without deleting anything
Shows how many ads match each spam filter
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

print("📊 SPAM ANALYSIS REPORT")
print("=" * 80)

with engine.connect() as conn:
    # Total ads
    result = conn.execute(text("SELECT COUNT(*) FROM ad_creatives"))
    total_ads = result.scalar()
    print(f"\n📈 Total ads in database: {total_ads}")
    
    # Broken ads (login pages, errors, no creative)
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM ad_creatives 
        WHERE product_name LIKE '%Login%' 
           OR product_name LIKE '%login%'
           OR product_name LIKE '%Sign in%'
           OR product_name LIKE '%Error%'
           OR product_name LIKE '%404%'
           OR (video_url IS NULL AND image_url IS NULL)
    """))
    broken_count = result.scalar()
    print(f"🚫 Broken ads (login/error/no creative): {broken_count}")
    
    # Romance/fantasy novel spam by advertiser
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM ad_creatives 
        WHERE advertiser_name ILIKE '%dreame%'
           OR advertiser_name ILIKE '%worth reading%'
           OR advertiser_name ILIKE '%novels lover%'
           OR advertiser_name ILIKE '%romance stories%'
           OR advertiser_name ILIKE '%happyday%'
           OR advertiser_name ILIKE '%myno%'
           OR advertiser_name ILIKE '%webnovel%'
           OR advertiser_name ILIKE '%goodnovel%'
           OR advertiser_name ILIKE '%inkitt%'
           OR advertiser_name ILIKE '%wattpad%'
           OR advertiser_name ILIKE '%alpha romance%'
           OR advertiser_name ILIKE '%luna tales%'
           OR advertiser_name ILIKE '%werewolf%'
           OR advertiser_name ILIKE '%vampire romance%'
           OR advertiser_name ILIKE '%billionaire romance%'
           OR advertiser_name ILIKE '%mafia romance%'
           OR advertiser_name ILIKE '%royal romance%'
           OR advertiser_name ILIKE '%dark romance%'
           OR advertiser_name ILIKE '%forbidden romance%'
           OR advertiser_name ILIKE '%alpha''s%'
           OR advertiser_name ILIKE '%dark alpha%'
           OR advertiser_name ILIKE '%fated mates%'
    """))
    spam_advertisers_count = result.scalar()
    print(f"🚫 Spam by advertiser name: {spam_advertisers_count}")
    
    # Spam by product name keywords
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM ad_creatives 
        WHERE product_name ILIKE '%alpha%'
           OR product_name ILIKE '%luna%'
           OR product_name ILIKE '%werewolf%'
           OR product_name ILIKE '%breed me%'
           OR product_name ILIKE '%daddy alpha%'
           OR product_name ILIKE '%betrayal%'
           OR product_name ILIKE '%revenge%'
           OR product_name ILIKE '%stepmother%'
           OR product_name ILIKE '%vampire%'
           OR product_name ILIKE '%billionaire%'
           OR product_name ILIKE '%bodyguard%'
           OR product_name ILIKE '%rejected%'
           OR product_name ILIKE '%romance novel%'
           OR product_name ILIKE '%chapter%'
    """))
    spam_products_count = result.scalar()
    print(f"🚫 Spam by product keywords: {spam_products_count}")
    
    # Mobile app stores
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM ad_creatives 
        WHERE landing_url LIKE '%play.google.com%'
           OR landing_url LIKE '%apps.apple.com%'
           OR landing_url LIKE '%app.google.com%'
    """))
    app_stores_count = result.scalar()
    print(f"🚫 Mobile app store ads: {app_stores_count}")
    
    # Novel platform domains
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM ad_creatives 
        WHERE landing_url LIKE '%dreame.com%'
           OR landing_url LIKE '%goodnovel.com%'
           OR landing_url LIKE '%webnovel.com%'
           OR landing_url LIKE '%ficfun.com%'
           OR landing_url LIKE '%bravonovel.com%'
    """))
    novel_domains_count = result.scalar()
    print(f"🚫 Novel platform domains: {novel_domains_count}")
    
    # Calculate total spam (with overlap removed)
    result = conn.execute(text("""
        SELECT COUNT(DISTINCT id) 
        FROM ad_creatives 
        WHERE product_name LIKE '%Login%' 
           OR product_name LIKE '%login%'
           OR product_name LIKE '%Sign in%'
           OR product_name LIKE '%Error%'
           OR product_name LIKE '%404%'
           OR (video_url IS NULL AND image_url IS NULL)
           OR advertiser_name ILIKE '%dreame%'
           OR advertiser_name ILIKE '%worth reading%'
           OR advertiser_name ILIKE '%novels lover%'
           OR advertiser_name ILIKE '%romance stories%'
           OR advertiser_name ILIKE '%happyday%'
           OR advertiser_name ILIKE '%myno%'
           OR advertiser_name ILIKE '%webnovel%'
           OR advertiser_name ILIKE '%goodnovel%'
           OR advertiser_name ILIKE '%inkitt%'
           OR advertiser_name ILIKE '%wattpad%'
           OR advertiser_name ILIKE '%alpha romance%'
           OR advertiser_name ILIKE '%werewolf%'
           OR advertiser_name ILIKE '%vampire romance%'
           OR advertiser_name ILIKE '%billionaire romance%'
           OR advertiser_name ILIKE '%royal romance%'
           OR product_name ILIKE '%alpha%'
           OR product_name ILIKE '%luna%'
           OR product_name ILIKE '%werewolf%'
           OR product_name ILIKE '%vampire%'
           OR product_name ILIKE '%billionaire%'
           OR product_name ILIKE '%romance novel%'
           OR landing_url LIKE '%play.google.com%'
           OR landing_url LIKE '%apps.apple.com%'
           OR landing_url LIKE '%dreame.com%'
           OR landing_url LIKE '%goodnovel.com%'
           OR landing_url LIKE '%webnovel.com%'
    """))
    total_spam = result.scalar()
    
    clean_ads = total_ads - total_spam
    spam_percentage = (total_spam / total_ads * 100) if total_ads > 0 else 0
    
    print(f"\n" + "=" * 80)
    print(f"📊 SUMMARY")
    print(f"=" * 80)
    print(f"Total spam/broken ads: {total_spam} ({spam_percentage:.1f}%)")
    print(f"Clean ads remaining: {clean_ads} ({100-spam_percentage:.1f}%)")
    print(f"\n💡 Run 'python cleanup_broken_ads.py' to remove all spam ads")
    
    # Show some examples of spam ads
    print(f"\n📋 SPAM EXAMPLES (first 10):")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT advertiser_name, product_name, landing_url
        FROM ad_creatives 
        WHERE advertiser_name ILIKE '%dreame%'
           OR advertiser_name ILIKE '%worth reading%'
           OR advertiser_name ILIKE '%novels lover%'
           OR advertiser_name ILIKE '%romance stories%'
           OR advertiser_name ILIKE '%myno%'
           OR advertiser_name ILIKE '%alpha%'
           OR advertiser_name ILIKE '%werewolf%'
           OR product_name ILIKE '%alpha%'
           OR product_name ILIKE '%luna%'
           OR product_name ILIKE '%login%'
           OR landing_url LIKE '%play.google.com%'
        LIMIT 10
    """))
    
    for row in result:
        advertiser = row[0] or "N/A"
        product = row[1] or "N/A"
        url = row[2] or "N/A"
        print(f"  • {advertiser[:30]:<30} | {product[:40]:<40}")
        if "play.google.com" in url or "dreame.com" in url or "goodnovel.com" in url:
            print(f"    🔗 {url[:70]}")
    
    print("\n" + "=" * 80)
