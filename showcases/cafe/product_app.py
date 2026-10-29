from pathlib import Path
import re
import os
from typing import Dict

try:
    from .content.cafe_info import (
        MENU,
        CAFE_IDENTITY,
        CAFE_CONTACT,
        get_menu_by_category,
    )
except ImportError:
    from showcases.cafe.content.cafe_info import (
        MENU,
        CAFE_IDENTITY,
        CAFE_CONTACT,
        get_menu_by_category,
    )
try:
    from .services.cafe_profile_service import cafe_profile_service
    from .services.cafe_language_service import cafe_language_service
except ImportError:
    try:
        from showcases.cafe.services.cafe_profile_service import cafe_profile_service
    except ImportError:
        cafe_profile_service = None
    from showcases.cafe.services.cafe_language_service import cafe_language_service

HAS_LANGUAGE_SERVICE = True
SUPPORTED_LANGUAGES = set(cafe_language_service.supported_languages)
DEFAULT_LANGUAGE = cafe_language_service.default_language
CAFE_BASE_URL = os.environ.get("CAFE_BASE_URL")


def is_menu_ro_complete() -> bool:
    for it in MENU:
        if getattr(it, "slug", "") == "avg_check":
            continue
        name_ro = getattr(it, "name_ro", None)
        if not name_ro:
            return False
        desc_ru = getattr(it, "description_ru", None) or getattr(
            it, "description_en", None
        )
        if desc_ru:
            desc_ro = getattr(it, "description_ro", None)
            if not desc_ro:
                return False
    return True


def _is_valid_phone(phone: str) -> bool:
    if not phone:
        return False
    p = phone.strip()
    if not p:
        return False
    # фиктивные из шаблона
    if '123 456' in p or 'example' in p.lower() or p in ('+123456789', '123456789'):
        return False
    return True


def is_lang_content_complete(lang: str) -> bool:
    if lang == "ru":
        return True
    if lang == "en":
        return all(CAFE_IDENTITY.get(k) for k in ["city_en", "tagline_en", "about_en"])
    if lang == "ro":
        identity_ok = (
            bool(CAFE_IDENTITY.get("city_ro"))
            and bool(CAFE_IDENTITY.get("tagline_ro"))
            and bool(CAFE_IDENTITY.get("about_ro"))
            and bool(CAFE_CONTACT.get("address_ro"))
            and bool(CAFE_CONTACT.get("hours_ro"))
        )
        if not identity_ok:
            return False
        return is_menu_ro_complete()
    return False


def get_complete_languages():
    comp = []
    for lang in SUPPORTED_LANGUAGES:
        if lang in ("ru", "en"):
            comp.append(lang)
        elif lang == "ro" and is_lang_content_complete("ro"):
            comp.append(lang)
    return sorted(comp)


def resolve_language(
    lang: str = None, visitor_lang: str = None, admin_lang: str = None, **kwargs
):
    for cand in [admin_lang, visitor_lang, lang]:
        if cand:
            norm = cafe_language_service.normalize_language(cand)
            if norm in SUPPORTED_LANGUAGES:
                return norm
    return DEFAULT_LANGUAGE


def get_ui_for_lang(lang: str):
    norm = cafe_language_service.normalize_language(lang)
    svc = cafe_language_service.get_ui(norm)
    title = svc.get("menu", {}).get("title", "")
    base = {
        "ru": {
            "home": "Главная",
            "menu": "Меню",
            "about": "О кафе",
            "map": "Карта",
            "avg_check_label": "Средний чек",
        },
        "en": {
            "home": "Home",
            "menu": "Menu",
            "about": "About",
            "map": "Map",
            "avg_check_label": "Average check",
        },
        "ro": {
            "home": "Acasă",
            "menu": title or "Meniu",
            "about": "Despre cafenea",
            "map": "Hartă",
            "avg_check_label": "Cec mediu",
        },
    }
    nav = base.get(norm, base[DEFAULT_LANGUAGE])
    if title:
        nav["menu"] = title
    return nav


UI = {
    "ru": get_ui_for_lang("ru"),
    "en": get_ui_for_lang("en"),
    "ro": get_ui_for_lang("ro"),
}
ROOT = Path(__file__).parent
TEMPLATES = ROOT / "templates"


