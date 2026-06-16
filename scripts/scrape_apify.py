#!/usr/bin/env python3
"""
Quét Google Maps toàn quốc bằng Apify Google Maps Scraper.
Chiến lược: mỗi tỉnh 3 query → tối ưu coverage, giảm trùng lặp.

Input:  API key (từ biến môi trường APIFY_API_KEY)
Output: data/raw/apify_nationwide.csv

Pricing: PAY_PER_EVENT (~$2-4 per 1000 places)
Estimated cost: $15-30 cho toàn quốc
"""

import os, sys, json, time, urllib.request
from pathlib import Path
from datetime import datetime
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
API_KEY = os.environ.get("APIFY_API_KEY", "")
ACTOR_ID = "nwua9Gu5YrADL7ZDj"

# ── 63 tỉnh thành Việt Nam ──
PROVINCES = [
    "Hà Nội", "TP Hồ Chí Minh", "Hải Phòng", "Đà Nẵng", "Cần Thơ",
    "An Giang", "Bà Rịa - Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu",
    "Bắc Ninh", "Bến Tre", "Bình Định", "Bình Dương", "Bình Phước",
    "Bình Thuận", "Cà Mau", "Cao Bằng", "Đắk Lắk", "Đắk Nông",
    "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang",
    "Hà Nam", "Hà Tĩnh", "Hải Dương", "Hậu Giang", "Hòa Bình",
    "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu",
    "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định",
    "Nghệ An", "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên",
    "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị",
    "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên",
    "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang", "Trà Vinh", "Tuyên Quang",
    "Vĩnh Long", "Vĩnh Phúc", "Yên Bái",
]

# ── Query templates per province ──
# 3 queries = 1 broad + 1 specific + 1 local
QUERY_TEMPLATES = [
    "quán ăn ngon {province}",       # Broad: good restaurants
    "đặc sản {province}",            # Specialties
    "ăn vặt {province}",             # Street food / snacks
]

# Food-related Google Maps categories to keep
FOOD_CATEGORIES = [
    "Nhà hàng", "Quán ăn", "Quán ăn nhanh", "Tiệm bánh", "Quán cà phê",
    "Quán ăn nhẹ", "Tiệm chè", "Quán nhậu", "Quán bia",
    "Restaurant", "Cafe", "Bakery", "Fast food restaurant",
    "Family restaurant", "Vietnamese restaurant",
]


def run_actor(search_strings: list[str], max_places: int = 40) -> dict:
    """Run Apify Google Maps Scraper and return run info."""
    run_input = {
        "searchStringsArray": search_strings,
        "maxCrawledPlacesPerSearch": max_places,
        "language": "vi",
        "maxReviews": 0,
        "maxImages": 1,
        "includeWebResults": False,
        "scrapeDirectories": False,
    }

    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={API_KEY}"
    req = urllib.request.Request(
        url,
        data=json.dumps(run_input).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    run_info = data.get("data", data)
    return {
        "run_id": run_info["id"],
        "dataset_id": run_info["defaultDatasetId"],
        "queries": search_strings,
    }


def wait_for_run(run_id: str, timeout: int = 300) -> str:
    """Wait for run to complete. Returns final status."""
    start = time.time()
    while time.time() - start < timeout:
        url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={API_KEY}"
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            status = data.get("data", {}).get("status", "UNKNOWN")

            if status == "RUNNING":
                stats = data.get("data", {}).get("stats", {})
                places = stats.get("placesScraped", "?")
                print(f"  Running... ({places} places scraped)", end="\r")
                time.sleep(8)
                continue

            return status
        except Exception as e:
            print(f"\n  Poll error: {e}")
            time.sleep(10)

    return "TIMEOUT"


def get_results(dataset_id: str) -> list[dict]:
    """Fetch all results from a dataset."""
    all_items = []
    offset = 0
    limit = 100

    while True:
        url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={API_KEY}&limit={limit}&offset={offset}&format=json"
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=30)
            items = json.loads(resp.read())
            if not items:
                break
            all_items.extend(items)
            offset += limit
            print(f"  Fetched {len(all_items)} results...", end="\r")
            time.sleep(0.3)
        except Exception as e:
            print(f"\n  Fetch error at offset {offset}: {e}")
            break

    print(f"  Total: {len(all_items)} results")
    return all_items


