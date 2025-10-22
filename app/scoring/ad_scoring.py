import math
from typing import Dict

# --- Saturating transform constants ---
V95 = 10_000_000  # 95th percentile traffic
AGE_PLATEAU = 120  # days where ad is proven
DUPS_HALF = 5  # half-credit duplicates

def visits_score(monthly_visits: int) -> float:
    """
    Saturating transform for monthly visits.
    Returns value between 0 and 1.
    """
    if monthly_visits is None or monthly_visits <= 0:
        return 0.0
    return min(1.0, math.log1p(monthly_visits) / math.log1p(V95))

def age_score(days: int) -> float:
    """
    Saturating transform for ad age with bonus for very old ads.
    Returns value between 0 and 1.
    """
    if days is None or days <= 0:
        return 0.0
    
    # Base score: linear up to AGE_PLATEAU
    a = min(days, AGE_PLATEAU) / AGE_PLATEAU
    
    # Bonus for ads beyond plateau (evergreen proof)
    bonus = 0.0
    if days > AGE_PLATEAU:
        bonus = min(0.1, math.log1p(max(0, days - AGE_PLATEAU)) / math.log(1 + 365 - AGE_PLATEAU)) * 0.2
    
    return min(1.0, a + bonus)

def dup_score(dups: int) -> float:
    """
    Saturating transform for duplicate count (creative variants).
    Returns value between 0 and 1.
    More duplicates = higher score (indicates testing/scaling).
    """
    if dups is None or dups < 0:
        return 0.0
    
    k = math.log(2) / DUPS_HALF
    return 1.0 - math.exp(-k * max(0, dups))

def calculate_ad_score(monthly_visits: int, ad_age_days: int, duplicate_count: int) -> int:
    """
    Weighted composite score using saturating transforms.
    
    Args:
        monthly_visits: Estimated monthly site traffic
        ad_age_days: Days the ad has been running
        duplicate_count: Number of creative variants (excluding self)
    
    Returns:
        Score from 0-100
    """
    s = (
        dup_score(duplicate_count) * 0.45 +
        age_score(ad_age_days) * 0.35 +
        visits_score(monthly_visits) * 0.20
    )
    return round(s * 100)

def stars_from_score(score: int) -> int:
    """
    Convert score (0-100) to star rating (1-5).
    """
    if score >= 80:
        return 5
    elif score >= 60:
        return 4
    elif score >= 40:
        return 3
    elif score >= 20:
        return 2
    else:
        return 1

def score_ad(ad: Dict) -> Dict:
    """
    Takes a single ad dict and returns it with scoring fields added.
    Uses weighted formula: duplicates (45%), age (35%), visits (20%).
    """
    monthly_visits = ad.get("monthly_visits") or 0
    days_running = ad.get("days_running") or 0
    
    # creative_variant_count includes the ad itself, so subtract 1 for duplicates
    creative_variant_count = ad.get("creative_variant_count") or 1
    duplicate_count = max(0, creative_variant_count - 1)
    
    # Calculate weighted composite score (0-100)
    total_score = calculate_ad_score(monthly_visits, days_running, duplicate_count)
    
    # Calculate star rating
    stars = stars_from_score(total_score)
    
    # Add scoring fields to ad
    ad["total_score"] = total_score
    ad["stars"] = stars
    
    # Keep old scoring fields as null for backward compatibility
    ad["demand_score"] = None
    ad["competition_score"] = None
    ad["angle_score"] = None
    ad["geo_score"] = None
    
    return ad
