"""
Cafe v0.5 - site_generator
Generates dist/cafe_site

Usage: python -m showcases.cafe.site_generator
"""
from __future__ import annotations
import pathlib
from showcases.cafe.product_app import render_page
from showcases.cafe.content.static_writer import clean_dist, write_file

DIST = pathlib.Path("dist/cafe_site")

PAGES = ["index", "menu", "about"]
LANGS = ["ru", "en"]

def generate():
    clean_dist(DIST)
    count = 0
    for lang in LANGS:
        for page in PAGES:
            data = render_page(page, lang)
            # structure: dist/cafe_site/ru/index.html, /ru/menu.html etc + default root
            if page == "index":
                # root for language
                write_file(DIST, f"{lang}/index.html", data["html"])
                # default language copy to root index
                if lang == "ru":
                    write_file(DIST, f"index.html", data["html"])
            else:
                write_file(DIST, f"{lang}/{page}.html", data["html"])
                if lang == "ru":
                    write_file(DIST, f"{page}.html", data["html"])
            count += 1
    # also generate en root
    # summary
    print(f"[site_generator] Generated {count} pages to {DIST.resolve()}")
    for p in sorted(DIST.rglob("*.html")):
        print(f"  - {p.relative_to(DIST)}")
    return DIST

if __name__ == "__main__":
    generate()
