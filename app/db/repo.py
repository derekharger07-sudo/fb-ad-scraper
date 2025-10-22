import os
import hashlib
from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy import text  # ✅ NEW: Import for SQL query
from app.db.models import AdCreative, OpportunityCard

# Load .env file if running locally (for connecting local scraper to Replit database)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required in Replit

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dev.db")

# ⚡ Connection pool tuning for 100 parallel threads
# Default pool_size=5 causes pauses - increased to 50 to prevent blocking
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_size=50,  # Allow 50 concurrent connections (was 5)
    max_overflow=50,  # Allow 50 additional connections if pool is full (was 10)
    pool_pre_ping=True  # Test connections before use
)

def get_session():
    return Session(engine)

def init_db():
    SQLModel.metadata.create_all(engine)
    print("✅ Database initialized")

def normalize_media_url(url: str) -> str:
    """Normalize video/image URLs by removing tracking parameters."""
    if not url:
        return ""
    # Remove common tracking params: _nc_gid, _nc_zt, oh, oe, ccb, efg
    import re
    # Keep only the base URL up to the first ? and essential params
    base = url.split('?')[0] if '?' in url else url
    return base

def make_creative_hash(ad: dict) -> str:
    """Generate a stable hash for a creative using its video/image/caption content."""
    # Normalize URLs to remove tracking parameters
    video_url = normalize_media_url(ad.get("video_url") or "")
    image_url = normalize_media_url(ad.get("image_url") or "")
    
    key = (
        video_url +
        image_url +
        (ad.get("caption") or "")
    ).strip()
    if not key:
        return ""
    return hashlib.md5(key.encode("utf-8")).hexdigest()

# ✅ save_ads with deduplication and lifetime tracking
def save_ads(ad_list: list[dict]) -> int:
    """Save scraped Meta ads into AdCreative using existing columns.
    - Stores search_query, country
    - Stores scoring fields
    - Stores lifetime tracking: started_running_on, days_running
    - Stashes full dict in `raw`
    - Deduplicates based on platform, landing_url, and video_url
    - Updates last_seen_ts for existing ads
    """
    from datetime import datetime, date
    import json
    
    def prepare_for_json(obj):
        """Convert date objects to ISO strings for JSON serialization."""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: prepare_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [prepare_for_json(item) for item in obj]
        return obj
    
    saved = 0
    with get_session() as s:
        for ad in ad_list:
            platform = "meta"
            landing_url = ad.get("landing_url")
            video_url = ad.get("video_url") or ad.get("image_url") or ad.get("poster_url")

            # Skip if nothing useful
            if not landing_url and not video_url and not ad.get("caption"):
                continue

            # Calculate creative hash for variant detection (with normalized URLs)
            creative_hash = make_creative_hash(ad)
            
            # Normalize video URL for deduplication (remove tracking params)
            normalized_video_url = normalize_media_url(video_url) if video_url else ""

            # Check if ad already exists (deduplication)
            # True duplicate = same platform + landing_url + normalized video
            if normalized_video_url:
                existing = s.exec(
                    select(AdCreative).where(
                        AdCreative.platform == platform,
                        AdCreative.landing_url == landing_url,
                        AdCreative.video_url.like(f"{normalized_video_url}%")  # type: ignore
                    )
                ).first()
            else:
                existing = None

            if existing:
                # ⚡ FAST MODE: Skip duplicates without database updates (10x speedup)
                # Note: Use separate backfill script to update last_seen timestamps later
                continue
            
            # Parse fb_delivery_stop_time if provided
            fb_stop_time = None
            if ad.get("fb_delivery_stop_time"):
                try:
                    fb_stop_time = datetime.strptime(ad["fb_delivery_stop_time"], '%B %d, %Y').date()
                except:
                    pass
            
            row = AdCreative(
                platform=platform,
                external_id=None,
                account_name=ad.get("advertiser_name"),
                advertiser_favicon=ad.get("advertiser_favicon"),  # 👤 Profile picture
                caption=ad.get("caption"),
                landing_url=landing_url,
                video_url=video_url,
                metrics={"cta_text": ad.get("cta_text")},
                raw=prepare_for_json(ad),  # type: ignore  # Convert dates to strings for JSON storage
                search_query=ad.get("search_query"),
                country=ad.get("country"),
                page_id=ad.get("page_id"),  # 📍 Facebook page ID

                # 🕓 Lifetime tracking fields
                started_running_on=ad.get("started_running_on"),
                days_running=ad.get("days_running", 0),
                
                # 🔄 Two-layer detection fields
                fb_delivery_status=ad.get("fb_delivery_status"),
                fb_delivery_stop_time=fb_stop_time,
                detection_method=ad.get("detection_method", "3_miss_detection"),

                # 🎨 Creative tracking
                creative_hash=creative_hash,

                # 🏷️ Product data
                product_name=ad.get("product_name"),
                product_price=ad.get("product_price"),

                # 📊 Traffic data
                monthly_visits=ad.get("monthly_visits"),
                is_spark_ad=ad.get("is_spark_ad", False),
                platform_type=ad.get("platform_type"),
                page_type=ad.get("page_type"),

                # ✅ scoring fields
                demand_score=ad.get("demand_score"),
                competition_score=ad.get("competition_score"),
                angle_score=ad.get("angle_score"),
                geo_score=ad.get("geo_score"),
                total_score=ad.get("total_score"),
                stars=ad.get("stars"),
            )
            s.add(row)
            saved += 1
        s.commit()

        # ⚡ PERFORMANCE FIX: Removed full-table UPDATE and rescoring that caused deadlocks
        # creative_variant_count and scoring will be calculated in post-processing instead
        # Run after scraping: python update_variant_counts.py

    return saved

