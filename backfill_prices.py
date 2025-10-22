#!/usr/bin/env python3
"""
Backfill product_price for ads without prices by loading landing pages and extracting prices.
Reuses the same price extraction logic from the main scraper.
"""

import os
import sys
import asyncio
import re
from sqlmodel import Session, select
from app.db.models import AdCreative
from app.db.repo import engine
from playwright.async_api import async_playwright, Page
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

async def extract_price_from_page(page: Page, url: str, timeout: int = 10) -> str:
    """
    Extract product price from a landing page.
    Reuses the same logic from run_test_scraper.py
    """
    if not url or "facebook.com" in url:
        return None
    
    new_page = None
    try:
        # Create new page
        new_page = await page.context.new_page()
        
        # Block resources for faster loading
        await new_page.route("**/*", lambda route: (
            route.abort() if route.request.resource_type in ["image", "font", "media", "stylesheet"]
            else route.continue_()
        ))
        
        # Navigate to page
        await new_page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        await asyncio.sleep(0.5)  # Brief wait for JS to render prices
        
        # Currency symbol detection
        currency_symbol = "$"
        try:
            meta_currency = await new_page.query_selector("meta[property='og:price:currency']")
            if meta_currency:
                curr = await meta_currency.get_attribute("content")
                symbols = {"USD": "$", "EUR": "€", "GBP": "£", "CAD": "$", "AUD": "$", "JPY": "¥"}
                currency_symbol = symbols.get(curr, "$")
        except:
            pass
        
        # Price selectors (same as main scraper)
        price_selectors = [
            ".product-price",
            ".price",
            "[class*='price']",
            "[data-price]",
            "meta[property='og:price:amount']",
            "meta[property='product:price:amount']",
            "span[class*='Price']",
            "div[class*='price']",
        ]
        
        product_price = None
        
        # Try meta tags first (most reliable)
        for meta_sel in ["meta[property='og:price:amount']", "meta[property='product:price:amount']"]:
            try:
                el = await new_page.query_selector(meta_sel)
                if el:
                    amount = await el.get_attribute("content")
                    if amount:
                        product_price = f"{currency_symbol}{amount}"
                        break
            except:
                continue
        
        # Try Shopify-specific JavaScript
        if not product_price:
            try:
                product_price = await new_page.evaluate(
                    """() => {
                        const price = window.ShopifyAnalytics?.meta?.product?.price;
                        const currency = window.Shopify?.currency?.active || 'USD';
                        const symbols = {USD: '$', EUR: '€', GBP: '£', CAD: '$', AUD: '$', JPY: '¥'};
                        const symbol = symbols[currency] || '$';
                        return price ? `${symbol}${(price / 100).toFixed(2)}` : null;
                    }"""
                )
            except:
                pass
        
        # Try DOM selectors
        if not product_price:
            for sel in price_selectors:
                try:
                    el = await new_page.query_selector(sel)
                    if el:
                        if "data-price" in sel:
                            price_data = await el.get_attribute("data-price")
                            if price_data and re.match(r'^\d+$', price_data):
                                price_cents = int(price_data)
                                product_price = f"{currency_symbol}{price_cents / 100:.2f}"
                                break
                        else:
                            text = (await el.text_content() or "").strip()
                            price_match = re.search(r'([$€£¥]\s*[\d,.]+|\d[\d,.]+\s*[$€£¥])', text)
                            if price_match:
                                product_price = price_match.group(1).strip()
                                break
                except:
                    continue
        
        return product_price
        
    except Exception as e:
        return None
    finally:
        if new_page:
            await new_page.close()


async def process_batch(ads_batch, browser, batch_num, total_batches):
    """Process a batch of ads to extract prices."""
    results = []
    page = await browser.new_page()
    
    for i, (ad_id, landing_url) in enumerate(ads_batch, 1):
        try:
            print(f"[Batch {batch_num}/{total_batches}] [{i}/{len(ads_batch)}] Extracting price from: {landing_url[:60]}...")
            
            price = await extract_price_from_page(page, landing_url)
            
            if price:
                print(f"  ✅ Found price: {price}")
                results.append({"ad_id": ad_id, "price": price, "status": "success"})
            else:
                print(f"  ⚠️  No price found")
                results.append({"ad_id": ad_id, "price": None, "status": "no_price"})
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({"ad_id": ad_id, "price": None, "status": "error"})
    
    await page.close()
    return results


async def backfill_prices_async(limit: int = None, batch_size: int = 50):
    """
    Backfill product_price for ads with missing prices.
    
    Args:
        limit: Max number of ads to process (None = all)
        batch_size: Number of ads per batch
    """
    
    print("=" * 80)
    print("🚀 PRICE BACKFILL - Starting")
    print("=" * 80)
    
    # Get ads with missing prices
    with Session(engine) as session:
        stmt = select(AdCreative.id, AdCreative.landing_url).where(
            (AdCreative.product_price.is_(None)) | (AdCreative.product_price == '')
        ).where(
            AdCreative.landing_url.is_not(None)
        )
        
        # Skip platform domains
        stmt = stmt.where(
            ~AdCreative.landing_url.like('%youtube.com%'),
            ~AdCreative.landing_url.like('%facebook.com%'),
            ~AdCreative.landing_url.like('%instagram.com%'),
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        ads = session.exec(stmt).all()
        
        if not ads:
            print("✅ No ads need price backfill!")
            return
        
        print(f"📊 Found {len(ads)} ads with missing prices")
        print(f"📦 Batch size: {batch_size}")
        print()
        
        # Launch Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Process in batches
            batches = [ads[i:i+batch_size] for i in range(0, len(ads), batch_size)]
            total_batches = len(batches)
            all_results = []
            
            for batch_num, batch in enumerate(batches, 1):
                results = await process_batch(batch, browser, batch_num, total_batches)
                all_results.extend(results)
            
            await browser.close()
        
        # Update database
        print("\n💾 Saving results to database...")
        updated_count = 0
        
        for result in all_results:
            if result["status"] == "success" and result["price"]:
                ad = session.get(AdCreative, result["ad_id"])
                if ad:
                    ad.product_price = result["price"]
                    session.add(ad)
                    updated_count += 1
        
        session.commit()
        
        # Stats
        success_count = sum(1 for r in all_results if r["status"] == "success")
        no_price_count = sum(1 for r in all_results if r["status"] == "no_price")
        error_count = sum(1 for r in all_results if r["status"] == "error")
        
        print("\n" + "=" * 80)
        print("🎯 BACKFILL COMPLETE")
        print("=" * 80)
        print(f"✅ Prices extracted: {success_count} ads")
        print(f"⚠️  No price found: {no_price_count} ads")
        print(f"❌ Errors: {error_count} ads")
        print(f"💾 Database updated: {updated_count} ads")
        print("=" * 80)


def backfill_prices(limit: int = None, batch_size: int = 50):
    """Synchronous wrapper for async backfill."""
    asyncio.run(backfill_prices_async(limit, batch_size))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill product prices for ads")
    parser.add_argument("--limit", type=int, default=None, help="Max ads to process (default: all)")
    parser.add_argument("--batch-size", type=int, default=50, help="Ads per batch (default: 50)")
    
    args = parser.parse_args()
    
    backfill_prices(limit=args.limit, batch_size=args.batch_size)
