#!/usr/bin/env python3
"""
AI phân loại món ăn từ tên quán + mô tả + menu text.
Dùng keyword matching thông minh để gán dish_name và dish_category.

Input:  data/enriched/vendors_enriched.csv
Output: data/enriched/vendors_enriched.csv (in-place update)
"""

import csv, re, sys
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "enriched" / "vendors_enriched.csv"

# ── Dish detection: keyword → (dish_name, category) ──
# Priority-ordered: more specific patterns first
DISH_PATTERNS = [
    # ── Noodle soups ──
    ("phở bò", "Phở bò", "Phở/Bún/Miến"),
    ("phở gà", "Phở gà", "Phở/Bún/Miến"),
    ("phở cuốn", "Phở cuốn", "Phở/Bún/Miến"),
    ("phở xào", "Phở xào", "Phở/Bún/Miến"),
    ("phở chiên", "Phở chiên", "Phở/Bún/Miến"),
    ("phở", "Phở", "Phở/Bún/Miến"),
    ("pho", "Phở", "Phở/Bún/Miến"),  # English spelling without diacritic
    ("bún bò huế", "Bún bò Huế", "Phở/Bún/Miến"),
    ("bún bò", "Bún bò", "Phở/Bún/Miến"),
    ("bún chả", "Bún chả", "Phở/Bún/Miến"),
    ("bún đậu mắm tôm", "Bún đậu mắm tôm", "Phở/Bún/Miến"),
    ("bún đậu", "Bún đậu", "Phở/Bún/Miến"),
    ("bún riêu", "Bún riêu", "Phở/Bún/Miến"),
    ("bún ốc", "Bún ốc", "Phở/Bún/Miến"),
    ("bún thang", "Bún thang", "Phở/Bún/Miến"),
    ("bún mắm", "Bún mắm", "Phở/Bún/Miến"),
    ("bún", "Bún", "Phở/Bún/Miến"),
    ("mì quảng", "Mì Quảng", "Phở/Bún/Miến"),
    ("miến lươn", "Miến lươn", "Phở/Bún/Miến"),
    ("miến cua", "Miến cua", "Phở/Bún/Miến"),
    ("miến gà", "Miến gà", "Phở/Bún/Miến"),
    ("miến", "Miến", "Phở/Bún/Miến"),
    ("hủ tiếu", "Hủ tiếu", "Phở/Bún/Miến"),
    ("bánh canh", "Bánh canh", "Phở/Bún/Miến"),
    ("mì vằn thắn", "Mì vằn thắn", "Phở/Bún/Miến"),
    ("mì hoành thánh", "Mì hoành thánh", "Phở/Bún/Miến"),
    ("cao lầu", "Cao lầu", "Phở/Bún/Miến"),

    # ── Rice dishes ──
    ("cơm tấm", "Cơm tấm", "Cơm"),
    ("cơm gà", "Cơm gà", "Cơm"),
    ("cơm rang", "Cơm rang", "Cơm"),
    ("cơm cháy", "Cơm cháy", "Cơm"),
    ("cơm niêu", "Cơm niêu", "Cơm"),
    ("cơm hến", "Cơm hến", "Cơm"),
    ("cơm", "Cơm", "Cơm"),
    ("xôi", "Xôi", "Cơm"),
    ("cháo", "Cháo", "Cơm"),

    # ── Bánh (cakes/breads) ──
    ("bánh mỳ miến", "Bánh mỳ miến", "Bánh"),
    ("bánh mì miến", "Bánh mỳ miến", "Bánh"),
    ("bánh mì", "Bánh mì", "Bánh"),
    ("bánh mỳ", "Bánh mì", "Bánh"),
    ("bánh bông lan chấm trứng", "Bánh bông lan chấm trứng", "Bánh"),
    ("bánh bông lan", "Bánh bông lan", "Bánh"),
    ("bánh cuốn", "Bánh cuốn", "Bánh"),
    ("bánh xèo", "Bánh xèo", "Bánh"),
    ("bánh bèo", "Bánh bèo", "Bánh"),
    ("bánh khọt", "Bánh khọt", "Bánh"),
    ("bánh ướt", "Bánh ướt", "Bánh"),
    ("bánh tráng", "Bánh tráng", "Bánh"),
    ("bánh bao", "Bánh bao", "Bánh"),
    ("bánh rán", "Bánh rán", "Bánh"),
    ("bánh flan", "Bánh flan", "Chè/Tráng miệng"),
    ("bánh bột lọc", "Bánh bột lọc", "Bánh"),
    ("bánh đa", "Bánh đa", "Bánh"),
    ("bánh gà", "Bánh gà", "Bánh"),
    ("bánh tiêu", "Bánh tiêu", "Bánh"),
    ("bánh dày", "Bánh dày", "Bánh"),
    ("bánh đúc", "Bánh đúc", "Bánh"),
    ("bánh nậm", "Bánh nậm", "Bánh"),
    ("bánh tét", "Bánh tét", "Bánh"),
    ("bánh chưng", "Bánh chưng", "Bánh"),
    ("bánh", "Bánh", "Bánh"),

    # ── Desserts / Sweets ──
    ("chè bột lọc", "Chè bột lọc", "Chè/Tráng miệng"),
    ("chè", "Chè", "Chè/Tráng miệng"),
    ("kem", "Kem", "Chè/Tráng miệng"),
    ("tào phớ", "Tào phớ", "Chè/Tráng miệng"),
    ("caramen", "Caramen", "Chè/Tráng miệng"),
    ("sữa chua", "Sữa chua", "Chè/Tráng miệng"),
    ("yaourt", "Sữa chua", "Chè/Tráng miệng"),
    ("rau câu", "Rau câu", "Chè/Tráng miệng"),
    ("thạch", "Thạch", "Chè/Tráng miệng"),
    ("trà sữa", "Trà sữa", "Đồ uống"),
    ("sinh tố", "Sinh tố", "Đồ uống"),
    ("nước mía", "Nước mía", "Đồ uống"),
    ("nước dừa", "Nước dừa", "Đồ uống"),

    # ── Seafood ──
    ("ốc", "Ốc", "Ốc/Hải sản"),
    ("nghêu", "Nghêu", "Ốc/Hải sản"),
    ("hàu", "Hàu", "Ốc/Hải sản"),
    ("cua", "Cua", "Ốc/Hải sản"),
    ("ghẹ", "Ghẹ", "Ốc/Hải sản"),
    ("tôm", "Tôm", "Ốc/Hải sản"),
    ("mực", "Mực", "Ốc/Hải sản"),
    ("bạch tuộc", "Bạch tuộc", "Ốc/Hải sản"),
    ("hải sản", "Hải sản", "Ốc/Hải sản"),

    # ── Rolls / Salads ──
    ("nem chua", "Nem chua", "Nem/Chả/Gỏi"),
    ("nem lụi", "Nem lụi", "Nem/Chả/Gỏi"),
    ("nem nướng", "Nem nướng", "Nem/Chả/Gỏi"),
    ("nem rán", "Nem rán", "Nem/Chả/Gỏi"),
    ("nem", "Nem", "Nem/Chả/Gỏi"),
    ("chả giò", "Chả giò", "Nem/Chả/Gỏi"),
    ("chả cá", "Chả cá", "Nem/Chả/Gỏi"),
    ("chả rươi", "Chả rươi", "Nem/Chả/Gỏi"),
    ("chả mực", "Chả mực", "Nem/Chả/Gỏi"),
    ("chả", "Chả", "Nem/Chả/Gỏi"),
    ("gỏi cuốn", "Gỏi cuốn", "Nem/Chả/Gỏi"),
    ("gỏi", "Gỏi", "Nem/Chả/Gỏi"),
    ("ram", "Ram", "Nem/Chả/Gỏi"),
    ("nộm", "Nộm", "Nem/Chả/Gỏi"),

    # ── Grilled / BBQ ──
    ("bò nướng", "Bò nướng", "Đồ nướng"),
    ("gà nướng", "Gà nướng", "Đồ nướng"),
    ("heo quay", "Heo quay", "Đồ nướng"),
    ("vịt quay", "Vịt quay", "Đồ nướng"),
    ("nướng", "Đồ nướng", "Đồ nướng"),

    # ── Hot pot ──
    ("lẩu", "Lẩu", "Lẩu"),

    # ── VN specialties ──
    ("bò né", "Bò né", "Đặc sản"),
    ("bò kho", "Bò kho", "Đặc sản"),
    ("bò bía", "Bò bía", "Đặc sản"),
    ("bột chiên", "Bột chiên", "Đặc sản"),
    ("cá viên", "Cá viên", "Ăn vặt"),
    ("xiên que", "Xiên que", "Ăn vặt"),
    ("xiên", "Xiên", "Đồ nướng"),
    ("gà rán", "Gà rán", "Ăn vặt"),
    ("khoai tây chiên", "Khoai tây chiên", "Ăn vặt"),
    ("bắp xào", "Bắp xào", "Ăn vặt"),
    ("bò bía", "Bò bía", "Ăn vặt"),

    # ── Japanese / Korean (common in VN) ──
    ("takoyaki", "Takoyaki", "Ăn vặt"),
    ("sushi", "Sushi", "Đặc sản"),
    ("tokbokki", "Tokbokki", "Ăn vặt"),
    ("kimbap", "Kimbap", "Đặc sản"),
    ("bibimbap", "Bibimbap", "Đặc sản"),
    ("tempura", "Tempura", "Đặc sản"),
    ("udon", "Udon", "Phở/Bún/Miến"),
    ("ramen", "Ramen", "Phở/Bún/Miến"),
    ("sashimi", "Sashimi", "Đặc sản"),
    ("nhật bản", "Đồ Nhật", "Đặc sản"),
    ("hàn quốc", "Đồ Hàn", "Đặc sản"),
    ("gogi", "Đồ Hàn", "Đặc sản"),

    # ── Street food snacks ──
    ("ăn vặt", "Ăn vặt", "Ăn vặt"),
    ("vỉa hè", "Ẩm thực vỉa hè", "Ăn vặt"),
    ("lề đường", "Ẩm thực đường phố", "Ăn vặt"),

    # ── Vegetarian ──
    ("chay", "Đồ chay", "Chay"),

    # ── Coffee / Drinks ──
    ("cà phê", "Cà phê", "Đồ uống"),
    ("coffee", "Cà phê", "Đồ uống"),
    ("trà chanh", "Trà chanh", "Đồ uống"),
    ("trà đá", "Trà đá", "Đồ uống"),
    ("trà sữa", "Trà sữa", "Đồ uống"),
    ("matcha", "Matcha", "Đồ uống"),
    ("nước ép", "Nước ép", "Đồ uống"),
    ("soda", "Soda", "Đồ uống"),

    # ── Generic Vietnamese restaurant types (extract from name) ──
    ("lòng", "Lòng", "Đặc sản"),
    ("trâu", "Thịt trâu", "Đặc sản"),
    ("dê", "Thịt dê", "Đặc sản"),
    ("bê", "Thịt bê", "Đặc sản"),
    ("thỏ", "Thịt thỏ", "Đặc sản"),
    ("chó", "Thịt chó", "Đặc sản"),
    ("cầy", "Thịt cầy", "Đặc sản"),
    ("chim", "Thịt chim", "Đặc sản"),
    ("cá lóc", "Cá lóc", "Ốc/Hải sản"),
    ("cá kho", "Cá kho", "Đặc sản"),
    ("cá", "Cá", "Ốc/Hải sản"),
    ("vịt", "Vịt", "Đặc sản"),
    ("gà", "Gà", "Đặc sản"),
    ("đặc sản", "Đặc sản", "Đặc sản"),
    ("cốm", "Cốm", "Đặc sản"),
    ("miền tây", "Đặc sản Miền Tây", "Đặc sản"),
    ("tây bắc", "Đặc sản Tây Bắc", "Đặc sản"),
    ("đồng quê", "Ẩm thực đồng quê", "Đặc sản"),
    ("ngọt", "Đồ ngọt", "Chè/Tráng miệng"),
    ("dessert", "Tráng miệng", "Chè/Tráng miệng"),
    ("đồ ăn đêm", "Ăn đêm", "Ăn vặt"),
    ("pizza", "Pizza", "Đặc sản"),
    ("buffet", "Buffet", "Đặc sản"),
    ("nhà hàng", "Ẩm thực", "Khác"),
    ("quán ăn", "Ẩm thực", "Khác"),
    ("quán ngon", "Ẩm thực", "Khác"),
    ("ngon", "Ẩm thực", "Khác"),
    ("ẩm thực", "Ẩm thực", "Khác"),
    ("hương biển", "Hải sản", "Ốc/Hải sản"),
    ("hải sơn", "Hải sản", "Ốc/Hải sản"),
    ("seafood", "Hải sản", "Ốc/Hải sản"),
    ("làng chài", "Hải sản", "Ốc/Hải sản"),
    ("chinese food", "Đồ Hoa", "Đặc sản"),
    ("sương sa", "Sương sa", "Chè/Tráng miệng"),
    ("mít trộn", "Mít trộn", "Ăn vặt"),
    ("đu đủ", "Đu đủ", "Ăn vặt"),
    ("heo", "Thịt heo", "Đặc sản"),
    ("bò", "Thịt bò", "Đặc sản"),
    ("phố cổ", "Ẩm thực phố cổ", "Đặc sản"),
    ("phố núi", "Ẩm thực phố núi", "Đặc sản"),
    ("quán", "Quán ăn", "Khác"),
    ("café", "Cà phê", "Đồ uống"),
    ("cafe", "Cà phê", "Đồ uống"),
    ("gánh", "Ẩm thực Hà Nội", "Đặc sản"),
    ("việt mỳ", "Mỳ Việt", "Phở/Bún/Miến"),
    ("ăn tối", "Ẩm thực", "Khác"),
    ("bốn mùa", "Ẩm thực", "Khác"),
    ("không gian xưa", "Ẩm thực Huế", "Đặc sản"),
    ("nhà bếp xưa", "Ẩm thực", "Khác"),
    ("tiệm ăn", "Ẩm thực", "Khác"),
    ("ăn thôi", "Ẩm thực", "Khác"),
    ("nén", "Ẩm thực Việt", "Đặc sản"),
]


