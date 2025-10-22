from typing import Optional
from datetime import datetime, date
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import BigInteger


class AdCreative(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str
    external_id: Optional[str] = None

    # 🕓 Lifetime tracking fields
    started_running_on: Optional[date] = None  # from "Started running on..."
    first_seen_ts: datetime = Field(default_factory=datetime.utcnow)
    last_seen_ts: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    days_running: Optional[int] = 0
    missing_count: int = Field(default=0)  # Track consecutive misses (inactive after 3)
    
    # 🔄 Two-Layer Detection System
    fb_delivery_status: Optional[str] = None  # Facebook's status: "ACTIVE", "INACTIVE", or None
    fb_delivery_stop_time: Optional[date] = None  # When Facebook says ad stopped (from HTML)
    detection_method: Optional[str] = Field(default="3_miss_detection")  # "facebook_status", "3_miss_detection", "hybrid"

    # 🧠 Core ad data
    account_name: Optional[str] = None
    advertiser_favicon: Optional[str] = None  # Advertiser profile picture URL
    caption: Optional[str] = None
    landing_url: Optional[str] = None
    video_url: Optional[str] = None
    geo: Optional[str] = None  # comma-delimited geos for simplicity
    metrics: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    product_name: Optional[str] = None  # Extracted product name from landing page
    product_price: Optional[str] = None  # Extracted price (e.g., "$29.99", "€45.00")
    product_hash: Optional[str] = None
    angle_tags: Optional[str] = None  # comma-delimited tags
    embed: Optional[bytes] = None  # placeholder if you add vector store later
    raw: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    page_id: Optional[str] = None  # Facebook page ID extracted from advertiser URL

    # 🔍 Multi-keyword scraping
    search_query: Optional[str] = None
    country: Optional[str] = None

    # 🧮 Scoring fields
    demand_score: Optional[int] = 0
    competition_score: Optional[int] = 0
    angle_score: Optional[int] = 0
    geo_score: Optional[int] = 0
    total_score: Optional[int] = 0
    stars: Optional[int] = 0  # Star rating (1-5) based on total_score

    # 💻 Traffic Intelligence (NEW)
    monthly_visits: Optional[int] = Field(default=0, sa_column=Column(BigInteger))  # supports large traffic numbers
    is_spark_ad: bool = Field(default=False)  # True if brand site is Instagram (UGC/Spark ad)
    platform_type: Optional[str] = Field(default=None)  # E-commerce platform: shopify, wix, woocommerce, custom, etc.
    page_type: Optional[str] = Field(default="product_page")  # Always "product_page" (quiz detection removed for simplicity)
    
    # 🏷️ Niche Classification (AI-driven)
    category: Optional[str] = Field(default=None)  # Product niche/category (e.g., "Beauty & Health", "Women's Clothing")

    # 🆕 Creative-level fingerprint tracking
    creative_hash: Optional[str] = Field(default=None, index=True)
    creative_variant_count: int = Field(default=1)  # how many duplicates/variants of this creative were seen


class OpportunityCard(SQLModel, table=True):
    product_hash: str = Field(primary_key=True)
    score: float = 0.0
    price_band: Optional[str] = None
    recommended_geos: Optional[str] = None  # comma-delimited
    reasons: Optional[str] = None           # newline-delimited bullet points
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