def transform_to_csv(items: list[dict], query: str, province: str) -> pd.DataFrame:
    """Transform Apify results to our CSV format."""
    rows = []
    for item in items:
        # Only keep food-related places
        cat = item.get("categoryName", "")
        cats = item.get("categories", [])
        all_cats = [cat] + cats

        is_food = any(
            any(fc.lower() in str(c).lower() for fc in FOOD_CATEGORIES)
            for c in all_cats
        )
        if not is_food:
            continue

        # Skip permanently closed
        if item.get("permanentlyClosed"):
            continue

        # Build address
        addr_parts = []
        for f in ["street", "neighborhood", "address"]:
            v = item.get(f, "")
            if v and v not in addr_parts:
                addr_parts.append(str(v))
        address = ", ".join(addr_parts)

        # Extract price
        price = item.get("price", "")

        # Opening hours summary
        hours_list = item.get("openingHours", [])
        hours_str = "; ".join(
            f"{h.get('day','')}: {h.get('hours','')}"
            for h in (hours_list or [])[:5]
        )

        # Additional info
        add_info = item.get("additionalInfo", {})
        services = add_info.get("Các tùy chọn dịch vụ", [])
        service_tags = []
        for svc in services:
            if isinstance(svc, dict):
                service_tags.extend(k for k, v in svc.items() if v)

        rows.append({
            "dish_name": "",
            "vendor_name": str(item.get("title", "")).strip(),
            "address": address,
            "ward": str(item.get("neighborhood", "")),
            "district": str(item.get("street", "")),
            "province": province,
            "city": str(item.get("city", province)),
            "price_range": str(price),
            "hours": hours_str,
            "is_original": False,
            "rating": float(item.get("totalScore", 0) or 0),
            "description": str(item.get("description", "")),
            "tags": "; ".join(service_tags),
            "dish_category": str(cat),
            "image_urls": str(item.get("imageUrl", "")),
            "source": f"apify:{query}",
            "place_id": str(item.get("placeId", "")),
            "reviews_count": int(item.get("reviewsCount", 0) or 0),
            "lat": item.get("location", {}).get("lat", ""),
            "lng": item.get("location", {}).get("lng", ""),
        })

    return pd.DataFrame(rows)


def scrape_batch(provinces_batch: list[str], batch_num: int, max_per_search: int = 40):
    """Scrape a batch of provinces in a single Apify run."""
    # Build all search queries for this batch
    queries = []
    for prov in provinces_batch:
        for template in QUERY_TEMPLATES:
            queries.append(template.format(province=prov))

    total_queries = len(queries)
    max_total = max_per_search * total_queries
    print(f"\n{'='*60}")
    print(f"BATCH {batch_num}: {len(provinces_batch)} provinces, {total_queries} queries")
    print(f"Max results: {max_total}")
    print(f"Provinces: {', '.join(provinces_batch[:5])}...")
    print(f"{'='*60}")

    # Run actor
    run_info = run_actor(queries, max_per_search)
    run_id = run_info["run_id"]
    dataset_id = run_info["dataset_id"]
    print(f"Run ID: {run_id}")
    print(f"Dataset ID: {dataset_id}")

    # Wait for completion
    print("Waiting for run to complete...")
    status = wait_for_run(run_id)
    print(f"\nFinal status: {status}")

    if status != "SUCCEEDED":
        print(f"WARNING: Run did not succeed ({status})")
        return pd.DataFrame()

    # Get results
    items = get_results(dataset_id)
    if not items:
        print("No results!")
        return pd.DataFrame()

    # Transform all results
    all_rows = []
    for prov in provinces_batch:
        prov_items = [
            it for it in items
            if prov.lower() in str(it.get("searchString", "")).lower()
        ]
        if prov_items:
            # Create a combined query string for reference
            queries_for_prov = [q for q in queries if prov in q]
            df = transform_to_csv(prov_items, queries_for_prov[0] if queries_for_prov else "", prov)
            all_rows.append(df)
            print(f"  {prov}: {len(prov_items)} items → {len(df)} food places")

    if not all_rows:
        return pd.DataFrame()

    result = pd.concat(all_rows, ignore_index=True)
    result = result.drop_duplicates(subset=["vendor_name", "address"], keep="first")

    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    output = RAW_DIR / f"apify_batch_{batch_num}_{ts}.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"\nSaved: {output} ({len(result)} unique food places)")
    return result


def main():
    print("=" * 60)
    print("ĐẶC SẢN PHỐ — Apify Nationwide Scraper")
    print(f"Total provinces: {len(PROVINCES)}")
    print(f"Strategy: {len(QUERY_TEMPLATES)} queries per province")
    print(f"Estimated Apify cost: $0.50-1.00 per batch")
    print("=" * 60)

    if len(sys.argv) > 1:
        # Manual mode: specify provinces
        provinces = sys.argv[1:]
        print(f"Manual mode: {len(provinces)} provinces")
    else:
        provinces = PROVINCES
        print("Full nationwide mode: all 63 provinces")

    # Split into batches of 8 provinces (24 queries per batch)
    # This keeps individual run costs low and manageable
    BATCH_SIZE = 8
    batches = [
        provinces[i:i + BATCH_SIZE]
        for i in range(0, len(provinces), BATCH_SIZE)
    ]

    print(f"Batches: {len(batches)} (max {BATCH_SIZE} provinces/batch)")
    print(f"Estimated total: ${len(batches) * 0.50:.2f} - ${len(batches) * 1.00:.2f}")
    print()

    all_results = []
    for i, batch in enumerate(batches, 1):
        try:
            df = scrape_batch(batch, i, max_per_search=40)
            if len(df) > 0:
                all_results.append(df)
            # Small delay between batches
            if i < len(batches):
                print("\nCooling down 5s before next batch...")
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n\nInterrupted! Saving what we have...")
            break
        except Exception as e:
            print(f"\nERROR in batch {i}: {e}")
            continue

    if all_results:
        final = pd.concat(all_results, ignore_index=True)
        final = final.drop_duplicates(subset=["vendor_name", "address"], keep="first")
        output = RAW_DIR / f"apify_all_nationwide_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        final.to_csv(output, index=False, encoding="utf-8-sig")
        print(f"\n{'='*60}")
        print(f"ALL DONE! {len(final)} unique food places")
        print(f"Saved: {output}")
        print("Run: python3 scripts/clean_data.py to process")
    else:
        print("\nNo results collected.")


if __name__ == "__main__":
    main()
