# test_dedup.py
from app.db.repo import save_ads, get_session
from app.db.models import AdCreative
from sqlmodel import select

# Two identical ads (should count as one if dedupe works)
ads = [
    {
        "advertiser_name": "Test Brand",
        "caption": "Amazing leggings ad!",
        "landing_url": "https://testbrand.com",
        "video_url": "https://cdn.test/video.mp4",
        "search_query": "leggings",
        "country": "US",
    },
    {
        "advertiser_name": "Test Brand",
        "caption": "Amazing leggings ad!",
        "landing_url": "https://testbrand.com",
        "video_url": "https://cdn.test/video.mp4",
        "search_query": "leggings",
        "country": "US",
    },
]

print("🧪 Saving two identical ads …")
saved = save_ads(ads)
print(f"✅  save_ads() returned: {saved}")

with get_session() as s:
    total = s.exec(select(AdCreative)).all()
    print(f"📊 Ads currently stored in DB: {len(total)}")
    for ad in total:
        print(f"- {ad.account_name} | {ad.landing_url}")
