import os
import requests

# ✅ RapidAPI credentials
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "0021f31222mshc787216197e8947p13e89bjsn11276befd073")
BASE_URL = "https://similarweb12.p.rapidapi.com/v2/website-analytics/"
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "similarweb12.p.rapidapi.com",
    "Accept": "application/json"
}

def get_monthly_visits(domain: str) -> dict:
    """
    Fetch monthly visits for a given domain using SimilarWeb v2 Website Analytics.
    Returns only the total visits count (traffic.visitsTotalCount).
    """
    params = {"domain": domain}

    try:
        res = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=15)
        res.raise_for_status()
        data = res.json()

        visits = None
        if data.get("status") == "success":
            # Safely extract from nested traffic data
            traffic = data.get("traffic", {})
            visits = traffic.get("visitsTotalCount")

        result = {"domain": domain, "monthly_visits": visits}
        print(f"✅ {domain} — Monthly Visits: {visits}")
        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Request error for {domain}: {e}")
        return {"domain": domain, "monthly_visits": None}
