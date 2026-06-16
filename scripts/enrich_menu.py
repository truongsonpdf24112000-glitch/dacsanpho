#!/usr/bin/env python3
"""
Tìm website cho vendor qua Startpage search, rồi crawl menu từ website đó.

1. Với mỗi vendor chưa có website, search Google (Startpage) để tìm URL
2. Crawl website tìm menu (keywords: "thực đơn", "menu", "giá", "món")
3. Lưu kết quả vào CSV
"""

import csv, re, sys, time, urllib.request, urllib.parse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT = PROJECT_ROOT / "data" / "enriched" / "vendors_enriched.csv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def find_website(vendor: str, city: str) -> str | None:
    """Search for vendor's website via Startpage."""
    query = f"{vendor} {city} thực đơn menu"
    url = f"https://www.startpage.com/do/dsearch?{urllib.parse.urlencode({'query': query, 'language': 'vi', 'cat': 'web'})}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")

        # Find URLs — skip foody, facebook, google
        links = re.findall(r'https?://[^\s"\'<>]+', html)
        for link in links:
            link = link.rstrip('.,;:"\'')
            skip = [
                "google.com", "facebook.com", "youtube.com", "foody.vn",
                "startpage.com", "wikipedia.org", "instagram.com",
                "googleapis.com", "gstatic.com", "cloudflare.com",
                "fonts.googleapis", "cdn", "schema.org", "w3.org",
                "twitter.com", "tiktok.com", "shopee.vn", "lazada.vn",
            ]
            if not any(s in link for s in skip) and len(link) > 25 and link.startswith("http"):
                return link
    except:
        pass
    return None


def scrape_menu_from_website(url: str) -> dict:
    """Try to extract menu information from a website."""
    result = {"website": url, "menu_text": "", "menu_items": ""}

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")

        # Remove scripts and styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)

        # Look for menu-related sections
        menu_keywords = [
            "thực đơn", "menu", "món ăn", "đồ uống", "bảng giá",
            "giá", "combo", "set", "phần", "suất",
        ]

        menu_lines = []
        for line in text.split("."):
            line = line.strip()
            if any(kw in line.lower() for kw in menu_keywords) and len(line) > 20:
                menu_lines.append(line[:200])

        result["menu_text"] = " | ".join(menu_lines[:10])

        # Try to extract structured menu items with prices
        prices = re.findall(r'([^\d\n]{5,60}?)\s*[:\-]?\s*(\d{1,3}(?:[.,]\d{3})*\s*(?:k|K|đ|vnđ|VNĐ|nghìn|ngàn))', text)
        items = [f"{name.strip()} - {price}" for name, price in prices[:20]]
        result["menu_items"] = " | ".join(items)

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    print(f"Finding websites & menus for first {limit} vendors...")

    rows = []
    with open(INPUT, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for col in ["website_url", "menu_text", "menu_items"]:
            if col not in fieldnames:
                fieldnames.append(col)
        for row in reader:
            rows.append(row)

    found = 0
    for i, row in enumerate(rows[:limit]):
        vendor = row.get("vendor_name", "")
        city = row.get("city", row.get("province", ""))
        if not vendor:
            continue

        # Skip if already has website
        if row.get("website_url", "").strip():
            continue

        print(f"[{i+1}/{min(limit, len(rows))}] {vendor[:45]}...", end=" ", flush=True)

        website = find_website(vendor, city)
        if website:
            print(f"✅ {website[:50]}...")
            data = scrape_menu_from_website(website)
            for col in ["website_url", "menu_text", "menu_items"]:
                row[col] = data.get(col, "")
            found += 1
            time.sleep(1.5)
        else:
            print("❌")
            for col in ["website_url", "menu_text", "menu_items"]:
                row[col] = ""
            time.sleep(0.5)

    # Save
    import pandas as pd
    df = pd.DataFrame(rows, columns=fieldnames)
    df.to_csv(INPUT, index=False, encoding="utf-8-sig")
    print(f"\nFound websites: {found}/{min(limit, len(rows))}")
    print(f"Saved: {INPUT}")


if __name__ == "__main__":
    main()
