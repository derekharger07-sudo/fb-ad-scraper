import os
import time
import requests
import base64
from typing import Dict, Any, List

# Load .env file if running locally
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

# =========================================================
# 🔑 SpyFu API credentials
# =========================================================
SPYFU_API_KEY = os.getenv("SPYFU_API_KEY", "")
print(f"[Debug] Raw SPYFU_API_KEY loaded: {repr(SPYFU_API_KEY[:20]) if SPYFU_API_KEY else 'None'}...")

if ":" in SPYFU_API_KEY:
    API_ID, SECRET_KEY = SPYFU_API_KEY.split(":", 1)
    print(f"[Debug] Split: API_ID={API_ID[:8]}..., SECRET_KEY={SECRET_KEY[:8]}...")
else:
    API_ID = None
    SECRET_KEY = SPYFU_API_KEY
    print(f"[Debug] No ':' found - treating as SECRET only: {SECRET_KEY[:8]}...")

BASE_URL = "https://api.spyfu.com/apis/domain_stats_api/v2/getAllDomainStats"
PPC_MULTIPLIER = 1.10

# =========================================================
# 🧠 Core Function
# =========================================================
def get_seo_clicks(domain: str, country_code: str = "US") -> Dict[str, Any]:
    """
    Fetch live SEO clicks using SpyFu v2 endpoint.
    Returns monthlyOrganicClicks and related SEO metrics from the latest month.
    """
    params = {
        "domain": domain,
        "format": "json",
    }
    headers = {
        "accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    if API_ID and SECRET_KEY:
        credentials = base64.b64encode(f"{API_ID}:{SECRET_KEY}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
        print(f"[Debug] Added Basic Auth header")

    try:
        resp = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
        print(f"[Debug] SpyFu API for {domain}: Status {resp.status_code}")
        print(f"[Debug] Raw response: {resp.text[:500]}...")
        resp.raise_for_status()

        data = resp.json()

        # Handle new response structure with "results" instead of "data"
        if "results" in data and data["results"]:
            # Get the latest month (max searchYear, then searchMonth)
            monthly_data = max(
                data["results"],
                key=lambda x: (x.get("searchYear", 0), x.get("searchMonth", 0))
            )
            seo_clicks = int(float(monthly_data.get("monthlyOrganicClicks", 0)))  # Handle float
            click_value = monthly_data.get("monthlyOrganicValue", 0)
            total_volume = monthly_data.get("totalOrganicResults", 0)

            est_total = round(seo_clicks * PPC_MULTIPLIER)
            return {
                "domain": domain,
                "seo_clicks": seo_clicks,
                "est_total_visits": est_total,
                "click_value": click_value,
                "total_volume": total_volume,
                "status": "ok",
                "search_month": monthly_data.get("searchMonth"),
                "search_year": monthly_data.get("searchYear"),
            }
        else:
            print(f"[Debug] No valid results: {data}")
            return {
                "domain": domain,
                "seo_clicks": None,
                "status": "failed",
                "error": f"No results in response: {data.get('message', 'Unknown')}",
            }

    except requests.exceptions.HTTPError as e:
        resp = e.response
        print(f"[SpyFu HTTP {resp.status_code}] {domain}: Server error")
        print(f"[Debug] Raw response: {resp.text[:500]}...")
        return {
            "domain": domain,
            "seo_clicks": None,
            "status": "failed",
            "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
        }
    except Exception as e:
        print(f"[SpyFu Error] {domain}: {e}")
        return {
            "domain": domain,
            "seo_clicks": None,
            "status": "failed",
            "error": str(e),
        }

# =========================================================
# 🔁 Batch Helper
# =========================================================
def batch_fetch_seo_clicks(
    domains: List[str], country_code: str = "US", delay: float = 1.0, max_retries: int = 2
) -> List[Dict[str, Any]]:
    results = []
    for i, domain in enumerate(domains, 1):
        print(f"[{i}/{len(domains)}] Fetching SpyFu SEO stats for {domain}...")
        result = get_seo_clicks(domain, country_code)
        retries = 0
        while result["status"] == "failed" and retries < max_retries:
            print(f"  Retrying {domain} (attempt {retries + 1})...")
            time.sleep(2.0)
            result = get_seo_clicks(domain, country_code)
            retries += 1
        results.append(result)
        time.sleep(delay)
    return results

# =========================================================
# 🧪 Local test runner
# =========================================================
if __name__ == "__main__":
    test_domains = ["spyfu.com", "nike.com", "gymshark.com"]
    print("\n" + "=" * 80)
    print("🧩 SPYFU API TEST (v2 Domain Stats)")
    print("💡 Endpoint: /apis/domain_stats_api/v2/getAllDomainStats")
    print("=" * 80 + "\n")

    if not SPYFU_API_KEY:
        print("❌ No key! Add SPYFU_API_KEY in Secrets.")
    else:
        print(f"🔑 Key: {'✅ ID:secret' if ':' in SPYFU_API_KEY else '⚠️ Secret only'}")

    results = batch_fetch_seo_clicks(test_domains)
    for r in results:
        print(
            f"\n📊 {r['domain']}: {r['seo_clicks']} SEO clicks | Est total: {r.get('est_total_visits')} | Status: {r['status']}"
        )
        if r.get("search_month") and r.get("search_year"):
            print(f"   📅 Data from: {r['search_month']}/{r['search_year']}")
        if r.get("error"):
            print(f"   ❌ {r['error']}")

    print("\n" + "=" * 80)
    print("🚀 If you get 401 (Unauthorized), double-check SPYFU_API_KEY.")
    print("💡 Run: python app\\workers\\spyfu_api.py")