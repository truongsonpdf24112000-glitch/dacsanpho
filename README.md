# Danh Bạ Món Ăn Đường Phố Việt Nam

> Static HTML directory of Vietnamese street food — find authentic local dishes and their original vendors.
> Built following the Frey Chu "Static Pillar Page Directory" model, adapted for VN market.

## Data Model

Mỗi dòng = 1 quán/vendor bán món đường phố:

| Field | Type | Example | Notes |
|---|---|---|---|
| id | int | 1 | Auto-increment |
| dish_name | string | Bánh mỳ miến | Tên món chính |
| vendor_name | string | Quán bà Lan | Tên quán (có thể để trống nếu là xe đẩy) |
| address | string | 123 Trần Hưng Đạo | Địa chỉ cụ thể |
| ward | string | Phường Trần Hưng Đạo | Phường/xã |
| district | string | TP Hải Dương | Quận/huyện/thành phố |
| province | string | Hải Dương | Tỉnh/thành phố |
| price_range | string | 15.000 - 25.000đ | Khoảng giá |
| hours | string | 14:00 - 20:00 | Giờ mở cửa |
| is_original | bool | true | Có phải quán gốc / lâu đời nhất không |
| established | int | 1985 | Năm mở quán (nếu biết) |
| rating | float | 4.5 | Đánh giá 1-5 |
| description | string | Bánh mỳ giòn, miến... | Mô tả ngắn |
| tags | string | bánh,mặn,ăn sáng | Tags phân loại |
| dish_category | string | Bánh | Danh mục món |
| image_urls | string | url1,url2,url3 | Ảnh món ăn |
| source | string | google_maps | Nguồn data |

## Categories (Danh mục món)

- **Bánh**: bánh mì, bánh cuốn, bánh xèo, bánh bông lan, bánh mỳ miến...
- **Phở/Bún/Miến**: phở bò, bún chả, bún đậu, miến lươn...
- **Chè/Tráng miệng**: chè, kem, sữa chua, caramen...
- **Ốc/Hải sản**: ốc luộc, nghêu hấp, bạch tuộc...
- **Nem/Chả/Gỏi**: nem rán, chả cá, gỏi cuốn...
- **Đồ nướng**: thịt nướng, xiên que, bò nướng...
- **Khác**: trà sữa, sinh tố, đồ uống...

## Project Structure

```
street-food-directory/
├── data/
│   ├── raw/           # Raw scraped CSV files
│   ├── clean/         # Cleaned & verified
│   └── enriched/      # Final enriched with tags
├── templates/         # HTML templates
├── scripts/           # Python pipeline
├── public/            # Generated static site
│   ├── index.html
│   ├── tinh/          # Province pages
│   ├── mon/           # Dish pages
│   └── css/
└── README.md
```

## Pipeline

```bash
# 1. Scrape (Startpage + manual curation)
python scripts/scrape_data.py

# 2. Clean & verify
python scripts/clean_data.py

# 3. Enrich (categorize, tag, detect originals)
python scripts/enrich_data.py

# 4. Generate static site
python scripts/generate_site.py

# 5. Deploy
cd public && git subtree push --prefix public origin gh-pages
```

## Data Sources (Vietnam)

| Source | Quality | Notes |
|---|---|---|
| Manual curation | ⭐⭐⭐⭐⭐ | Tự tổng hợp - chính xác nhất |
| Google Maps VN | ⭐⭐⭐ | Cần lọc kỹ, nhiễu nhiều |
| Foody.vn | ⭐⭐⭐ | Nhiều quán đóng cửa |
| Facebook Groups | ⭐⭐⭐⭐ | Hội ẩm thực, review đồ ăn |
| TikTok Food Reviews | ⭐⭐⭐ | Khó scrape |
| Startpage search | ⭐⭐⭐ | Proxy Google, hoạt động tốt với query tiếng Việt |
