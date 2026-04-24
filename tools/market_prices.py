import json
import os
import re
from datetime import date as _date_cls, timedelta

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "market_prices.json")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "price_history.json")

# Common alternate names → canonical district key in market_prices.json
_MARKET_ALIASES = {
    "kochi":          "Ernakulam",
    "cochin":         "Ernakulam",
    "ekm":            "Ernakulam",
    "trivandrum":     "Thiruvananthapuram",
    "tvm":            "Thiruvananthapuram",
    "calicut":        "Kozhikode",
    "alleppey":       "Alappuzha",
    "quilon":         "Kollam",
}


def _resolve_market(requested: str, available: list[str]) -> str | None:
    """Resolve a market name to a district key, trying aliases first."""
    req = requested.lower().strip()

    # 1. Check alias table
    if req in _MARKET_ALIASES:
        canonical = _MARKET_ALIASES[req]
        if canonical in available:
            return canonical

    # 2. Exact case-insensitive match
    for key in available:
        if key.lower() == req:
            return key

    # 3. Substring match
    for key in available:
        if req in key.lower() or key.lower() in req:
            return key

    return None


def _fuzzy_match(requested: str, available: list[str]) -> str | None:
    """Return the best matching key from available, or None."""
    req = requested.lower().strip()
    # Exact case-insensitive match
    for key in available:
        if key.lower() == req:
            return key
    # Substring match (e.g. "seer" matches "Seer Fish")
    for key in available:
        if req in key.lower() or key.lower() in req:
            return key
    return None


def _load_prices() -> dict:
    """Load prices from file, scraping fresh data first if today's prices are missing."""
    from datetime import date as _date
    prices = {}
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r") as f:
                prices = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    last_updated = prices.get("_metadata", {}).get("last_updated")
    if last_updated != _date.today().isoformat():
        print("[PriceScraper] Prices stale — scraping on demand...")
        try:
            from tools.price_scraper import run_scrape
            prices = run_scrape()
        except Exception as e:
            print(f"[PriceScraper] On-demand scrape failed: {e}")

    return prices


def get_market_price(fish_type: str, market: str) -> dict:
    prices = _load_prices()

    # Skip metadata key
    city_keys = [k for k in prices if not k.startswith("_")]

    # Resolve market via aliases then fuzzy match
    matched_market = _resolve_market(market, city_keys)
    if not matched_market:
        return {"error": f"Market '{market}' not found", "available": city_keys}

    market_prices = prices[matched_market]

    # Exact match first, then fuzzy
    if fish_type in market_prices:
        matched_fish = fish_type
    else:
        matched_fish = _fuzzy_match(fish_type, list(market_prices.keys()))

    if not matched_fish:
        return {"error": "Fish type not found", "available": list(market_prices.keys())}

    # Include last_updated from metadata if available
    last_updated = prices.get("_metadata", {}).get("last_updated")

    return {
        "fish_type": matched_fish,
        "market": matched_market,
        "price": market_prices[matched_fish],
        "unit": "per kg",
        "last_updated": last_updated,
    }


def _resolve_date(date_str: str) -> str | None:
    """
    Resolve a relative or absolute date string to YYYY-MM-DD.
    Accepts: 'yesterday', '2 days ago', 'YYYY-MM-DD'.
    Returns None if unparseable.
    """
    today = _date_cls.today()
    s = date_str.strip().lower()

    if s == "yesterday":
        return (today - timedelta(days=1)).isoformat()

    # "N days ago"
    m = re.match(r"(\d+)\s+days?\s+ago", s)
    if m:
        return (today - timedelta(days=int(m.group(1)))).isoformat()

    # ISO date: YYYY-MM-DD
    if re.match(r"\d{4}-\d{2}-\d{2}", date_str.strip()):
        return date_str.strip()

    return None


def get_price_history(fish_type: str, market: str, days: int = 7, date: str = None) -> dict:
    """
    Return price trend for a fish variety in a given market.

    If `date` is given (YYYY-MM-DD, 'yesterday', or 'N days ago'), return
    the price for that specific day only (if it falls within the stored history).
    Otherwise return the last `days` entries as a trend.
    """
    if not os.path.exists(HISTORY_PATH):
        return {"error": "No price history available yet. Run the scraper first."}

    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("history", [])
    except (json.JSONDecodeError, OSError):
        return {"error": "Could not read price history file."}

    # Resolve a specific date lookup
    target_date = None
    if date:
        target_date = _resolve_date(date)
        if not target_date:
            return {"error": f"Could not understand date '{date}'. Use YYYY-MM-DD or 'yesterday'."}

    # Work with last `days` entries
    window = entries[-days:]

    # Resolve market and fish using alias + fuzzy matching
    matched_market = None
    matched_fish = None
    for entry in reversed(window):
        city_keys = list(entry.get("prices", {}).keys())
        matched_market = _resolve_market(market, city_keys)
        if matched_market:
            variety_keys = list(entry["prices"][matched_market].keys())
            matched_fish = _fuzzy_match(fish_type, variety_keys)
            break

    if not matched_market:
        return {"error": f"Market '{market}' not found in history."}
    if not matched_fish:
        return {"error": f"Fish type '{fish_type}' not found in history for {matched_market}."}

    # ── Single date lookup ──────────────────────────────────────────────
    if target_date:
        for entry in window:
            if entry["date"] == target_date:
                price = entry.get("prices", {}).get(matched_market, {}).get(matched_fish)
                if price is not None:
                    return {
                        "fish_type": matched_fish,
                        "market": matched_market,
                        "date": target_date,
                        "price": price,
                        "unit": "per kg",
                        "note": f"Price on {target_date}",
                    }
        return {
            "error": f"No data for {matched_fish} in {matched_market} on {target_date}. "
                     f"Available dates: {[e['date'] for e in window]}",
        }

    # ── Full trend ──────────────────────────────────────────────────────
    trend = []
    for entry in window:
        city_prices = entry.get("prices", {}).get(matched_market, {})
        price = city_prices.get(matched_fish)
        if price is not None:
            trend.append({"date": entry["date"], "price": price})

    return {
        "fish_type": matched_fish,
        "market": matched_market,
        "history": trend,
        "unit": "per kg",
    }
