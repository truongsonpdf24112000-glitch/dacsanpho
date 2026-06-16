#!/usr/bin/env python3
"""
Generate static HTML site — PasGo-style layout.

Input:  data/enriched/vendors_enriched.csv
Output: public/ (complete static site)
"""

import json, re, sys, urllib.parse
from pathlib import Path
from datetime import datetime
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT = PROJECT_ROOT / "data" / "enriched" / "vendors_enriched.csv"
TEMPLATES = PROJECT_ROOT / "templates"
PUBLIC = PROJECT_ROOT / "public"
SITE = "Đặc Sản Phố"
URL = "https://dacsanpho.com"
YEAR = str(datetime.now().year)

CAT_ICONS = {
    "Bánh": "🥖", "Phở/Bún/Miến": "🍜", "Chè/Tráng miệng": "🍨",
    "Ốc/Hải sản": "🦐", "Nem/Chả/Gỏi": "🥢", "Đồ nướng": "🔥",
    "Cơm": "🍚", "Đồ uống": "🥤", "Khác": "🍽️",
    "Lẩu": "🍲", "Ăn vặt": "🍿", "Đặc sản": "🏆", "Chay": "🥬",
}

FOOTER_PROVS = ""
NAV = {"home": "", "province": "", "dish": ""}


def safe_str(val, default=""):
    if pd.isna(val) or str(val).strip() in ("", "nan", "None", "none"):
        return default
    return str(val).strip()


def load():
    if not INPUT.exists():
        print(f"ERROR: {INPUT} not found."); sys.exit(1)
    return pd.read_csv(INPUT)


def load_tpl(name):
    p = TEMPLATES / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write(path, html):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def render(title, desc, content, canonical, schema="", depth=0, nav_active=""):
    base = load_tpl("base.html")
    sp = "../" * depth if depth > 0 else ""

    for k in NAV:
        NAV[k] = ""
    if nav_active in NAV:
        NAV[nav_active] = "active"

    base = base.replace("{{TITLE}}", title)
    base = base.replace("{{DESCRIPTION}}", desc)
    base = base.replace("{{STYLE_PATH}}", sp + "css/")
    base = base.replace("{{CANONICAL}}", canonical)
    base = base.replace("{{SCHEMA}}", schema)
    base = base.replace("{{FOOTER_PROVINCES}}", FOOTER_PROVS)
    base = base.replace("{{NAV_HOME}}", NAV["home"])
    base = base.replace("{{NAV_PROVINCE}}", NAV["province"])
    base = base.replace("{{NAV_DISH}}", NAV["dish"])
    base = base.replace("{{YEAR}}", YEAR)
    return base.replace("{{CONTENT}}", content)


