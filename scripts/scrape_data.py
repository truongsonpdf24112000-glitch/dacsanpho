#!/usr/bin/env python3
"""
Scrape street food data from Startpage (Google proxy) for Vietnamese queries.

Usage: python scripts/scrape_data.py "bánh mỳ miến Hải Dương"

Uses Startpage because DuckDuckGo returns zero results for Vietnamese local queries.
"""

import re, sys, time, urllib.parse
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "data" / "raw" / "scraped_data.csv"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

START_PAGE_URL = "https://www.startpage.com/do/dsearch"

VN_PHONE_RE = re.compile(r"(?:0[3|5|7|8|9]|84|\+84)\d{8,9}")
VN_ADDRESS_RE = re.compile(
    r"(?:số\s*)?\d+[\s,/]*[\w\s]+(?:phường|quận|huyện|tp|tỉnh|đường|phố|ngõ|hẻm)[\w\s,]*",
    re.IGNORECASE
)
VN_PRICE_RE = re.compile(r"(\d{1,3}[.,]?\d{0,3})\s*(?:k|đ|vnđ|nghìn|ngàn)", re.IGNORECASE)


def search_startpage(query: str, max_results: int = 20) -> list[str]:
    """Search Startpage and return result URLs."""
    import urllib.request

    params = urllib.parse.urlencode({
        "query": query,
        "language": "vi",
        "cat": "web",
    })
    url = f"{START_PAGE_URL}?{params}"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Error: {e}")
        return []

    # Extract result links
    links = re.findall(
        r'<a[^>]*class="[^"]*result-link[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )

    urls = []
    for link, title in links[:max_results]:
        if link.startswith("http"):
            urls.append(link)

    print(f"  Found {len(urls)} URLs")
    return urls


def extract_info_from_page(url: str) -> dict:
    """Extract phone, address, price from a single page."""
    import urllib.request

    result = {"url": url, "phone": "", "address": "", "price": ""}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return result

    # Extract phone
    phones = VN_PHONE_RE.findall(html)
    if phones:
        result["phone"] = phones[0]

    # Extract address
    addrs = VN_ADDRESS_RE.findall(html)
    if addrs:
        result["address"] = addrs[0][:100]

    # Extract price
    prices = VN_PRICE_RE.findall(html)
    if prices:
        result["price"] = prices[0]

    return result


def scrape_query(query: str, province: str, dish_name: str = ""):
    """Main scrape function."""
    print(f"\nSearching: {query}")
    urls = search_startpage(query, max_results=10)

    results = []
    for i, url in enumerate(urls):
        print(f"  [{i+1}/{len(urls)}] Scraping: {url[:60]}...")
        info = extract_info_from_page(url)
        info["query"] = query
        info["province"] = province
        info["dish_name"] = dish_name or query
        info["source"] = "startpage"
        results.append(info)
        time.sleep(0.8)  # Rate limit

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/scrape_data.py 'query' [province] [dish_name]")
        print("Example: python scripts/scrape_data.py 'bánh mỳ miến Hải Dương' 'Hải Dương' 'Bánh mỳ miến'")
        sys.exit(1)

    query = sys.argv[1]
    province = sys.argv[2] if len(sys.argv) > 2 else ""
    dish_name = sys.argv[3] if len(sys.argv) > 3 else ""

    results = scrape_query(query, province, dish_name)

    # Append to CSV
    df_new = pd.DataFrame(results)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if OUTPUT.exists():
        df_existing = pd.read_csv(OUTPUT)
        df = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df = df_new

    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\nSaved {len(results)} results to {OUTPUT}")


if __name__ == "__main__":
    main()
