"""
Enhanced Product Name Extraction Module

This module provides a comprehensive, multi-strategy approach to extracting product names
from e-commerce landing pages with high reliability.
"""

import re
from typing import Optional, Tuple
from playwright.async_api import Page


class ProductNameExtractor:
    """Extract product names from landing pages using multiple strategies."""
    
    # Primary selectors (ordered by confidence)
    PRIMARY_SELECTORS = [
        # Meta tags (highest confidence for structured data)
        ("meta[property='og:title']", "content", 10),
        ("meta[name='og:title']", "content", 10),
        ("meta[property='twitter:title']", "content", 9),
        ("meta[name='twitter:title']", "content", 9),
        ("meta[itemprop='name']", "content", 9),
        ("meta[name='title']", "content", 8),
        
        # Heading elements (high confidence)
        ("h1.product-title", "text", 10),
        ("h1[class*='product']", "text", 9),
        ("h1[class*='Product']", "text", 9),
        ("h1", "text", 8),
        
        # Product-specific attributes (medium-high confidence)
        ("[data-product-title]", "data-product-title", 7),
        ("[data-product-name]", "data-product-name", 7),
        ("[class*='product-title']", "text", 7),
        ("[class*='productTitle']", "text", 7),
        ("[class*='product_name']", "text", 7),
        ("[class*='productName']", "text", 7),
        ("[id*='product-title']", "text", 6),
        ("[id*='productTitle']", "text", 6),
    ]
    
    # Fallback selectors
    FALLBACK_SELECTORS = [
        ("h1", "text", 5),
        ("h2.product-name", "text", 4),
        ("h2[class*='product']", "text", 4),
        ("title", "text", 3),
    ]
    
    # Cleanup patterns
    CLEANUP_PATTERNS = [
        (r'\s*[|–—-]\s*Official Site.*$', ''),
        (r'\s*[|–—-]\s*Buy Now.*$', ''),
        (r'\s*[|–—-]\s*Shop.*$', ''),
        (r'\s*[|–—-]\s*Free Shipping.*$', ''),
        (r'\s*[|–—-]\s*\d+%\s*OFF.*$', ''),
        (r'\s*[|–—-]\s*Sale.*$', ''),
        (r'\s*[|–—-]\s*[A-Z][a-z]+\s*$', ''),  # Remove trailing brand names like "- Nike"
        (r'^\s*Buy\s+', ''),  # Remove leading "Buy "
        (r'^\s*Shop\s+', ''),  # Remove leading "Shop "
    ]
    
    # Invalid page indicators (login/error pages)
    INVALID_INDICATORS = [
        "login", "log in", "sign in", "sign up", "error", "404", "403",
        "page not found", "access denied", "unavailable", "suspended",
        "verify", "captcha", "blocked", "restricted", "authentication required"
    ]

    @staticmethod
    async def extract(page: Page, url: str, debug: bool = False) -> Optional[str]:
        """
        Extract product name using multi-strategy approach.
        
        Args:
            page: Playwright page object with loaded content
            url: URL of the page (for context)
            debug: Enable debug logging
            
        Returns:
            Extracted product name or None if invalid page detected
        """
        if not url or "facebook.com" in url:
            return None
        
        # Track best match
        best_match = None
        best_confidence = 0
        
        # Strategy 1: Primary selectors with confidence scoring
        for selector, attr_type, confidence in ProductNameExtractor.PRIMARY_SELECTORS:
            try:
                el = await page.query_selector(selector)
                if el:
                    if attr_type == "text":
                        text = (await el.text_content() or "").strip()
                    else:
                        text = (await el.get_attribute(attr_type) or "").strip()
                    
                    # More lenient length validation
                    if text and len(text) > 2 and len(text) < 200:
                        # Clean the text
                        cleaned = ProductNameExtractor._cleanup_name(text)
                        
                        # More lenient validation
                        if cleaned and len(cleaned) > 2:
                            if confidence > best_confidence:
                                best_match = cleaned
                                best_confidence = confidence
                                if debug:
                                    print(f"  ✓ Found via {selector} ({attr_type}): '{cleaned}' (confidence: {confidence})")
                                # If we found high-confidence match, we can stop
                                if confidence >= 9:
                                    break
            except Exception as e:
                if debug:
                    print(f"  ✗ Error with {selector}: {e}")
                continue
        
        # Return if we found ANY match from primary selectors
        if best_match and best_confidence >= 6:
            return best_match
        
        # Strategy 2: JavaScript-based extraction (Shopify, etc.)
        if not best_match or best_confidence < 7:
            try:
                js_name = await page.evaluate(
                    """() => {
                        // Try Shopify
                        if (window.ShopifyAnalytics?.meta?.product?.title) {
                            return window.ShopifyAnalytics.meta.product.title;
                        }
                        // Try WooCommerce
                        if (window.wc_product_data?.title) {
                            return wc_product_data.title;
                        }
                        // Try JSON-LD schema
                        const jsonLD = document.querySelector('script[type="application/ld+json"]');
                        if (jsonLD) {
                            try {
                                const data = JSON.parse(jsonLD.textContent);
                                if (data.name) return data.name;
                                if (data['@graph']) {
                                    const product = data['@graph'].find(item => item['@type'] === 'Product');
                                    if (product?.name) return product.name;
                                }
                            } catch (e) {}
                        }
                        return null;
                    }"""
                )
                if js_name and 3 < len(js_name) < 150:
                    cleaned = ProductNameExtractor._cleanup_name(js_name)
                    if ProductNameExtractor._is_valid_product_name(cleaned):
                        best_match = cleaned
                        best_confidence = 8
            except:
                pass
        
        # Return if we found a decent match
        if best_match and best_confidence >= 6:
            return best_match
        
        # Strategy 3: Fallback selectors
        for selector, attr_type, confidence in ProductNameExtractor.FALLBACK_SELECTORS:
            try:
                el = await page.query_selector(selector)
                if el:
                    if attr_type == "text":
                        text = (await el.text_content() or "").strip()
                    else:
                        text = (await el.get_attribute(attr_type) or "").strip()
                    
                    if 3 < len(text) < 150:
                        cleaned = ProductNameExtractor._cleanup_name(text)
                        if ProductNameExtractor._is_valid_product_name(cleaned):
                            if confidence > best_confidence:
                                best_match = cleaned
                                best_confidence = confidence
            except:
                continue
        
        # Strategy 4: Content-based extraction (last resort)
        if not best_match or best_confidence < 4:
            try:
                content_name = await page.evaluate(
                    """() => {
                        // Look for prominent text in main content area
                        const main = document.querySelector('main, [role="main"], .main-content, #main-content, .product-main');
                        if (main) {
                            // Find the first prominent heading
                            const heading = main.querySelector('h1, h2, .product-title, [class*="product-name"]');
                            if (heading && heading.textContent.trim().length > 3) {
                                return heading.textContent.trim();
                            }
                        }
                        return null;
                    }"""
                )
                if content_name and 3 < len(content_name) < 150:
                    cleaned = ProductNameExtractor._cleanup_name(content_name)
                    if ProductNameExtractor._is_valid_product_name(cleaned):
                        best_match = cleaned
            except:
                pass
        
        # Final validation: check for login/error pages
        if best_match:
            if ProductNameExtractor._is_invalid_page(best_match):
                print(f"🚫 Detected login/error page: '{best_match}' - returning None")
                return None
            return best_match
        
        # Last resort: return None (will trigger placeholder in scraper)
        return None
    
    @staticmethod
    def _cleanup_name(name: str) -> str:
        """Clean up product name by removing branding and extra content."""
        if not name:
            return ""
        
        # Apply cleanup patterns
        cleaned = name
        for pattern, replacement in ProductNameExtractor.CLEANUP_PATTERNS:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove emoji and special characters (keep basic punctuation)
        cleaned = re.sub(r'[^\w\s\-&\'\".,()]+', '', cleaned)
        
        return cleaned
    
    @staticmethod
    def _is_valid_product_name(name: str) -> bool:
        """Check if the extracted text is a valid product name."""
        if not name or len(name) < 3:
            return False
        
        # Should contain at least some alphanumeric characters
        if not re.search(r'[a-zA-Z0-9]', name):
            return False
        
        # Should not be just numbers
        if re.match(r'^\d+$', name):
            return False
        
        # Should not be just special characters
        if re.match(r'^[^\w\s]+$', name):
            return False
        
        return True
    
    @staticmethod
    def _is_invalid_page(name: str) -> bool:
        """Check if the page is a login/error page based on product name."""
        if not name:
            return True
        
        name_lower = name.lower()
        
        # Check for invalid indicators
        for indicator in ProductNameExtractor.INVALID_INDICATORS:
            if indicator in name_lower:
                # Allow if it has other content (e.g., "Login to view Amazing Product")
                if len(name.split()) <= 4:  # Short messages like "Login • Instagram"
                    return True
        
        return False
    
    @staticmethod
    def detect_survey_page(html_text: str, url: str) -> bool:
        """
        Detect if a page is a survey/quiz page using keyword-based detection.
        This runs AFTER product extraction and does not interfere with it.
        
        Args:
            html_text: The HTML content of the page
            url: The URL of the page
            
        Returns:
            True if the page is a survey/quiz, False otherwise
        """
        if not html_text and not url:
            return False
        
        import re
        
        # Layer 1: Visible Text Check (Main Layer)
        # Extract visible text by removing HTML tags
        visible_text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
        visible_text = re.sub(r'<style[^>]*>.*?</style>', '', visible_text, flags=re.DOTALL | re.IGNORECASE)
        visible_text = re.sub(r'<[^>]+>', ' ', visible_text)
        visible_text_lower = visible_text.lower()
        
        # Visible text phrases that indicate a quiz/survey (specific multi-word phrases only)
        visible_phrases = [
            "take our quiz", "personalized plan",
            "start quiz", "calculate your", "step 1 of",
            "next question", "take the quiz",
            "start assessment", "start the quiz"
        ]
        
        for phrase in visible_phrases:
            if phrase in visible_text_lower:
                print(f"🔍 SURVEY DETECTED (Visible Text): '{phrase}' in {url[:60]}...")
                return True
        
        # Layer 2: URL Detection
        url_lower = url.lower() if url else ""
        flow_keywords = ["quiz", "assessment", "onboarding"]
        
        # Check URL for quiz keywords
        for keyword in flow_keywords:
            if keyword in url_lower:
                print(f"🔍 SURVEY DETECTED (URL): '{keyword}' in {url[:60]}...")
                return True
        
        return False
    
    @staticmethod
    def detect_product_page(html_text: str) -> bool:
        """
        Detect if a page is a product page based on e-commerce indicators.
        This runs AFTER survey detection and uses lightweight text-based matching only.
        
        Args:
            html_text: The HTML content of the page
            
        Returns:
            True if the page shows clear signs of a single-product e-commerce page
        """
        if not html_text:
            return False
        
        html_lower = html_text.lower()
        
        # A. Purchase Intent Keywords - strong signals for product pages
        purchase_keywords = [
            "add to cart", "buy now", "select size", "choose color", 
            "quantity", "in stock", "sold out", "add to bag", 
            "checkout", "pay now", "shop now", "add to basket",
            "purchase", "order now", "get it now", "buy it now"
        ]
        
        # B. Product Details / Specs Keywords - supporting signals
        product_detail_keywords = [
            "description", "specifications", "materials", "ingredients", 
            "how to use", "shipping info", "return policy", "product details",
            "features", "dimensions", "care instructions"
        ]
        
        # C. Single Product Signal - indicates single product focus
        single_product_signals = [
            "this product", "our product", "the product", "the item", 
            "your order", "this item"
        ]
        
        # Check for purchase intent (highest confidence)
        purchase_found = any(keyword in html_lower for keyword in purchase_keywords)
        
        # Check for product details
        details_found = any(keyword in html_lower for keyword in product_detail_keywords)
        
        # Check for single product signals
        single_product_found = any(signal in html_lower for signal in single_product_signals)
        
        # Check if plural indicators dominate (collection/catalog pages)
        plural_indicators = ["products", "shop all", "view all", "browse", "category"]
        plural_count = sum(1 for indicator in plural_indicators if indicator in html_lower)
        
        # Classification logic:
        # If we find purchase keywords OR (details + single product signals)
        # AND plural indicators don't dominate, it's a product page
        if purchase_found:
            return True
        
        if details_found and single_product_found and plural_count < 3:
            return True
        
        return False
