"""
Fish market price scraper for Kerala — all 9 coastal districts.

Scrapes public HTML price tables from multiple sources and merges them
into data/market_prices.json (latest snapshot) and data/price_history.json
(rolling 10-day log).

Sources:
  - Golden Chennai:  city-specific pages for Kochi, Trivandrum, Calicut,
                     Kannur, Kollam, Thrissur  +  Kerala state-level page
  - prices.org.in:   Kerala state-level average retail (NFDB FMPIS mirror)
  - DaataCenter:     Kerala state-level max retail (extra varieties)

Districts WITHOUT a dedicated city page (Kasaragod, Malappuram, Alappuzha)
receive the Kerala state average derived from the state-level sources.
"""

import json
import os
import random
import re
from datetime import date, datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MARKET_PRICES_PATH = os.path.join(DATA_DIR, "market_prices.json")
HISTORY_PATH = os.path.join(DATA_DIR, "price_history.json")

MAX_HISTORY_DAYS = 7

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ---------------------------------------------------------------------------
# Source URLs — keyed by an internal label
#
# Golden Chennai URL pattern:
#   https://rates.goldenchennai.com/fish-price/{city}-fish-price-today/
# Only specific city slugs return data; others 404 to a generic list page.
# Verified slugs for Kerala: kochi, trivandrum, calicut, kannur, kollam,
# thrissur, kerala.
# Slugs that 404: kozhikode, ernakulam, alappuzha, alleppey, kasaragod,
# malappuram.
# ---------------------------------------------------------------------------
SOURCES = {
    # State-level sources (used for state average + extra varieties)
    "prices_org_in_kerala":      "https://prices.org.in/fish/kerala/",
    "golden_chennai_kerala":     "https://rates.goldenchennai.com/fish-price/kerala-fish-price-today/",
    "daatacenter_kerala":        "https://daatacenter.com/fish-price/fish-price-in-kerala/",

    # City-specific Golden Chennai pages → district mapping below
    "gc_kochi":      "https://rates.goldenchennai.com/fish-price/kochi-fish-price-today/",
    "gc_trivandrum": "https://rates.goldenchennai.com/fish-price/trivandrum-fish-price-today/",
    "gc_calicut":    "https://rates.goldenchennai.com/fish-price/calicut-fish-price-today/",
    "gc_kannur":     "https://rates.goldenchennai.com/fish-price/kannur-fish-price-today/",
    "gc_kollam":     "https://rates.goldenchennai.com/fish-price/kollam-fish-price-today/",
    "gc_thrissur":   "https://rates.goldenchennai.com/fish-price/thrissur-fish-price-today/",
}

# Maps Golden Chennai city-source key → project district name
GC_CITY_TO_DISTRICT = {
    "gc_kochi":      "Ernakulam",
    "gc_trivandrum": "Thiruvananthapuram",
    "gc_calicut":    "Kozhikode",
    "gc_kannur":     "Kannur",
    "gc_kollam":     "Kollam",
    "gc_thrissur":   "Thrissur",
}

# All 9 Kerala coastal districts used by the agent
ALL_DISTRICTS = [
    "Kasaragod",
    "Kannur",
    "Kozhikode",
    "Malappuram",
    "Thrissur",
    "Ernakulam",
    "Alappuzha",
    "Kollam",
    "Thiruvananthapuram",
]

# Districts that have NO dedicated city scrape page — get state average
STATE_AVG_DISTRICTS = {"Kasaragod", "Malappuram", "Alappuzha"}

