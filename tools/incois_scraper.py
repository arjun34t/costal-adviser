import asyncio
import json
import os
import re
from datetime import datetime, date, timezone

from tools.location_finder import KERALA_COASTAL_LOCATIONS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CACHE_PATH = os.path.join(DATA_DIR, "incois_cache.json")
FALLBACK_PATH = os.path.join(DATA_DIR, "incois_fallback.json")

INCOIS_URL = (
    "https://incois.gov.in/MarineFisheries/TextDataHome"
    "?mfid=1&request_locale=en"
)

_KERALA_SET = {loc.lower() for loc in KERALA_COASTAL_LOCATIONS}


def _is_kerala_location(name: str) -> bool:
    return name.strip().lower() in _KERALA_SET


def _parse_range(value: str) -> tuple[float, float]:
    """Parse '10-20' or '15' into (min, max) floats."""
    value = value.strip()
    match = re.match(r"([\d.]+)\s*[-–]\s*([\d.]+)", value)
    if match:
        return float(match.group(1)), float(match.group(2))
    try:
        v = float(value)
        return v, v
    except ValueError:
        return 0.0, 0.0


def _parse_forecast_date(raw: str) -> str | None:
    """Parse '3 APR 2026' into ISO date string '2026-04-03', or None."""
    try:
        return datetime.strptime(raw.strip(), "%d %b %Y").date().isoformat()
    except ValueError:
        return None


async def scrape_incois_data() -> tuple[list, str | None]:
    """Returns (rows, forecast_date_iso). forecast_date_iso may be None."""
    from playwright.async_api import async_playwright

    results = []
    forecast_date = None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(INCOIS_URL, timeout=30000)
            await page.wait_for_selector("select", timeout=15000)

            # Extract forecast date from the date row (4-col row before dropdown)
            rows_early = await page.query_selector_all("table tr")
            for row in rows_early:
                cells = await row.query_selector_all("td, th")
                texts = [(await c.inner_text()).strip() for c in cells]
                if len(texts) == 4 and re.match(r"\d{1,2} [A-Z]{3} \d{4}", texts[1]):
                    forecast_date = _parse_forecast_date(texts[1])
                    break

            # Select KERALA from the sector dropdown (3rd select on the page)
            selects = await page.query_selector_all("select")
            await selects[2].select_option(label="KERALA")

            # Wait until data rows appear (more than 4 rows means data loaded)
            await page.wait_for_function(
                "document.querySelectorAll('table tr').length > 4",
                timeout=15000,
            )

            rows = await page.query_selector_all("table tr")

            for row in rows:
                cells = await row.query_selector_all("td, th")
                texts = [(await c.inner_text()).strip() for c in cells]

                # Only process 7-column data rows whose first cell is a known location
                if len(texts) != 7:
                    continue
                location = texts[0]
                if not _is_kerala_location(location):
                    continue

                try:
                    direction = texts[1]
                    bearing_deg = int(re.sub(r"[^\d]", "", texts[2]) or 0)
                    dist_min, dist_max = _parse_range(texts[3])
                    depth_min, depth_max = _parse_range(texts[4])
                    latitude = texts[5]
                    longitude = texts[6]
                except (ValueError, IndexError):
                    continue

                results.append({
                    "location": location,
                    "direction": direction,
                    "bearing_deg": bearing_deg,
                    "distance_min_km": dist_min,
                    "distance_max_km": dist_max,
                    "depth_min_m": depth_min,
                    "depth_max_m": depth_max,
                    "latitude": latitude,
                    "longitude": longitude,
                })

        finally:
            await browser.close()

    return results, forecast_date


def save_to_cache(data: list, forecast_date: str | None) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "forecast_date": forecast_date,
        "data": data,
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_from_cache() -> list:
    if not os.path.exists(CACHE_PATH):
        return []
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)

        # Use scraped_at to determine cache freshness — forecast_date can lag by a day
        scraped_at_str = payload.get("scraped_at", "")[:10]
        if not scraped_at_str:
            return []
        if date.fromisoformat(scraped_at_str) != date.today():
            return []
        return payload.get("data", [])
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def _load_fallback() -> list:
    if not os.path.exists(FALLBACK_PATH):
        return []
    try:
        with open(FALLBACK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


_last_call_scraped = False  # True when the most recent get_incois_data() triggered a live scrape


def get_incois_data() -> list:
    global _last_call_scraped
    data = load_from_cache()
    if data:
        _last_call_scraped = False
        return data

    _last_call_scraped = True
    try:
        data, forecast_date = asyncio.run(scrape_incois_data())
        if data:
            save_to_cache(data, forecast_date)
            return data
    except Exception as e:
        print(f"[INCOIS] Scraping failed: {e}")

    return _load_fallback()


def was_scraped() -> bool:
    """Returns True if the last get_incois_data() call triggered a live scrape."""
    return _last_call_scraped
