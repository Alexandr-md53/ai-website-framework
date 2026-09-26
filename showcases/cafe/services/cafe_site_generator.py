"""
Cafe Site Generator v0.1 — showcase-local, deterministic, sorted, duplicate fail-fast
Uses: GeneratedPage VO (path, html, kind), StaticSiteWriter is sole FS boundary (in app_factory)
"""

from __future__ import annotations

from typing import List
from ai_framework.rendering.generated_page import GeneratedPage
from showcases.cafe.services.cafe_renderer import CafeRenderer
from showcases.cafe.services.cafe_menu_service import CafeMenuService


class CafeSiteGenerator:
    def __init__(self, service: CafeMenuService, renderer: CafeRenderer):
        self.service = service
        self.renderer = renderer

    def generate(self) -> List[GeneratedPage]:
        pages: List[GeneratedPage] = []
        seen_paths = set()

        def add_page(path: str, html: str, kind: str = "page"):
            if path in seen_paths:
                raise ValueError(f"Duplicate path: {path}")
            seen_paths.add(path)
            pages.append(GeneratedPage(path=path, html=html, kind=kind))

        categories = sorted(self.service.list_categories(), key=lambda c: c.slug)

        # index.html
        index_html = self.renderer.render_index(categories)
        add_page("index.html", index_html, kind="index")

        # menu/index.html
        menu_index_html = self.renderer.render_menu_index(categories)
        add_page("menu/index.html", menu_index_html, kind="menu_index")

        for cat in categories:
            published_items = sorted(
                self.service.list_published(category_slug=cat.slug),
                key=lambda i: i.slug,
            )
            # category page
            cat_html = self.renderer.render_category(cat, published_items)
            add_page(f"menu/{cat.slug}/index.html", cat_html, kind="category")

            for item in published_items:
                item_html, _ = self.renderer.render_item(item, cat.slug)
                add_page(
                    f"menu/{cat.slug}/{item.slug}/index.html", item_html, kind="item"
                )

        # sitemap — will be rendered after collecting pages, but we need content for sitemap
        sitemap_content = self.renderer.render_sitemap(pages)
        add_page("sitemap.xml", sitemap_content, kind="sitemap")

        # deterministic sorted by path
        pages_sorted = sorted(pages, key=lambda p: p.path)
        return pages_sorted