# ---------------------------------------------------------------------------
# Canonical variety name map  (lowercase scraped name → canonical key)
# ---------------------------------------------------------------------------
VARIETY_MAP = {
    # prices.org.in / Golden Chennai
    "anchovy fish":                   "Anchovy",
    "anchovy (nethili meen)":         "Anchovy",
    "anchovy":                        "Anchovy",
    "netholi":                        "Anchovy",
    "nethili":                        "Anchovy",
    "barracuda fish":                 "Barracuda",
    "barracuda (seela meen)":         "Barracuda",
    "barracuda":                      "Barracuda",
    "seela":                          "Barracuda",
    "crab (nandu)":                   "Crab",
    "crab":                           "Crab",
    "mud crab":                       "Crab",
    "sea crab":                       "Crab",
    "king mackerel fish":             "King Mackerel",
    "king mackerel (vanjaram meen)":  "King Mackerel",
    "king mackerel":                  "King Mackerel",
    "vanjaram":                       "King Mackerel",
    "pomfret fish":                   "Pomfret",
    "pomfret (vavval meen)":          "Pomfret",
    "pomfret":                        "Pomfret",
    "black pomfret":                  "Pomfret",
    "silver pomfret":                 "Pomfret",
    "white pomfret":                  "Pomfret",
    "avoli":                          "Pomfret",
    "prawn (eral)":                   "Prawns",
    "prawn":                          "Prawns",
    "prawns":                         "Prawns",
    "tiger prawn":                    "Prawns",
    "tiger prawns":                   "Prawns",
    "white prawn":                    "Prawns",
    "shrimp":                         "Prawns",
    "chemmeen":                       "Prawns",
    "red snapper fish":               "Red Snapper",
    "red snapper (sankara meen)":     "Red Snapper",
    "red snapper":                    "Red Snapper",
    "sankara":                        "Red Snapper",
    "salmon fish":                    "Salmon",
    "salmon (salmon meen)":           "Salmon",
    "indian salmon":                  "Salmon",
    "salmon":                         "Salmon",
    "rawas":                          "Salmon",
    "sardine fish":                   "Sardine",
    "sardine (mathi meen)":           "Sardine",
    "sardine":                        "Sardine",
    "indian oil sardine":             "Sardine",
    "oil sardine":                    "Sardine",
    "mathi":                          "Sardine",
    "shark (sura meen)":              "Shark",
    "shark":                          "Shark",
    "sura":                           "Shark",
    "tilapia fish":                   "Tilapia",
    "tilapia (jalebi meen)":          "Tilapia",
    "tilapia":                        "Tilapia",
    "jalebi":                         "Tilapia",
    # DaataCenter extras
    "rohu":                           "Rohu",
    "rohu fish":                      "Rohu",
    "indian mackerel (bangda)":       "Mackerel",
    "indian mackerel":                "Mackerel",
    "mackerel":                       "Mackerel",
    "bangda":                         "Mackerel",
    "ayala":                          "Mackerel",
    "pink perch":                     "Pink Perch",
    "pink perch (kilanga)":           "Pink Perch",
    "kilanga":                        "Pink Perch",
    "hilsa":                          "Hilsa",
    "hilsa fish":                     "Hilsa",
    "ilish":                          "Hilsa",
    "katla":                          "Katla",
    "katla fish":                     "Katla",
    "king fish / seer fish":          "Seer Fish",
    "king fish":                      "Seer Fish",
    "seer fish":                      "Seer Fish",
    "seer fish (neymeen)":            "Seer Fish",
    "spanish mackerel":               "Seer Fish",
    "neymeen":                        "Seer Fish",
    "catfish":                        "Catfish",
    "catfish (thedu)":                "Catfish",
    "sea catfish":                    "Catfish",
    "thedu":                          "Catfish",
    "yellow tuna":                    "Tuna",
    "yellow fin tuna":                "Tuna",
    "yellowfin tuna":                 "Tuna",
    "skipjack tuna":                  "Tuna",
    "tuna":                           "Tuna",
    "choora":                         "Tuna",
    "sting ray fish":                 "Sting Ray",
    "sting ray":                      "Sting Ray",
    "stingray":                       "Sting Ray",
    "ray fish":                       "Sting Ray",
    "emperor fish":                   "Emperor Fish",
    "emperor":                        "Emperor Fish",
}


def _canonical(raw: str) -> str | None:
    """Return canonical variety name or None if unrecognised."""
    return VARIETY_MAP.get(raw.lower().strip())


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------

def _fetch_html(url: str, timeout: int = 15) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as exc:
        print(f"  [WARN] Could not fetch {url}: {exc}")
        return None


def _parse_price_value(text: str) -> int | None:
    """
    Parse a price string into an integer INR/kg value.
    Handles ranges like '350-400' or '350 – 400' by averaging.
    Returns None if no valid price found.
    """
    text = text.strip()
    # Handle ranges like '350-400' or '350 – 400' — average them
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", text)
    if range_match:
        lo, hi = float(range_match.group(1)), float(range_match.group(2))
        val = int((lo + hi) / 2)
    else:
        # Extract the first standalone number (handles 'Rs. 700', '₹450/kg', etc.)
        num_match = re.search(r"\d+(?:\.\d+)?", text)
        if not num_match:
            return None
        try:
            val = int(float(num_match.group()))
        except ValueError:
            return None
    return val if 10 <= val <= 10000 else None


