#!/usr/bin/env python3
"""
🏷️ AD CATEGORY CLASSIFIER
Lightweight AI-driven classification that enriches existing ads with product niches.
Uses keyword matching and semantic similarity (no heavy external APIs).

This is a gentle add-on that:
- Preserves all existing data and scraping flow
- Adds a new `category` field to each ad
- Runs on your existing ~10,000 ad dataset
- Follows your current naming conventions and code style
"""

import re
from typing import Optional, List
from multiprocessing import Pool, cpu_count
from sqlmodel import Session, select
from app.db.models import AdCreative
from app.db.repo import engine
import time

# 🎯 Category definitions with keyword patterns
CATEGORY_KEYWORDS = {
    "Beauty & Health": [
        "skincare", "makeup", "beauty", "cosmetic", "serum", "cream", "lotion", "moisturizer",
        "anti-aging", "wrinkle", "facial", "cleanser", "toner", "mask", "spa", "wellness",
        "vitamin", "supplement", "protein", "collagen", "hair care", "shampoo", "conditioner",
        "fragrance", "perfume", "deodorant", "nail", "manicure", "pedicure", "massage",
        "essential oil", "aromatherapy", "skin", "face", "body", "lip", "eye", "acne",
        "sunscreen", "spf", "glow", "radiant", "healthy skin", "natural beauty"
    ],
    
    "Women's Clothing": [
        "dress", "blouse", "skirt", "women's", "ladies", "gown", "top", "leggings",
        "cardigan", "sweater", "pants", "jeans", "jumpsuit", "romper", "tunic", "tank top",
        "maxi", "midi", "mini", "cocktail dress", "evening dress", "casual wear",
        "activewear women", "yoga pants", "sports bra", "women's jacket", "coat women"
    ],
    
    "Men's Clothing": [
        "men's shirt", "polo", "t-shirt men", "men's pants", "chinos", "suit", "blazer men",
        "men's jacket", "hoodie men", "sweatshirt men", "men's shorts", "cargo pants",
        "button-down", "dress shirt", "casual shirt", "men's jeans", "men's activewear"
    ],
    
    "Shoes": [
        "shoes", "sneakers", "boots", "sandals", "heels", "flats", "loafers", "slippers",
        "running shoes", "athletic shoes", "dress shoes", "casual shoes", "footwear",
        "trainers", "pumps", "wedges", "mules", "oxfords", "ankle boots", "knee boots"
    ],
    
    "Jewelry & Accessories": [
        "jewelry", "necklace", "bracelet", "earring", "ring", "pendant", "chain",
        "watch", "brooch", "anklet", "charm", "gemstone", "diamond", "gold", "silver",
        "pearl", "crystal", "accessory", "fashion jewelry", "fine jewelry"
    ],
    
    "Watches": [
        "watch", "timepiece", "smartwatch", "fitness watch", "chronograph", "wristwatch",
        "luxury watch", "sports watch", "digital watch", "analog watch"
    ],
    
    "Luggage & Bags": [
        "bag", "handbag", "backpack", "purse", "tote", "clutch", "satchel", "messenger bag",
        "duffel", "luggage", "suitcase", "travel bag", "crossbody", "shoulder bag",
        "wallet", "briefcase", "laptop bag", "diaper bag", "gym bag"
    ],
    
    "Home & Garden": [
        "plant", "garden", "outdoor", "patio", "lawn", "gardening", "flower", "seeds",
        "planter", "pot", "vase", "watering", "fertilizer", "soil", "landscaping",
        "yard", "deck", "fence", "greenhouse", "herb garden", "succulent"
    ],
    
    "Home Improvement": [
        "drill", "saw", "hammer", "paint", "hardware", "renovation", "repair", "diy",
        "construction", "building", "plumbing", "electrical", "flooring", "tile",
        "roofing", "insulation", "ceiling", "door", "window", "cabinet"
    ],
    
    "Furniture": [
        "sofa", "couch", "chair", "table", "desk", "bed", "mattress", "dresser",
        "bookshelf", "cabinet", "nightstand", "ottoman", "bench", "stool", "sectional",
        "recliner", "dining table", "coffee table", "office chair", "wardrobe"
    ],
    
    "Home Appliances": [
        "refrigerator", "washing machine", "dryer", "dishwasher", "microwave", "oven",
        "stove", "freezer", "vacuum", "air conditioner", "heater", "fan", "humidifier",
        "dehumidifier", "water heater", "garbage disposal", "range hood"
    ],
    
    "Consumer Electronics": [
        "phone", "smartphone", "tablet", "laptop", "computer", "tv", "television",
        "monitor", "speaker", "headphone", "earbuds", "camera", "gaming", "console",
        "smart home", "alexa", "google home", "drone", "projector", "keyboard", "mouse"
    ],
    
    "Cellphones & Telecommunication": [
        "iphone", "android", "samsung", "mobile phone", "cell phone", "phone case",
        "screen protector", "charger", "power bank", "phone mount", "sim card",
        "wireless charger", "phone accessories", "bluetooth headset"
    ],
    
    "Computer & Office": [
        "printer", "scanner", "toner", "ink", "office supplies", "stationery", "paper",
        "notebook", "pen", "pencil", "marker", "folder", "binder", "calculator",
        "laminator", "shredder", "desk organizer", "filing cabinet"
    ],
    
    "Education & Office Supplies": [
        "school supplies", "textbook", "learning", "educational", "classroom",
        "teaching", "study", "homework", "backpack school", "lunchbox", "pencil case",
        "eraser", "ruler", "compass", "protractor", "glue", "tape", "scissors"
    ],
    
    "Sports & Entertainment": [
        "fitness", "exercise", "workout", "gym", "sports equipment", "athletic",
        "yoga mat", "dumbbells", "resistance band", "treadmill", "bike", "basketball",
        "football", "soccer", "tennis", "golf", "swim", "skateboard", "camping",
        "hiking", "fishing", "hunting", "outdoor recreation"
    ],
    
    "Toys & Hobbies": [
        "toy", "doll", "action figure", "lego", "puzzle", "board game", "kids toy",
        "stuffed animal", "rc car", "remote control", "play set", "craft", "hobby",
        "model kit", "collectible", "trading card", "arts and crafts", "coloring"
    ],
    
    "Mother & Kids": [
        "baby", "infant", "toddler", "children", "kids clothing", "maternity",
        "pregnancy", "nursing", "breastfeeding", "diaper", "stroller", "car seat",
        "crib", "high chair", "baby monitor", "pacifier", "bottle", "baby food"
    ],
    
    "Pet Products": [
        "pet", "dog", "cat", "puppy", "kitten", "pet food", "pet toy", "leash",
        "collar", "pet bed", "litter box", "aquarium", "fish", "bird", "hamster",
        "pet grooming", "pet carrier", "pet supplies"
    ],
    
    "Food": [
        "snack", "chocolate", "candy", "coffee", "tea", "protein bar", "nutrition",
        "organic food", "gourmet", "meal", "recipe", "cooking", "baking", "spice",
        "sauce", "condiment", "beverage", "drink", "smoothie", "juice"
    ],
    
    "Automobiles & Motorcycles": [
        "car", "auto", "vehicle", "motorcycle", "bike", "automotive", "car accessories",
        "car parts", "tire", "wheel", "motor oil", "car care", "dash cam", "gps",
        "car seat cover", "floor mat", "bike helmet", "motorcycle gear"
    ],
    
    "Tools": [
        "tool", "wrench", "screwdriver", "pliers", "toolbox", "power tool",
        "hand tool", "mechanic", "workshop", "garage", "socket set", "allen key",
        "utility knife", "measuring tape", "level", "clamp"
    ],
    
    "Lights & Lighting": [
        "light", "lamp", "led", "bulb", "chandelier", "pendant light", "ceiling light",
        "floor lamp", "table lamp", "wall sconce", "string lights", "fairy lights",
        "outdoor lighting", "solar light", "flashlight", "lantern", "night light"
    ],
    
    "Security & Protection": [
        "security camera", "alarm system", "door lock", "safe", "surveillance",
        "home security", "sensor", "motion detector", "doorbell camera", "cctv",
        "access control", "keypad", "biometric", "guard", "protection"
    ],
    
    "Weddings & Events": [
        "wedding", "bride", "groom", "engagement", "anniversary", "party supplies",
        "decoration", "invitation", "favor", "centerpiece", "bouquet", "veil",
        "wedding dress", "tuxedo", "ceremony", "reception", "celebration"
    ],
    
    "Gift": [
        "gift", "present", "gift card", "gift box", "gift basket", "gift set",
        "personalized gift", "custom gift", "birthday gift", "holiday gift",
        "anniversary gift", "valentine", "christmas gift", "gift for him", "gift for her"
    ],
    
    "Underwear & Accessories": [
        "underwear", "lingerie", "bra", "panties", "boxers", "briefs", "undershirt",
        "camisole", "sleepwear", "pajamas", "nightgown", "robe", "intimates",
        "shapewear", "compression wear"
    ],
    
    "Hair Extensions & Wigs": [
        "wig", "hair extension", "hairpiece", "hair weave", "toupee", "lace front",
        "clip-in hair", "human hair", "synthetic hair", "hair bundle", "closure",
        "frontal", "hair topper"
    ],
    
    "Novelty & Special Use": [
        "novelty", "gag gift", "prank", "costume", "cosplay", "halloween", "mascot",
        "special occasion", "theme party", "prop", "memorabilia", "collectible item"
    ],
    
    "Electronic Components & Supplies": [
        "resistor", "capacitor", "transistor", "diode", "circuit", "pcb", "breadboard",
        "arduino", "raspberry pi", "sensor", "wire", "cable", "connector", "led strip",
        "relay", "module", "component kit", "soldering"
    ],
    
    "Virtual Goods": [
        "game currency", "in-game", "digital download", "virtual item", "game code",
        "gift card digital", "ebook", "software license", "app subscription",
        "online course", "digital art", "nft"
    ]
}


