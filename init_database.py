#!/usr/bin/env python3
"""
Database initialization script
Creates the database tables if they don't exist
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.models import SQLModel
from app.db.repo import engine

def init_database():
    """Initialize database tables"""
    print("🔧 Initializing database...")
    
    try:
        # Create all tables
        SQLModel.metadata.create_all(engine)
        print("✅ Database tables created successfully!")
        print("\nTables created:")
        print("  - adcreative (main ads table)")
        print("  - domaintraffic (traffic cache)")
        print("\n🚀 Database is ready! You can now run the scraper.")
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
