#!/usr/bin/env python3
"""
Generate static HTML site for Vietnamese street food directory.

Input:  data/enriched/vendors_enriched.csv
Output: public/ (complete static site)

Site structure:
  public/
  ├── index.html
  ├── tinh/{province_slug}/index.html
  ├── mon/{dish_slug}-{id}/index.html
  ├── sitemap.xml
  └── robots.txt
"""

import json, re, sys
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

FOOTER_LINKS = '<br>'.join([
    f'<a href="/tinh/{s}/">{n}</a>'
    for s, n in [("ha-noi","Hà Nội"),("tp-ho-chi-minh","TP HCM"),
                 ("hai-duong","Hải Dương"),("hai-phong","Hải Phòng"),
                 ("da-nang","Đà Nẵng"),("can-tho","Cần Thơ")]
])

def load():
    if not INPUT.exists():
        print(f"ERROR: {INPUT} not found. Run enrich_data.py first."); sys.exit(1)
    return pd.read_csv(INPUT)

def load_tpl(name):
    p = TEMPLATES / name
    return p.read_text(encoding="utf-8") if p.exists() else ""

def write(path, html):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")

def render(title, desc, content, canonical, schema="", depth=0):
    base = load_tpl("base.html")
    sp = "../" * depth if depth > 0 else ""
    base = base.replace("{{TITLE}}", title)
    base = base.replace("{{DESCRIPTION}}", desc)
    base = base.replace("{{STYLE_PATH}}", sp + "css/")
    base = base.replace("{{CANONICAL}}", canonical)
    base = base.replace("{{SCHEMA}}", schema)
    base = base.replace("{{FOOTER_LINKS}}", FOOTER_LINKS)
    base = base.replace("{{YEAR}}", YEAR)
    return base.replace("{{CONTENT}}", content)

def vendor_card(r, depth=0):
    """Generate card HTML for a vendor."""
    sp = "../" * depth if depth > 0 else ""
    dish = str(r["dish_name"])
    vname = r.get("vendor_name", "")
    if pd.isna(vname) or str(vname).strip() in ("", "nan", "None"):
        vname = ""
    name = str(vname) if vname else ""
    province = str(r.get("province", ""))
    price = str(r.get("price_range", ""))
    rid = int(r["id"])
    slug = str(r.get("dish_slug", f"mon-{rid}"))
    is_orig = r.get("is_original") in [True, "True", "true", "1"]
    badges = '<span class="badge badge-original">Quán gốc</span> ' if is_orig else ""
    display_name = f"{name} · " if name else ""

    return f"""<div class="card">
  <h3><a href="{sp}mon/{slug}-{rid}/">{dish}</a></h3>
  <div class="meta">{badges}{display_name}{province}</div>
  <div class="price">{price}</div>
</div>"""

def gen_homepage(df):
    print("Generating homepage...")
    total = len(df)
    provinces = df["province"].nunique()
    dishes = df["dish_name"].nunique()

    # Province cards
    pc = df.groupby(["province", "province_slug"]).size().reset_index(name="n")
    pc = pc.sort_values("n", ascending=False).head(24)
    prov_cards = "".join(
        f'<a href="/tinh/{r["province_slug"]}/" class="card"><h3>{r["province"]}</h3><div class="meta">{r["n"]} quán</div></a>'
        for _, r in pc.iterrows()
    )

    # Top dishes
    dc = df.groupby(["dish_name", "dish_slug"]).size().reset_index(name="n")
    dc = dc.sort_values("n", ascending=False).head(12)
    dish_cards = "".join(
        f'<div class="card"><h3><a href="/mon/?dish={r["dish_slug"]}">{r["dish_name"]}</a></h3><div class="meta">{r["n"]} quán</div></div>'
        for _, r in dc.iterrows()
    )

    # Original spots
    orig = df[df["is_original"].isin([True, "True", "true", "1"])].head(12)
    orig_cards = "".join(vendor_card(r) for _, r in orig.iterrows())

    # Categories
    cats = df["dish_category"].value_counts().head(12)
    cat_cards = "".join(
        f'<div class="card"><h3><a href="/mon/?cat={i}">{i}</a></h3><div class="meta">{c} quán</div></div>'
        for i, c in cats.items()
    )

    content = load_tpl("home_content.html")
    content = content.replace("{{TOTAL}}", str(total))
    content = content.replace("{{PROVINCES}}", str(provinces))
    content = content.replace("{{DISHES}}", str(dishes))
    content = content.replace("{{PROVINCE_CARDS}}", prov_cards)
    content = content.replace("{{DISH_CARDS}}", dish_cards)
    content = content.replace("{{ORIGINAL_CARDS}}", orig_cards)
    content = content.replace("{{CATEGORY_CARDS}}", cat_cards)

    html = render(f"{SITE} — Danh Bạ Món Ăn Đường Phố Việt Nam",
                  f"Khám phá {total}+ quán ăn đường phố trên {provinces} tỉnh thành. Tìm quán gốc, đúng vị.",
                  content, URL + "/", depth=0)
    write(PUBLIC / "index.html", html)

