import asyncio
import json
import random
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from playwright.async_api import async_playwright, Page, Locator
from sqlmodel import select
from app.db.repo import save_ads, get_session
from app.db.models import AdCreative
from app.scoring.ad_scoring import score_ad
from app.config import CHROMIUM_BIN, SEARCH_QUERIES, COUNTRIES, MAX_ADS_PER_QUERY

# ---------- helpers ----------

def compute_run_time(ad: Dict[str, Any]) -> None:
    """
    Parse started_running_on date and calculate days_running.
    Updates the ad dictionary in-place with:
    - started_running_on (as ISO string)
    - days_running (as integer)
    """
    date_str = ad.get("started_running_on")
    if not date_str:
        return

    try:
        # Try both short and long month formats
        parsed_date = None
        for fmt in ["%b %d, %Y", "%B %d, %Y"]:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue

        if parsed_date:
            # Calculate days running
            days_running = (datetime.utcnow() - parsed_date).days
            # Store as ISO string and days
            ad["started_running_on"] = parsed_date.date().isoformat()
            ad["days_running"] = days_running
    except Exception as e:
        # If parsing fails, just skip
        pass


def make_creative_hash(ad: Dict[str, Any]) -> str:
    """
    Generate a stable hash for a creative using its video/image/caption content.
    Used to detect duplicate ads (variants).
    """
    key = (
        (ad.get("video_url") or "") +
        (ad.get("image_url") or "") +
        (ad.get("caption") or "")
    ).strip()
    if not key:
        return ""
    return hashlib.md5(key.encode("utf-8")).hexdigest()


async def click_if_visible(page: Page, selector: str) -> bool:
    try:
        el = page.locator(selector).first
        if await el.is_visible(timeout=1000):
            await el.click()
            return True
    except:
        pass
    return False


async def accept_cookies_if_present(page: Page):
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
    try:
        chip = page.get_by_role("button", name=re.compile(r"\bAll ads\b", re.I))
        if await chip.is_visible(timeout=2000):
            await chip.click()
            await page.wait_for_timeout(1200)
    except:
        pass


async def smart_scroll(page: Page):
    js = """
    () => {
      const main = document.querySelector('div[role="main"]');
      if (main) { main.scrollBy(0, main.clientHeight * 0.9); }
      window.scrollBy(0, Math.floor(window.innerHeight * 0.9));
    }
    """
    await page.evaluate(js)


async def click_all_see_more(page: Page) -> int:
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

# ---------- extraction ----------

async def extract_ads_from_page(page: Page) -> List[Dict[str, Any]]:
    ads: List[Dict[str, Any]] = []

    # NEW APPROACH: Use JavaScript to extract ad data directly
    extract_js = """
    () => {
        const images = Array.from(document.querySelectorAll('img[src*="scontent"]'));
        const ads = [];
        const seenAds = new Set();

        images.forEach(img => {
            // Walk up to find ad card container
            let current = img;
            let depth = 0;
            let adCard = null;

            while (current && depth < 15) {
                const text = current.textContent?.trim() || '';
                // Look for container with "Sponsored" text and reasonable content
                if (text.includes('Sponsored') && text.length > 50) {
                    adCard = current;
                    break;
                }
                current = current.parentElement;
                depth++;
            }

            if (adCard && !seenAds.has(adCard)) {
                seenAds.add(adCard);

                const data = {};

                // Advertiser name and URL
                const advertiserLink = adCard.querySelector('a[href*="facebook.com/"]');
                if (advertiserLink) {
                    data.advertiser_name = advertiserLink.textContent?.trim();
                    data.advertiser_url = advertiserLink.getAttribute('href');
                }

                // Get all images (excluding small avatars)
                const allImages = Array.from(adCard.querySelectorAll('img[src*="scontent"]'));
                const adImages = allImages.filter(img => {
                    const width = img.naturalWidth || parseInt(img.getAttribute('width')) || 0;
                    return width > 100; // Filter out small avatar images
                });
                if (adImages.length > 0) {
                    data.image_url = adImages[0].getAttribute('src');
                }

                // Video
                const video = adCard.querySelector('video');
                if (video) {
                    data.video_url = video.getAttribute('src') || video.querySelector('source')?.getAttribute('src');
                    data.poster_url = video.getAttribute('poster');
                }

                // Caption - get the main text content
                const fullText = adCard.textContent || '';
                const lines = fullText.split('\\n').map(l => l.trim()).filter(l => l);

                // Extract "Started running on" date - search in parent container
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
                        break;
                    }
                    containerToSearch = containerToSearch.parentElement;
                    searchDepth++;
                }

                // Filter out "Sponsored", advertiser name, and runtime text from caption
                const caption = lines.filter(l => 
                    l !== 'Sponsored' && 
                    l !== data.advertiser_name &&
                    !l.includes('Started running on') &&
                    l.length > 10
                ).join(' ').substring(0, 500);
                if (caption) {
                    data.caption = caption;
                }

                // Landing URL and CTA
                const ctaLinks = Array.from(adCard.querySelectorAll('a[href^="http"]')).filter(a => {
                    const href = a.getAttribute('href') || '';
                    // Include Facebook redirect links but exclude Facebook pages/profiles
                    if (href.includes('.facebook.com/') && href.includes('.php?u=')) {
                        return true; // Keep redirect links like l.facebook.com/l.php?u=... or 1.facebook.com/1.php?u=...
                    }
                    return !href.includes('facebook.com/ads/library') &&
                           !href.includes('facebook.com/profile') &&
                           !href.includes('facebook.com/pages/') &&
                           !href.includes('facebook.com/');
                });
                if (ctaLinks.length > 0) {
                    let rawUrl = ctaLinks[0].getAttribute('href') || '';

                    // 🧠 Handle redirect links (l.facebook.com/l.php?u=... or 1.facebook.com/1.php?u=...)
                    if (rawUrl.includes('.facebook.com/') && rawUrl.includes('.php?u=')) {
                        const match = rawUrl.match(/u=([^&]+)/);
                        if (match && match[1]) {
                            rawUrl = decodeURIComponent(match[1]);
                        }
                    }

                    // 🧹 Clean tracking params
                    rawUrl = rawUrl.replace(/(\?|&)fbclid=[^&]+/g, '').replace(/(\?|&)utm_[^&]+/g, '');

                    data.landing_url = rawUrl;
                    data.cta_text = ctaLinks[0].textContent?.trim() || null;
                } else {
                    // Fallback: Extract URLs from plain text  
                    const httpIndex = fullText.toLowerCase().indexOf('http');
                    const wwwIndex = fullText.toLowerCase().indexOf('www.');
                    let startIndex = -1;

                    if (httpIndex >= 0 and (wwwIndex < 0 or httpIndex < wwwIndex)):
                        startIndex = httpIndex
                    elif wwwIndex >= 0:
                        startIndex = wwwIndex

                    if startIndex >= 0:
                        let endIndex = fullText.indexOf(' ', startIndex)
                        if endIndex < 0: endIndex = fullText.indexOf('\\n', startIndex)
                        if endIndex < 0: endIndex = fullText.length

                        let extractedUrl = fullText.substring(startIndex, endIndex).trim().toLowerCase()
                        if not extractedUrl.startswith('http'):
                            extractedUrl = 'https://' + extractedUrl
                        data.landing_url = extractedUrl
                }

                // Only add if we have some useful data
                if (data.caption or data.image_url or data.video_url or data.landing_url):
                    ads.append(data)
            }
        })

        return ads
    }
    """

    ads = await page.evaluate(extract_js)
    return ads

