"""
Debug script to diagnose product name extraction issues.
Grabs a few ads from database and re-tests extraction with detailed logging.
"""
import asyncio
from playwright.async_api import async_playwright
from app.config import CHROMIUM_BIN, DATABASE_URL
from sqlalchemy import create_engine, text
import sys

async def test_extraction(url: str):
    """Test extraction on a single URL with detailed logging"""
    print(f"\n{'='*80}")
    print(f"Testing: {url}")
    print(f"{'='*80}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path=CHROMIUM_BIN)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to page...")
            await page.goto(url, wait_until='domcontentloaded', timeout=10000)
            await page.wait_for_timeout(2000)
            
            print(f"📄 Page loaded, checking common selectors...")
            
            # Test og:title
            og_title = await page.locator('meta[property="og:title"]').get_attribute('content')
            print(f"  og:title = {og_title}")
            
            # Test h1
            h1 = await page.locator('h1').first.text_content() if await page.locator('h1').count() > 0 else None
            print(f"  h1 = {h1}")
            
            # Test title tag
            title = await page.title()
            print(f"  <title> = {title}")
            
            # Test page text (first 200 chars)
            body_text = await page.locator('body').text_content()
            print(f"  body preview = {body_text[:200] if body_text else 'None'}...")
            
            # Check for login/error indicators
            login_keywords = ['sign in', 'log in', 'login', 'password', 'create account']
            found_login = any(kw in body_text.lower() if body_text else '' for kw in login_keywords)
            print(f"  🔐 Login page detected? {found_login}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        await browser.close()

async def main():
    print("🔍 Facebook Ad Product Extraction Debugger")
    print("=" * 80)
    
    # Connect to database
    engine = create_engine(DATABASE_URL)
    
    # Fetch some recent ads with landing URLs but "Unknown Product"
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT landing_url, product_name, account_name 
            FROM adcreative 
            WHERE landing_url IS NOT NULL 
              AND platform = 'facebook'
              AND product_name IN ('Unknown Product', 'Extraction Error')
            ORDER BY last_seen_ts DESC 
            LIMIT 5
        """))
        
        ads = result.fetchall()
        
        if not ads:
            print("✅ No failed extractions found! All ads have product names.")
            sys.exit(0)
        
        print(f"Found {len(ads)} ads with extraction failures:\n")
        
        for i, (url, prod_name, advertiser) in enumerate(ads, 1):
            print(f"{i}. {advertiser}")
            print(f"   URL: {url}")
            print(f"   Current: {prod_name}")
            
            # Test extraction
            await test_extraction(url)
            
            if i < len(ads):
                print(f"\n{'─'*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