def get_seo_for_page(page: str, lang: str):
    lang = cafe_language_service.normalize_language(lang)
    name = CAFE_IDENTITY.get("name", "Cafe Name")
    city = CAFE_IDENTITY.get(
        f"city_{lang}", CAFE_IDENTITY.get(f"city_{DEFAULT_LANGUAGE}", "")
    )
    tagline = CAFE_IDENTITY.get(f"tagline_{lang}", "")
    about = CAFE_IDENTITY.get(f"about_{lang}", "")
    ui = get_ui_for_lang(lang)
    if page == "index":
        title = f"{name} {city} — {tagline}".strip(" — ")
        desc = about
    elif page == "menu":
        title = f"{ui['menu']} — {name} {city}"
        desc = f"Menu of {name}"
    else:
        title = f"{ui['about']} — {name} {city}"
        desc = about
    return {"title": title, "description": desc}


def _make_contact_for_lang(lang: str):
    lang = cafe_language_service.normalize_language(lang)
    # Чтение из сервиса если доступен (сохранение после рестарта)
    if cafe_profile_service is not None:
        try:
            prof = cafe_profile_service.get_profile_for_lang(lang)
            addr = prof.get("address")
            hours = prof.get("hours")
            phone = prof.get("phone")
            map_url = prof.get("map_url")
        except Exception:
            addr = None
            hours = None
            phone = None
            map_url = None
    else:
        addr = None
        hours = None
        phone = None
        map_url = None

    # Fallback на старый словарь если сервис не дал данных
    if not addr:
        addr = (
            CAFE_CONTACT.get(f"address_{lang}")
            or CAFE_CONTACT.get(f"address_{DEFAULT_LANGUAGE}")
            or CAFE_CONTACT.get("address_en")
        )
    if not hours:
        hours = (
            CAFE_CONTACT.get(f"hours_{lang}")
            or CAFE_CONTACT.get(f"hours_{DEFAULT_LANGUAGE}")
            or CAFE_CONTACT.get("hours_en")
        )
    if not phone:
        phone = CAFE_CONTACT.get("phone")
    if not map_url:
        map_url = CAFE_CONTACT.get("map_url")

    # Фикс фиктивных контактов - не рендерить tel: с примером
    if not _is_valid_phone(phone):
        phone = None

    # map_url только если реальный http
    if map_url and "example.com" in str(map_url):
        map_url = None
    if not any([addr, hours, phone, map_url]):
        return None
    ui = get_ui_for_lang(lang)
    return {
        "address": addr,
        "hours": hours,
        "phone": phone,
        "map_url": map_url,
        "map_label": ui["map"],
    }


def _avg_check_html(lang: str = "ru"):
    lang = cafe_language_service.normalize_language(lang)
    ui = get_ui_for_lang(lang)
    label = ui.get("avg_check_label", "Average check")
    return f'<p class="avg-check">{label}: 150 MDL</p>'


