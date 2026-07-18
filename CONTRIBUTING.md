# Đóng góp cho Đặc Sản Phố

Cảm ơn bạn đã quan tâm đóng góp! 🎉

## Cách đóng góp

### Thêm đặc sản mới

Cách dễ nhất: gửi thông tin quán ăn qua [Issues](https://github.com/truongsonpdf24112000-glitch/dacsanpho/issues) với template "Thêm quán mới".

### Gửi Pull Request

```bash
# 1. Fork repo
# 2. Clone fork
git clone https://github.com/YOUR_USERNAME/dacsanpho.git
cd dacsanpho

# 3. Thêm data vào data/enriched/vendors_enriched.csv
# HOẶC sửa templates/css

# 4. Generate site
pip install pandas
python scripts/generate_site.py

# 5. Commit & push
git checkout -b add-dish-ten-mon
git add .
git commit -m "feat: thêm quán [tên quán] tại [tỉnh]"
git push origin add-dish-ten-mon
```

### Quy ước commit

- `feat:` thêm quán mới / tính năng mới
- `fix:` sửa thông tin sai
- `style:` CSS / giao diện
- `docs:` tài liệu

## Cộng đồng

- Tôn trọng mọi người tham gia
- Xem [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