def card_html(r, depth=0):
    """PasGo-style card."""
    sp = "../" * depth if depth > 0 else ""
    dish = safe_str(r.get("dish_name", ""))
    vname = safe_str(r.get("vendor_name", ""))
    display = dish if dish else vname if vname else f"Quán #{int(r['id'])}"
    province = safe_str(r.get("province", ""))
    price = safe_str(r.get("price_range", ""), "Liên hệ")
    rating = r.get("rating", 0) or 0
    rid = int(r["id"])
    slug = safe_str(r.get("dish_slug", ""), safe_str(r.get("vendor_slug", ""), f"quan-{rid}"))
    is_orig = r.get("is_original") in [True, "True", "true", "1"]
    cat = safe_str(r.get("dish_category", ""), "Khác")
    addr = safe_str(r.get("address", ""), f"{province}")
    reviews = int(r.get("reviews_count", 0) or 0) if pd.notna(r.get("reviews_count")) else 0

    # Parse price level for filtering
    price_level = "-1"  # unknown
    price_str = str(r.get("price_range", "")).strip()
    if price_str and price_str not in ("nan", "None", "", "Liên hệ"):
        import re as _re
        nums = _re.findall(r'\d[\d,.]*', price_str.replace(".", ""))
        if nums:
            try:
                max_p = max(int(n) for n in nums if n.isdigit())
                if max_p < 50000: price_level = "0"     # budget
                elif max_p < 150000: price_level = "1"   # mid
                else: price_level = "2"                   # premium
            except:
                pass

    badge = '<span class="card-badge original">⭐ Quán gốc</span>' if is_orig else ""
    cat_icon = CAT_ICONS.get(cat, "🍽️")
    img_url = safe_str(r.get("image_urls", ""))
    
    img_html = ""
    if img_url and img_url.startswith("http"):
        img_html = f'<img src="{img_url}" alt="{display}" loading="lazy">'
    else:
        img_html = cat_icon

    return f"""<div class="card" data-category="{cat}" data-rating="{rating:.0f}" data-reviews="{reviews}" data-price="{price_level}" data-original="{'true' if is_orig else 'false'}">
  <a href="{sp}mon/{slug}-{rid}/">
    <div class="card-img">{badge}{img_html}</div>
    <div class="card-body">
      <h3>{display}</h3>
      <div class="card-meta">
        <span class="card-location">{addr[:40]}</span>
        <span class="card-rating">{rating:.1f}</span>
      </div>
      <div class="card-price">{price}</div>
    </div>
  </a>
</div>"""


def gen_homepage(df):
    print("Generating homepage...")
    total = len(df)
    provinces = df["province"].nunique()

    # Province selector options
    pc = df.groupby(["province", "province_slug"]).size().reset_index(name="n")
    pc = pc.sort_values("n", ascending=False)
    province_options = "".join(
        f'<option value="/tinh/{r["province_slug"]}/">{r["province"]} ({r["n"]})</option>'
        for _, r in pc.iterrows()
    )

    # Category chips
    cats = df["dish_category"].value_counts()
    cat_chips = ""
    for cat_name, count in cats.items():
        if cat_name and cat_name != "Khác":
            icon = CAT_ICONS.get(cat_name, "🍽️")
            cat_chips += f'<span class="cat-chip" onclick="filterCat(\'{cat_name}\')"><span class="icon">{icon}</span>{cat_name}</span>\n'

    # Province grid
    prov_grid = "".join(
        f'<a href="/tinh/{r["province_slug"]}/" class="city-card"><h3>{r["province"]}</h3><div class="count">{r["n"]} quán</div></a>'
        for _, r in pc.head(24).iterrows()
    )

    # Category grid
    cat_grid = "".join(
        f'<a href="/mon/?cat={cat_name}" class="city-card"><h3>{CAT_ICONS.get(cat_name, "🍽️")} {cat_name}</h3><div class="count">{count} quán</div></a>'
        for cat_name, count in cats.items() if cat_name
    )

    # Original spots
    orig = df[df["is_original"].isin([True, "True", "true", "1"])].head(8)
    orig_cards = "".join(card_html(r) for _, r in orig.iterrows()) if len(orig) > 0 else ""

    # Top rated
    top = df.nlargest(8, "rating")
    top_cards = "".join(card_html(r) for _, r in top.iterrows())

    content = load_tpl("home_content.html")
    content = content.replace("{{PROVINCE_OPTIONS}}", province_options)
    content = content.replace("{{CATEGORY_CHIPS}}", cat_chips)
    content = content.replace("{{ORIGINAL_CARDS}}", orig_cards)
    content = content.replace("{{TOP_RATED_CARDS}}", top_cards)
    content = content.replace("{{PROVINCE_GRID}}", prov_grid)
    content = content.replace("{{CATEGORY_GRID}}", cat_grid)

    html = render(f"{SITE} — Danh Bạ Món Ăn Đường Phố Việt Nam",
                  f"Khám phá {total}+ quán ăn đường phố trên {provinces} tỉnh thành.",
                  content, URL + "/", nav_active="home")
    write(PUBLIC / "index.html", html)


