"""Debug script — selects KERALA from dropdown and dumps resulting table."""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright

INCOIS_URL = (
    "https://incois.gov.in/MarineFisheries/TextDataHome"
    "?mfid=1&request_locale=en"
)

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(INCOIS_URL, timeout=30000)
        await page.wait_for_selector("select", timeout=15000)

        # Print all select elements and their options
        selects = await page.query_selector_all("select")
        print(f"Found {len(selects)} <select> elements\n")
        for i, sel in enumerate(selects):
            name = await sel.get_attribute("name") or await sel.get_attribute("id") or f"select[{i}]"
            options = await sel.query_selector_all("option")
            opt_texts = [(await o.inner_text()).strip() for o in options]
            print(f"  Select '{name}': {opt_texts}")

        print("\nSelecting KERALA...")
        # Select KERALA in the sector select (index 2)
        sector_select = selects[2]
        await sector_select.select_option(label="KERALA")

        # Wait for table rows to appear
        await page.wait_for_timeout(3000)

        rows = await page.query_selector_all("table tr")
        print(f"\nTotal <tr> rows after selection: {len(rows)}\n")
        for i, row in enumerate(rows[:100]):
            cells = await row.query_selector_all("td, th")
            texts = [(await c.inner_text()).strip() for c in cells]
            if any(texts):
                print(f"Row {i:3d} ({len(texts)} cols): {texts}")

        await browser.close()

asyncio.run(main())
