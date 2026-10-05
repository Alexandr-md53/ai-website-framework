"""
Cafe Site Generator v0.1 — fixed duplicate sitemap in generate_all_languages
"""

from __future__ import annotations

from typing import List
from ai_framework.rendering.generated_page import GeneratedPage
from showcases.cafe.services.cafe_renderer import CafeRenderer
from showcases.cafe.services.cafe_menu_service import CafeMenuService


class CafeSiteGenerator:
    def __init__(self, service: CafeMenuService, renderer: CafeRenderer, language_service=None):
        self.service = service
        self.renderer = renderer
        self.language_service = language_service
        if self.language_service is None:
            try:
                from showcases.cafe.services.cafe_language_service import cafe_language_service
                self.language_service = cafe_language_service
            except Exception:
                self.language_service = None

    def generate(self, lang: str = "ru") -> List[GeneratedPage]:
        pages: List[GeneratedPage] = []
        seen_paths = set()

        def add_page(path: str, html: str, kind: str = "page"):
            if path in seen_paths:
                raise ValueError(f"Duplicate path: {path}")
            seen_paths.add(path)
            pages.append(GeneratedPage(path=path, html=html, kind=kind))

        if self.language_service:
            lang = self.language_service.normalize_language(lang)
        else:
            lang = lang or "ru"

        ui = self.language_service.get_ui(lang) if self.language_service else {}

        categories = sorted(self.service.list_categories(), key=lambda c: c.slug)

        index_html = self.renderer.render_index(categories, lang=lang, ui=ui)
        add_page("index.html", index_html, kind="index")

        menu_index_html = self.renderer.render_menu_index(categories, lang=lang, ui=ui)
        add_page("menu/index.html", menu_index_html, kind="menu_index")

        for cat in categories:
            published_items = sorted(
                self.service.list_published(category_slug=cat.slug),
                key=lambda i: i.slug,
            )
            cat_html = self.renderer.render_category(cat, published_items, lang=lang, ui=ui)
            add_page(f"menu/{cat.slug}/index.html", cat_html, kind="category")

            for item in published_items:
                item_html, _ = self.renderer.render_item(item, cat.slug, lang=lang, ui=ui)
                add_page(
                    f"menu/{cat.slug}/{item.slug}/index.html", item_html, kind="item"
                )

        sitemap_content = self.renderer.render_sitemap(pages)
        add_page("sitemap.xml", sitemap_content, kind="sitemap")

        pages_sorted = sorted(pages, key=lambda p: p.path)
        return pages_sorted

    def generate_all_languages(self) -> List[GeneratedPage]:
        """Fixed: avoid duplicate sitemap.xml — filter sitemap from ru base before final aggregation"""
        all_pages: List[GeneratedPage] = []
        langs = ["ru", "en", "ro"]
        if self.language_service:
            langs = list(self.language_service.supported_languages)
        for lang in langs:
            pages = self.generate(lang=lang)
            if lang == "ru":
                # FIX: do NOT include ru sitemap.xml here, it will be regenerated as final aggregated sitemap
                for p in pages:
                    if p.path == "sitemap.xml":
                        continue
                    all_pages.append(p)
            else:
                for p in pages:
                    if p.path == "sitemap.xml":
                        continue
                    new_path = f"{lang}/{p.path}"
                    all_pages.append(GeneratedPage(path=new_path, html=p.html, kind=f"{p.kind}_{lang}"))
        sitemap_content = self.renderer.render_sitemap(all_pages)
        all_pages.append(GeneratedPage(path="sitemap.xml", html=sitemap_content, kind="sitemap"))
        return sorted(all_pages, key=lambda p: p.path)