def classify_ad(ad: AdCreative) -> Optional[str]:
    """
    Classify an ad into a product category using keyword matching.
    Analyzes caption, product_name, account_name, and landing_url.
    
    Returns the best matching category or None if no match found.
    """
    # Gather all available text fields
    text_parts = []
    
    if ad.caption:
        text_parts.append(ad.caption.lower())
    if ad.product_name:
        text_parts.append(ad.product_name.lower())
    if ad.account_name:
        text_parts.append(ad.account_name.lower())
    if ad.landing_url:
        text_parts.append(ad.landing_url.lower())
    
    if not text_parts:
        return None
    
    # Combine all text
    combined_text = " ".join(text_parts)
    
    # Score each category based on keyword matches
    category_scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        matched_keywords = []
        
        for keyword in keywords:
            # Use word boundaries for more accurate matching
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = len(re.findall(pattern, combined_text))
            
            if matches > 0:
                # Weight longer keywords higher (more specific)
                keyword_weight = len(keyword.split())
                score += matches * keyword_weight
                matched_keywords.append(keyword)
        
        if score > 0:
            category_scores[category] = {
                "score": score,
                "matched_keywords": matched_keywords
            }
    
    # Return category with highest score
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1]["score"])
        return best_category[0]
    
    return "Other"  # Default category if no matches