def gen_provinces(df):
    print(f"Generating province pages...")
    for (prov, slug), grp in df.groupby(["province", "province_slug"]):
        cnt = len(grp)
        cards = "".join(card_html(r, depth=1) for _, r in grp.iterrows())

        nearby = '<section class="section"><div class="section-header"><h2>Tỉnh Lân Cận</h2></div><div class="city-grid">'
        for ps in df["province_slug"].unique()[:6]:
            if ps != slug:
                nearby += f'<a href="/tinh/{ps}/" class="city-card"><h3>{ps.replace("-"," ").title()}</h3></a>'
        nearby += "</div></section>"

        content = load_tpl("province_content.html")
        content = content.replace("{{PROVINCE}}", str(prov))
        content = content.replace("{{COUNT}}", str(cnt))
        content = content.replace("{{VENDOR_CARDS}}", cards)
        content = content.replace("{{NEARBY}}", nearby)

        html = render(f"Món Ăn Đường Phố {prov} — {cnt} quán — {SITE}",
                      f"Khám phá {cnt} quán ăn đường phố tại {prov}.",
                      content, f"{URL}/tinh/{slug}/", depth=1, nav_active="province")
        write(PUBLIC / "tinh" / slug / "index.html", html)
    print(f"  {df['province_slug'].nunique()} province pages")


