# =============================================
# 🧮 Traffic Calibration Based on Tier Ratios
# =============================================

def estimate_monthly_visits(spyfu_clicks, tier=None):
    """
    Converts SpyFu's estimated SEO clicks into estimated total monthly visits.
    Uses empirically derived ratios based on calibration tests.
    
    Args:
        spyfu_clicks: Monthly SEO clicks from SpyFu API
        tier: Optional tier classification ("high", "mid", "low")
              If None, will auto-detect based on SpyFu clicks volume
    
    Returns:
        Estimated total monthly visits (float)
    """

    # Default multipliers (based on your actual data analysis)
    TIER_MULTIPLIERS = {
        "high": 66,   # 100M+ sites (Nike, Walmart, Apple, Shein)
        "mid": 47,    # 1–20M visits (Gymshark, Alo, YoungLA, etc.)
        "low": 85     # 50K–1M visits (Shecurve, small DTC brands)
    }

    # Handle nulls or missing data
    if spyfu_clicks is None or spyfu_clicks == 0:
        return 0

    # Auto-detect tier if not specified based on SpyFu clicks volume
    if tier is None:
        if spyfu_clicks >= 1_500_000:  # 1.5M+ SEO clicks → high tier
            tier = "high"
        elif spyfu_clicks >= 20_000:   # 20K+ SEO clicks → mid tier
            tier = "mid"
        else:                           # <20K SEO clicks → low tier
            tier = "low"

    # Choose tier multiplier
    multiplier = TIER_MULTIPLIERS.get(tier, 47)  # default to mid if unspecified

    # Convert SpyFu SEO clicks → Total Visits
    estimated_visits = spyfu_clicks * multiplier

    return estimated_visits


def get_tier_from_visits(spyfu_clicks):
    """Helper to determine tier based on SpyFu clicks."""
    if spyfu_clicks is None or spyfu_clicks == 0:
        return "unknown"
    
    if spyfu_clicks >= 1_500_000:
        return "high"
    elif spyfu_clicks >= 20_000:
        return "mid"
    else:
        return "low"
