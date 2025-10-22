"""
Test the enhanced product name extraction system.

This script demonstrates the improved extraction capabilities.
"""

import asyncio
from playwright.async_api import async_playwright
from app.workers.product_name_extractor import ProductNameExtractor
from app.config import CHROMIUM_BIN

# Test URLs representing various e-commerce platforms and patterns
TEST_URLS = [
    "https://www.shopify.com/",  # Has og:title
    "https://www.etsy.com/",  # Complex meta structure
]

async def test_extraction():
    """Test product name extraction on various URLs."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM_BIN
        )
        page = await browser.new_page()
        
        print("🚀 Testing Enhanced Product Name Extraction\n")
        print("=" * 60)
        
        for url in TEST_URLS:
            print(f"\n📍 Testing: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=8000)
                product_name = await ProductNameExtractor.extract(page, url)
                
                if product_name:
                    print(f"✅ Extracted: '{product_name}'")
                else:
                    print(f"❌ No product name found (might be login/error page)")
            except Exception as e:
                print(f"⚠️ Error: {str(e)[:100]}")
        
        print("\n" + "=" * 60)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_extraction())