# ---------- main ----------

async def scrape_meta():
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

        grand_total = 0

        for query in SEARCH_QUERIES:
            for country in COUNTRIES:
                url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={country}&q={query}"
                print(f"\n🌍 Scraping {query!r} in {country} → {url}")
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)

                await accept_cookies_if_present(page)
                await ensure_all_ads_tab(page)

                # Wait for images to load (indicating ads have rendered)
                try:
                    await page.wait_for_selector('img[src*="scontent"]', timeout=15000)
                    print("✅ Images loaded, ads should be visible")
                except:
                    print("⚠️ No images found, but continuing...")

                # 📸 Take a debug screenshot of the current page
                await page.screenshot(path="debug.png", full_page=True)
                print("📸 Saved screenshot of current page to debug.png")

                # 🔍 Inspect DOM (unchanged)
                inspect_js = """ ... """  # kept as-is

                dom_info = await page.evaluate(inspect_js)
                with open("dom_inspection.json", "w") as f:
                    json.dump(dom_info, f, indent=2)

                results: List[Dict[str, Any]] = []

                # ✅ NEW: grab first batch immediately
                first_batch = await extract_ads_from_page(page)
                for ad in first_batch:
                    ad["search_query"] = query
                    ad["country"] = country
                    compute_run_time(ad)

                    # 🧠 Creative hash + variant count
                    ad["creative_hash"] = make_creative_hash(ad)
                    if ad["creative_hash"]:
                        with get_session() as s:
                            existing = s.exec(
                                select(AdCreative).where(AdCreative.creative_hash == ad["creative_hash"])
                            ).all()
                            ad["creative_variant_count"] = len(existing) + 1
                    else:
                        ad["creative_variant_count"] = 1

                    ad_scored = score_ad(ad)
                    save_ads([ad_scored])
                    results.append(ad_scored)
                print(f"📥 Initial load captured {len(first_batch)} ads for {query}/{country}")

                stalled = 0
                while len(results) < MAX_ADS_PER_QUERY and stalled < 3:
                    await smart_scroll(page)
                    await page.wait_for_timeout(random.randint(1200, 2200))
                    clicked = await click_all_see_more(page)
                    if clicked:
                        print(f"👉 Clicked {clicked} 'See more ads' button(s)")

                    batch = await extract_ads_from_page(page)
                    new = 0
                    for ad in batch:
                        ad["search_query"] = query
                        ad["country"] = country
                        compute_run_time(ad)

                        # 🧠 Creative hash + variant count
                        ad["creative_hash"] = make_creative_hash(ad)
                        if ad["creative_hash"]:
                            with get_session() as s:
                                existing = s.exec(
                                    select(AdCreative).where(AdCreative.creative_hash == ad["creative_hash"])
                                ).all()
                                ad["creative_variant_count"] = len(existing) + 1
                        else:
                            ad["creative_variant_count"] = 1

                        ad_scored = score_ad(ad)
                        save_ads([ad_scored])
                        results.append(ad_scored)
                        new += 1

                    print(f"📊 Collected {len(results)} ads so far for {query}/{country} (+{new} new)")
                    stalled = stalled + 1 if new == 0 else 0

                print(f"✅ Done {query}/{country}: saved {len(results)}")
                grand_total += len(results)

        print(f"\n🎉 GRAND TOTAL scraped: {grand_total}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_meta())