def classify_vendor(vendor_name: str, description: str = "", menu_items: str = "",
                     menu_text: str = "", tags: str = "") -> tuple[str, str]:
    """Classify a vendor into dish_name and category."""
    text = f"{vendor_name} {description} {menu_items} {menu_text} {tags}".lower()

    for keyword, dish_name, category in DISH_PATTERNS:
        if keyword.lower() in text:
            return (dish_name, category)

    return ("", "Khác")


def is_likely_us_address(address: str, province: str) -> bool:
    """Detect if a vendor is likely in the US (Vietnamese restaurants abroad)."""
    addr = (address + " " + province).lower()
    us_indicators = [
        "bolsa", "westminster", "garden grove", "fountain valley",
        "santa ana", "san jose", "houston", "dallas", "little saigon",
        "orange county", "irvine", "anaheim", "rosemead", "el monte",
        "alhambra", "falls church", "arlington", "fairfax",
        "doraville", "chamblee", "orlando", "new orleans",
        "blvd", "ste ", "unit ", "ca 9", "tx 7", "on l",
    ]
    for ind in us_indicators:
        if ind in addr:
            return True
    # Check for US zip codes
    if re.search(r'\b\d{5}(?:-\d{4})?\b', addr):
        # Only flag if the address also doesn't have VN province markers
        vn_markers = ["hải dương", "hà nội", "đà nẵng", "hải phòng", "huế",
                      "ninh bình", "an giang", "cần thơ", "bến tre"]
        addr_no_prov = address.lower()
        if not any(m in addr_no_prov for m in vn_markers):
            return True
    return False


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            rows.append(r)

    print(f"Loaded: {len(rows)} vendors")
    if limit:
        rows = rows[:limit]
        print(f"Processing first {limit}...")

    # Stats
    us_count = 0
    classified_count = 0
    already_had = 0
    category_counts = Counter()

    for i, r in enumerate(rows):
        vendor = r.get("vendor_name", "")
        desc = r.get("description", "")
        menu_items = r.get("menu_items", "")
        menu_text = r.get("menu_text", "")
        tags = r.get("tags", "")

        # Flag US addresses
        addr = r.get("address", "")
        province = r.get("province", "")
        if is_likely_us_address(addr, province):
            r["_location"] = "US"
            us_count += 1
        else:
            r["_location"] = "VN"

        # Classify dish if not already set
        if not r.get("dish_name", "").strip():
            dish_name, category = classify_vendor(vendor, desc, menu_items, menu_text, tags)
            if dish_name:
                r["dish_name"] = dish_name
                r["dish_category"] = category
                classified_count += 1
                category_counts[category] += 1
        else:
            already_had += 1
            category_counts[r.get("dish_category", "Khác")] += 1

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(rows)}...")

    # Save
    # Ensure new columns exist in fieldnames
    for col in ["_location"]:
        if col not in fieldnames:
            fieldnames.append(col)

    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n=== Results ===")
    print(f"US addresses detected: {us_count}")
    print(f"VN addresses:          {len(rows) - us_count}")
    print(f"Already had dish_name: {already_had}")
    print(f"Newly classified:      {classified_count}")
    print(f"Still unknown:         {len(rows) - already_had - classified_count}")
    print()
    print("Category distribution:")
    for cat, count in category_counts.most_common():
        print(f"  {cat}: {count}")
    print(f"\nSaved: {CSV_PATH}")


if __name__ == "__main__":
    main()