def gen_details(df):
    print("Generating detail pages...")
    for _, r in df.iterrows():
        rid = int(r["id"])
        slug = safe_str(r.get("dish_slug", ""), safe_str(r.get("vendor_slug", ""), f"quan-{rid}"))
        dish = safe_str(r["dish_name"], "")
        vname = safe_str(r.get("vendor_name", ""))
        display_name = dish if dish else vname if vname else f"Quán #{rid}"
        prov = safe_str(r.get("province", ""))
        prov_slug = safe_str(r.get("province_slug", ""))
        addr = safe_str(r.get("address", ""))
        price = safe_str(r.get("price_range", ""), "Liên hệ")
        hours = safe_str(r.get("hours", ""), "Chưa có thông tin")
        rating = r.get("rating", 0) or 0
        desc_val = safe_str(r.get("description", ""))
        desc = desc_val if desc_val else f"{display_name} — địa điểm ăn uống tại {prov}."
        cat = safe_str(r.get("dish_category", ""), "Ẩm thực đường phố")
        est = r.get("established", "")
        is_orig = r.get("is_original") in [True, "True", "true", "1"]
        place_id = safe_str(r.get("place_id", ""))
        reviews = int(r.get("reviews_count", 0) or 0) if pd.notna(r.get("reviews_count")) else 0
        website = safe_str(r.get("website", ""))
        img_url = safe_str(r.get("image_urls", ""))
        tags_str = safe_str(r.get("tags", ""))

        # Badge
        badge = '<span style="background:var(--yellow);color:#5c3d00;padding:2px 8px;border-radius:4px;font-size:0.8rem;">⭐ Quán gốc</span> ' if is_orig else ""
        
        # Maps URL
        maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(addr)}" if addr else "#"
        if place_id:
            maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

        est_row = ""
        if pd.notna(est) and str(est).strip() not in ("", "nan", "None"):
            try:
                ey = int(float(est))
                est_row = f'<div class="info-row"><span class="label">📅 Từ năm</span><span class="value">{ey}</span></div>'
            except:
                pass

        # Other vendors — same province, different ID
        others = df[(df["province_slug"] == prov_slug) & (df["id"] != rid)].head(6)
        other_html = ""
        if len(others) > 0:
            other_html = '<section style="margin-top:24px;"><h2 style="font-size:1.1rem;margin-bottom:12px;">🍜 Các quán khác tại ' + prov + '</h2><div class="card-grid">'
            other_html += "".join(card_html(r2, depth=2) for _, r2 in others.iterrows())
            other_html += "</div></section>"

        content = load_tpl("detail_content.html")
        content = content.replace("{{DISPLAY_NAME}}", display_name)
        content = content.replace("{{PROVINCE}}", prov)
        content = content.replace("{{PROVINCE_SLUG}}", prov_slug)
        content = content.replace("{{ADDRESS}}", addr)
        content = content.replace("{{PRICE}}", price)
        content = content.replace("{{HOURS}}", hours)
        content = content.replace("{{RATING}}", f"{rating:.1f}")
        content = content.replace("{{REVIEWS}}", str(reviews))
        content = content.replace("{{DESCRIPTION}}", desc)
        content = content.replace("{{CATEGORY}}", cat)
        content = content.replace("{{PLACE_ID}}", place_id if place_id else "")
        content = content.replace("{{MAPS_URL}}", maps_url)
        content = content.replace("{{BADGE}}", badge)
        content = content.replace("{{ESTABLISHED_ROW}}", est_row)
        content = content.replace("{{OTHER_VENDORS}}", other_html)
        
        # Image HTML
        if img_url and img_url.startswith("http"):
            img_html = f'<div style="border-radius:8px;overflow:hidden;margin-bottom:16px;"><img src="{img_url}" alt="{display_name}" style="width:100%;max-height:400px;object-fit:cover;"></div>'
        else:
            img_html = ""
        content = content.replace("{{IMAGE_HTML}}", img_html)
        
        # Tags
        if tags_str:
            tag_list = [t.strip() for t in tags_str.split(";") if t.strip()]
            tags_html = '<div style="margin:8px 0;display:flex;flex-wrap:wrap;gap:6px;">' + "".join(
                f'<span style="background:#e8f5e9;color:#2e7d32;padding:4px 10px;border-radius:4px;font-size:0.82rem;">✅ {t}</span>'
                for t in tag_list[:10]
            ) + '</div>'
        else:
            tags_html = ""
        content = content.replace("{{TAGS_HTML}}", tags_html)
        
        # Website button
        if website:
            website_button = f'<a href="{website}" target="_blank" rel="nofollow" style="display:inline-flex;align-items:center;gap:6px;background:#ea4335;color:#fff;padding:10px 20px;border-radius:8px;font-weight:600;text-decoration:none;">🌐 Website quán</a>'
        else:
            website_button = ""
        content = content.replace("{{WEBSITE_BUTTON}}", website_button)
        
        # Menu section (from scraped data)
        menu_items = safe_str(r.get("menu_items", ""))
        menu_text = safe_str(r.get("menu_text", ""))
        if menu_items or menu_text:
            menu_html = '<h2 style="font-size:1.1rem;margin:16px 0 8px;">📋 Thực đơn</h2>'
            if menu_items:
                for item in menu_items.split("|")[:10]:
                    item = item.strip()
                    if item:
                        menu_html += f'<div style="padding:8px 0;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;"><span>{item}</span></div>'
            elif menu_text:
                menu_html += f'<p style="background:#fafafa;padding:12px;border-radius:6px;">{menu_text}</p>'
            menu_html = f'<div style="margin:16px 0;">{menu_html}</div>'
        else:
            menu_html = ""
        content = content.replace("{{MENU_SECTION}}", menu_html)
        
        # Website row
        if website:
            website_row = f'<div class="info-row"><span class="label">🌐 Website</span><span class="value"><a href="{website}" target="_blank" rel="nofollow">Truy cập →</a></span></div>'
        else:
            website_row = ""
        content = content.replace("{{WEBSITE_ROW}}", website_row)

        schema = json.dumps({
            "@context": "https://schema.org",
            "@type": "FoodEstablishment",
            "name": display_name,
            "address": {"addressLocality": prov, "streetAddress": addr},
        })

        html = render(f"{display_name} tại {prov} — {SITE}",
                      f"{display_name} — {addr}, {prov}. {desc[:120]}",
                      content, f"{URL}/mon/{slug}-{rid}/",
                      f'<script type="application/ld+json">{schema}</script>', depth=2)
        write(PUBLIC / "mon" / f"{slug}-{rid}" / "index.html", html)

    print(f"  {len(df)} detail pages")


