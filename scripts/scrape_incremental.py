#!/usr/bin/env python3
"""
Scrape từng tỉnh một — an toàn, có thể dừng bất cứ lúc nào.
Kết quả lưu NGAY sau mỗi tỉnh, không sợ mất data.

Cách dùng:
  1. Set API key:  export APIFY_API_KEY="apify_api_xxx"
  2. Chạy:         python3 scripts/scrape_incremental.py
  3. Khi muốn dừng: Ctrl+C — data đã scrape được giữ lại

Mỗi tỉnh: 3 queries × 40 places = max 120 kết quả
Chi phí mỗi tỉnh: ~$0.05-0.10
"""

import os, sys, json, time, urllib.request
from pathlib import Path
from datetime import datetime
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
API_KEY = os.environ.get("APIFY_API_KEY", "")

if not API_KEY:
    print("❌ Chưa set APIFY_API_KEY!")
    print("   export APIFY_API_KEY='apify_api_xxx'")
    sys.exit(1)

ACTOR_ID = "nwua9Gu5YrADL7ZDj"  # Google Maps Scraper

# ── 50 tỉnh còn thiếu (đã có 13 tỉnh) ──
MISSING_PROVINCES = [
    "Bà Rịa - Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu",
    "Bắc Ninh", "Bình Định", "Bình Dương", "Bình Phước",
    "Bình Thuận", "Cà Mau", "Cao Bằng", "Đắk Lắk", "Đắk Nông",
    "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai",
    "Hà Nam", "Hà Tĩnh", "Hậu Giang", "Hòa Bình",
    "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu",
    "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định",
    "Nghệ An", "Phú Thọ", "Phú Yên",
    "Quảng Bình", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị",
    "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên",
    "Thanh Hóa", "Tiền Giang", "Trà Vinh", "Tuyên Quang",
    "Vĩnh Long", "Vĩnh Phúc", "Yên Bái",
]

QUERIES = [
    "quán ăn ngon {province}",
    "đặc sản {province}",
    "ăn vặt {province}",
]

OUTPUT = RAW_DIR / f"apify_incremental_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

FOOD_CATS = [
    "Nhà hàng", "Quán ăn", "Quán ăn nhanh", "Tiệm bánh", "Quán cà phê",
    "Quán ăn nhẹ", "Tiệm chè", "Quán nhậu", "Quán bia",
    "Restaurant", "Cafe", "Bakery", "Fast food restaurant",
    "Family restaurant", "Vietnamese restaurant",
]


def scrape_province(province: str, max_places: int = 40) -> list[dict]:
    """Scrape 1 province with 3 queries, return list of food places."""
    queries = [q.format(province=province) for q in QUERIES]
    
    run_input = {
        "searchStringsArray": queries,
        "maxCrawledPlacesPerSearch": max_places,
        "language": "vi",
        "maxReviews": 0,
        "maxImages": 1,
        "includeWebResults": False,
        "scrapeDirectories": False,
    }

    # 1. Start run
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={API_KEY}"
    req = urllib.request.Request(url, data=json.dumps(run_input).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
    resp = urllib.request.urlopen(req, timeout=30)
    run_data = json.loads(resp.read())["data"]
    run_id = run_data["id"]
    dataset_id = run_data["defaultDatasetId"]
    print(f"  Run: {run_id[:8]}... ", end="", flush=True)

    # 2. Wait
    start = time.time()
    while time.time() - start < 180:
        url2 = f"https://api.apify.com/v2/actor-runs/{run_id}?token={API_KEY}"
        data = json.loads(urllib.request.urlopen(urllib.request.Request(url2), timeout=15).read())
        status = data.get("data", {}).get("status", "?")
        if status != "RUNNING":
            break
        time.sleep(5)
    
    if status != "SUCCEEDED":
        print(f"⚠ {status}")
        return []

    # 3. Fetch results
    all_items = []
    offset = 0
    while True:
        url3 = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={API_KEY}&limit=100&offset={offset}&format=json"
        items = json.loads(urllib.request.urlopen(urllib.request.Request(url3), timeout=30).read())
        if not items:
            break
        all_items.extend(items)
        offset += 100
        time.sleep(0.2)

    # 4. Filter & transform
    rows = []
    for item in all_items:
        cat = item.get("categoryName", "")
        cats = item.get("categories", [])
        all_cats = [cat] + cats
        if not any(any(fc.lower() in str(c).lower() for fc in FOOD_CATS) for c in all_cats):
            continue
        if item.get("permanentlyClosed"):
            continue
        
        addr_parts = []
        for f in ["street", "neighborhood", "address"]:
            v = item.get(f, "")
            if v and v not in addr_parts:
                addr_parts.append(str(v))
        
        hours_list = item.get("openingHours", [])
        hours_str = "; ".join(f"{h.get('day','')}: {h.get('hours','')}" for h in (hours_list or [])[:5])
        
        rows.append({
            "dish_name": "",
            "vendor_name": str(item.get("title", "")).strip(),
            "address": ", ".join(addr_parts),
            "ward": str(item.get("neighborhood", "")),
            "district": str(item.get("street", "")),
            "province": province,
            "price_range": str(item.get("price", "")),
            "hours": hours_str,
            "is_original": False,
            "rating": float(item.get("totalScore", 0) or 0),
            "description": str(item.get("description", "")),
            "tags": "",
            "dish_category": str(cat),
            "image_urls": str(item.get("imageUrl", "")),
            "source": f"apify:{province}",
            "place_id": str(item.get("placeId", "")),
            "reviews_count": int(item.get("reviewsCount", 0) or 0),
            "lat": item.get("location", {}).get("lat", ""),
            "lng": item.get("location", {}).get("lng", ""),
        })

    print(f"✅ {len(rows)} places")
    return rows


def main():
    print("=" * 60)
    print("ĐẶC SẢN PHỐ — Incremental Scraper")
    print(f"Còn thiếu: {len(MISSING_PROVINCES)} tỉnh")
    print(f"API key: {API_KEY[:12]}...{API_KEY[-4:]}")
    print(f"Output: {OUTPUT}")
    print("=" * 60)
    print()
    print("⚠ Nhấn Ctrl+C để dừng — data đã scrape được giữ lại")
    print()

    all_rows = []
    done = 0
    skipped = 0

    for i, province in enumerate(MISSING_PROVINCES, 1):
        print(f"[{i}/{len(MISSING_PROVINCES)}] {province} ... ", end="", flush=True)
        
        try:
            places = scrape_province(province)
            if places:
                all_rows.extend(places)
                done += 1
            else:
                skipped += 1
            
            # Save after EVERY province
            if all_rows:
                df = pd.DataFrame(all_rows)
                df = df.drop_duplicates(subset=["vendor_name", "address"], keep="first")
                df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
        except KeyboardInterrupt:
            print("\n\n⏸ Đã dừng!")
            break
        except Exception as e:
            print(f"❌ {str(e)[:80]}")
            skipped += 1
        
        time.sleep(2)  # Rate limit

    print(f"\n{'='*60}")
    print(f"HOÀN THÀNH: {done} tỉnh OK, {skipped} lỗi/bỏ qua")
    if all_rows:
        df = pd.DataFrame(all_rows)
        df = df.drop_duplicates(subset=["vendor_name", "address"], keep="first")
        df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
        print(f"Tổng: {len(df)} places → {OUTPUT}")
        print()
        print("Tiếp theo:")
        print("  python3 scripts/clean_data.py")
        print("  python3 scripts/classify_dishes.py")
        print("  python3 scripts/generate_site.py")
    else:
        print("Không có data.")


if __name__ == "__main__":
    main()
