"""
Run once daily to refresh Kerala fish market prices and update the
10-day rolling price history.

Usage:
    python run_price_scraper.py

Output files:
    data/market_prices.json  – latest prices per city (read by the agent)
    data/price_history.json  – rolling 10-day history
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.price_scraper import run_scrape, load_history


def main():
    try:
        updated = run_scrape()
    except RuntimeError as exc:
        print(f"Scraping failed: {exc}")
        sys.exit(1)

    # Summary report
    cities = [k for k in updated if not k.startswith("_")]
    print(f"\nUpdated {len(cities)} cities:")
    for city in cities:
        varieties = updated[city]
        sample = list(varieties.items())[:4]
        sample_str = ", ".join(f"{k}: ₹{v}" for k, v in sample)
        print(f"  {city:<22} ({len(varieties)} varieties)  e.g. {sample_str}")

    history = load_history()
    print(f"\nPrice history: {len(history)} day(s) stored "
          f"(showing dates: {', '.join(e['date'] for e in history)})")


if __name__ == "__main__":
    main()