# ✅ Helper functions for distributed scraper
def db_get_ad_by_hash(ad_hash: str) -> AdCreative | None:
    """Get ad by its content hash to check for duplicates."""
    with get_session() as s:
        result = s.exec(
            select(AdCreative).where(AdCreative.creative_hash == ad_hash)
        ).first()
        return result

def db_insert_ad(ad_dict: dict) -> AdCreative:
    """Insert a single ad into the database."""
    from datetime import datetime
    
    # Calculate creative hash
    creative_hash = make_creative_hash(ad_dict)
    
    # Parse fb_delivery_stop_time if provided
    fb_stop_time = None
    if ad_dict.get("fb_delivery_stop_time"):
        try:
            fb_stop_time = datetime.strptime(ad_dict["fb_delivery_stop_time"], '%B %d, %Y').date()
        except:
            pass
    
    with get_session() as s:
        row = AdCreative(
            platform="meta",
            external_id=None,
            account_name=ad_dict.get("advertiser_name"),
            caption=ad_dict.get("caption"),
            landing_url=ad_dict.get("landing_url"),
            video_url=ad_dict.get("video_url") or ad_dict.get("image_url") or ad_dict.get("poster_url"),
            metrics={"cta_text": ad_dict.get("cta_text")},
            raw=ad_dict,
            search_query=ad_dict.get("search_query"),
            country=ad_dict.get("country"),
            page_id=ad_dict.get("page_id"),
            started_running_on=ad_dict.get("started_running_on"),
            days_running=ad_dict.get("days_running", 0),
            fb_delivery_status=ad_dict.get("fb_delivery_status"),
            fb_delivery_stop_time=fb_stop_time,
            detection_method=ad_dict.get("detection_method", "3_miss_detection"),
            creative_hash=creative_hash,
            product_name=ad_dict.get("product_name"),
            product_price=ad_dict.get("product_price"),
            monthly_visits=ad_dict.get("monthly_visits"),
            is_spark_ad=ad_dict.get("is_spark_ad", False),
            platform_type=ad_dict.get("platform_type"),
            page_type=ad_dict.get("page_type"),
            demand_score=ad_dict.get("demand_score"),
            competition_score=ad_dict.get("competition_score"),
            angle_score=ad_dict.get("angle_score"),
            geo_score=ad_dict.get("geo_score"),
            total_score=ad_dict.get("total_score"),
            stars=ad_dict.get("stars"),
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return row

# Simple domain cache (in-memory) to avoid duplicate SpyFu lookups across threads
_domain_cache = {}

def db_domain_exists(domain: str) -> dict | None:
    """Check if domain has been processed for traffic data. Returns dict with seo_clicks if exists."""
    # Check in-memory cache first
    if domain in _domain_cache:
        return _domain_cache[domain]
    
    # Check database - look for any ad with this domain that has monthly_visits data
    with get_session() as s:
        result = s.exec(
            select(AdCreative)
            .where(AdCreative.landing_url.like(f"%{domain}%"))  # type: ignore
            .where(AdCreative.monthly_visits.is_not(None))  # type: ignore
        ).first()
        
        if result:
            data = {"domain": domain, "seo_clicks": result.monthly_visits}
            _domain_cache[domain] = data
            return data
        return None

def db_insert_domain(domain: str, seo_clicks: int = 0):
    """Mark domain as processed with its SEO clicks data (stores in cache)."""
    _domain_cache[domain] = {"domain": domain, "seo_clicks": seo_clicks}
    # Note: Actual storage happens when ad is inserted with monthly_visits set

if __name__ == "__main__":
    import sys
    if "--init" in sys.argv:
        init_db()