def render_page(page: str, lang: str = "ru"):
    lang = cafe_language_service.normalize_language(lang)
    ui = get_ui_for_lang(lang)
    # Чтение из profile service (сохранение после рестарта)
    if cafe_profile_service is not None:
        try:
            prof = cafe_profile_service.get_profile_for_lang(lang)
            city = prof.get("city") or CAFE_IDENTITY.get(f"city_{lang}", CAFE_IDENTITY.get(f"city_{DEFAULT_LANGUAGE}", ""))
            name = prof.get("name") or CAFE_IDENTITY.get("name", "Cafe Name")
        except Exception:
            city = CAFE_IDENTITY.get(f"city_{lang}", CAFE_IDENTITY.get(f"city_{DEFAULT_LANGUAGE}", ""))
            name = CAFE_IDENTITY.get("name", "Cafe Name")
    else:
        city = CAFE_IDENTITY.get(f"city_{lang}", CAFE_IDENTITY.get(f"city_{DEFAULT_LANGUAGE}", ""))
        name = CAFE_IDENTITY.get("name", "Cafe Name")
    contact_ctx = _make_contact_for_lang(lang)
    seo = get_seo_for_page(page, lang)
    if page == "index":
        tagline = CAFE_IDENTITY.get(
            f"tagline_{lang}", CAFE_IDENTITY.get(f"tagline_{DEFAULT_LANGUAGE}", "")
        )
        about = CAFE_IDENTITY.get(
            f"about_{lang}", CAFE_IDENTITY.get(f"about_{DEFAULT_LANGUAGE}", "")
        )
        marker = (
            "<!-- MISSING TRANSLATION: tagline_ro -->"
            if lang == "ro" and not CAFE_IDENTITY.get("tagline_ro")
            else ""
        )
        body = f"{marker}<h1>{name}</h1><p>{tagline}</p><p>{about}</p>{_avg_check_html(lang)}"
        body += '<div class="interior-preview"><img src="/assets/interior/interior_01.png" alt="Interior" loading="lazy" width="1000" height="700"></div><ul>'
        for it in MENU[:3]:
            if it.slug == "avg_check":
                continue
            n = getattr(it, f"name_{lang}", None) or getattr(
                it, f"name_{DEFAULT_LANGUAGE}", ""
            )
            if lang == "ro" and not getattr(it, f"name_{lang}", None):
                n = f"{n} <!-- MISSING RO -->"
            body += f"<li>{n} — {it.price_mdl} MDL</li>"
        body += "</ul>"
    elif page == "menu":
        by_cat = get_menu_by_category(lang)
        parts = [f"<h1>{ui['menu']}</h1>"]
        for cat, items in by_cat.items():
            if cat == "meta":
                continue
            # Отображение категории на языке посетителя, ID сохраняется для логики
            cat_display = cat
            if items:
                first = items[0]
                if hasattr(first, "category_name"):
                    try:
                        cat_display = first.category_name(lang)
                    except Exception:
                        cat_display = cat
                else:
                    cat_display = getattr(first, f"category_{lang}", None) or cat
            parts.append(f"<h2>{cat_display}</h2><ul>")
            for it in items:
                n = getattr(it, f"name_{lang}", None) or getattr(
                    it, f"name_{DEFAULT_LANGUAGE}", ""
                )
                d = getattr(it, f"description_{lang}", None) or getattr(
                    it, f"description_{DEFAULT_LANGUAGE}", ""
                )
                if lang == "ro" and not getattr(it, f"name_{lang}", None):
                    n = f"{n} <!-- MISSING RO -->"
                img = (
                    f'<img src="/assets/{it.image}" alt="{n}" loading="lazy">'
                    if it.image
                    else ""
                )
                parts.append(
                    f"<li>{img}<strong>{n}</strong> — {it.price_mdl} MDL<br><small>{d}</small></li>"
                )
            parts.append("</ul>")
        parts.append(_avg_check_html(lang))
        body = "\n".join(parts)
    else:
        about = CAFE_IDENTITY.get(
            f"about_{lang}", CAFE_IDENTITY.get(f"about_{DEFAULT_LANGUAGE}", "")
        )
        marker = (
            "<!-- MISSING TRANSLATION: about_ro -->"
            if lang == "ro" and not CAFE_IDENTITY.get("about_ro")
            else ""
        )
        body = f"{marker}<h1>{ui['about']} — {name}</h1><p>{about}</p>"
        body += f'<div class="about-interior"><img src="/assets/interior/interior_01.png" alt="Interior - {name} {city}" loading="lazy" width="1000" height="700"></div>'
        body += _avg_check_html(lang)

    base_html = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    home_url = f"/{lang}/"
    menu_url = f"/{lang}/menu.html"
    about_url = f"/{lang}/about.html"
    lang_switch = {}
    for l in sorted(SUPPORTED_LANGUAGES):
        lang_switch[l] = f"/{l}/" if page == "index" else f"/{l}/{page}.html"
    if CAFE_BASE_URL:
        base = CAFE_BASE_URL.rstrip("/")
        canonical = (
            f'<link rel="canonical" href="{base}/{lang}/">'
            if page == "index"
            else f'<link rel="canonical" href="{base}/{lang}/{page}.html">'
        )
        comp = get_complete_languages()
        tags = []
        for cl in comp:
            href = f"{base}/{cl}/" if page == "index" else f"{base}/{cl}/{page}.html"
            tags.append(f'<link rel="alternate" hreflang="{cl}" href="{href}">')
        tags.append(
            f'<link rel="alternate" hreflang="x-default" href="{base}/{DEFAULT_LANGUAGE}/">'
        )
        hreflang = "\n".join(tags)
    else:
        canonical = (
            "<!-- canonical NOT READY FOR PRODUCTION — CAFE_BASE_URL not set -->"
        )
        hreflang = (
            "<!-- hreflang NOT READY — incomplete translations or base_url missing -->"
        )
    out = (
        base_html.replace("{{ lang }}", lang)
        .replace("{{ title }}", seo["title"])
        .replace("{{ description }}", seo["description"])
        .replace("{{ body | safe }}", body)
    )
    out = (
        out.replace("{{ home_url }}", home_url)
        .replace("{{ menu_url }}", menu_url)
        .replace("{{ about_url }}", about_url)
    )
    out = out.replace("{{ cafe_name }}", name).replace("{{ cafe_city }}", city)
    out = (
        out.replace("{{ nav.home }}", ui["home"])
        .replace("{{ nav.menu }}", ui["menu"])
        .replace("{{ nav.about }}", ui["about"])
    )
    out = (
        out.replace("{{ lang_switch.ru }}", lang_switch.get("ru", "/ru/"))
        .replace("{{ lang_switch.en }}", lang_switch.get("en", "/en/"))
        .replace("{{ lang_switch.ro }}", lang_switch.get("ro", "/ro/"))
    )
    out = out.replace("{{ canonical_url }}", canonical).replace(
        "{{ hreflang_tags }}", hreflang
    )
    if contact_ctx:
        out = (
            out.replace("{{ contact.address }}", contact_ctx.get("address") or "")
            .replace("{{ contact.hours }}", contact_ctx.get("hours") or "")
            .replace("{{ contact.phone }}", contact_ctx.get("phone") or "")
            .replace("{{ contact.map_url }}", contact_ctx.get("map_url") or "")
            .replace("{{ contact.map_label }}", contact_ctx.get("map_label") or "Map")
        )
    out = re.sub(r"{%.*?%}", "", out, flags=re.DOTALL)
    out = re.sub(r"{{\s*contact\..*?}}", "", out)
    out = out.replace(
        "Contacts to be added — see CAFE_CONTACT in content/cafe_info.py", ""
    ).replace("Contacts to be added", "")
    return {
        "html": out,
        "title": seo["title"],
        "description": seo["description"],
        "lang": lang,
        "is_complete": is_lang_content_complete(lang),
    }


