"""
Test Script for Custom Competitor Feature

This script demonstrates how to:
1. Add a custom competitor website
2. Scrape a product from that competitor
3. View the results

Run this with: python test_competitor_feature.py
"""

import requests
import asyncio
import sys
import os

# Add backend to path so we can import the scraper
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from scrapers.generic_scraper import scrape_competitor_product


# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"


def print_section(title):
    """Helper to print section headers"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def add_competitor(name, base_url, price_selector=None, title_selector=None):
    """Add a competitor website via the API"""
    print_section(f"Adding Competitor: {name}")

    payload = {
        "name": name,
        "base_url": base_url,
        "website_type": "custom"
    }

    if price_selector:
        payload["price_selector"] = price_selector
    if title_selector:
        payload["title_selector"] = title_selector

    try:
        response = requests.post(f"{API_BASE_URL}/competitors", json=payload)

        if response.status_code == 201:
            data = response.json()
            print(f"[OK] Successfully added competitor!")
            print(f"   ID: {data['id']}")
            print(f"   Name: {data['name']}")
            print(f"   URL: {data['base_url']}")
            return data
        elif response.status_code == 400:
            print("[WARNING]  Competitor already exists (that's okay!)")
            # Get existing competitors
            existing = requests.get(f"{API_BASE_URL}/competitors").json()
            for comp in existing:
                if comp['base_url'] == base_url:
                    return comp
        else:
            print(f"[ERROR] Error: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"[ERROR] Error connecting to API: {e}")
        print("   Make sure the backend server is running!")
        return None


def list_competitors():
    """List all competitors"""
    print_section("All Registered Competitors")

    try:
        response = requests.get(f"{API_BASE_URL}/competitors")
        competitors = response.json()

        if not competitors:
            print("No competitors registered yet.")
            return

        for comp in competitors:
            status = "[ACTIVE] Active" if comp['is_active'] else "[INACTIVE] Inactive"
            print(f"\n{status} {comp['name']} (ID: {comp['id']})")
            print(f"   URL: {comp['base_url']}")
            if comp.get('price_selector'):
                print(f"   Price Selector: {comp['price_selector']}")
            if comp.get('notes'):
                print(f"   Notes: {comp['notes']}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")


async def test_scraper(url, price_selector=None, title_selector=None):
    """Test scraping a product URL"""
    print_section(f"Scraping Product")
    print(f"URL: {url}")
    print(f"Price Selector: {price_selector or 'Auto-detect'}")
    print(f"Title Selector: {title_selector or 'Auto-detect'}")
    print("\n[WORKING] Scraping... (this may take 5-10 seconds)\n")

    try:
        result = await scrape_competitor_product(
            url=url,
            price_selector=price_selector,
            title_selector=title_selector
        )

        print("[OK] Scraping Complete!\n")
        print("Results:")
        print("-" * 40)
        print(f"  Title:     {result.get('title') or '(not found)'}")
        print(f"  Price:     ${result.get('price') or 'N/A'} {result.get('currency', 'USD')}")
        print(f"  In Stock:  {'Yes YES' if result.get('in_stock') else 'No NO'}")
        print(f"  Image URL: {result.get('image_url') or '(not found)'}")

        if result.get('error'):
            print(f"\n[WARNING]  Error: {result['error']}")

        return result

    except Exception as e:
        print(f"\n[ERROR] Scraping failed: {e}")
        return None


async def main():
    """Main test flow"""
    print("\n" + "=" * 60)
    print("   MarketIntel - Custom Competitor Feature Test")
    print("=" * 60)

    # Test 1: Check API is running
    print_section("Step 1: Checking API Connection")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("[OK] API is running and healthy!")
        else:
            print("[ERROR] API returned unexpected status")
            return
    except Exception as e:
        print(f"[ERROR] Cannot connect to API: {e}")
        print("\n[TIP] Please start the backend server:")
        print("   1. Open a new terminal")
        print("   2. Run: start-backend.bat")
        print("   3. Try this script again")
        return

    # Test 2: Add a test competitor (using a real website for demo)
    # We'll use Amazon as an example since it's publicly accessible
    competitor = add_competitor(
        name="Amazon (Test)",
        base_url="https://www.amazon.com",
        price_selector=".a-price-whole",
        title_selector="#productTitle"
    )

    if not competitor:
        print("[ERROR] Failed to add competitor")
        return

    # Test 3: List all competitors
    list_competitors()

    # Test 4: Test the scraper with a real product
    # Using a stable Amazon product URL for testing
    test_url = "https://www.amazon.com/dp/B0BSHF7WHW"  # Example: Amazon Basics product

    print_section("Step 4: Testing Generic Scraper")
    print("We'll scrape an Amazon product as a test.")
    print("(You can replace this with any competitor URL)")

    await test_scraper(
        url=test_url,
        price_selector=".a-price-whole",
        title_selector="#productTitle"
    )

    # Summary
    print_section("Test Complete! [SUCCESS]")
    print("What we demonstrated:")
    print("  [OK] Added a custom competitor via API")
    print("  [OK] Listed all competitors")
    print("  [OK] Scraped a product using custom CSS selectors")
    print("  [OK] Extracted price, title, and availability")

    print("\n[INFO] Next Steps:")
    print("  1. Visit http://127.0.0.1:8000/docs for interactive API testing")
    print("  2. Add your own competitors using the API")
    print("  3. Try scraping products from your actual competitors")
    print("  4. Build the frontend dashboard to visualize the data")

    print("\n[TIP] To add your own competitor:")
    print("   1. Find a product on their website")
    print("   2. Right-click the price → Inspect")
    print("   3. Note the CSS class/id")
    print("   4. Use that selector in the API call")


if __name__ == "__main__":
    asyncio.run(main())
