#!/usr/bin/env python3
"""
Enrich: tìm Foody.vn page cho mỗi vendor → scrape menu + reviews.

Dùng Startpage để tìm Foody URL, sau đó scrape trang Foody.
Chạy sample 20 vendors trước, rồi scale lên toàn bộ.
"""

import csv, re, sys, time, urllib.request, urllib.parse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT = PROJECT_ROOT / "data" / "enriched" / "vendors_enriched.csv"
OUTPUT = PROJECT_ROOT / "data" / "enriched" / "vendors_enriched.csv"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DELAY = 2.0  # seconds between requests


def search_foody(vendor_name: str, city: str) -> str | None:
    """Search Startpage for vendor + city on Foody.vn."""
    query = f"{vendor_name} {city} foody.vn"
    url = f"https://www.startpage.com/do/dsearch?{urllib.parse.urlencode({'query': query, 'language': 'vi', 'cat': 'web'})}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")

        # Find Foody.vn URLs in results
        foody_urls = re.findall(r'https?://(?:www\.)?foody\.vn/[^\s"\'<>]+', html)
        if foody_urls:
            return foody_urls[0].split('"')[0].split("'")[0].split("<")[0]
    except Exception as e:
        pass
    return None


def scrape_foody_page(url: str) -> dict:
    """Scrape menu and review info from a Foody.vn page."""
    result = {"foody_url": url, "menu_items": "", "review_snippets": "", "foody_rating": ""}

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")

        # Extract menu items (look for dish names + prices)
        # Foody uses specific patterns in their HTML
        menu_patterns = re.findall(
            r'(?:class="[^"]*dish-name[^"]*"[^>]*>|class="[^"]*item-name[^"]*"[^>]*>|class="[^"]*name[^"]*"[^>]*>)\s*(.*?)\s*<',
            html, re.DOTALL
        )
        if not menu_patterns:
            # Fallback: look for h4/h5 tags that might be dish names
            menu_patterns = re.findall(r'<h[45][^>]*>(.*?)</h[45]>', html, re.DOTALL)

        menu_items = []
        for m in menu_patterns[:20]:
            clean = re.sub(r'<[^>]+>', '', m).strip()
            if clean and len(clean) > 3 and len(clean) < 100:
                menu_items.append(clean)

        result["menu_items"] = " | ".join(menu_items[:15])

        # Extract review snippets
        reviews = re.findall(
            r'(?:class="[^"]*review-text[^"]*"[^>]*>|class="[^"]*comment[^"]*"[^>]*>|class="[^"]*description[^"]*"[^>]*>)\s*(.*?)\s*<',
            html, re.DOTALL
        )
        snippets = []
        for rv in reviews[:10]:
            clean = re.sub(r'<[^>]+>', '', rv).strip()
            if clean and len(clean) > 20:
                snippets.append(clean[:200])

        result["review_snippets"] = " || ".join(snippets[:5])

        # Rating
        rating_match = re.search(r'(?:rating|đánh giá)[^\d]*([\d.]+)', html, re.IGNORECASE)
        if rating_match:
            result["foody_rating"] = rating_match.group(1)

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


def enrich_batch(limit: int = 20):
    """Enrich first N vendors with Foody data."""
    rows = []
    with open(INPUT, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Add new columns if needed
    new_cols = ["foody_url", "menu_items", "review_snippets", "foody_rating"]
    for col in new_cols:
        if col not in fieldnames:
            fieldnames = list(fieldnames) + [col]

    enriched = 0
    for i, row in enumerate(rows[:limit]):
        vendor = row.get("vendor_name", "")
        city = row.get("city", row.get("province", ""))

        if not vendor:
            continue

        # Skip if already has menu data
        if row.get("menu_items", "").strip():
            continue

        print(f"[{i+1}/{min(limit, len(rows))}] {vendor[:40]}...", end=" ")

        foody_url = search_foody(vendor, city)
        if foody_url:
            print(f"✅ Found Foody")
            data = scrape_foody_page(foody_url)
            for col in new_cols:
                row[col] = data.get(col, "")
            enriched += 1
            time.sleep(DELAY)
        else:
            print("❌ No Foody")
            for col in new_cols:
                row[col] = ""
            time.sleep(0.5)

    # Save
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'='*50}")
    print(f"Enriched: {enriched}/{min(limit, len(rows))} vendors with Foody data")
    print(f"Saved: {OUTPUT}")


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    print(f"Enriching first {limit} vendors...")
    enrich_batch(limit)


if __name__ == "__main__":
    main()