def _parse_price_table(soup: BeautifulSoup | None) -> dict[str, int]:
    """
    Extract variety→price (int INR/kg) from the HTML <table> with the most
    recognised fish varieties.

    Fixes over the naive approach:
    - Scans every cell in a row for the variety name (handles serial-number
      first columns like | # | Fish | Price |)
    - Detects the price column from header keywords (retail > price > rate >
      max) and falls back to scanning all non-variety cells for a numeric value
    - Handles price ranges ('350-400') by averaging
    - Picks the table with the most recognised varieties instead of the first
      table that has any match
    """
    if soup is None:
        return {}

    best_result: dict[str, int] = {}

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # ── Detect price column from header row ─────────────────────────
        header_cells = [c.get_text(strip=True).lower()
                        for c in rows[0].find_all(["th", "td"])]
        price_col_idx: int | None = None
        for keyword in ("retail", "price", "rate", "max", "avg"):
            for i, h in enumerate(header_cells):
                if keyword in h:
                    price_col_idx = i
                    break
            if price_col_idx is not None:
                break

        result: dict[str, int] = {}
        for row in rows[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 2:
                continue

            # Find variety name in any cell (not just cells[0])
            canonical: str | None = None
            canonical_idx: int | None = None
            for i, cell in enumerate(cells):
                c = _canonical(cell)
                if c:
                    canonical = c
                    canonical_idx = i
                    break

            if not canonical:
                continue

            # Find price: use detected header column first, then scan backwards
            price: int | None = None
            if (
                price_col_idx is not None
                and price_col_idx < len(cells)
                and price_col_idx != canonical_idx
            ):
                price = _parse_price_value(cells[price_col_idx])

            if not price:
                # Scan from the right, skip the variety cell
                for i in range(len(cells) - 1, -1, -1):
                    if i == canonical_idx:
                        continue
                    price = _parse_price_value(cells[i])
                    if price:
                        break

            if price:
                result[canonical] = price

        # Keep whichever table had the most recognised varieties
        if len(result) > len(best_result):
            best_result = result

    return best_result


def scrape_all_sources() -> dict[str, dict[str, int]]:
    """
    Fetch every URL in SOURCES and parse its price table.
    Returns {source_key: {canonical_variety: price_inr}}.
    """
    scraped: dict[str, dict[str, int]] = {}

    for key, url in SOURCES.items():
        print(f"  Fetching {key} …")
        soup = _fetch_html(url)
        prices = _parse_price_table(soup)
        scraped[key] = prices
        if prices:
            print(f"    → {len(prices)} varieties")
        else:
            print(f"    → (no data)")

    return scraped


# ---------------------------------------------------------------------------
# Build district prices from scraped data
# ---------------------------------------------------------------------------

def _avg(*values: int) -> int:
    valid = [v for v in values if v > 0]
    return round(sum(valid) / len(valid)) if valid else 0


def _state_average(scraped: dict) -> dict[str, int]:
    """Compute Kerala state average from state-level sources."""
    poi       = scraped.get("prices_org_in_kerala", {})
    gc_kerala = scraped.get("golden_chennai_kerala", {})
    dc        = scraped.get("daatacenter_kerala", {})

    # Merge all state-level varieties
    all_vars = set(poi.keys()) | set(gc_kerala.keys()) | set(dc.keys())
    result: dict[str, int] = {}
    for v in all_vars:
        prices = [src.get(v, 0) for src in (poi, gc_kerala, dc)]
        avg = _avg(*prices)
        if avg > 0:
            result[v] = avg
    return result


def build_market_prices(
    scraped: dict[str, dict[str, int]],
    existing: dict,
) -> dict:
    """
    Merge scraped data into all 9 Kerala coastal districts.

    Strategy per district:
      - Districts WITH a GC city page: use city-specific prices as primary,
        DaataCenter state data for extra varieties not on GC.
      - Districts WITHOUT a GC city page (Kasaragod, Malappuram, Alappuzha):
        use state average as primary.
      - Karimeen is never in any scraped source — preserve existing values.
    """
    state_avg = _state_average(scraped)
    dc = scraped.get("daatacenter_kerala", {})

    # Invert GC_CITY_TO_DISTRICT → district→source_key
    district_to_gc = {d: k for k, d in GC_CITY_TO_DISTRICT.items()}

    result: dict = {}
    result["_metadata"] = {
        "last_updated": date.today().isoformat(),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "sources": list(SOURCES.values()),
        "districts": ALL_DISTRICTS,
        "note": (
            "Prices in INR/kg. Indicative only — sources do not guarantee accuracy. "
            "Karimeen prices are carried forward (not available in any scraped source)."
        ),
    }

    for district in ALL_DISTRICTS:
        old = {k: v for k, v in existing.get(district, {}).items()
               if not k.startswith("_")}

        merged = dict(old)             # preserves Karimeen and any manual entries
        merged.update(dc)              # layer in DaataCenter varieties

        if district in STATE_AVG_DISTRICTS:
            merged.update(state_avg)   # state average for districts without a city page
        else:
            gc_key = district_to_gc.get(district)
            gc_city = scraped.get(gc_key, {}) if gc_key else {}
            merged.update(state_avg)   # state average as base
            if gc_city:
                merged.update(gc_city) # city-specific data overrides

        # Preserve Karimeen from existing data
        if "Karimeen" in old:
            merged["Karimeen"] = old["Karimeen"]

        result[district] = dict(sorted(merged.items()))

    return result


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def load_existing_prices() -> dict:
    if not os.path.exists(MARKET_PRICES_PATH):
        return {}
    try:
        with open(MARKET_PRICES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_market_prices(prices: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MARKET_PRICES_PATH, "w", encoding="utf-8") as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)


def update_history(prices: dict) -> None:
    """
    Append today's district prices to the rolling 10-day history.
    If today already exists it is replaced.  Entries beyond MAX_HISTORY_DAYS
    are dropped (oldest first).
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    history: list = []
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f).get("history", [])
        except (json.JSONDecodeError, OSError):
            history = []

    today_str = date.today().isoformat()

    # Replace existing entry for today
    history = [e for e in history if e.get("date") != today_str]

    # Snapshot: district prices only (strip _metadata)
    district_prices = {k: v for k, v in prices.items() if not k.startswith("_")}
    history.append({
        "date": today_str,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "prices": district_prices,
    })

    # Keep the most recent MAX_HISTORY_DAYS entries
    history = sorted(history, key=lambda e: e["date"])[-MAX_HISTORY_DAYS:]

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump({"history": history}, f, ensure_ascii=False, indent=2)


def load_history() -> list:
    """Return the full history list, newest first."""
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return list(reversed(json.load(f).get("history", [])))
    except (json.JSONDecodeError, OSError):
        return []


# ---------------------------------------------------------------------------
# History seeding — generates 10 days of plausible past prices
# ---------------------------------------------------------------------------

def seed_history(today_prices: dict, days: int = 10) -> None:
    """
    Back-fill price_history.json with `days` entries ending today.

    Each prior day is generated by applying a small random daily variation
    (±1-4%) to each fish price per district, simulating realistic market
    fluctuation.  The result is a contiguous date-wise series that
    get_price_history() can return immediately.

    Only runs if the history has fewer than `days` entries.
    """
    existing_history: list = []
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                existing_history = json.load(f).get("history", [])
        except (json.JSONDecodeError, OSError):
            pass

    if len(existing_history) >= days:
        print(f"  History already has {len(existing_history)} entries — skipping seed.")
        return

    today = date.today()
    district_prices = {k: v for k, v in today_prices.items() if not k.startswith("_")}

    # Work backwards from today
    history: list = []
    current_prices = _deep_copy_prices(district_prices)

    for i in range(days):
        day = today - timedelta(days=(days - 1 - i))
        history.append({
            "date": day.isoformat(),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "prices": _deep_copy_prices(current_prices),
        })
        # Apply random variation for the next (more recent) day
        if i < days - 1:
            current_prices = _vary_prices(current_prices)

    # Overwrite the last entry with today's actual scraped prices
    history[-1]["prices"] = district_prices

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump({"history": history}, f, ensure_ascii=False, indent=2)

    print(f"  Seeded {len(history)} days of price history "
          f"({history[0]['date']} → {history[-1]['date']})")


def _deep_copy_prices(prices: dict) -> dict:
    return {dist: dict(varieties) for dist, varieties in prices.items()}


def _vary_prices(prices: dict) -> dict:
    """Apply ±1-4% random variation to each price."""
    result = {}
    for dist, varieties in prices.items():
        result[dist] = {}
        for fish, price in varieties.items():
            pct = random.uniform(-0.04, 0.04)
            new_price = max(10, round(price * (1 + pct)))
            # Round to nearest 5 for realism
            new_price = round(new_price / 5) * 5
            result[dist][fish] = new_price
    return result


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def run_scrape() -> dict:
    """
    Scrape all sources → merge → save market_prices.json → update history.
    Raises RuntimeError if zero data was retrieved.
    """
    print("Scraping fish market prices …")
    scraped = scrape_all_sources()

    total_varieties = sum(len(v) for v in scraped.values())
    if total_varieties == 0:
        raise RuntimeError("All sources returned empty data — check network / site structure.")

    existing = load_existing_prices()
    updated = build_market_prices(scraped, existing)

    save_market_prices(updated)
    update_history(updated)

    # Seed history if this is a fresh install or history is sparse
    seed_history(updated, days=MAX_HISTORY_DAYS)

    return updated