def classify_ad_batch(ad_data_list):
    """
    Classify a batch of ads (for parallel processing).
    
    Args:
        ad_data_list: List of tuples (id, caption, product_name, account_name, landing_url)
    
    Returns:
        List of tuples (id, category)
    """
    results = []
    for ad_data in ad_data_list:
        ad_id, caption, product_name, account_name, landing_url = ad_data
        
        # Gather text fields
        text_parts = []
        if caption:
            text_parts.append(caption.lower())
        if product_name:
            text_parts.append(product_name.lower())
        if account_name:
            text_parts.append(account_name.lower())
        if landing_url:
            text_parts.append(landing_url.lower())
        
        if not text_parts:
            results.append((ad_id, "Other"))
            continue
        
        combined_text = " ".join(text_parts)
        
        # Score categories
        category_scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = len(re.findall(pattern, combined_text))
                if matches > 0:
                    keyword_weight = len(keyword.split())
                    score += matches * keyword_weight
            
            if score > 0:
                category_scores[category] = score
        
        # Get best category
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
            results.append((ad_id, best_category))
        else:
            results.append((ad_id, "Other"))
    
    return results


def classify_all_ads(batch_size: int = 1000, limit: Optional[int] = None, workers: Optional[int] = None):
    """
    Classify all ads in the database using parallel processing.
    
    Args:
        batch_size: Number of ads to process per batch
        limit: Maximum number of ads to classify (None = all)
        workers: Number of parallel workers (None = use all CPU cores)
    """
    start_time = time.time()
    
    # Use all available CPU cores if not specified
    if workers is None:
        workers = cpu_count()
    
    print("=" * 80)
    print("🏷️  AD CATEGORY CLASSIFIER - TURBO MODE")
    print("=" * 80)
    print(f"🚀 CPU Cores: {cpu_count()} available, using {workers} workers")
    print(f"💾 Batch size: {batch_size:,} ads per batch")
    print("=" * 80)
    
    with Session(engine) as session:
        # Get all ads without a category
        stmt = select(
            AdCreative.id,
            AdCreative.caption,
            AdCreative.product_name,
            AdCreative.account_name,
            AdCreative.landing_url
        ).where(
            (AdCreative.category.is_(None)) | (AdCreative.category == '')
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        ads_data = session.exec(stmt).all()
        
        if not ads_data:
            print("✅ All ads are already classified!")
            return
        
        total = len(ads_data)
        print(f"📊 Found {total:,} ads to classify")
        print()
        
        # Split into chunks for parallel processing
        chunk_size = max(1, total // (workers * 4))  # Create 4x chunks per worker for load balancing
        chunks = [ads_data[i:i+chunk_size] for i in range(0, total, chunk_size)]
        
        print(f"⚡ Processing {len(chunks)} chunks across {workers} CPU cores...")
        print()
        
        # Parallel processing
        all_results = []
        with Pool(processes=workers) as pool:
            for i, results in enumerate(pool.imap_unordered(classify_ad_batch, chunks), 1):
                all_results.extend(results)
                progress = (len(all_results) / total) * 100
                print(f"✅ Progress: {len(all_results):,}/{total:,} ads ({progress:.1f}%) - Chunk {i}/{len(chunks)}")
        
        # Update database in batches
        print("\n💾 Saving results to database...")
        category_counts = {}
        
        for i in range(0, len(all_results), batch_size):
            batch = all_results[i:i+batch_size]
            
            for ad_id, category in batch:
                ad = session.get(AdCreative, ad_id)
                if ad:
                    ad.category = category
                    session.add(ad)
                    category_counts[category] = category_counts.get(category, 0) + 1
            
            session.commit()
            print(f"  💾 Saved {min(i+batch_size, len(all_results)):,}/{len(all_results):,} ads")
        
        elapsed = time.time() - start_time
        ads_per_sec = total / elapsed if elapsed > 0 else 0
        
        # Print results
        print("\n" + "=" * 80)
        print("🎯 CLASSIFICATION COMPLETE")
        print("=" * 80)
        print(f"✅ Total ads classified: {len(all_results):,}")
        print(f"⏱️  Time elapsed: {elapsed:.1f} seconds")
        print(f"⚡ Speed: {ads_per_sec:.0f} ads/second")
        print()
        print("📊 Category Distribution:")
        print("-" * 80)
        
        # Sort by count descending
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        
        for category, count in sorted_categories:
            percentage = (count / len(all_results) * 100) if all_results else 0
            bar = "█" * int(percentage / 2)
            print(f"{category:30s} {count:5,} ads ({percentage:5.1f}%) {bar}")
        
        print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Classify Facebook ads into product categories - TURBO MODE")
    parser.add_argument("--limit", type=int, default=None, help="Max ads to classify (default: all)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for DB writes (default: 1000)")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel workers (default: all CPU cores)")
    
    args = parser.parse_args()
    
    classify_all_ads(batch_size=args.batch_size, limit=args.limit, workers=args.workers)
