# Product Research Tool - Project Documentation

## Overview
This project is a Product Research Tool designed to discover ads and analyze product/SKU intelligence. Its primary purpose is to identify promising product opportunities by scraping ad data from Facebook Ads Library, applying intelligent filters, and scoring ads based on various metrics. The tool aims to provide actionable insights for businesses looking to identify trending products and market gaps.

**Current Configuration**: 100 parallel browsers (10 workers × 10 threads), 246 keywords, Fast Mode (10x speedup), Advertiser Deep Scraping ENABLED, Database Pool: 50+50 connections, Deadlock-Free (no full-table UPDATEs during scraping)

## User Preferences
- **MUST use SpyFu API** for traffic data - never switch to SimilarWeb without explicit request
- SpyFu integration is non-negotiable even if API has issues
- **Product extraction must NEVER return "Unknown Product"** - always extract something from URL if page scan fails

## System Architecture
The application is built with FastAPI for the web API, SQLModel as the ORM, and Playwright for web scraping. PostgreSQL is used as the primary database. User authentication is implemented with session-based cookies and scrypt password hashing.

### UI/UX Decisions
The system focuses on providing clear, actionable product opportunity cards. Ads are scored and categorized with star ratings (1-5 stars) based on a weighted formula. Filters are implemented to ensure only high-quality, relevant product ads are displayed. Profile icons use letter initials instead of Facebook CDN images to avoid 403 blocking issues.

