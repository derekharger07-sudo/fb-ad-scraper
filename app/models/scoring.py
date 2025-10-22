from typing import List, Optional

def cold_start_score(metrics: dict | None, angle_tags: List[str], geos: List[str] | None, price_hint: Optional[float] = None) -> float:
    base = 50.0
    if "testimonial" in angle_tags: base += 5
    if "pain" in angle_tags: base += 4
    if geos and len(geos) <= 2: base += 3  # potential whitespace
    if price_hint and 29 <= price_hint <= 59: base += 3
    likes = (metrics or {}).get("likes") if isinstance(metrics, dict) else None
    if likes and likes > 1000: base += 2
    return float(max(0.0, min(100.0, base)))
