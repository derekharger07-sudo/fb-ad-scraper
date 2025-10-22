#!/usr/bin/env python3
"""
🧪 Test Database Connection
Tests connection from your PC to Replit's PostgreSQL database
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_connection():
    print("🧪 Testing database connection...\n")
    
    # Check if DATABASE_URL exists
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL not found!")
        print("\n📝 Did you create a .env file with your DATABASE_URL?")
        print("\nSteps:")
        print("1. In Replit shell, run: echo $DATABASE_URL")
        print("2. Copy the output")
        print("3. Create .env file in this folder")
        print("4. Add: DATABASE_URL=<paste-the-url-here>")
        return False
    
    print(f"✅ DATABASE_URL found")
    print(f"   Host: {db_url.split('@')[1].split('/')[0] if '@' in db_url else 'unknown'}")
    print()
    
    # Try to connect
    try:
        from app.db.repo import get_session
        from app.db.models import AdCreative
        from sqlmodel import select
        
        print("🔌 Attempting connection...")
        
        with get_session() as session:
            # Try a simple query
            result = session.exec(select(AdCreative)).first()
            ad_count = session.exec(select(AdCreative)).all()
            
            print("✅ CONNECTION SUCCESSFUL!\n")
            print(f"📊 Database contains: {len(ad_count)} ads")
            
            if ad_count:
                print(f"\n🎯 Sample ad:")
                sample = ad_count[0]
                print(f"   Product: {sample.product_name or 'N/A'}")
                print(f"   Price: ${sample.product_price or 'N/A'}")
                print(f"   Platform: {sample.platform_type or 'N/A'}")
            
            print("\n🚀 Your local scraper is ready to save ads to Replit!")
            return True
            
    except ImportError as e:
        print(f"❌ ERROR: Missing package - {e}")
        print("\n📦 Install required packages:")
        print("   pip install psycopg2-binary sqlmodel")
        return False
        
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}\n")
        
        if "could not connect" in str(e).lower():
            print("🔍 Possible issues:")
            print("   1. Check DATABASE_URL is correct (no typos)")
            print("   2. Make sure you have internet connection")
            print("   3. Verify the URL ends with ?sslmode=require")
        elif "ssl" in str(e).lower():
            print("🔍 SSL Issue detected:")
            print("   Make sure DATABASE_URL ends with: ?sslmode=require")
        else:
            print("🔍 Unexpected error - check your DATABASE_URL format")
        
        return False

if __name__ == "__main__":
    # Load .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not required, just nice to have
    
    success = test_connection()
    sys.exit(0 if success else 1)
