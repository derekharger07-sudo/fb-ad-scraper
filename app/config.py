import os

# Browser configuration
# Use Playwright's default Chromium (works on Windows, Mac, Linux)
# Set CHROMIUM_BIN env variable to override if needed
CHROMIUM_BIN = os.getenv("CHROMIUM_BIN", None)  # None = use Playwright default

# Page loading configuration
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "20000"))  # 20 seconds default

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dev.db")

# Helper to load from text files
def load_list(path: str):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

# Scraping configuration
SEARCH_QUERIES = load_list("keywords.txt") or ["leggings", "supplements", "gaming chair"]
COUNTRIES = load_list("countries.txt") or ["US"]
MAX_ADS_PER_QUERY = int(os.getenv("MAX_ADS_PER_QUERY", "100"))

# 🔎 Debug prints
print("🔎 Loaded queries:", SEARCH_QUERIES)
print("🔎 Loaded countries:", COUNTRIES)
print("🔎 Max ads per query:", MAX_ADS_PER_QUERY)
