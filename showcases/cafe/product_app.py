from __future__ import annotations
from typing import Dict

try:
    from showcases.cafe.services.cafe_language_service import resolve_language

    HAS_LANGUAGE_SERVICE = True
except Exception:
    HAS_LANGUAGE_SERVICE = False

    def resolve_language(request=None, visitor_lang=None, admin_lang=None, **kw):
        return (
            admin_lang
            if admin_lang in ("ru", "en")
            else visitor_lang
            if visitor_lang in ("ru", "en")
            else "ru"
        )


from showcases.cafe.content.cafe_info import (
    CAFE_IDENTITY,
    get_menu_by_category,
    get_seo_for_page,
    ABOUT,
)

UI = {
    "ru": {"home": "Главная", "menu": "Меню", "about": "О нас"},
    "en": {"home": "Home", "menu": "Menu", "about": "About"},
}


def _load_base():
    from pathlib import Path

    p = Path(__file__).parent / "templates" / "base.html"
    if p.exists():
        txt = p.read_text(encoding="utf-8")
        # если файл старый с {% block %} — заменим на наш v0.6 шаблон
        if "{% block content %}" in txt or "{{ body" not in txt:
            # fallback к встроенному v0.6 шаблону
            return None
        return txt
    return None


BASE_FALLBACK = """<!doctype html>
<html lang="{{ lang }}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title><meta name="description" content="{{ description }}">
<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:0 auto;padding:16px} header{display:flex;justify-content:space-between;border-bottom:1px solid #ddd;padding-bottom:12px;margin-bottom:24px;flex-wrap:wrap} nav a{margin-right:12px;text-decoration:none} nav a.active{font-weight:bold} footer{margin-top:32px;border-top:1px solid #ddd;padding-top:12px;color:#666}</style>
</head><body><header><div><strong>{{ cafe_name }}</strong> - {{ city }}</div>
<nav><a href="{{ nav.home }}">{{ ui.home }}</a> <a href="{{ nav.menu }}">{{ ui.menu }}</a> <a href="{{ nav.about }}">{{ ui.about }}</a> | <a href="{{ lang_switch.ru }}">RU</a> <a href="{{ lang_switch.en }}">EN</a></nav></header>
<main>{{ body | safe }}</main><footer>{{ cafe_name }} - 150 MDL - bakery - {{ city }}</footer></body></html>"""


def render_page(page: str, lang: str) -> Dict[str, str]:
    lang = "en" if lang == "en" else "ru"
    seo = get_seo_for_page(page, lang)
    menu_by_cat = get_menu_by_category()
    name = CAFE_IDENTITY["name"]
    city = CAFE_IDENTITY["city"]
    tagline = CAFE_IDENTITY["tagline"][lang]
    about_text = ABOUT[lang]
    ui = UI[lang]

    if page == "index":
        body = f"<h1>{name}</h1><p>{tagline}</p><p>{about_text}</p><p>Средний чек 150 MDL - bakery, хлеб, круассаны, кофе.</p>"
    elif page == "menu":
        items_html = ""
        for cat, items in menu_by_cat.items():
            items_html += f"<h2>{cat}</h2><ul>"
            for it in items:
                n = it.name_ru if lang == "ru" else it.name_en
                items_html += f"<li>{n} - {it.price_mdl} MDL</li>"
            items_html += "</ul>"
        body = (
            f"<h1>{ui['menu']} - {name}</h1><p>150 MDL average - bakery</p>{items_html}"
        )
    else:
        body = (
            f"<h1>{ui['about']} - {name}</h1><p>{about_text}</p><p>bakery in {city}</p>"
        )

    nav = (
        {"home": "/", "menu": "/menu.html", "about": "/about.html"}
        if lang == "ru"
        else {"home": "/en/", "menu": "/en/menu.html", "about": "/en/about.html"}
    )
    lang_switch = (
        {"ru": "/", "en": "/en/"}
        if page == "index"
        else {"ru": f"/{page}.html", "en": f"/en/{page}.html"}
    )

    tmpl = _load_base() or BASE_FALLBACK
    html = (
        tmpl.replace("{{ lang }}", lang)
        .replace("{{ title }}", seo["title"])
        .replace("{{ description }}", seo["description"])
        .replace("{{ cafe_name }}", name)
        .replace("{{ city }}", city)
        .replace("{{ body | safe }}", body)
        .replace("{{ page }}", page)
        .replace("{{ ui.home }}", ui["home"])
        .replace("{{ ui.menu }}", ui["menu"])
        .replace("{{ ui.about }}", ui["about"])
        .replace("{{ nav.home }}", nav["home"])
        .replace("{{ nav.menu }}", nav["menu"])
        .replace("{{ nav.about }}", nav["about"])
        .replace("{{ lang_switch.ru }}", lang_switch["ru"])
        .replace("{{ lang_switch.en }}", lang_switch["en"])
    )
    # очистка остатков Jinja active логики
    html = (
        html.replace(
            "{{ 'active' if page=='index' else '' }}",
            "active" if page == "index" else "",
        )
        .replace(
            "{{ 'active' if page=='menu' else '' }}", "active" if page == "menu" else ""
        )
        .replace(
            "{{ 'active' if page=='about' else '' }}",
            "active" if page == "about" else "",
        )
    )
    html = (
        html.replace("{% block content %}{% endblock %}", body)
        .replace("{% block content %}", "")
        .replace("{% endblock %}", "")
    )
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
    app = FastAPI(title="Cafe Aurora v0.6")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(render_page("index", "ru")["html"])

    @app.get("/menu", response_class=HTMLResponse)
    def menu():
        return HTMLResponse(render_page("menu", "ru")["html"])

    @app.get("/about", response_class=HTMLResponse)
    def about():
        return HTMLResponse(render_page("about", "ru")["html"])

    @app.get("/en/", response_class=HTMLResponse)
    def i_en():
        return HTMLResponse(render_page("index", "en")["html"])

    @app.get("/en/menu.html", response_class=HTMLResponse)
    def m_en():
        return HTMLResponse(render_page("menu", "en")["html"])

    @app.get("/en/about.html", response_class=HTMLResponse)
    def a_en():
        return HTMLResponse(render_page("about", "en")["html"])

    return app


app = create_product_app()
