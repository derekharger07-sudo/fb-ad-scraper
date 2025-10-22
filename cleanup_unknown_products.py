"""
Cleanup script to remove ads with Unknown Product or Extraction Error names.
These are failed extractions that clutter the dashboard.
"""
from app.db import Session, engine
from app.db.models import AdCreative
from sqlmodel import select, or_

def cleanup_unknown_products():
    """Remove ads with Unknown Product or Extraction Error product names"""
    
    with Session(engine) as session:
        # Count before cleanup
        total_before = session.query(AdCreative).count()
        print(f"📊 Total ads before cleanup: {total_before}")
        
        # Find ads to delete
        stmt = select(AdCreative).where(
            or_(
                AdCreative.product_name == "Unknown Product",
                AdCreative.product_name == "Extraction Error",
                AdCreative.product_name == None
            )
        )
        ads_to_delete = session.exec(stmt).all()
        
        print(f"🗑️  Found {len(ads_to_delete)} ads with failed product extraction")
        
        if len(ads_to_delete) == 0:
            print("✅ No cleanup needed!")
            return
        
        # Confirm deletion
        response = input(f"\n⚠️  Delete {len(ads_to_delete)} ads? (yes/no): ")
        
        if response.lower() == 'yes':
            for ad in ads_to_delete:
                session.delete(ad)
            session.commit()
            
            # Count after cleanup
            total_after = session.query(AdCreative).count()
            print(f"✅ Cleanup complete!")
            print(f"📊 Total ads after cleanup: {total_after}")
            print(f"🗑️  Removed: {total_before - total_after} ads")
        else:
            print("❌ Cleanup cancelled")

if __name__ == "__main__":
    cleanup_unknown_products()
