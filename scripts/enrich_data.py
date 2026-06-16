#!/usr/bin/env python3
"""
Làm giàu dữ liệu: phân loại món, gán tags, phát hiện quán gốc.

Input:  data/clean/vendors_cleaned.csv
Output: data/enriched/vendors_enriched.csv
"""

import re, sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT = PROJECT_ROOT / "data" / "clean" / "vendors_cleaned.csv"
OUTPUT = PROJECT_ROOT / "data" / "enriched" / "vendors_enriched.csv"

# ── Category detection by keywords in dish_name ──
CATEGORY_RULES = [
    ("Bánh", [
        "bánh", "bánh mì", "bánh mỳ", "bánh cuốn", "bánh xèo",
        "bánh bông lan", "bánh bèo", "bánh khọt", "bánh ướt",
        "bánh tráng", "bánh bao", "bánh rán", "bánh canh",
        "bánh flan", "bánh tiêu", "bánh cam", "bánh da lợn",
        "bánh mỳ miến",
    ]),
    ("Phở/Bún/Miến", [
        "phở", "bún", "miến", "hủ tiếu", "mì quảng",
        "bánh canh", "bún đậu", "bún chả", "bún riêu",
        "bún bò", "bún ốc", "bún thang", "mì vằn thắn",
        "cao lầu", "bánh đa",
    ]),
    ("Chè/Tráng miệng", [
        "chè", "kem", "caramen", "sữa chua", "bánh flan",
        "rau câu", "thạch", "cháo", "tào phớ", "trà sữa",
        "sinh tố", "nước mía", "nước dừa",
    ]),
    ("Ốc/Hải sản", [
        "ốc", "nghêu", "sò", "bạch tuộc", "mực",
        "cua", "ghẹ", "tôm", "hàu", "hải sản",
    ]),
    ("Nem/Chả/Gỏi", [
        "nem", "chả", "gỏi", "giò", "chạo", "tré",
        "bì cuốn", "ram", "nộm",
    ]),
    ("Đồ nướng", [
        "nướng", "xiên", "que", "bò nướng", "gà nướng",
        "thịt nướng", "lẩu", "nướng than",
    ]),
    ("Cơm", [
        "cơm", "xôi", "cơm tấm", "cơm gà",
    ]),
    ("Đồ uống", [
        "cà phê", "trà", "sinh tố", "nước ép",
        "sữa chua", "trà sữa", "matcha",
    ]),
]

# Keywords that suggest "original" / oldest vendor
ORIGINAL_KEYWORDS = [
    "gốc", "đầu tiên", "lâu đời", "từ năm", "truyền thống",
    "original", "chính gốc", "chính hiệu", "gia truyền",
    "cổ truyền", "xưa nhất", "nổi tiếng nhất",
]

# Dish tags
TAG_KEYWORDS = {
    "ăn sáng": ["sáng", "breakfast", "ăn sáng"],
    "ăn trưa": ["trưa", "lunch"],
    "ăn tối": ["tối", "dinner", "chiều"],
    "ăn vặt": ["vặt", "snack", "ăn chơi", "lặt vặt"],
    "mặn": ["mặn", "thịt", "nước mắm", "mắm"],
    "ngọt": ["ngọt", "đường", "chè", "kem"],
    "cay": ["cay", "ớt", "sa tế"],
    "chay": ["chay", "không thịt", "rau"],
    "nóng": ["nóng", "nước dùng", "súp", "canh"],
    "lạnh": ["lạnh", "đá", "mát"],
}


def categorize(dish_name: str) -> str:
    """Detect dish category from name."""
    if pd.isna(dish_name):
        return "Khác"
    name = str(dish_name).lower().strip()
    for cat, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in name:
                return cat
    return "Khác"


def detect_tags(dish_name: str, description: str) -> str:
    """Detect tags from dish name and description."""
    text = f"{dish_name} {description}".lower()
    tags = []
    for tag, keywords in TAG_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                tags.append(tag)
                break
    return ";".join(tags) if tags else ""


def detect_original(dish_name: str, vendor_name: str, description: str) -> bool:
    """Detect if this is likely the original vendor."""
    text = f"{vendor_name} {description}".lower()
    for kw in ORIGINAL_KEYWORDS:
        if kw in text:
            return True
    return False


def extract_year(text: str) -> int | None:
    """Try to extract founding year from text."""
    if pd.isna(text):
        return None
    years = re.findall(r"(?:từ năm|since|năm)\s*(\d{4})", str(text), re.IGNORECASE)
    if years:
        y = int(years[0])
        return y if 1950 <= y <= 2026 else None
    return None


def main():
    print("=" * 50)
    print("STREET FOOD DIRECTORY - Data Enrichment")

    if not INPUT.exists():
        print(f"ERROR: {INPUT} not found. Run clean_data.py first.")
        sys.exit(1)

    df = pd.read_csv(INPUT)
    print(f"Loaded: {len(df)} vendors")

    # Categorize
    df["dish_category"] = df["dish_name"].apply(categorize)
    cat_counts = df["dish_category"].value_counts()
    for cat, count in cat_counts.items():
        print(f"  {cat}: {count}")

    # Tags
    df["tags"] = df.apply(
        lambda r: detect_tags(r["dish_name"], r.get("description", "")),
        axis=1
    )

    # Original detection
    if "is_original" not in df.columns or df["is_original"].isna().all():
        df["is_original"] = df.apply(
            lambda r: detect_original(
                r["dish_name"], r.get("vendor_name", ""), r.get("description", "")
            ),
            axis=1
        )

    # Extract founding year
    if "established" in df.columns:
        mask = df["established"].isna() | (df["established"] == "nan")
        df.loc[mask, "established"] = df.loc[mask].apply(
            lambda r: extract_year(str(r.get("description", ""))), axis=1
        )

    # Generate slug fields for URL generation
    def make_slug(val):
        if pd.isna(val) or not val:
            return "unknown"
        slug = str(val).lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        return slug[:60]

    df["province_slug"] = df["province"].apply(make_slug)
    df["dish_slug"] = df["dish_name"].apply(make_slug)
    df["vendor_slug"] = df["vendor_name"].apply(make_slug)

    # Save
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\nSaved: {OUTPUT}")
    print(f"Categories: {df['dish_category'].nunique()}")
    print(f"Originals detected: {df['is_original'].sum()}")


if __name__ == "__main__":
    main()