def gen_provinces(df):
    print(f"Generating province pages...")
    for (prov, slug), grp in df.groupby(["province", "province_slug"]):
        cnt = len(grp)
        cards = "".join(vendor_card(r, depth=1) for _, r in grp.iterrows())

        # Nearby (same region)
        nearby = '<section class="section"><h2>Tỉnh lân cận</h2><div class="grid grid-2">'
        for ps in df["province_slug"].unique()[:6]:
            if ps != slug:
                nearby += f'<a href="/tinh/{ps}/" class="card"><h3>{ps.replace("-"," ").title()}</h3></a>'
        nearby += "</div></section>"

        content = load_tpl("province_content.html")
        content = content.replace("{{PROVINCE}}", str(prov))
        content = content.replace("{{COUNT}}", str(cnt))
        content = content.replace("{{VENDOR_CARDS}}", cards)
        content = content.replace("{{NEARBY}}", nearby)

        html = render(f"Món Ăn Đường Phố {prov} — {cnt} quán ngon — {SITE}",
                      f"Khám phá {cnt} quán ăn đường phố tại {prov}. Đặc sản địa phương chính gốc.",
                      content, f"{URL}/tinh/{slug}/", depth=1)
        write(PUBLIC / "tinh" / slug / "index.html", html)

    print(f"  {df['province_slug'].nunique()} province pages")

def gen_details(df):
    print("Generating detail pages...")
    for _, r in df.iterrows():
        rid = int(r["id"])
        slug = str(r.get("dish_slug", f"mon-{rid}"))
        dish = str(r["dish_name"])
        vname = str(r.get("vendor_name", dish))
        prov = str(r.get("province", ""))
        prov_slug = str(r.get("province_slug", ""))
        addr = str(r.get("address", ""))
        price = str(r.get("price_range", ""))
        hours = str(r.get("hours", ""))
        desc = str(r.get("description", f"{dish} — món ăn đường phố nổi tiếng tại {prov}."))
        cat = str(r.get("dish_category", "Khác"))
        est = r.get("established", "")
        is_orig = r.get("is_original") in [True, "True", "true", "1"]

        orig_badge = '<span class="badge badge-original">Quán gốc</span>' if is_orig else ""
        est_line = f'<div class="row"><span>📅 Từ năm</span><span>{int(est)}</span></div>' if pd.notna(est) and str(est).isdigit() else ""

        # Other vendors of same dish
        others = df[(df["dish_name"] == dish) & (df["id"] != rid)].head(4)
        other_cards = "".join(vendor_card(r2, depth=2) for _, r2 in others.iterrows()) if len(others) > 0 else ""

        content = load_tpl("detail_content.html")
        content = content.replace("{{DISH_NAME}}", dish)
        content = content.replace("{{VENDOR_NAME}}", vname)
        content = content.replace("{{PROVINCE}}", prov)
        content = content.replace("{{PROVINCE_SLUG}}", prov_slug)
        content = content.replace("{{ADDRESS}}", addr)
        content = content.replace("{{PRICE}}", price)
        content = content.replace("{{HOURS}}", hours)
        content = content.replace("{{DESCRIPTION}}", desc)
        content = content.replace("{{CATEGORY}}", cat)
        content = content.replace("{{CATEGORY_SLUG}}", cat.lower().replace("/","-"))
        content = content.replace("{{OTHER_VENDORS}}", other_cards)
        content = content.replace("{{ESTABLISHED}}", str(int(est)) if pd.notna(est) and str(est).isdigit() else "")
        content = content.replace("{{#IS_ORIGINAL}}", orig_badge)
        content = content.replace("{{/IS_ORIGINAL}}", "")
        content = content.replace("{{#ESTABLISHED}}", est_line)
        content = content.replace("{{/ESTABLISHED}}", "")

        schema = json.dumps({
            "@context": "https://schema.org",
            "@type": "FoodEstablishment",
            "name": f"{dish} — {vname}",
            "address": {"addressLocality": prov, "streetAddress": addr},
        })

        html = render(f"{dish} — {vname} tại {prov} — {SITE}",
                      f"{dish} — {vname} tại {addr}, {prov}. {desc[:120]}",
                      content, f"{URL}/mon/{slug}-{rid}/", f'<script type="application/ld+json">{schema}</script>', depth=2)
        write(PUBLIC / "mon" / f"{slug}-{rid}" / "index.html", html)

    print(f"  {len(df)} detail pages")

def gen_supporting(df):
    # Sitemap
    urls = [f"{URL}/"]
    for ps in df["province_slug"].unique():
        urls.append(f"{URL}/tinh/{ps}/")
    for _, r in df.iterrows():
        urls.append(f"{URL}/mon/{r['dish_slug']}-{int(r['id'])}/")

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    sitemap += "\n</urlset>\n"
    write(PUBLIC / "sitemap.xml", sitemap)
    write(PUBLIC / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n")

    # Provinces index
    pc = df.groupby(["province", "province_slug"]).size().reset_index(name="n")
    pc = pc.sort_values("n", ascending=False)
    cards = "".join(
        f'<a href="/tinh/{r["province_slug"]}/" class="card"><h3>{r["province"]}</h3><div class="meta">{r["n"]} quán</div></a>'
        for _, r in pc.iterrows()
    )
    html = render("Tất cả tỉnh thành — " + SITE, "Danh sách tỉnh thành có món ăn đường phố.",
                  f'<div class="container"><h1 style="padding:24px 0">Tất cả tỉnh thành</h1><div class="grid grid-2">{cards}</div></div>',
                  f"{URL}/tinh/", depth=1)
    write(PUBLIC / "tinh" / "index.html", html)
    print("  sitemap, robots.txt, provinces index done")

def main():
    print("=" * 50)
    print(f"{SITE} — Static Site Generator")
    df = load()
    print(f"Loaded {len(df)} vendors, {df['province'].nunique()} provinces, {df['dish_name'].nunique()} dishes")
    gen_homepage(df)
    gen_provinces(df)
    gen_details(df)
    gen_supporting(df)
    files = sum(1 for _ in PUBLIC.rglob("*.html"))
    print(f"\nDone! {files} files in {PUBLIC}")

if __name__ == "__main__":
    main()
