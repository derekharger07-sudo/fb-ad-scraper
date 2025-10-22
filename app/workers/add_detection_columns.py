"""
Migration script to add two-layer detection columns to existing AdCreative table.

Adds:
- fb_delivery_status: Facebook's delivery status (ACTIVE/INACTIVE)
- fb_delivery_stop_time: When Facebook says ad stopped
- detection_method: How we determined the status
"""

from sqlalchemy import text
from app.db.repo import get_session


def add_detection_columns():
    """Add two-layer detection columns to AdCreative table."""
    with get_session() as session:
        print("🔄 Adding two-layer detection columns to AdCreative table...")
        
        # Check if columns already exist
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'adcreative' 
            AND column_name IN ('fb_delivery_status', 'fb_delivery_stop_time', 'detection_method')
        """)
        existing = session.exec(check_query).fetchall()
        existing_cols = {row[0] for row in existing}
        
        # Add fb_delivery_status column if not exists
        if 'fb_delivery_status' not in existing_cols:
            print("  📝 Adding fb_delivery_status column...")
            session.exec(text("""
                ALTER TABLE adcreative 
                ADD COLUMN fb_delivery_status VARCHAR
            """))
            print("  ✅ fb_delivery_status column added")
        else:
            print("  ⏭️ fb_delivery_status column already exists")
        
        # Add fb_delivery_stop_time column if not exists
        if 'fb_delivery_stop_time' not in existing_cols:
            print("  📝 Adding fb_delivery_stop_time column...")
            session.exec(text("""
                ALTER TABLE adcreative 
                ADD COLUMN fb_delivery_stop_time DATE
            """))
            print("  ✅ fb_delivery_stop_time column added")
        else:
            print("  ⏭️ fb_delivery_stop_time column already exists")
        
        # Add detection_method column if not exists
        if 'detection_method' not in existing_cols:
            print("  📝 Adding detection_method column...")
            session.exec(text("""
                ALTER TABLE adcreative 
                ADD COLUMN detection_method VARCHAR DEFAULT '3_miss_detection'
            """))
            print("  ✅ detection_method column added")
        else:
            print("  ⏭️ detection_method column already exists")
        
        session.commit()
        print("✅ Migration complete! Two-layer detection columns added.")
        
        # Show current schema
        count_query = text("SELECT COUNT(*) FROM adcreative")
        count = session.exec(count_query).one()
        print(f"\n📊 Total ads in database: {count}")


if __name__ == "__main__":
    add_detection_columns()
