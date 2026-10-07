from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from showcases.cafe.product_app import render_page

DIST = Path("dist/cafe_site")


def generate():
    out = DIST
    out.mkdir(parents=True, exist_ok=True)
    (out / "en").mkdir(exist_ok=True)
    (out / "ru").mkdir(exist_ok=True)
    for page in ["index", "menu", "about"]:
        # root ru
        data_ru = render_page(page, "ru")
        fname = "index.html" if page == "index" else f"{page}.html"
        (out / fname).write_text(data_ru["html"], encoding="utf-8")
        (out / "ru" / fname).write_text(data_ru["html"], encoding="utf-8")
        # en
        data_en = render_page(page, "en")
        (out / "en" / fname).write_text(data_en["html"], encoding="utf-8")
        print(f" - {fname} ru + en/ru")
    print(f"[site_generator v0.6] Generated to {out.resolve()}")
    return out  # <-- важно для test_generated_site_structure


if __name__ == "__main__":
    generate()
