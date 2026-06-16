#!/usr/bin/env python3
"""
Làm sạch dữ liệu món ăn đường phố từ nhiều nguồn.

Input:  data/raw/ (bất kỳ CSV nào, tự detect columns)
Output: data/clean/vendors_cleaned.csv (chuẩn hóa cấu trúc)

Hỗ trợ input từ: Google Maps VN, Foody, manual CSV, Startpage scrape.
"""

import sys, re
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT = PROJECT_ROOT / "data" / "clean" / "vendors_cleaned.csv"

# Standard output columns
STD_COLS = [
    "dish_name", "vendor_name", "address", "ward", "district",
    "province", "price_range", "hours", "is_original",
    "established", "rating", "description", "tags",
    "dish_category", "image_urls", "source"
]

# VN province name normalization
PROVINCE_NORM = {
    "tp hồ chí minh": "TP Hồ Chí Minh", "sài gòn": "TP Hồ Chí Minh",
    "hcm": "TP Hồ Chí Minh", "tphcm": "TP Hồ Chí Minh",
    "hà nội": "Hà Nội", "hn": "Hà Nội",
    "hải dương": "Hải Dương", "hải phòng": "Hải Phòng",
    "đà nẵng": "Đà Nẵng", "cần thơ": "Cần Thơ",
    "nha trang": "Khánh Hòa", "vũng tàu": "Bà Rịa - Vũng Tàu",
    "đà lạt": "Lâm Đồng", "huế": "Thừa Thiên Huế",
    "hạ long": "Quảng Ninh",
}

# Column name aliases for auto-detection
COL_ALIASES = {
    "dish_name": ["dish_name", "món", "dish", "food_name", "tên món", "name", "title"],
    "vendor_name": ["vendor_name", "quán", "vendor", "shop", "tên quán", "restaurant"],
    "address": ["address", "địa chỉ", "location", "addr", "full_address"],
    "price_range": ["price_range", "giá", "price", "khoảng giá", "cost"],
    "hours": ["hours", "giờ mở cửa", "opening_hours", "time", "schedule"],
    "rating": ["rating", "đánh giá", "sao", "score", "avg_rating"],
    "description": ["description", "mô tả", "desc", "note", "ghi chú"],
    "province": ["province", "tỉnh", "city", "thành phố", "state"],
    "district": ["district", "quận", "huyện", "quan", "huyen"],
}


def detect_columns(df: pd.DataFrame) -> dict:
    """Map input columns to standard names."""
    mapping = {}
    lower_cols = {c.lower().strip(): c for c in df.columns}

    for std_col, aliases in COL_ALIASES.items():
        for alias in aliases:
            if alias in lower_cols:
                mapping[std_col] = lower_cols[alias]
                break

    print("Column mapping:")
    for k, v in mapping.items():
        print(f"  {k}: {v}")
    return mapping


def clean_data(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Clean and standardize data."""
    out = pd.DataFrame()

    for std_col in STD_COLS:
        src = mapping.get(std_col)
        if src and src in df.columns:
            out[std_col] = df[src].astype(str).str.strip()
            out[std_col] = out[std_col].replace(["nan", "None", ""], None)
        else:
            out[std_col] = None

    # Remove rows where both dish_name AND vendor_name are missing
    out = out[~(out["dish_name"].isna() & out["vendor_name"].isna())]

    # Normalize province names
    def norm_prov(val):
        if pd.isna(val):
            return None
        v = str(val).lower().strip()
        return PROVINCE_NORM.get(v, str(val).title())

    out["province"] = out["province"].apply(norm_prov)

    # Clean price
    out["price_range"] = out["price_range"].apply(
        lambda x: re.sub(r"[^\d.,\-\sđvn]+", "", str(x)).strip() if pd.notna(x) else None
    )

    # Add ID
    out.insert(0, "id", range(1, len(out) + 1))

    return out


def main():
    print("=" * 50)
    print("STREET FOOD DIRECTORY - Data Cleaning")

    csv_files = list(RAW_DIR.glob("*.csv"))
    if not csv_files:
        print(f"ERROR: No CSV files in {RAW_DIR}")
        print("Add your CSV data then re-run.")
        sys.exit(1)

    all_rows = []
    for f in csv_files:
        print(f"\nProcessing: {f.name}")
        try:
            df = pd.read_csv(f, encoding="utf-8")
        except:
            df = pd.read_csv(f, encoding="latin-1")
        print(f"  Rows: {len(df)}")
        mapping = detect_columns(df)
        cleaned = clean_data(df, mapping)
        all_rows.append(cleaned)

    result = pd.concat(all_rows, ignore_index=True)
    result = result.drop_duplicates(subset=["dish_name", "vendor_name", "address"], keep="first")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\nSaved: {OUTPUT}")
    print(f"Total: {len(result)} vendors across {result['province'].nunique()} provinces")


if __name__ == "__main__":
    main()
