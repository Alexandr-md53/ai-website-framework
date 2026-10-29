"""
Café Language Service v0.3 — showcase-local, adapted from Nursery language pattern
FROZEN Framework — no ai_framework changes
No Nursery import — pattern copied/adapted, terminology dish/menu

What copied/adapted from Nursery (routes/main.py + app.py + translations/ui.py + translations/__init__.py + content_generators/plant_generator.py):

- SUPPORTED_LANGUAGES = {"ru","ro","en"} — same set
- DEFAULT_LANGUAGE = "ru" — same default
- Admin language: request.args.get("lang","ru") — ?lang= query param, per-request, no persistence, redirect preserves ?lang={lang}
- Visitor language: session["lang"] = lang via /set_language/<lang> if lang in supported, default session.get("lang","ru") — persistence via session/cookie, redirect referrer or "/"
- Translation model: separate columns per language name_ru/name_ro/name_en description_ru/ro/en — not separate rows, explicit branching if lang=="en": name_en elif ro: name_ro else name_ru
- UI translations: UI dict {ru:{...}, en:{...}, ro:{...}} + get_ui(lang) returns UI.get(lang, UI["ru"]) — fallback to ru
- normalize_language: if content_lang not in SUPPORTED_LANGUAGES -> fallback (in plant_generator normalize_content_language, in app.py supported check)

What adapted:
- module = "cafe" not "nursery" — terminology dish/menu
- service methods showcase-local: normalize_language(), get_admin_lang(query_params), get_visitor_lang(cookies/session_dict), get_localized_value(item, field_base, lang), get_ui(lang)
- translations dict UI adapted for Café: keys cafe-specific {menu, admin, dish} instead of plant/chat
- supports both query param ?lang and cookie lang for visitor
- added fallback chain: requested -> default if empty -> ru
- configurable via __init__ for test isolation (supported set, default)

What NOT copied: Nursery models, routes, templates, DB, Flask Blueprint
"""

from __future__ import annotations

from typing import Dict, Optional, Any

CAFE_SUPPORTED_LANGUAGES = {"ru", "ro", "en"}
CAFE_DEFAULT_LANGUAGE = "ru"

# Café UI translations — showcase-local, adapted structure from Nursery translations/ui.py
# Nursery: UI = {ru: {chat:{...}, blog:{...}, quiz:{...}, admin:{...}, badges:{...}, plant:{...}}, en:{...}, ro:{...}}
# Café: same nested structure but domain-adapted: cafe-specific keys menu, dish, order, admin
CAFE_UI: Dict[str, Dict[str, Dict[str, str]]] = {
    "ru": {
        "menu": {
            "title": "Меню",
            "description": "Полное меню кафе",
            "back_home": "← На главную",
            "price": "Цена:",
            "available": "В наличии",
            "no_items": "Пока нет блюд.",
        },
        "dish": {
            "price": "Цена:",
            "available": "Доступно",
            "unavailable": "Нет в наличии",
            "back_to_category": "Назад к категории",
            "description": "Описание",
        },
        "admin": {
            "dashboard_title": "Админ-панель кафе",
            "dashboard_subtitle": "Управление меню и заказами.",
            "categories": "Категории",
            "items": "Блюда",
            "orders": "Заказы",
            "save": "Сохранить",
            "edit": "Редактировать",
            "delete": "Удалить",
        },
    },
    "en": {
        "menu": {
            "title": "Menu",
            "description": "Full cafe menu",
            "back_home": "← Back to Home",
            "price": "Price:",
            "available": "Available",
            "no_items": "No dishes yet.",
        },
        "dish": {
            "price": "Price:",
            "available": "Available",
            "unavailable": "Out of stock",
            "back_to_category": "Back to category",
            "description": "Description",
        },
        "admin": {
            "dashboard_title": "Cafe Admin Panel",
            "dashboard_subtitle": "Manage menu and orders.",
            "categories": "Categories",
            "items": "Dishes",
            "orders": "Orders",
            "save": "Save",
            "edit": "Edit",
            "delete": "Delete",
        },
    },
    "ro": {
        "menu": {
            "title": "Meniu",
            "description": "Meniul complet al cafenelei",
            "back_home": "← Înapoi acasă",
            "price": "Preț:",
            "available": "Disponibil",
            "no_items": "Încă nu există preparate.",
        },
        "dish": {
            "price": "Preț:",
            "available": "Disponibil",
            "unavailable": "Indisponibil",
            "back_to_category": "Înapoi la categorie",
            "description": "Descriere",
        },
        "admin": {
            "dashboard_title": "Panou Admin Cafenea",
            "dashboard_subtitle": "Gestionarea meniului și comenzilor.",
            "categories": "Categorii",
            "items": "Preparate",
            "orders": "Comenzi",
            "save": "Salvează",
            "edit": "Editează",
            "delete": "Șterge",
        },
    },
}


