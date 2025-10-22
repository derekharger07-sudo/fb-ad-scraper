import asyncio
import json
import random
import re
import hashlib
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from dateutil import parser as date_parser
from urllib.parse import urlparse  # 🆕 for domain extraction
from playwright.async_api import async_playwright, Page
from app.db.repo import save_ads
from app.scoring.ad_scoring import score_ad
from app.config import CHROMIUM_BIN, SEARCH_QUERIES, COUNTRIES
from app.db import Session, engine
from app.db.models import AdCreative
from sqlmodel import select, func
from app.workers.spyfu_api import get_seo_clicks  # SpyFu for traffic estimation
from app.workers.traffic_estimator import estimate_monthly_visits, get_tier_from_visits
from app.workers.platform_detector import detect_platform_from_html_only
import requests

# ---------- ADVERTISER PAGE SCRAPING ----------
async def extract_page_id_from_html(page: Page, advertiser_url: str) -> str | None:
    """
    Extract NUMERIC page ID from Facebook page HTML source.
    Searches ONLY for "associated_page_id" in the page source.
    
    Args:
        page: Playwright page instance
        advertiser_url: Facebook page URL (e.g., https://www.facebook.com/nike)
    
    Returns:
        Numeric page ID (e.g., "112282648352877") or None
    """
    if not advertiser_url:
        return None
    
    try:
        # Navigate to the advertiser's Facebook page (fast timeout to avoid long pauses)
        await page.goto(advertiser_url, wait_until='domcontentloaded', timeout=8000)
        await page.wait_for_timeout(1000)  # Quick wait - page ID is in initial HTML
        
        # Get the HTML source
        html_content = await page.content()
        
        # Try multiple regex patterns to find page_id (Facebook changes formats)
        patterns = [
            r'"associated_page_id"\s*:\s*"(\d+)"',  # "associated_page_id":"123456"
            r'"associated_page_id"\s*:\s*(\d+)',     # "associated_page_id":123456 (no quotes)
            r'associated_page_id["\s:]+(\d+)',       # Flexible spacing/quotes
            r'"pageID"\s*:\s*"(\d+)"',               # Alternative: "pageID":"123456"
            r'"page_id"\s*:\s*"(\d+)"',              # Alternative: "page_id":"123456"
            r'page_id=(\d+)',                        # URL param: page_id=123456
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                page_id = match.group(1)
                print(f"  ✅ Found page_id: {page_id} (pattern: {pattern[:30]}...)")
                return page_id
        
        print(f"  ⚠️ Could not find page_id in HTML for {advertiser_url}")
        print(f"  💡 Tip: View source and search for 'page' or 'associated' to debug")
        return None
        
    except Exception as e:
        print(f"  ❌ Error extracting page_id from {advertiser_url}: {e}")
        return None

async def scrape_advertiser_all_ads(page: Page, page_id: str, advertiser_name: str, original_ad: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scrape all ads from a specific advertiser's page.
    
    Args:
        page: Playwright page instance
        page_id: Facebook page ID of the advertiser
        advertiser_name: Name of the advertiser (for logging)
        original_ad: The original ad that triggered this advertiser scrape (for metadata)
        
    Returns:
        List of scraped ads from this advertiser
    """
    print(f"\n🎯 Scraping ALL ads from advertiser: {advertiser_name} (page_id: {page_id})")
    
    advertiser_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&is_targeted_country=false&media_type=all&search_type=page&view_all_page_id={page_id}"
    
    try:
        # Navigate to advertiser's ad library page
        await page.goto(advertiser_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)  # Initial wait
        
        # Accept cookies if present (might block content)
        await accept_cookies_if_present(page)
        
        await page.wait_for_timeout(2000)  # Wait after cookie acceptance
        
        # Wait for ads to appear (look for Facebook CDN images)
        try:
            await page.wait_for_selector('img[src*="scontent"]', timeout=10000)
            print(f"  ✅ Ads loaded for {advertiser_name}")
        except:
            print(f"  ⚠️ No ad images found for {advertiser_name}, trying to extract anyway...")
        
        advertiser_ads = []
        scroll_attempts = 0
        max_scrolls = 10  # Limit scrolling to prevent infinite loops
        
        while scroll_attempts < max_scrolls:
            # Extract ads from current view (using existing extract_ads_from_page function)
            batch = await extract_ads_from_page(page)
            
            if not batch:
                if scroll_attempts == 0:
                    print(f"  ⚠️ No ads found on first try for {advertiser_name} - page might not have loaded")
                else:
                    print(f"  ⏭️ No more ads found for {advertiser_name}")
                break
            
            # Add metadata to track these came from advertiser scraping
            for ad in batch:
                ad["search_query"] = original_ad.get("search_query", "advertiser_scrape")
                ad["country"] = original_ad.get("country", "US")
                ad["from_advertiser_scrape"] = True  # Flag to identify these ads
            
            advertiser_ads.extend(batch)
            print(f"  📥 Found {len(batch)} ads (total: {len(advertiser_ads)})")
            
            # 🆕 Check if we've hit the max advertiser limit
            if len(advertiser_ads) >= MAX_ADVERTISER_ADS:
                print(f"  🎯 Reached limit of {MAX_ADVERTISER_ADS} ads for {advertiser_name}, stopping...")
                break
            
            # If we found ads, keep scrolling for more
            # Scroll to load more
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)  # Increased wait time after scroll
            scroll_attempts += 1
        
        print(f"  ✅ Scraped {len(advertiser_ads)} total ads from {advertiser_name}")
        return advertiser_ads
        
    except Exception as e:
        print(f"  ❌ Error scraping advertiser {advertiser_name}: {e}")
        return []

# ---------- settings ----------
MAX_TEST_ADS = 10000  # High limit - scrape until no more ads found
SCRAPE_ADVERTISER_ADS = True  # 🆕 Automatically scrapes all ads from each advertiser (set to False to disable)
MAX_ADVERTISER_ADS = 200  # 🆕 Maximum ads to collect per advertiser (prevents spending too much time on one advertiser)

# ---------- redirect resolver ----------
def resolve_final_domain(url: str, timeout: int = 5) -> str:
    """
    Follow redirects to get the final destination domain.
    Returns the final domain without 'www.' prefix.
    Falls back to original domain if redirect fails.
    """
    try:
        # Extract original domain as fallback
        from urllib.parse import urlparse
        original_domain = urlparse(url).netloc.replace("www.", "")
        
        # Follow redirects with HEAD request (faster than GET)
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        final_url = response.url
        final_domain = urlparse(final_url).netloc.replace("www.", "")
        
        return final_domain if final_domain else original_domain
    except Exception as e:
        # If redirect fails, return original domain
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")

# ---------- creative hash ----------
def normalize_media_url(url: str) -> str:
    """Normalize video/image URLs by removing tracking parameters."""
    if not url:
        return ""
    base = url.split('?')[0] if '?' in url else url
    return base

def creative_fingerprint(ad: Dict[str, Any]) -> Optional[str]:
    """Generate a stable hash for a creative using its video/image/caption content."""
    video_url = normalize_media_url(ad.get("video_url") or "")
    image_url = normalize_media_url(ad.get("image_url") or "")
    key = (
        video_url +
        image_url +
        (ad.get("caption") or "")
    ).strip()
    if not key:
        return None
    return hashlib.md5(key.encode("utf-8")).hexdigest()

# ---------- date parsing ----------
def parse_ad_start_date(date_str: str) -> tuple[Optional[date], int]:
    """Parse 'Started running on [date]' and return (date object, days_running)."""
    if not date_str:
        return None, 0
    try:
        start_date = date_parser.parse(date_str).date()
        days_running = (date.today() - start_date).days
        return start_date, days_running  # Return date object, not ISO string
    except:
        return None, 0

# ---------- helpers ----------
async def click_if_visible(page: Page, selector: str) -> bool:
    """Click an element if it is visible."""
    try:
        el = page.locator(selector).first
        if await el.is_visible(timeout=1000):
            await el.click()
            return True
    except:
        pass
    return False

async def accept_cookies_if_present(page: Page):
    """Accept cookies if a cookie consent button is present."""
    texts = [
        "Allow all cookies", "Accept all", "Accept All",
        "Only Allow Essential", "Allow essential and optional cookies"
    ]
    for t in texts:
        try:
            btn = page.get_by_role("button", name=re.compile(t, re.I))
            if await btn.is_visible(timeout=1000):
                await btn.click()
                await page.wait_for_timeout(1200)
                break
        except:
            pass

async def ensure_all_ads_tab(page: Page):
    """Ensure the 'All ads' tab is selected."""
    try:
        chip = page.get_by_role("button", name=re.compile(r"\bAll ads\b", re.I))
        if await chip.is_visible(timeout=2000):
            await chip.click()
            await page.wait_for_timeout(1200)
    except:
        pass

async def smart_scroll(page: Page):
    """Scroll the page to load more content."""
    js = """
    () => {
      const main = document.querySelector('div[role="main"]');
      if (main) { main.scrollBy(0, main.clientHeight * 0.9); }
      window.scrollBy(0, Math.floor(window.innerHeight * 0.9));
    }
    """
    await page.evaluate(js)

async def click_all_see_more(page: Page) -> int:
    """Click all 'See More Ads' or 'See more' buttons and return the count of clicks."""
    clicked = 0
    try:
        buttons = page.locator("div[role='button']:has-text('See More Ads')")
        count = await buttons.count()
        for i in range(count):
            try:
                btn = buttons.nth(i)
                if await btn.is_visible():
                    await btn.click()
                    clicked += 1
                    await page.wait_for_timeout(1200)
            except:
                pass

        more = page.locator("div[role='button']:has-text('See more')")
        mcount = await more.count()
        for i in range(mcount):
            try:
                btn = more.nth(i)
                if await btn.is_visible():
                    await btn.click()
                    clicked += 1
                    await page.wait_for_timeout(1200)
            except:
                pass
    except:
        pass
    return clicked

# ---------- product name and price extraction ----------
async def extract_product_name_from_url(page: Page, url: str) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Extract product name, HTML, price, and page type from a given URL.
    
    Optimized with:
    - Configurable 20s timeout (PAGE_TIMEOUT env var)
    - Resource blocking (images, fonts, media)
    - Automatic retry on failure
    - DOMContentLoaded for faster loading
    
    Returns:
        Tuple of (product_name, html_content, product_price, page_type)
    """
    if not url or "facebook.com" in url:
        return None, None, None, None

    from app.config import PAGE_TIMEOUT
    import time
    import re
    
    new_page = None
    max_attempts = 2
    start_time = time.time()
    
    for attempt in range(1, max_attempts + 1):
        try:
            start_time = time.time()
            
            # Create new page with resource blocking
            new_page = await page.context.new_page()
            
            # 🚀 Block heavy resources to speed up loading
            await new_page.route("**/*", lambda route: (
                route.abort() if route.request.resource_type in ["image", "font", "media", "stylesheet"]
                else route.continue_()
            ))
            
            # Navigate with DOMContentLoaded (faster than 'load')
            await new_page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            
            # Wait 1 second for JavaScript to render dynamic content (for survey detection)
            await new_page.wait_for_timeout(1000)
            
            elapsed = time.time() - start_time
            if attempt > 1:
                print(f"  ✓ Loaded in {elapsed:.1f}s (retry {attempt}/{max_attempts})")
            
            # Get HTML content for platform detection
            html_content = await new_page.content()

            # 🚀 Enhanced Product Name Extraction
            from app.workers.product_name_extractor import ProductNameExtractor
            product_name = await ProductNameExtractor.extract(new_page, url)

            # Extract product price
            detected_currency = "USD"
            currency_symbol = "$"
            try:
                # Check meta tags
                currency_meta = await new_page.query_selector("meta[property='og:price:currency'], meta[property='product:price:currency']")
                if currency_meta:
                    detected_currency = await currency_meta.get_attribute("content")
                else:
                    # Check Shopify
                    detected_currency = await new_page.evaluate("() => window.Shopify?.currency?.active || 'USD'")
            except:
                pass
            
            # Map currency to symbol
            currency_symbols = {"USD": "$", "EUR": "€", "GBP": "£", "CAD": "$", "AUD": "$", "JPY": "¥", "CHF": "CHF"}
            currency_symbol = currency_symbols.get(detected_currency or "USD", "$")
            
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
                                # Assume cents for integer values (Shopify standard)
                                if price_data and re.match(r'^\d+$', price_data):
                                    price_cents = int(price_data)
                                    product_price = f"{currency_symbol}{price_cents / 100:.2f}"
                                    break
                            else:
                                text = (await el.text_content() or "").strip()
                                # Look for price with currency symbol (leading or trailing)
                                # Matches: $59, $59.99, $1,099.00, €45, £23.50, 59,99€
                                price_match = re.search(r'([$€£¥]\s*[\d,.]+|\d[\d,.]+\s*[$€£¥])', text)
                                if price_match:
                                    product_price = price_match.group(1).strip()
                                    break
                                # Try without currency symbol (fallback with detected currency)
                                price_match = re.search(r'(\d{1,3}(?:[,.\s]\d{3})*(?:[.,]\d{2})?)', text)
                                if price_match and len(text) < 50:
                                    product_price = f"{currency_symbol}{price_match.group(1)}"
                                    break
                    except:
                        continue

            # Step 2: Detect survey/quiz pages AFTER product extraction (doesn't interfere with extraction)
            from app.workers.product_name_extractor import ProductNameExtractor
            is_survey = ProductNameExtractor.detect_survey_page(html_content, url)
            page_type = "survey_page" if is_survey else None
            
            # Step 3: If NOT a survey page, check if it's a product page
            if page_type != "survey_page":
                is_product_page = ProductNameExtractor.detect_product_page(html_content)
                if is_product_page:
                    page_type = "product_page"
                else:
                    # Default to product_page if no strong signals (backward compatible)
                    page_type = "product_page"
            
            await new_page.close()
            return product_name, html_content, product_price, page_type

        except Exception as e:
            elapsed = time.time() - start_time
            
            if new_page:
                await new_page.close()
                new_page = None
            
            # Retry on first failure
            if attempt < max_attempts:
                print(f"  ⚠️ Extraction error (attempt {attempt}/{max_attempts}, {elapsed:.1f}s): {str(e)[:50]}")
                await asyncio.sleep(1.5)  # Brief pause before retry
                continue
            else:
                # Final failure after all retries
                print(f"  ❌ Extraction failed after {max_attempts} attempts ({elapsed:.1f}s)")
                return None, None, None, None
    
    return None, None, None, None

# ---------- extraction ----------
async def extract_ads_from_page(page: Page) -> List[Dict[str, Any]]:
    """Extract ad data from the current page."""
    extract_js = """
    () => {
        const images = Array.from(document.querySelectorAll('img[src*="scontent"]'));
        const ads = [];
        const seenAds = new Set();

        images.forEach(img => {
            let current = img;
            let depth = 0;
            let adCard = null;

            while (current && depth < 15) {
                const text = current.textContent?.trim() || '';
                if (text.includes('Sponsored') && text.length > 50) {
                    adCard = current;
                    break;
                }
                current = current.parentElement;
                depth++;
            }

            if (adCard && !seenAds.has(adCard)) {
                seenAds.add(adCard);
                
                // Skip ads where media failed to load
                const adText = adCard.textContent || '';
                if (adText.includes("Sorry, we're having trouble playing this video") || 
                    adText.includes("having trouble playing this video")) {
                    console.log('⏭️ Skipping ad with failed media');
                    return; // Skip this ad
                }
                
                const data = {};

                // Find advertiser header container (contains profile pic)
                let advertiserHeaderContainer = null;
                const advertiserLink = adCard.querySelector('a[href*="facebook.com/"]');
                if (advertiserLink) {
                    data.advertiser_name = advertiserLink.textContent?.trim();
                    data.advertiser_url = adCard.querySelector('a[href*="facebook.com/"]').getAttribute('href');
                    
                    // Extract advertiser profile picture (favicon) - MULTIPLE STRATEGIES
                    let profileImg = null;
                    let faviconUrl = null;
                    
                    // Strategy 1: Look for img within the advertiser link
                    profileImg = advertiserLink.querySelector('img');
                    
                    // Strategy 2: Look in parent/sibling containers
                    if (!profileImg) {
                        const container = advertiserLink.closest('div');
                        if (container) {
                            // Try to find any img in the container
                            profileImg = container.querySelector('img');
                        }
                    }
                    
                    // Strategy 3: Look for the first small image near the advertiser name (likely profile pic)
                    if (!profileImg) {
                        const allImagesNearAdvertiser = Array.from(adCard.querySelectorAll('img'));
                        // Profile pics are typically small and appear early in the DOM
                        profileImg = allImagesNearAdvertiser.find(img => {
                            const rect = img.getBoundingClientRect();
                            const src = img.getAttribute('src') || '';
                            // Profile pics are usually round/small (under 100px) and contain scontent (Facebook CDN)
                            return (rect.width > 0 && rect.width <= 100 && src.includes('scontent'));
                        });
                    }
                    
                    // Extract URL from various possible attributes
                    if (profileImg) {
                        faviconUrl = profileImg.getAttribute('src') || 
                                    profileImg.getAttribute('data-src') || 
                                    profileImg.currentSrc || 
                                    null;
                        
                        if (faviconUrl) {
                            data.advertiser_favicon = faviconUrl;
                            console.log('✅ Favicon extracted:', faviconUrl.substring(0, 60) + '...');
                        } else {
                            console.log('⚠️ Profile img found but no src attribute');
                        }
                    } else {
                        console.log('⚠️ No profile img found for:', data.advertiser_name);
                    }
                    
                    advertiserHeaderContainer = advertiserLink.closest('div');
                }

                // STEP 1: Extract VIDEO (takes priority)
                const video = adCard.querySelector('video');
                if (video) {
                    const videoSrc = video.getAttribute('src') || video.querySelector('source')?.getAttribute('src');
                    if (videoSrc) {
                        data.video_url = videoSrc;
                        data.poster_url = video.getAttribute('poster');
                    }
                }

                // STEP 2: If NO video, extract IMAGE
                if (!data.video_url) {
                    const allImages = Array.from(adCard.querySelectorAll('img[src]'));
                    
                    // Filter to find ad creative images (not profile pics, icons, etc.)
                    const adCreativeImages = allImages.filter(img => {
                        const src = img.getAttribute('src') || '';
                        
                        // EXCLUDE: Images in advertiser header (profile pictures)
                        if (advertiserHeaderContainer && advertiserHeaderContainer.contains(img)) {
                            return false;
                        }
                        
                        // EXCLUDE: Small profile pics (60x60 or s60x60 in URL)
                        if (src.includes('s60x60') || src.includes('_s.')) {
                            return false;
                        }
                        
                        // EXCLUDE: Explicitly marked as favicon/logo/profile/icon
                        if (src.includes('favicon') || src.includes('logo') || src.includes('profile') || src.includes('icon')) {
                            return false;
                        }
                        
                        // EXCLUDE: Tiny images under 100x100
                        const width = img.naturalWidth || parseInt(img.getAttribute('width')) || 999;
                        const height = img.naturalHeight || parseInt(img.getAttribute('height')) || 999;
                        if (width < 100 || height < 100) {
                            return false;
                        }
                        
                        // INCLUDE: Facebook CDN images with proper extensions
                        if (src.includes('fbcdn.net') && (src.includes('.jpg') || src.includes('.png') || src.includes('.webp'))) {
                            return true;
                        }
                        
                        return false;
                    });
                    
                    if (adCreativeImages.length > 0) {
                        data.image_url = adCreativeImages[0].getAttribute('src');
                    }
                }

                const fullText = adCard.textContent || '';
                const lines = fullText.split('\\n').map(l => l.trim()).filter(l => l);

                let containerToSearch = adCard.parentElement;
                let searchDepth = 0;
                while (containerToSearch && searchDepth < 5) {
                    const containerText = containerToSearch.textContent || '';
                    const startedMatch = containerText.match(/Started running on\\s+([A-Za-z]+\\s+\\d{1,2},\\s+\\d{4})/i);
                    if (startedMatch) {
                        data.started_running_on = startedMatch[1].trim();
                        const fullMatch = containerText.match(/Started running on[^\\n·]+(·[^\\n]+)?/i);
                        if (fullMatch) {
                            data.raw_runtime_text = fullMatch[0].trim();
                        }
                        
                        // 🔄 Two-Layer Detection: Extract Facebook's delivery status
                        const stoppedMatch = containerText.match(/(Stopped|Ended)\\s+running\\s+on\\s+([A-Za-z]+\\s+\\d{1,2},\\s+\\d{4})/i);
                        if (stoppedMatch) {
                            data.fb_delivery_stop_time = stoppedMatch[2].trim();
                            data.fb_delivery_status = 'INACTIVE';
                        } else if (containerText.match(/\\bActive\\b|\\bCurrently\\s+running\\b/i)) {
                            data.fb_delivery_status = 'ACTIVE';
                        }
                        
                        break;
                    }
                    containerToSearch = containerToSearch.parentElement;
                    searchDepth++;
                }

                const caption = lines.filter(l => 
                    l !== 'Sponsored' && l !== data.advertiser_name && l.length > 10 && !l.startsWith('Started running on')
                ).join(' ').substring(0, 500);
                if (caption) data.caption = caption;

                let ctaElement = adCard.querySelector('div[role="button"], a[role="button"], button');
                if (ctaElement) {
                    const ctaText = ctaElement.textContent?.trim() || "";
                    if (ctaText && ctaText.length < 50 && /shop|learn|get|buy|download|sign|subscribe|watch|apply|book/i.test(ctaText)) {
                        data.cta_text = ctaText;
                    }
                }

                const ctaLinks = Array.from(adCard.querySelectorAll('a[href^="http"]')).filter(a => {
                    const href = a.getAttribute('href') || '';
                    if (href.includes('.facebook.com/') && href.includes('.php?u=')) {
                        return true;
                    }
                    return !href.includes('facebook.com/ads/library') &&
                           !href.includes('facebook.com/profile') &&
                           !href.includes('facebook.com/pages/') &&
                           !href.includes('facebook.com/');
                });
                if (ctaLinks.length > 0) {
                    let rawUrl = ctaLinks[0].getAttribute('href') || '';
                    if (rawUrl.includes('.facebook.com/') && rawUrl.includes('.php?u=')) {
                        const match = rawUrl.match(/u=([^&]+)/);
                        if (match && match[1]) {
                            rawUrl = decodeURIComponent(match[1]);
                        }
                    }
                    rawUrl = rawUrl.replace(/(\?|&)fbclid=[^&]+/g, '').replace(/(\?|&)utm_[^&]+/g, '');
                    data.landing_url = rawUrl;
                    if (!data.cta_text && ctaLinks[0].textContent) {
                        const linkText = ctaLinks[0].textContent.trim();
                        if (linkText && linkText.length < 50) data.cta_text = linkText;
                    }
                }

                if (data.caption || data.image_url || data.video_url || data.landing_url) {
                    ads.push(data);
                }
            }
        });
        return ads;
    }
    """
    ads = await page.evaluate(extract_js)
    return ads

# ---------- main test runner ----------
async def run_test_scrape(keyword: Optional[str] = None, limit: Optional[int] = None, country: str = "US"):
    """
    Run the test scrape for ads.
    
    Args:
        keyword: Single keyword to search (if None, uses SEARCH_QUERIES from config)
        limit: Max ads to scrape (if None, uses MAX_TEST_ADS)
        country: Country code (default: US)
    
    Returns:
        List of scraped ads
    """
    # Determine queries and max ads
    queries = [keyword] if keyword else SEARCH_QUERIES
    countries = [country] if keyword else COUNTRIES
    max_ads = limit if limit is not None else MAX_TEST_ADS
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM_BIN,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials'
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 850},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        total_ads = 0
        domain_cache = {}  # Cache for SpyFu API calls
        scraped_advertisers = set()  # Track already-scraped advertiser page_ids
        all_results = []  # Collect all ads to return
        print(f"🚀 Running TEST scrape (max {max_ads} ads)")

        for query in queries:
            for ctry in countries:
                if total_ads >= max_ads:
                    break

                url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={ctry}&q={query}"
                print(f"\n🌍 Scraping {query!r} in {ctry} → {url}")
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)

                await accept_cookies_if_present(page)
                await ensure_all_ads_tab(page)

                try:
                    await page.wait_for_selector('img[src*="scontent"]', timeout=15000)
                    print("✅ Images loaded, ads should be visible")
                except:
                    print("⚠️ No images found, continuing...")

                results: List[Dict[str, Any]] = []
                scroll_attempts = 0
                max_scrolls = 500  # Increased to allow more scrolling
                new_count = 0
                consecutive_filtered = 0  # Track consecutive spam-filtered ads
                MAX_CONSECUTIVE_FILTERED = 100  # Skip keyword after 100 consecutive filtered ads

                while total_ads < max_ads and scroll_attempts < max_scrolls:
                    batch = await extract_ads_from_page(page)

                    if scroll_attempts > 0 and len(batch) == 0:
                        print(f"⏭️ No new ads found, moving to next query")
                        break
                    
                    # Check if too many consecutive ads have been filtered
                    if consecutive_filtered >= MAX_CONSECUTIVE_FILTERED:
                        print(f"⏭️ Skipping keyword '{query}' - {MAX_CONSECUTIVE_FILTERED} consecutive spam ads detected")
                        break

                    for ad in batch:
                        if total_ads >= max_ads:
                            break

                        ad["search_query"] = query
                        ad["country"] = ctry

                        if ad.get("started_running_on"):
                            start_date, days_running = parse_ad_start_date(ad["started_running_on"])
                            ad["started_running_on"] = start_date
                            ad["days_running"] = days_running

                        ad["creative_hash"] = creative_fingerprint(ad)

                        # Initialize defaults
                        ad["product_name"] = None
                        ad["product_price"] = None
                        ad["platform_type"] = None
                        ad["page_type"] = "product_page"
                        ad["is_spark_ad"] = False
                        landing_html = None
                        
                        if not ad.get("landing_url"):
                            print(f"⏭️ Skipping ad - no landing URL")
                            consecutive_filtered += 1
                            continue
                        
                        landing_url = ad["landing_url"]
                        landing_url_lower = landing_url.lower()
                        
                        # STEP 1: Detect Instagram Spark Ads FIRST (before product extraction)
                        if "instagram.com" in landing_url_lower:
                            ad["is_spark_ad"] = True
                            ad["platform_type"] = "instagram"
                            
                            # Extract Instagram username from URL
                            try:
                                parsed = urlparse(landing_url)
                                path_parts = [p for p in parsed.path.split('/') if p]
                                if path_parts:
                                    # Get first path segment (username)
                                    instagram_username = path_parts[0]
                                    # Remove trailing underscore if present
                                    instagram_username = instagram_username.rstrip('_')
                                    ad["product_name"] = instagram_username
                                    print(f"📸 Instagram Spark Ad - Username: @{instagram_username}")
                                else:
                                    ad["product_name"] = "Instagram Profile"
                                    print(f"📸 Instagram Spark Ad - Could not extract username")
                            except Exception as e:
                                print(f"⚠️ Instagram username extraction failed: {e}")
                                ad["product_name"] = "Instagram Profile"
                        
                        # STEP 2: For non-Spark Ads, extract product info normally
                        else:
                            # ⚡ FAST MODE: Extract from URL only (no page loading)
                            from app.workers.url_product_extractor import extract_product_name_from_url_path
                            url_extracted_name = extract_product_name_from_url_path(landing_url)
                            ad["product_name"] = url_extracted_name
                            print(f"⚡ Product (URL-only): {url_extracted_name}")
                            
                            # Skip price, platform, and survey detection (requires page load)
                            ad["product_price"] = None
                            ad["page_type"] = "product_page"  # Default assumption
                            ad["platform_type"] = None

                        # ========== SPAM FILTER: Skip low-quality/irrelevant ads ==========
                        
                        # FILTER 1: Skip ads with Facebook landing pages (e.g., fitness classes, local services)
                        landing_url_lower = ad.get("landing_url", "").lower()
                        if "facebook.com" in landing_url_lower or "fb.me" in landing_url_lower:
                            print(f"🚫 Facebook landing page detected (advertiser: {ad.get('advertiser_name')}) - skipping")
                            consecutive_filtered += 1
                            continue
                        
                        # FILTER 2: Skip romance/fantasy novel ads
                        spam_advertisers = [
                            # Major novel platforms
                            "dreame", "worth reading", "novels lover", "romance stories", 
                            "happyday", "myno", "novelread", "webnovel", "goodnovel",
                            "readink", "ficfun", "anystories", "moboreader", "bravonovel",
                            "inkitt", "wattpad", "sofanovel", "novelstar", "star novel",
                            "novelmania", "royalnovel", "webfiction", "novelday", "forfun-100",
                            # Generic story apps
                            "dreamy stories", "my passion", "fiction lover", "storydreams",
                            "storylover", "storyjoy", "readstories", "storyheart",
                            "novelsweet", "dreamnovel", "fantasy lover", "romanceworld",
                            "storytale", "lovenovel",
                            # Alpha/werewolf themed
                            "alpha romance", "luna tales", "wolfmate stories", "alpha's mate",
                            "werewolf queen", "mate of the alpha", "the alpha's secret",
                            "dark alpha series", "eternal alpha", "fated mates", "twin alphas",
                            "alpha protector", "alpha's obsession", "alpha's claim",
                            "soulbound alpha", "queen's alpha", "the alpha prophecy",
                            "alpha's gambit", "alpha dynasty", "alpha's favor", "alpha's heir",
                            "alpha's bond", "alpha's curse", "alpha's revenge", "alpha's betrayal",
                            # Royal/billionaire themed
                            "forbidden romance", "billionaire romance", "mafia romance",
                            "dark romance realm", "royal romance tales", "broken royals",
                            "secret heir romance", "forbidden king", "hidden identity stories",
                            "royal blood romance", "enchanted kingdom", "cursed bloodlines",
                            "mystic romance", "twisted love", "witches & royals", "dark royals",
                            "lost heirs", "heir to the throne", "shattered promises",
                            "forbidden heirs", "hidden legacy", "shadow romance", "phantom love",
                            "royal seduction", "immortal royals", "vampire royals",
                            "royals & wolves", "fated royals", "phantom heir",
                            "forbidden royalty", "royal curse", "eclipse romance",
                            "dynasty romance", "empress of love", "dark prince romance",
                            "crown & alpha", "royal guardian",
                            # Vampire/paranormal themed
                            "vampire romance", "shifter romance", "paranormal royals",
                            "immortal love", "stepmother diaries", "revenge fantasy",
                            # Dating/video chat spam
                            "tp 1014 17"  # Video chat spam app
                        ]
                        spam_keywords = [
                            "alpha", "luna", "werewolf", "daddy", "breed", "betrayal", 
                            "revenge", "stepmother", "heartbreak", "prescription",
                            "fighter", "survivor", "stolen", "forbidden", "mate",
                            "pack", "omega", "shifter", "billionaire romance", "mafia",
                            "vampire", "alpha male", "stepdad", "stepson", "billionaire",
                            "ceo romance", "bodyguard", "rejected", "romance novel",
                            "story", "chapter", "book one", "episode", "novel app",
                            "wolf", "fantasy", "novel", "dreame", "goodnovel", "webnovel",
                            "royals", "heir", "crown", "throne", "prophecy", "curse",
                            "immortal", "fated", "soulbound", "dark romance", "paranormal",
                            "love stories",  # Romance story ads
                            "reader"  # Novel reader apps (LeReader, MoboReader, etc.)
                        ]
                        spam_domains = [
                            "dreame.com", "goodnovel.com", "webnovel.com", "ficfun.com",
                            "moboreader.com", "bravonovel.com", "anystories.com",
                            "play.google.com", "apps.apple.com", "app.google.com",
                            "itunes.apple.com",  # Apple App Store (legacy URLs)
                            "walmart.com", "temu.com",  # Large marketplace filters
                            "app.adjust.com",  # Tracking/spam redirect URLs
                            "apple.com/us/app/",  # Apple App Store URL patterns
                            "/id15",  # Apple app store IDs (e.g., /id1564066347)
                            "/id16",  # Apple app store IDs
                            "mt=8",   # Apple App Store parameter
                        ]
                        
                        # Check advertiser name - check both advertiser list AND keywords
                        advertiser_lower = ad.get("advertiser_name", "").lower()
                        if any(spam in advertiser_lower for spam in spam_advertisers):
                            print(f"🚫 Spam detected (advertiser: {ad.get('advertiser_name')}) - skipping")
                            consecutive_filtered += 1
                            continue
                        # Also check if advertiser name contains spam keywords
                        if any(keyword in advertiser_lower for keyword in spam_keywords):
                            print(f"🚫 Spam keyword in advertiser name: {ad.get('advertiser_name')} - skipping")
                            consecutive_filtered += 1
                            continue
                        
                        # Check product name
                        product_lower = ad.get("product_name", "").lower()
                        if any(keyword in product_lower for keyword in spam_keywords):
                            print(f"🚫 Spam detected (product: {ad.get('product_name')}) - skipping")
                            consecutive_filtered += 1
                            continue
                        
                        # Check caption content - now checks for ANY spam keyword or advertiser name
                        caption_lower = ad.get("caption", "").lower()
                        
                        # Check for spam keywords in caption
                        caption_spam_keywords = [kw for kw in spam_keywords if kw in caption_lower]
                        if caption_spam_keywords:
                            print(f"🚫 Spam detected in caption (found: {', '.join(caption_spam_keywords[:3])}) - skipping")
                            consecutive_filtered += 1
                            continue
                        
                        # Also check if caption contains any spam advertiser names
                        caption_spam_advertisers = [adv for adv in spam_advertisers if adv in caption_lower]
                        if caption_spam_advertisers:
                            print(f"🚫 Spam detected in caption (advertiser name: {caption_spam_advertisers[0]}) - skipping")
                            consecutive_filtered += 1
                            continue
                        
                        # Check landing URL domain for spam domains
                        landing_url_lower = ad.get("landing_url", "").lower()
                        if any(domain in landing_url_lower for domain in spam_domains):
                            # More descriptive message based on domain type
                            if "apple.com" in landing_url_lower or "google.com" in landing_url_lower:
                                print(f"🚫 App Store link detected - skipping")
                            elif "walmart.com" in landing_url_lower or "temu.com" in landing_url_lower:
                                print(f"🚫 Large marketplace detected (Walmart/Temu) - skipping")
                            else:
                                print(f"🚫 Spam detected (domain: novel/story platform) - skipping")
                            consecutive_filtered += 1
                            continue
                        
                        # Check full landing URL for spam keywords (chapter, novel, love stories, etc.)
                        url_spam_keywords = [kw for kw in spam_keywords if kw in landing_url_lower]
                        if url_spam_keywords:
                            print(f"🚫 Spam detected in URL (found: {', '.join(url_spam_keywords[:3])}) - skipping")
                            consecutive_filtered += 1
                            continue
                        # ========== END SPAM FILTER ==========

                        # Initialize monthly_visits
                        ad["monthly_visits"] = None
                        
                        # Detect platform type (skip for Instagram Spark Ads - already set earlier)
                        if not ad.get("is_spark_ad") and landing_html:
                            try:
                                platform = detect_platform_from_html_only(landing_html)
                                ad["platform_type"] = platform
                                if platform and platform != "custom":
                                    print(f"🛒 Platform: {platform.title()}")
                            except Exception as e:
                                print(f"⚠️ Platform detection failed: {e}")
                        
                        if ad["is_spark_ad"]:
                            print(f"✨ Spark Ad detected (Instagram) - skipping traffic lookup")
                        elif ad.get("landing_url"):
                            try:
                                # Resolve redirects to get final destination domain
                                final_domain = await asyncio.to_thread(resolve_final_domain, ad["landing_url"])
                                
                                if final_domain:
                                    # Store the extracted root domain (e.g., mutha.com, healthcentral.com)
                                    ad["domain"] = final_domain
                                    
                                    if final_domain in domain_cache:
                                        ad["monthly_visits"] = domain_cache[final_domain]
                                    else:
                                        # Run SpyFu API in thread pool to avoid blocking
                                        spyfu_data = await asyncio.to_thread(get_seo_clicks, final_domain)
                                        if spyfu_data.get("status") == "ok" and spyfu_data.get("seo_clicks"):
                                            seo_clicks = spyfu_data["seo_clicks"]
                                            tier = get_tier_from_visits(seo_clicks)
                                            # Convert SEO clicks to estimated total visits
                                            estimated_visits = estimate_monthly_visits(seo_clicks, tier)
                                            ad["monthly_visits"] = int(estimated_visits)
                                            domain_cache[final_domain] = ad["monthly_visits"]
                                            original_domain = urlparse(ad["landing_url"]).netloc.replace("www.", "")
                                            redirect_info = f" (redirect: {original_domain} → {final_domain})" if original_domain != final_domain else ""
                                            print(f"📊 SpyFu: {final_domain}{redirect_info} → {seo_clicks:,} SEO clicks ({tier} tier) → {ad['monthly_visits']:,} est. visits")
                                        else:
                                            domain_cache[final_domain] = None
                                            print(f"⚠️ SpyFu: No SEO data for {final_domain}")
                            except Exception as e:
                                print(f"❌ SpyFu error for {ad.get('landing_url')}: {e}")

                        # 🆕 Extract and set page_id for main ad BEFORE scoring
                        if ad.get("advertiser_url"):
                            main_page_id = await extract_page_id_from_html(page, ad["advertiser_url"])
                            if main_page_id:
                                ad["page_id"] = main_page_id
                        
                        ad_scored = score_ad(ad)
                        save_ads([ad_scored])
                        results.append(ad_scored)
                        all_results.append(ad_scored)  # Collect for return
                        total_ads += 1
                        new_count += 1
                        consecutive_filtered = 0  # Reset counter on successful ad acceptance
                        
                        # 🆕 ADVERTISER SCRAPING: Scrape all ads from this advertiser's page
                        if SCRAPE_ADVERTISER_ADS and ad_scored.get("advertiser_url"):
                            advertiser_name = ad_scored.get("advertiser_name", "Unknown")
                            print(f"\n🔍 Extracting page_id from {advertiser_name}...")
                            page_id = await extract_page_id_from_html(page, ad_scored["advertiser_url"])
                            if page_id:
                                # ✅ Check if we've already scraped this advertiser
                                if page_id in scraped_advertisers:
                                    print(f"  ⏭️ Already scraped {advertiser_name} (page_id: {page_id}), skipping...")
                                    continue
                                
                                # Scrape all ads from this advertiser
                                advertiser_ads = await scrape_advertiser_all_ads(page, page_id, advertiser_name, ad_scored)
                                
                                if advertiser_ads:
                                    # Process and save advertiser's ads
                                    for adv_ad in advertiser_ads:
                                        # Add date parsing and hash
                                        if adv_ad.get("started_running_on"):
                                            start_date, days_running = parse_ad_start_date(adv_ad["started_running_on"])
                                            adv_ad["started_running_on"] = start_date
                                            adv_ad["days_running"] = days_running
                                        
                                        adv_ad["creative_hash"] = creative_fingerprint(adv_ad)
                                        
                                        # Set page_id for advertiser ads
                                        adv_ad["page_id"] = page_id
                                        
                                        # 🆕 Extract product name and price (same as main ads)
                                        if adv_ad.get("landing_url"):
                                            landing_url = adv_ad["landing_url"]
                                            
                                            # Check for Instagram Spark Ads
                                            if "instagram.com" in landing_url.lower():
                                                adv_ad["is_spark_ad"] = True
                                                adv_ad["platform_type"] = "instagram"
                                                adv_ad["page_type"] = "product_page"
                                                try:
                                                    parsed = urlparse(landing_url)
                                                    path_parts = [p for p in parsed.path.split('/') if p]
                                                    if path_parts:
                                                        instagram_username = path_parts[0].rstrip('_')
                                                        adv_ad["product_name"] = instagram_username
                                                    else:
                                                        adv_ad["product_name"] = "Instagram Profile"
                                                except Exception as e:
                                                    adv_ad["product_name"] = "Instagram Profile"
                                            else:
                                                # ⚡ FAST MODE: Extract from URL only (no page loading)
                                                from app.workers.url_product_extractor import extract_product_name_from_url_path
                                                adv_ad["product_name"] = extract_product_name_from_url_path(landing_url)
                                                adv_ad["product_price"] = None
                                                adv_ad["page_type"] = "product_page"
                                                adv_ad["platform_type"] = None
                                            
                                            # Extract domain
                                            try:
                                                adv_ad["domain"] = urlparse(landing_url).netloc.replace("www.", "")
                                            except:
                                                pass
                                        
                                        # Score and save
                                        adv_ad_scored = score_ad(adv_ad)
                                        save_ads([adv_ad_scored])
                                        results.append(adv_ad_scored)
                                        all_results.append(adv_ad_scored)
                                        total_ads += 1
                                        new_count += 1
                                    
                                    print(f"  💾 Saved {len(advertiser_ads)} ads from {advertiser_name}")
                                
                                # Mark this advertiser as scraped to prevent re-scraping
                                scraped_advertisers.add(page_id)
                                print(f"  ✅ Marked {advertiser_name} as scraped (page_id: {page_id})")
                                
                                # Navigate back to original search page (re-navigate instead of go_back to avoid timeout)
                                print(f"\n🔙 Returning to search results...")
                                try:
                                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                                    await page.wait_for_timeout(2000)
                                except Exception as e:
                                    print(f"  ⚠️ Error returning to search: {e}")
                            else:
                                print(f"  ⏭️ Skipping {advertiser_name} - couldn't extract page_id, continuing...")

                        await asyncio.sleep(random.uniform(0.1, 0.3))

                    if total_ads < max_ads:
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                        scroll_attempts += 1
                        if scroll_attempts % 5 == 0:
                            print(f"📜 Scrolled {scroll_attempts} times (total ads: {total_ads})")

                print(f"📥 Scraping complete for this query — saved {new_count} ads (total {total_ads})")

        await browser.close()
        print(f"\n🎯 TEST complete — scraped {total_ads} ads total!")

        with Session(engine) as session:
            count = session.exec(select(func.count()).select_from(AdCreative)).one()
            print(f"📊 Ads now stored in DB: {count}")
        
        return all_results

# Synchronous wrapper for distributed scraper
def main(keyword: Optional[str] = None, limit: Optional[int] = None, country: str = "US") -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for run_test_scrape.
    Used by distributed scraper workers.
    
    Args:
        keyword: Single keyword to search
        limit: Max ads to scrape
        country: Country code (default: US)
    
    Returns:
        List of scraped ads
    """
    return asyncio.run(run_test_scrape(keyword=keyword, limit=limit, country=country))

if __name__ == "__main__":
    asyncio.run(run_test_scrape())