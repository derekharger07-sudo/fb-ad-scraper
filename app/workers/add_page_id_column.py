"""
Migration script to add page_id column to AdCreative table.
This column stores the Facebook page ID extracted from the advertiser URL.

Run: PYTHONPATH=/home/runner/workspace/product-research-tool-starter python3 app/workers/add_page_id_column.py
"""

import os
import sys
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.repo import engine

def add_page_id_column():
    """Add page_id column to AdCreative table if it doesn't exist."""
    
    print("🔄 Adding page_id column to AdCreative table...")
    
    with engine.connect() as conn:
        # Check if column already exists
        check_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'adcreative' AND column_name = 'page_id'
        """)
        
        try:
            result = conn.execute(check_sql)
            if result.fetchone():
                print("✅ page_id column already exists, skipping migration")
                return
        except Exception:
            # SQLite doesn't have information_schema, try direct approach
            pass
        
        # Add page_id column
        print("  📝 Adding page_id column...")
        try:
            alter_sql = text("ALTER TABLE adcreative ADD COLUMN page_id VARCHAR")
            conn.execute(alter_sql)
            conn.commit()
            print("  ✅ page_id column added successfully")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  ✅ page_id column already exists")
            else:
                print(f"  ⚠️ Error adding column: {e}")
                raise
    
    print("✅ Migration complete!")

if __name__ == "__main__":
    add_page_id_column()