def create_product_app():
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, RedirectResponse
    except ImportError:
        return None
    app = FastAPI()

    @app.get("/", response_class=HTMLResponse)
    def root():
        return RedirectResponse(url=f"/{DEFAULT_LANGUAGE}/", status_code=302)

    @app.get("/ru/", response_class=HTMLResponse)
    @app.get("/ru", response_class=HTMLResponse)
    def index_ru():
        return render_page("index", "ru")["html"]

    @app.get("/ro/", response_class=HTMLResponse)
    @app.get("/ro", response_class=HTMLResponse)
    def index_ro():
        return render_page("index", "ro")["html"]

    @app.get("/en/", response_class=HTMLResponse)
    @app.get("/en", response_class=HTMLResponse)
    def index_en():
        return render_page("index", "en")["html"]

    @app.get("/ru/menu.html", response_class=HTMLResponse)
    def menu_ru():
        return render_page("menu", "ru")["html"]

    @app.get("/ro/menu.html", response_class=HTMLResponse)
    def menu_ro():
        return render_page("menu", "ro")["html"]

    @app.get("/en/menu.html", response_class=HTMLResponse)
    def menu_en():
        return render_page("menu", "en")["html"]

    @app.get("/ru/about.html", response_class=HTMLResponse)
    def about_ru():
        return render_page("about", "ru")["html"]

    @app.get("/ro/about.html", response_class=HTMLResponse)
    def about_ro():
        return render_page("about", "ro")["html"]

    @app.get("/en/about.html", response_class=HTMLResponse)
    def about_en():
        return render_page("about", "en")["html"]

    @app.get("/menu", response_class=HTMLResponse)
    @app.get("/menu.html", response_class=HTMLResponse)
    def menu_legacy():
        return render_page("menu", "ru")["html"]

    @app.get("/about", response_class=HTMLResponse)
    @app.get("/about.html", response_class=HTMLResponse)
    def about_legacy():
        return render_page("about", "ru")["html"]

    return app