### Authentication System
-   **User Authentication**: Session-based authentication with HTTPOnly cookies for secure credential storage.
-   **Password Security**: Passwords are hashed using Python's built-in scrypt algorithm (N=16384, r=8, p=1) with per-user 32-byte salts and constant-time comparison to prevent timing attacks.
-   **Session Management**: Stateless signed tokens using itsdangerous with 7-day expiration. Tokens contain user_id and creation timestamp.
-   **Cookie Security**: HTTPOnly cookies with SameSite=lax for CSRF protection. Secure flag enabled in production (Replit deployments).
-   **CORS Configuration**: Restricted to specific frontend origins (configured via FRONTEND_URL environment variable) to prevent unauthorized cross-origin requests.
-   **API Endpoints**: POST /api/signup (create account), POST /api/login (authenticate), POST /api/logout (clear session), GET /api/user (get current user info).
-   **Protected Routes**: Authentication system available but /ads endpoint is public for easy access.
-   **Database**: User table stores id, username (unique), email (unique), password_hash, created_at, and updated_at fields.
-   **Environment Requirements**: Requires SESSION_SECRET environment variable (fails to start if not set). Frontend URL can be configured via FRONTEND_URL env var (defaults to http://localhost:3000).

### Technical Implementations
-   **AI-Driven Category Classification**: Lightweight keyword-based classification that automatically assigns each ad to one of 32 product niches (e.g., Beauty & Health, Women's Clothing, Electronics, etc.). Analyzes caption, product_name, account_name, and landing_url fields using weighted keyword matching. Non-intrusive add-on that enriches existing ads with a `category` field without modifying scraping logic. Run `classify_ads.py` to classify all ads in the database.
-   **Smart Spam & Quality Filters**: Automatically skips login/error pages, romance/fantasy novel ads (100+ advertisers and 40+ keywords including "love stories", "chapter", "novel" checked in advertiser name, caption, product name, and URL), mobile app store ads (Apple App Store: `apps.apple.com`, `itunes.apple.com`; Google Play: `play.google.com`, `app.google.com`), large marketplaces (Walmart, Temu), dating/video chat spam apps (TP 1014 17, app.adjust.com tracking URLs), and ads without extractable product information or broken media.
-   **Survey/Quiz Page Detection**: Lightweight text-based detection that runs AFTER product extraction to classify pages as "survey_page" or "product_page" without interfering with extraction. Checks for 20+ quiz/survey keywords in HTML and URL (e.g., "take our quiz", "find your type", "personalized plan").
-   **Advertiser Deep Scraping (ENABLED BY DEFAULT)**: Automatically scrapes ALL ads from each advertiser by extracting page_id from advertiser_url and navigating to their Ad Library profile. Enhanced with multiple regex patterns to catch different Facebook HTML formats, fast 8-second timeout to avoid long pauses, improved error logging, and graceful fallback when page_id cannot be extracted. Controlled by `SCRAPE_ADVERTISER_ADS` flag in run_test_scraper.py (line 138, default: True) and `ENABLE_ADVERTISER_SCRAPING` in distributed_scraper.py (line 45, default: True). Finds complete ad portfolios beyond keyword search results.
-   **Distributed Facebook Ad Scraper**: High-performance parallel scraping architecture with automatic post-processing. After scraping completes, automatically: (1) classifies ads into 32 product categories, (2) shares traffic data across same domains, (3) shares prices across same URLs. All-in-one single-run solution.
-   **GPT-5 AI Video Analyzer**: Extracts frames and performs OCR from ad videos, then uses GPT-5 for multimodal analysis of emotions, scene types, product focus, and creative structure.
-   **Advertiser Favicon Extraction**: Scrapes and stores the advertiser's profile image.
-   **Two-Layer Ad Inactive Detection System**: Combines Facebook's `ad_delivery_status` with a 3-miss disappearance detection fallback to accurately determine ad activity.
-   **⚡ Fast Mode Scraping**: URL-only extraction mode that skips page loading for 10x faster performance. Product names extracted from URL patterns, prices and platform detection disabled to maximize speed. **Duplicate Skip Mode**: When duplicates are detected, scraper skips them without database UPDATE operations (10x speedup vs updating last_seen). Use separate backfill script for timestamp updates if needed.
-   **Weighted Scoring Formula**: Replaces rule-based scoring with a data-driven approach, combining Duplicate Count (45%), Ad Age (35%), and Monthly Visits (20%) with saturating transforms, producing a 0-100 score and star rating.
-   **URL-Based Product Name Extraction**: Fast extraction directly from URL patterns without page loading. Extracts from `/products/`, `/p/`, `/items/`, `/shop/` paths, Amazon `/dp/` patterns, path segments, or domain names. Guarantees 100% extraction rate with no "Unknown Product" entries. **Instagram Spark Ads**: Special handling extracts profile name directly from URL (e.g., `instagram.com/bearathleticaus` → "bearathleticaus").
-   **Playwright Configuration**: Uses a system-wide Chromium installation for scraping, ensuring compatibility and stability.

### Feature Specifications
-   API endpoints for health checks and product opportunity cards.
-   Automatic detection and filtering of irrelevant or low-quality ads.
-   Comprehensive ad creative analysis, including video content.
-   Accurate tracking of ad activity status.
-   Detailed product information extraction (name, price, platform).
-   Dynamic scoring and ranking of product opportunities.

### System Design Choices
-   **Modular Architecture**: Organized into `api`, `workers`, `scoring`, `models`, and `db` directories for clear separation of concerns.
-   **Database Models**: `AdCreative` for raw ad data and `OpportunityCard` for processed, scored product opportunities.
-   **Rescan Worker**: A daily worker (`rescan_ads.py`) for detecting inactive ads and maintaining data freshness.
-   **Database Schema Compatibility**: All NOT NULL columns have database-level defaults to ensure backward compatibility with old scraper versions. This allows historical ZIP file versions to insert records without providing newer fields like `page_type`, `is_spark_ad`, etc.

## External Dependencies
-   **PostgreSQL**: Primary database for data storage.
-   **Playwright**: For browser automation and web scraping (e.g., Facebook Ads Library).
-   **SpyFu API**: For retrieving estimated website traffic and SEO data.
-   **OpenAI API (GPT-5)**: For advanced AI-powered video and creative analysis.
-   **Pytesseract, OpenCV-Python, Pillow**: For OCR and image/video processing within the AI video analyzer.
-   **Uvicorn**: ASGI server to run FastAPI.
