import math
import os
import requests as _requests
from datetime import datetime, timezone, timedelta

_IST = timezone(timedelta(hours=5, minutes=30))
import openmeteo_requests
import requests_cache
from retry_requests import retry
from tools.incois_scraper import get_incois_data, was_scraped
from tools.location_finder import get_locations_by_district

WORLDTIDES_API_KEY = os.environ.get("WORLDTIDES_API_KEY", "")
_WORLDTIDES_URL = "https://www.worldtides.info/api/v3"


def _get_tide_info(lat: float, lon: float) -> dict:
    """
    Fetch next tide extremes from WorldTides API.
    Strict no-fallback policy: returns available=False on any failure.
    Never returns estimated or calculated tide times.
    """
    if not WORLDTIDES_API_KEY:
        return {
            "available": False,
            "message": "Tide data unavailable. Consult your harbor master before departure.",
        }

    try:
        resp = _requests.get(
            _WORLDTIDES_URL,
            params={"extremes": "", "lat": lat, "lon": lon, "key": WORLDTIDES_API_KEY, "days": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != 200:
            raise ValueError(f"WorldTides error: {data.get('error', 'unknown')}")

        extremes = data.get("extremes", [])
        if not extremes:
            raise ValueError("No tide extremes in response")

        now = datetime.now(timezone.utc)

        def _fmt(ts):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.astimezone(_IST).strftime("%H:%M IST"), round((dt - now).total_seconds() / 60)

        next_high = next((e for e in extremes if e["type"] == "High"
                          and datetime.fromtimestamp(e["dt"], tz=timezone.utc) > now), None)
        next_low  = next((e for e in extremes if e["type"] == "Low"
                          and datetime.fromtimestamp(e["dt"], tz=timezone.utc) > now), None)

        if not next_high and not next_low:
            raise ValueError("No upcoming tide extremes found")

        result = {"available": True}

        if next_high:
            t_str, mins = _fmt(next_high["dt"])
            result["next_high_tide"] = {"time": t_str, "mins_from_now": mins, "height_m": round(next_high["height"], 2)}

        if next_low:
            t_str, mins = _fmt(next_low["dt"])
            result["next_low_tide"] = {"time": t_str, "mins_from_now": mins, "height_m": round(next_low["height"], 2)}

        # Departure window: best to leave 1–3 hrs before high tide
        # Avoid: within 30 min of low tide (shallow near shore, strong currents)
        if next_high:
            mins_to_high = result["next_high_tide"]["mins_from_now"]
            if 60 <= mins_to_high <= 180:
                result["departure_window"] = "good"
                result["departure_note"] = f"Good departure window — high tide in {mins_to_high} min."
            elif mins_to_high < 60:
                result["departure_window"] = "marginal"
                result["departure_note"] = f"High tide arriving in {mins_to_high} min — launch soon or wait for next cycle."
            else:
                result["departure_window"] = "early"
                result["departure_note"] = f"High tide in {mins_to_high} min — conditions will improve closer to high tide."
        else:
            result["departure_window"] = None

        return result

    except Exception as e:
        print(f"[TideAPI] Failed: {e}")
        return {
            "available": False,
            "message": "Tide data unavailable. Consult your harbor master before departure.",
        }

DISTRICT_COORDS = {
    "Kasaragod":          (12.4996, 74.9869),
    "Kannur":             (11.8745, 75.3704),
    "Kozhikode":          (11.2588, 75.7804),
    "Malappuram":         (10.7667, 75.9167),
    "Thrissur":           (10.5276, 76.2144),
    "Ernakulam":          (9.9312,  76.2673),
    "Kochi":              (9.9312,  76.2673),
    "Alappuzha":          (9.4981,  76.3388),
    "Kollam":             (8.8932,  76.6141),
    "Thiruvananthapuram": (8.5241,  76.9366),
}

cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


def get_sea_safety(district: str) -> dict:
    coords = DISTRICT_COORDS.get(district)
    if not coords:
        return {"error": f"Unknown district: {district}", "safe_to_fish": False}

    lat, lon = coords
    try:
        # Wave height from marine API
        marine_resp = openmeteo.weather_api(
            "https://marine-api.open-meteo.com/v1/marine",
            params={"latitude": lat, "longitude": lon, "current": ["wave_height"]},
        )
        wave_height = float(marine_resp[0].Current().Variables(0).Value())

        # Wind speed from forecast API
        forecast_resp = openmeteo.weather_api(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current": ["windspeed_10m"]},
        )
        wind_kmh = float(forecast_resp[0].Current().Variables(0).Value())

        if math.isnan(wave_height) or math.isnan(wind_kmh):
            return {"error": "Could not fetch data", "safe_to_fish": False}

        # INCOIS fishing zones for this district
        # Filter to coastal zones (≤150 km) and sort nearest first
        district_locations = set(get_locations_by_district(district))
        all_zones = get_incois_data()
        incois_scraped = was_scraped()
        zones = sorted(
            [
                {
                    "location": r["location"],
                    "direction": r["direction"],
                    "distance_km": f"{r['distance_min_km']:.0f}–{r['distance_max_km']:.0f}",
                    "depth_m": f"{r['depth_min_m']:.0f}–{r['depth_max_m']:.0f}",
                    "_dist": r["distance_min_km"],
                }
                for r in all_zones
                if r["location"] in district_locations
                and r["distance_min_km"] <= 150
            ],
            key=lambda z: z["_dist"],
        )
        # Drop the internal sort key before returning
        for z in zones:
            z.pop("_dist")

        tide = _get_tide_info(lat, lon)

        return {
            "wave_height_m": round(wave_height, 2),
            "wind_kmh": round(wind_kmh, 2),
            "safe_to_fish": wave_height < 2.5 and wind_kmh < 40,
            "fishing_zones": zones[:3],
            "tide": tide,
            "_incois_scraped": incois_scraped,
        }
    except Exception:
        return {"error": "Could not fetch data", "safe_to_fish": False}
