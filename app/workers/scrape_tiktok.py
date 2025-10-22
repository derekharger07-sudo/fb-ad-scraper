import asyncio
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from playwright.async_api import async_playwright

# NOTE: STUB. Update selectors to match the current DOM responsibly.
# Prefer official endpoints where available and follow platform rules.

async def scrape_keyword(keyword: str, max_ads: int = 30) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/nix/store/qa9cnw4v5xkxyip6mb9kxqfq1z4x2dx1-chromium-138.0.7204.100/bin/chromium"
        )
        context = await browser.new_context()
        page = await context.new_page()

        url = f"https://www.tiktok.com/business/creativecenter/search/{keyword}"
        await page.goto(url, wait_until="networkidle")

        # --- REAL SELECTORS ---
        cards = await page.query_selector_all("div.CommonGridLayoutDataList_cardWrapper_jkA9g")

        for card in cards[:max_ads]:
            # caption
            caption_spans = await card.query_selector_all("span.TopadsVideoCard_title_UeLe1")
            caption_parts = [await span.inner_text() for span in caption_spans]
            caption = " ".join(caption_parts).strip() if caption_parts else None

            # advertiser
            account_el = await card.query_selector("span.TopadsVideoCard_secondTitle__Ee86S")
            account = await account_el.inner_text() if account_el else None

            # likes/ctr/budget
            footer = await card.query_selector("div.TopadsVideoCard_cardInfo_NDm3_")
            items = await footer.query_selector_all("div.TopadsVideoCard_cardInfoItem_vjGkP") if footer else []
            likes, ctr, budget = None, None, None

            if len(items) >= 1:
                val = await items[0].query_selector("span.TopadsVideoCard_itemValue_ON0xu")
                likes = await val.inner_text() if val else None
            if len(items) >= 2:
                val = await items[1].query_selector("span.TopadsVideoCard_itemValue_ON0xu")
                ctr = await val.inner_text() if val else None
            if len(items) >= 3:
                val = await items[2].query_selector("span.TopadsVideoCard_itemValue_ON0xu")
                budget = await val.inner_text() if val else None

            # video
            video_el = await card.query_selector("video")
            video_url = await video_el.get_attribute("src") if video_el else None

            results.append({
                "caption": caption,
                "account_name": account,
                "video_url": video_url,
                "likes": likes,
                "ctr": ctr,
                "budget": budget,
                "first_seen_ts": datetime.now(timezone.utc).isoformat()
            })

        await browser.close()
    return results

if __name__ == "__main__":
    data = asyncio.run(scrape_keyword("fleece lined leggings"))
    print(json.dumps(data[:3], indent=2))