def gen_supporting(df):
    global FOOTER_PROVS
    top = df.groupby(["province", "province_slug"]).size().reset_index(name="n")
    top = top.sort_values("n", ascending=False).head(10)
    FOOTER_PROVS = "\n".join(
        f'<a href="/tinh/{r["province_slug"]}/">{r["province"]}</a>'
        for _, r in top.iterrows()
    )

    urls = [f"{URL}/"]
    for ps in df["province_slug"].unique():
        urls.append(f"{URL}/tinh/{ps}/")
    for _, r in df.iterrows():
        slug = safe_str(r.get("dish_slug", ""), safe_str(r.get("vendor_slug", ""), f"quan-{int(r['id'])}"))
        urls.append(f"{URL}/mon/{slug}-{int(r['id'])}/")

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    sitemap += "\n</urlset>\n"
    write(PUBLIC / "sitemap.xml", sitemap)
    write(PUBLIC / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n")

    pc = df.groupby(["province", "province_slug"]).size().reset_index(name="n")
    pc = pc.sort_values("n", ascending=False)
    cards = "".join(
        f'<a href="/tinh/{r["province_slug"]}/" class="city-card"><h3>{r["province"]}</h3><div class="count">{r["n"]} quán</div></a>'
        for _, r in pc.iterrows()
    )
    html = render("Tất cả tỉnh thành — " + SITE, "Danh sách tỉnh thành.",
                  f'<div class="container"><h1 style="padding:24px 0">Tất cả tỉnh thành</h1><div class="city-grid">{cards}</div></div>',
                  f"{URL}/tinh/", depth=1, nav_active="province")
    write(PUBLIC / "tinh" / "index.html", html)
    
    # Dishes index page
    dc = df.groupby(["dish_name", "dish_slug", "dish_category"]).size().reset_index(name="n")
    dc = dc[dc["dish_name"].notna() & (dc["dish_name"] != "")]
    dc = dc.sort_values("n", ascending=False)
    
    if len(dc) > 0:
        dish_cards = "".join(
            f'<a href="/mon/?cat={r["dish_category"]}" class="city-card"><h3>{r["dish_name"]}</h3><div class="count">{r["n"]} quán</div></a>'
            for _, r in dc.head(100).iterrows()
        )
        dish_html = render("Tất cả món ăn — " + SITE, "Danh sách món ăn đường phố.",
                          f'<div class="container"><h1 style="padding:24px 0">Tất cả món ăn</h1><div class="city-grid">{dish_cards}</div></div>',
                          f"{URL}/mon/", depth=1, nav_active="dish")
    else:
        # Fallback: show all vendors
        vendor_cards = "".join(card_html(r, depth=1) for _, r in df.head(100).iterrows())
        dish_html = render("Tất cả món ăn — " + SITE, "Danh sách quán ăn đường phố.",
                          f'<div class="container"><h1 style="padding:24px 0">Tất cả quán ăn</h1><div class="card-grid">{vendor_cards}</div></div>',
                          f"{URL}/mon/", depth=1, nav_active="dish")
    write(PUBLIC / "mon" / "index.html", dish_html)
    
    print("  sitemap, robots.txt, provinces index, dishes index done")


def main():
    print("=" * 50)
    print(f"{SITE} — Static Site Generator")
    df = load()
    print(f"Loaded {len(df)} vendors, {df['province'].nunique()} provinces")
    gen_supporting(df)
    gen_homepage(df)
    gen_provinces(df)
    gen_details(df)
    files = sum(1 for _ in PUBLIC.rglob("*.html"))
    print(f"\nDone! {files} files in {PUBLIC}")


if __name__ == "__main__":
    main()
