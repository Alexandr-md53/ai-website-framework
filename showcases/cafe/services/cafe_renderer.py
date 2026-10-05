"""
Cafe Renderer v0.1 — minimal templates per screenshot sample
Uses correct framework VO signatures:
- GeneratedPage(path, html, kind)
- SeoContext(seo_title, seo_description, og_title, og_description, canonical_url, title)
"""

from __future__ import annotations
from pathlib import Path
from typing import List

from ai_framework.rendering.jinja import JinjaTemplateRenderer
from ai_framework.rendering.generated_page import GeneratedPage
from ai_framework.rendering.seo import SeoContext, SeoInjector
from typing import Optional


class CafeRenderer:
    def __init__(self, templates_dir: Path | None = None):
        if templates_dir is None:
            candidates = [
                Path(__file__).parent.parent / "templates",
                Path(__file__).parent / "templates",
                Path("showcases/cafe/templates"),
            ]
            for c in candidates:
                if c.exists():
                    templates_dir = c
                    break
            if templates_dir is None:
                templates_dir = candidates[0]
        self.templates_dir = Path(templates_dir)
        self.renderer = JinjaTemplateRenderer(str(self.templates_dir))
        self.seo_injector = SeoInjector()

    def _make_seo(self, seo_title: str, seo_description: str = "", canonical_url: str = "", title_fallback: str = "") -> SeoContext:
        # SeoContext signature: seo_title (required), seo_description, og_title, og_description, canonical_url, title
        return SeoContext(
            seo_title=seo_title,
            seo_description=seo_description,
            og_title=seo_title,
            og_description=seo_description,
            canonical_url=canonical_url,
            title=title_fallback or seo_title,
        )

    def _seo_context_for_item(self, item, page_url: str, lang: str = "ru") -> SeoContext:
        # v0.3 language-aware SEO — uses localized title/description if available
        loc_title = getattr(item, "get_localized_title", lambda l: item.title)(lang) if hasattr(item, "get_localized_title") else item.title
        loc_desc = getattr(item, "get_localized_description", lambda l: item.description)(lang) if hasattr(item, "get_localized_description") else item.description
        seo_title = item.seo.seo_title if item.seo and item.seo.seo_title else loc_title
        seo_desc = item.seo.seo_description if item.seo and item.seo.seo_description else loc_desc[:160]
        canonical = item.seo.canonical_url if item.seo and item.seo.canonical_url else page_url
        return self._make_seo(seo_title, seo_desc, canonical, loc_title)

    def _get_image_url(self, item, version: str = "detail") -> Optional[str]:
        filename = getattr(item, "image_filename", None)
        if not filename:
            return None
        return f"/static/uploads/menu/{version}/{filename}"

    def _get_localized_category_name(self, category, lang: str = "ru") -> str:
        # Nursery pattern: if lang=="en": name_en elif ro: name_ro else name_ru
        if lang == "en" and getattr(category, "name_en", None):
            return category.name_en
        if lang == "ro" and getattr(category, "name_ro", None):
            return category.name_ro
        return getattr(category, "name_ru", None) or category.name

    def render_item(self, item, category_slug: str, lang: str = "ru", ui: dict | None = None):
        page_url = f"/menu/{category_slug}/{item.slug}/"
        if lang != "ru":
            page_url = f"/menu/{category_slug}/{item.slug}/?lang={lang}"
        seo_ctx = self._seo_context_for_item(item, page_url, lang)
        image_url = self._get_image_url(item, "detail")
        image_url_catalog = self._get_image_url(item, "catalog")
        loc_title = item.get_localized_title(lang) if hasattr(item, "get_localized_title") else item.title
        loc_desc = item.get_localized_description(lang) if hasattr(item, "get_localized_description") else item.description
        html = self.renderer.render(
            "item.html",
            {
                "item": item,
                "category_slug": category_slug,
                "page_url": page_url,
                "price": str(item.price),
                "is_available": item.is_available,
                "image_url": image_url,
                "image_url_catalog": image_url_catalog,
                "lang": lang,
                "ui": ui or {},
                "localized_title": loc_title,
                "localized_description": loc_desc,
            },
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html, seo_ctx

    def render_category(self, category, items: List, lang: str = "ru", ui: dict | None = None) -> str:
        page_url = f"/menu/{category.slug}/"
        if lang != "ru":
            page_url = f"/menu/{category.slug}/?lang={lang}"
        loc_name = self._get_localized_category_name(category, lang)
        seo_ctx = self._make_seo(f"{loc_name} — Menu", f"Menu category {loc_name}", page_url, loc_name)
        items_with_images = []
        for it in items:
            items_with_images.append({
                "item": it,
                "image_url": self._get_image_url(it, "catalog"),
                "localized_title": it.get_localized_title(lang) if hasattr(it, "get_localized_title") else it.title,
            })
        html = self.renderer.render(
            "category.html",
            {
                "category": category,
                "items": items,
                "items_with_images": items_with_images,
                "page_url": page_url,
                "lang": lang,
                "ui": ui or {},
                "localized_name": loc_name,
            },
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html

    def render_menu_index(self, categories, lang: str = "ru", ui: dict | None = None) -> str:
        page_url = "/menu/"
        if lang != "ru":
            page_url = f"/menu/?lang={lang}"
        seo_ctx = self._make_seo("Menu — Cafe", "Full cafe menu", page_url, "Menu")
        # localize categories
        localized_cats = []
        for c in categories:
            localized_cats.append({
                "category": c,
                "localized_name": self._get_localized_category_name(c, lang),
            })
        html = self.renderer.render(
            "menu_index.html",
            {
                "categories": categories,
                "localized_categories": localized_cats,
                "page_url": page_url,
                "lang": lang,
                "ui": ui or {},
            },
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html

    def render_index(self, categories, lang: str = "ru", ui: dict | None = None) -> str:
        page_url = "/"
        if lang != "ru":
            page_url = f"/?lang={lang}"
        seo_ctx = self._make_seo("Cafe — Home", "Cafe home with menu", page_url, "Cafe")
        localized_cats = []
        for c in categories:
            localized_cats.append({
                "category": c,
                "localized_name": self._get_localized_category_name(c, lang),
            })
        html = self.renderer.render(
            "index.html",
            {
                "categories": categories,
                "localized_categories": localized_cats,
                "page_url": page_url,
                "lang": lang,
                "ui": ui or {},
            },
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html

    def render_sitemap(self, pages: List[GeneratedPage]) -> str:
        urls = [p.path for p in pages if not p.path.endswith("sitemap.xml")]
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for u in sorted(urls):
            loc = f"/{u}" if not u.startswith("/") else u
            if loc.endswith("index.html"):
                loc = loc[:-10] or "/"
            xml += f"  <url><loc>{loc}</loc></url>\n"
        xml += "</urlset>"
        return xml
