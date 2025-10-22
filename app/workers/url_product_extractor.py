"""
URL-based Product Name Extraction
Extracts product names directly from URL patterns without loading the page.
"""

import re
from urllib.parse import urlparse
from typing import Optional


def extract_product_name_from_url_path(url: str) -> Optional[str]:
    """
    Extract product name from URL path patterns.
    
    Examples:
        https://elevoraus.com/products/elevora-100-unrefined-batana-oil
        → "elevora 100 unrefined batana oil"
        
        https://stores.ashleyfurniture.com/
        → "ashleyfurniture"
    
    Args:
        url: The product URL
        
    Returns:
        Extracted product name or None
    """
    if not url:
        return None
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        # Strategy 1: Extract from common e-commerce URL patterns
        product_patterns = [
            r'/products?/([^/?#]+)',  # /products/product-name or /product/product-name
            r'/p/([^/?#]+)',          # /p/product-name
            r'/items?/([^/?#]+)',     # /item/product-name or /items/product-name
            r'/shop/([^/?#]+)',       # /shop/product-name
            r'/buy/([^/?#]+)',        # /buy/product-name
            r'/([^/?#]+)/dp/',        # Amazon: /Product-Name/dp/... (extract before /dp/)
            r'/([^/?#]+)/gp/product', # Amazon alternate: /Product-Name/gp/product/...
        ]
        
        for pattern in product_patterns:
            match = re.search(pattern, path, re.IGNORECASE)
            if match:
                product_slug = match.group(1)
                # Clean and format the product name
                product_name = _clean_url_slug(product_slug)
                if product_name and len(product_name) > 3:
                    return product_name
        
        # Strategy 2: Extract from last path segment (with quality filtering)
        if path and path != '/':
            segments = [s for s in path.split('/') if s]
            if segments:
                last_segment = segments[-1]
                # Try to extract from last segment with validation
                product_name = _clean_url_slug(last_segment)
                if product_name and _is_valid_product_name(product_name):
                    return product_name
        
        # Strategy 3: Extract brand/store name from domain (ALWAYS succeeds)
        if domain:
            # Remove common prefixes and TLDs
            domain_clean = domain.replace('www.', '').replace('shop.', '').replace('store.', '')
            domain_clean = domain_clean.replace('stores.', '').replace('m.', '').replace('latest.', '')
            
            # Get the main domain name (before first dot)
            domain_parts = domain_clean.split('.')
            if domain_parts and domain_parts[0]:
                brand_name = domain_parts[0]
                # Clean up common patterns
                brand_name = brand_name.replace('-', ' ').replace('_', ' ')
                return brand_name.strip().title()
        
        # Absolute fallback: return domain without TLD
        if domain:
            # Remove TLD (.com, .net, .org, etc.)
            domain_without_tld = domain.split('.')[0] if '.' in domain else domain
            # Clean up
            domain_without_tld = domain_without_tld.replace('-', ' ').replace('_', ' ')
            return domain_without_tld.strip().title()
        
        return "Product"
        
    except Exception as e:
        print(f"⚠️ URL extraction error: {e}")
        return None


def _is_valid_product_name(name: str) -> bool:
    """
    Validate if extracted name looks like a real product name, not garbage.
    
    Rejects:
        - Very short strings (< 3 chars)
        - Random tracking codes (long strings with no spaces)
        - Base64-looking strings
        - Single letter/number combinations
    """
    if not name or len(name) < 3:
        return False
    
    # Reject strings with no word boundaries (likely tracking codes)
    # e.g., "Eedtmx4gsrgshldlm55cpjaw" - too long with no spaces
    if len(name) > 20 and ' ' not in name:
        return False
    
    # Reject if mostly lowercase with random chars (base64/encoded)
    # e.g., "ym lms" or "_u"
    if name.islower() and len(name) < 6:
        return False
    
    # Reject single character or two-char strings
    if len(name) <= 2:
        return False
    
    # Reject if all uppercase (likely tracking code or parameter)
    if name.isupper() and len(name) > 5:
        return False
    
    # Must contain at least one letter
    if not any(c.isalpha() for c in name):
        return False
    
    # Reject common tracking parameter patterns
    tracking_patterns = [
        r'^[a-z0-9]{16,}$',  # Long hex/random strings
        r'^[A-Z0-9_]+$',     # All caps with underscores (SESSION_ID style)
        r'^v\d+$',           # Version numbers like "v1", "v2"
        r'^\d+$',            # Pure numbers
    ]
    
    for pattern in tracking_patterns:
        if re.match(pattern, name):
            return False
    
    return True


def _clean_url_slug(slug: str) -> str:
    """
    Convert URL slug to readable product name.
    
    Examples:
        'elevora-100-unrefined-batana-oil' → 'elevora 100 unrefined batana oil'
        'yoga_mat_pro_edition' → 'yoga mat pro edition'
    """
    if not slug:
        return ""
    
    # Replace hyphens and underscores with spaces
    cleaned = slug.replace('-', ' ').replace('_', ' ')
    
    # Remove common URL artifacts
    cleaned = re.sub(r'\.(html?|php|aspx?)$', '', cleaned, flags=re.IGNORECASE)
    
    # Remove query parameters if any slipped through
    cleaned = cleaned.split('?')[0].split('#')[0]
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Remove leading/trailing special characters
    cleaned = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', cleaned)
    
    # Lowercase everything
    cleaned = cleaned.lower()
    
    # Capitalize first letter of each word for better readability
    # But keep numbers and acronyms as-is
    words = cleaned.split()
    formatted_words = []
    for word in words:
        # Keep all-caps words (like SPF, LED) and numbers as-is
        if word.isupper() or word.isdigit():
            formatted_words.append(word)
        else:
            formatted_words.append(word.capitalize())
    
    return ' '.join(formatted_words)