class CafeLanguageService:
    def __init__(
        self,
        supported_languages: set[str] | None = None,
        default_language: str | None = None,
        ui_translations: Dict[str, Dict[str, Dict[str, str]]] | None = None,
    ) -> None:
        self.supported_languages = supported_languages or CAFE_SUPPORTED_LANGUAGES
        self.default_language = default_language or CAFE_DEFAULT_LANGUAGE
        self.ui = ui_translations or CAFE_UI

    def normalize_language(self, lang: Optional[str]) -> str:
        """Normalize content language — same as Nursery normalize_content_language"""
        if not lang:
            return self.default_language
        lang = lang.lower().strip()
        if lang not in self.supported_languages:
            return self.default_language
        return lang

    def get_admin_lang(self, query_params: Dict[str, Any] | None) -> str:
        """
        Admin language: ?lang=... query param, per-request, no persistence
        Nursery: lang = request.args.get("lang","ru")
        """
        if not query_params:
            return self.default_language
        raw = query_params.get("lang")
        return self.normalize_language(raw)

    def get_visitor_lang(
        self,
        cookies: Dict[str, str] | None = None,
        session: Dict[str, str] | None = None,
        query_params: Dict[str, Any] | None = None,
    ) -> str:
        """
        Visitor language: session["lang"] persistence
        Nursery: lang = session.get("lang","ru") + /set_language/<lang> sets session["lang"]=lang
        Adapted for FastAPI: checks cookie "lang" + session dict + fallback default
        Priority: query ?lang > session > cookie > default
        """
        # query ?lang has priority if visitor explicitly passes it (some implementations)
        if query_params and query_params.get("lang"):
            candidate = self.normalize_language(query_params.get("lang"))
            if candidate in self.supported_languages:
                return candidate
        if session and session.get("lang"):
            return self.normalize_language(session.get("lang"))
        if cookies and cookies.get("lang"):
            return self.normalize_language(cookies.get("lang"))
        return self.default_language

    def set_visitor_lang(self, lang: str) -> str:
        """
        Validate and return normalized lang to be stored in session/cookie
        Nursery: @main.route("/set_language/<lang>") if lang in ["ru","en","ro"]: session["lang"]=lang
        """
        return self.normalize_language(lang)

    def get_ui(self, lang: Optional[str]) -> Dict[str, Dict[str, str]]:
        """
        UI translations with fallback to default
        Nursery: UI.get(lang, UI["ru"])
        """
        norm = self.normalize_language(lang)
        return self.ui.get(norm, self.ui[self.default_language])

    def get_localized_field(
        self,
        obj: Any,
        field_base: str,
        lang: Optional[str],
        fallback: bool = True,
    ) -> Optional[str]:
        """
        Get translated value from object with separate columns per language
        Nursery pattern: if lang=="en": plant.name_en elif ro: name_ro else name_ru
        Café adaptation: generic field_base + lang suffix lookup + fallback to default if empty

        obj can have attributes like title_ru, title_en, title_ro or dict with keys
        """
        norm = self.normalize_language(lang)
        # try direct attribute field_base_lang
        attr_name = f"{field_base}_{norm}"
        value = None
        if isinstance(obj, dict):
            value = obj.get(attr_name) or obj.get(field_base)
        else:
            value = getattr(obj, attr_name, None)
            if value is None:
                # try dict-like translations field
                translations = getattr(obj, f"{field_base}_translations", None) or getattr(obj, "translations", None)
                if isinstance(translations, dict):
                    value = translations.get(norm)

        if value and isinstance(value, str) and value.strip():
            return value

        if fallback:
            # fallback to default language
            default_attr = f"{field_base}_{self.default_language}"
            if isinstance(obj, dict):
                fb_value = obj.get(default_attr) or obj.get(field_base)
            else:
                fb_value = getattr(obj, default_attr, None)
                if fb_value is None:
                    translations = getattr(obj, f"{field_base}_translations", None) or getattr(obj, "translations", None)
                    if isinstance(translations, dict):
                        fb_value = translations.get(self.default_language)
            if fb_value and isinstance(fb_value, str) and fb_value.strip():
                return fb_value
            # final fallback to base field
            if isinstance(obj, dict):
                return obj.get(field_base)
            return getattr(obj, field_base, None)
        return value

    def get_localized_value(
        self,
        translations: Dict[str, str] | None,
        lang: Optional[str],
        fallback: bool = True,
    ) -> Optional[str]:
        """Direct dict lookup with fallback — for simple translations dict"""
        if not translations:
            return None
        norm = self.normalize_language(lang)
        val = translations.get(norm)
        if val and val.strip():
            return val
        if fallback:
            return translations.get(self.default_language)
        return None


# singleton like Nursery image_service = ImageService()
cafe_language_service = CafeLanguageService()
