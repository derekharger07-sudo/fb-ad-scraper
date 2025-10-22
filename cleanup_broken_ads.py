"""
Clean up broken and spam ads from database
- Login pages, error pages, no creatives
- Romance/fantasy novel spam ads (Dreame, Worth Reading, etc.)
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

print("🔍 Finding broken and spam ads...")

with engine.connect() as conn:
    # Count broken ads (login pages, errors, no creative)
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
    print(f"📊 Broken ads (login/error/no creative): {broken_count}")
    
    # Count spam ads (romance/fantasy novels)
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
           OR advertiser_name ILIKE '%sofanovel%'
           OR advertiser_name ILIKE '%novelstar%'
           OR advertiser_name ILIKE '%star novel%'
           OR advertiser_name ILIKE '%novelmania%'
           OR advertiser_name ILIKE '%royalnovel%'
           OR advertiser_name ILIKE '%webfiction%'
           OR advertiser_name ILIKE '%novelday%'
           OR advertiser_name ILIKE '%dreamy stories%'
           OR advertiser_name ILIKE '%my passion%'
           OR advertiser_name ILIKE '%fiction lover%'
           OR advertiser_name ILIKE '%storydreams%'
           OR advertiser_name ILIKE '%storylover%'
           OR advertiser_name ILIKE '%storyjoy%'
           OR advertiser_name ILIKE '%readstories%'
           OR advertiser_name ILIKE '%storyheart%'
           OR advertiser_name ILIKE '%novelsweet%'
           OR advertiser_name ILIKE '%dreamnovel%'
           OR advertiser_name ILIKE '%fantasy lover%'
           OR advertiser_name ILIKE '%romanceworld%'
           OR advertiser_name ILIKE '%storytale%'
           OR advertiser_name ILIKE '%lovenovel%'
           OR advertiser_name ILIKE '%alpha romance%'
           OR advertiser_name ILIKE '%luna tales%'
           OR advertiser_name ILIKE '%wolfmate%'
           OR advertiser_name ILIKE '%werewolf queen%'
           OR advertiser_name ILIKE '%mate of the alpha%'
           OR advertiser_name ILIKE '%alpha''s mate%'
           OR advertiser_name ILIKE '%dark alpha%'
           OR advertiser_name ILIKE '%eternal alpha%'
           OR advertiser_name ILIKE '%fated mates%'
           OR advertiser_name ILIKE '%twin alphas%'
           OR advertiser_name ILIKE '%alpha protector%'
           OR advertiser_name ILIKE '%soulbound alpha%'
           OR advertiser_name ILIKE '%queen''s alpha%'
           OR advertiser_name ILIKE '%alpha prophecy%'
           OR advertiser_name ILIKE '%alpha dynasty%'
           OR advertiser_name ILIKE '%forbidden romance%'
           OR advertiser_name ILIKE '%billionaire romance%'
           OR advertiser_name ILIKE '%mafia romance%'
           OR advertiser_name ILIKE '%dark romance%'
           OR advertiser_name ILIKE '%royal romance%'
           OR advertiser_name ILIKE '%broken royals%'
           OR advertiser_name ILIKE '%secret heir%'
           OR advertiser_name ILIKE '%forbidden king%'
           OR advertiser_name ILIKE '%hidden identity%'
           OR advertiser_name ILIKE '%royal blood%'
           OR advertiser_name ILIKE '%enchanted kingdom%'
           OR advertiser_name ILIKE '%cursed bloodlines%'
           OR advertiser_name ILIKE '%mystic romance%'
           OR advertiser_name ILIKE '%twisted love%'
           OR advertiser_name ILIKE '%dark royals%'
           OR advertiser_name ILIKE '%lost heirs%'
           OR advertiser_name ILIKE '%heir to the throne%'
           OR advertiser_name ILIKE '%shattered promises%'
           OR advertiser_name ILIKE '%forbidden heirs%'
           OR advertiser_name ILIKE '%hidden legacy%'
           OR advertiser_name ILIKE '%shadow romance%'
           OR advertiser_name ILIKE '%phantom love%'
           OR advertiser_name ILIKE '%royal seduction%'
           OR advertiser_name ILIKE '%vampire romance%'
           OR advertiser_name ILIKE '%shifter romance%'
           OR advertiser_name ILIKE '%paranormal royals%'
           OR advertiser_name ILIKE '%immortal royals%'
           OR advertiser_name ILIKE '%vampire royals%'
           OR advertiser_name ILIKE '%fated royals%'
           OR advertiser_name ILIKE '%phantom heir%'
           OR advertiser_name ILIKE '%forbidden royalty%'
           OR advertiser_name ILIKE '%royal curse%'
           OR advertiser_name ILIKE '%eclipse romance%'
           OR advertiser_name ILIKE '%dynasty romance%'
           OR advertiser_name ILIKE '%empress of love%'
           OR advertiser_name ILIKE '%dark prince%'
           OR advertiser_name ILIKE '%crown & alpha%'
           OR advertiser_name ILIKE '%royal guardian%'
           OR advertiser_name ILIKE '%immortal love%'
           OR advertiser_name ILIKE '%stepmother diaries%'
           OR advertiser_name ILIKE '%revenge fantasy%'
           OR product_name ILIKE '%alpha%'
           OR product_name ILIKE '%luna%'
           OR product_name ILIKE '%werewolf%'
           OR product_name ILIKE '%breed me%'
           OR product_name ILIKE '%daddy alpha%'
           OR product_name ILIKE '%betrayal%'
           OR product_name ILIKE '%revenge%'
           OR product_name ILIKE '%stepmother%'
           OR product_name ILIKE '%stepdad%'
           OR product_name ILIKE '%stepson%'
           OR product_name ILIKE '%fighter%'
           OR product_name ILIKE '%survivor%'
           OR product_name ILIKE '%vampire%'
           OR product_name ILIKE '%billionaire%'
           OR product_name ILIKE '%ceo romance%'
           OR product_name ILIKE '%bodyguard%'
           OR product_name ILIKE '%rejected%'
           OR product_name ILIKE '%romance novel%'
           OR product_name ILIKE '%chapter%'
           OR product_name ILIKE '%book one%'
           OR product_name ILIKE '%episode%'
           OR landing_url LIKE '%dreame.com%'
           OR landing_url LIKE '%goodnovel.com%'
           OR landing_url LIKE '%webnovel.com%'
           OR landing_url LIKE '%ficfun.com%'
           OR landing_url LIKE '%bravonovel.com%'
           OR landing_url LIKE '%play.google.com%'
           OR landing_url LIKE '%apps.apple.com%'
           OR landing_url LIKE '%app.google.com%'
    """))
    spam_count = result.scalar()
    print(f"📊 Spam ads (romance/fantasy novels): {spam_count}")
    
    total_count = broken_count + spam_count
    
    if total_count == 0:
        print("✅ No broken or spam ads to clean up!")
        exit(0)
    
    # Ask for confirmation
    confirm = input(f"\n⚠️  Delete {total_count} total ads ({broken_count} broken + {spam_count} spam)? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Cleanup cancelled")
        exit(0)
    
    # Delete broken ads
    if broken_count > 0:
        conn.execute(text("""
            DELETE FROM ad_creatives 
            WHERE product_name LIKE '%Login%' 
               OR product_name LIKE '%login%'
               OR product_name LIKE '%Sign in%'
               OR product_name LIKE '%Error%'
               OR product_name LIKE '%404%'
               OR (video_url IS NULL AND image_url IS NULL)
        """))
        print(f"✅ Deleted {broken_count} broken ads")
    
    # Delete spam ads
    if spam_count > 0:
        conn.execute(text("""
            DELETE FROM ad_creatives 
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
               OR advertiser_name ILIKE '%sofanovel%'
               OR advertiser_name ILIKE '%novelstar%'
               OR advertiser_name ILIKE '%star novel%'
               OR advertiser_name ILIKE '%novelmania%'
               OR advertiser_name ILIKE '%royalnovel%'
               OR advertiser_name ILIKE '%webfiction%'
               OR advertiser_name ILIKE '%novelday%'
               OR advertiser_name ILIKE '%dreamy stories%'
               OR advertiser_name ILIKE '%my passion%'
               OR advertiser_name ILIKE '%fiction lover%'
               OR advertiser_name ILIKE '%storydreams%'
               OR advertiser_name ILIKE '%storylover%'
               OR advertiser_name ILIKE '%storyjoy%'
               OR advertiser_name ILIKE '%readstories%'
               OR advertiser_name ILIKE '%storyheart%'
               OR advertiser_name ILIKE '%novelsweet%'
               OR advertiser_name ILIKE '%dreamnovel%'
               OR advertiser_name ILIKE '%fantasy lover%'
               OR advertiser_name ILIKE '%romanceworld%'
               OR advertiser_name ILIKE '%storytale%'
               OR advertiser_name ILIKE '%lovenovel%'
               OR advertiser_name ILIKE '%alpha romance%'
               OR advertiser_name ILIKE '%luna tales%'
               OR advertiser_name ILIKE '%wolfmate%'
               OR advertiser_name ILIKE '%werewolf queen%'
               OR advertiser_name ILIKE '%mate of the alpha%'
               OR advertiser_name ILIKE '%alpha''s mate%'
               OR advertiser_name ILIKE '%dark alpha%'
               OR advertiser_name ILIKE '%eternal alpha%'
               OR advertiser_name ILIKE '%fated mates%'
               OR advertiser_name ILIKE '%twin alphas%'
               OR advertiser_name ILIKE '%alpha protector%'
               OR advertiser_name ILIKE '%soulbound alpha%'
               OR advertiser_name ILIKE '%queen''s alpha%'
               OR advertiser_name ILIKE '%alpha prophecy%'
               OR advertiser_name ILIKE '%alpha dynasty%'
               OR advertiser_name ILIKE '%forbidden romance%'
               OR advertiser_name ILIKE '%billionaire romance%'
               OR advertiser_name ILIKE '%mafia romance%'
               OR advertiser_name ILIKE '%dark romance%'
               OR advertiser_name ILIKE '%royal romance%'
               OR advertiser_name ILIKE '%broken royals%'
               OR advertiser_name ILIKE '%secret heir%'
               OR advertiser_name ILIKE '%forbidden king%'
               OR advertiser_name ILIKE '%hidden identity%'
               OR advertiser_name ILIKE '%royal blood%'
               OR advertiser_name ILIKE '%enchanted kingdom%'
               OR advertiser_name ILIKE '%cursed bloodlines%'
               OR advertiser_name ILIKE '%mystic romance%'
               OR advertiser_name ILIKE '%twisted love%'
               OR advertiser_name ILIKE '%dark royals%'
               OR advertiser_name ILIKE '%lost heirs%'
               OR advertiser_name ILIKE '%heir to the throne%'
               OR advertiser_name ILIKE '%shattered promises%'
               OR advertiser_name ILIKE '%forbidden heirs%'
               OR advertiser_name ILIKE '%hidden legacy%'
               OR advertiser_name ILIKE '%shadow romance%'
               OR advertiser_name ILIKE '%phantom love%'
               OR advertiser_name ILIKE '%royal seduction%'
               OR advertiser_name ILIKE '%vampire romance%'
               OR advertiser_name ILIKE '%shifter romance%'
               OR advertiser_name ILIKE '%paranormal royals%'
               OR advertiser_name ILIKE '%immortal royals%'
               OR advertiser_name ILIKE '%vampire royals%'
               OR advertiser_name ILIKE '%fated royals%'
               OR advertiser_name ILIKE '%phantom heir%'
               OR advertiser_name ILIKE '%forbidden royalty%'
               OR advertiser_name ILIKE '%royal curse%'
               OR advertiser_name ILIKE '%eclipse romance%'
               OR advertiser_name ILIKE '%dynasty romance%'
               OR advertiser_name ILIKE '%empress of love%'
               OR advertiser_name ILIKE '%dark prince%'
               OR advertiser_name ILIKE '%crown & alpha%'
               OR advertiser_name ILIKE '%royal guardian%'
               OR advertiser_name ILIKE '%immortal love%'
               OR advertiser_name ILIKE '%stepmother diaries%'
               OR advertiser_name ILIKE '%revenge fantasy%'
               OR product_name ILIKE '%alpha%'
               OR product_name ILIKE '%luna%'
               OR product_name ILIKE '%werewolf%'
               OR product_name ILIKE '%breed me%'
               OR product_name ILIKE '%daddy alpha%'
               OR product_name ILIKE '%betrayal%'
               OR product_name ILIKE '%revenge%'
               OR product_name ILIKE '%stepmother%'
               OR product_name ILIKE '%stepdad%'
               OR product_name ILIKE '%stepson%'
               OR product_name ILIKE '%fighter%'
               OR product_name ILIKE '%survivor%'
               OR product_name ILIKE '%vampire%'
               OR product_name ILIKE '%billionaire%'
               OR product_name ILIKE '%ceo romance%'
               OR product_name ILIKE '%bodyguard%'
               OR product_name ILIKE '%rejected%'
               OR product_name ILIKE '%romance novel%'
               OR product_name ILIKE '%chapter%'
               OR product_name ILIKE '%book one%'
               OR product_name ILIKE '%episode%'
               OR landing_url LIKE '%dreame.com%'
               OR landing_url LIKE '%goodnovel.com%'
               OR landing_url LIKE '%webnovel.com%'
               OR landing_url LIKE '%ficfun.com%'
               OR landing_url LIKE '%bravonovel.com%'
               OR landing_url LIKE '%play.google.com%'
               OR landing_url LIKE '%apps.apple.com%'
               OR landing_url LIKE '%app.google.com%'
        """))
        print(f"✅ Deleted {spam_count} spam ads")
    
    conn.commit()
    
    # Count remaining ads
    result = conn.execute(text("SELECT COUNT(*) FROM ad_creatives"))
    remaining = result.scalar()
    
    print(f"\n📊 Remaining ads: {remaining}")
    print("🎉 Database cleaned up successfully!")
