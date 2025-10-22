"""
E-commerce Platform Detection Module

Identifies the website platform/technology stack by analyzing:
- HTML content patterns
- HTTP headers
- JavaScript libraries
- Domain patterns
"""

import re
from typing import Optional
import requests
from urllib.parse import urlparse


PLATFORM_PATTERNS = {
    "shopify": {
        "html": [
            r"Shopify\.shop",
            r"cdn\.shopify\.com",
            r"shopify-section",
            r"shopifycdn\.com",
            r"monorail-edge\.shopifysvc\.com"
        ],
        "headers": ["x-shopid", "x-shopify-stage"],
        "meta": ["shopify-digital-wallet"]
    },
    "wix": {
        "html": [
            r"_wix",
            r"static\.wixstatic\.com",
            r"wix\.com",
            r"X-Wix-",
        ],
        "headers": ["x-wix-request-id", "x-wix-renderer-server"],
        "meta": []
    },
    "woocommerce": {
        "html": [
            r"wp-content/plugins/woocommerce",
            r"woocommerce",
            r"class=[\"'].*woocommerce.*[\"']"
        ],
        "headers": [],
        "meta": ["generator.*woocommerce"]
    },
    "squarespace": {
        "html": [
            r"squarespace\.com",
            r"static1\.squarespace\.com",
            r"Squarespace\.SQUARESPACE_CONTEXT"
        ],
        "headers": [],
        "meta": []
    },
    "bigcommerce": {
        "html": [
            r"bigcommerce\.com",
            r"cdn[0-9]*\.bigcommerce\.com"
        ],
        "headers": ["x-bc-storefront-origin"],
        "meta": []
    },
    "wordpress": {
        "html": [
            r"wp-content",
            r"wp-includes",
            r"wordpress"
        ],
        "headers": [],
        "meta": ["generator.*wordpress"]
    },
    "magento": {
        "html": [
            r"Mage\.Cookies",
            r"/static/frontend/",
            r"var/magento"
        ],
        "headers": ["x-magento-cache-id"],
        "meta": []
    },
    "prestashop": {
        "html": [
            r"prestashop",
            r"content_only=1"
        ],
        "headers": [],
        "meta": ["generator.*prestashop"]
    },
    "webflow": {
        "html": [
            r"webflow\.com",
            r"assets\.website-files\.com"
        ],
        "headers": [],
        "meta": []
    }
}


def detect_platform(url: str, html: str = None, headers: dict = None) -> Optional[str]:
    """
    Detect the e-commerce/website platform from URL, HTML content, and headers.
    
    Args:
        url: The website URL
        html: HTML content (optional, will be fetched if not provided)
        headers: HTTP response headers (optional, will be fetched if not provided)
    
    Returns:
        Platform name (e.g., 'shopify', 'wix') or 'custom' if unknown
    """
    
    # Fetch HTML and headers if not provided
    if html is None or headers is None:
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            if html is None:
                html = response.text
            if headers is None:
                headers = {k.lower(): v for k, v in response.headers.items()}
        except Exception as e:
            print(f"⚠️ Platform detection failed to fetch {url}: {e}")
            return "unknown"
    
    # Normalize headers to lowercase
    if headers:
        headers = {k.lower(): v for k, v in headers.items()}
    else:
        headers = {}
    
    # Check each platform
    for platform, patterns in PLATFORM_PATTERNS.items():
        # Check HTML patterns
        if html:
            for pattern in patterns["html"]:
                if re.search(pattern, html, re.IGNORECASE):
                    return platform
        
        # Check headers
        for header in patterns["headers"]:
            if header.lower() in headers:
                return platform
        
        # Check meta tags
        if html:
            for meta_pattern in patterns["meta"]:
                if re.search(f'<meta.*{meta_pattern}', html, re.IGNORECASE):
                    return platform
    
    # If no platform detected, return custom
    return "custom"


def detect_platform_from_html_only(html: str) -> Optional[str]:
    """
    Detect platform from HTML content only (faster, no HTTP request needed).
    
    Args:
        html: HTML content string
    
    Returns:
        Platform name or 'custom' if unknown
    """
    if not html:
        return "unknown"
    
    for platform, patterns in PLATFORM_PATTERNS.items():
        # Check HTML patterns only
        for pattern in patterns["html"]:
            if re.search(pattern, html, re.IGNORECASE):
                return platform
        
        # Check meta tags
        for meta_pattern in patterns["meta"]:
            if re.search(f'<meta.*{meta_pattern}', html, re.IGNORECASE):
                return platform
    
    return "custom"
