from __future__ import annotations
from typing import Dict

try:
    from showcases.cafe.services.cafe_language_service import resolve_language

    HAS_LANGUAGE_SERVICE = True
except Exception:
    HAS_LANGUAGE_SERVICE = False

    def resolve_language(request=None, visitor_lang=None, admin_lang=None, **kw):
        if admin_lang in ("ru", "en"):
            return admin_lang
        if visitor_lang in ("ru", "en"):
            return visitor_lang
        return "ru"


from showcases.cafe.content.cafe_info import (
    CAFE_IDENTITY,
    get_menu_by_category,
    get_seo_for_page,
    ABOUT,
)


def render_page(page: str, lang: str) -> Dict[str, str]:
    lang = "ru" if lang == "ru" else "en"
    seo = get_seo_for_page(page, lang)
    menu_by_cat = get_menu_by_category()
    name = CAFE_IDENTITY["name"]
    tagline = CAFE_IDENTITY["tagline"][lang]
    about_text = ABOUT[lang]
    if page == "index":
        body = f"<h1>{name}</h1><p>{tagline}</p><p>{about_text}</p><p>150 MDL</p><p>bakery</p>"
    elif page == "menu":
        items_html = ""
        for cat, items in menu_by_cat.items():
            items_html += f"<h2>{cat}</h2><ul>"
            for it in items:
                n = it.name_ru if lang == "ru" else it.name_en
                items_html += f"<li>{n} - {it.price_mdl} MDL</li>"
            items_html += "</ul>"
        body = f"<h1>Menu - {name}</h1>{items_html}"
    else:
        body = f"<h1>About - {name}</h1><p>{about_text}</p><p>bakery in {CAFE_IDENTITY['city']}</p>"
    html = f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><title>{seo['title']}</title><meta name='description' content='{seo['description']}'><meta property='og:description' content='{seo['description']}'></head><body>{body}<footer>{name} - 150 MDL - {seo['description']}</footer></body></html>"
    return {
        "html": html,
        "title": seo["title"],
        "description": seo["description"],
        "lang": lang,
    }


def create_product_app():
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse
    except ImportError:
        return None
    app = FastAPI(title="Cafe Aurora Product App v0.5")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(render_page("index", "ru")["html"])

    @app.get("/menu", response_class=HTMLResponse)
    def menu():
        return HTMLResponse(render_page("menu", "ru")["html"])

    @app.get("/about", response_class=HTMLResponse)
    def about():
        return HTMLResponse(render_page("about", "ru")["html"])

    return app


app = create_product_app()
