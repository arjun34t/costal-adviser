"""
Run once daily to refresh the INCOIS marine fisheries cache.
Usage: python run_incois_scraper.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.incois_scraper import scrape_incois_data, save_to_cache


async def main():
    print("Scraping INCOIS marine fisheries data...")
    try:
        data, forecast_date = await scrape_incois_data()
    except Exception as e:
        print(f"Scraping failed: {e}")
        sys.exit(1)

    if not data:
        print("No Kerala rows found — check if the page structure changed.")
        sys.exit(1)

    save_to_cache(data, forecast_date)
    print(f"Saved {len(data)} rows to data/incois_cache.json (forecast date: {forecast_date})")

    print("\nSample rows:")
    for row in data[:5]:
        print(
            f"  {row['location']:<30} "
            f"{row['direction']:<5} "
            f"{row['bearing_deg']:>3}°  "
            f"{row['distance_min_km']}-{row['distance_max_km']} km  "
            f"depth {row['depth_min_m']}-{row['depth_max_m']} m"
        )


if __name__ == "__main__":
    asyncio.run(main())
