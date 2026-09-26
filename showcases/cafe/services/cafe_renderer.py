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

    def _make_seo(
        self,
        seo_title: str,
        seo_description: str = "",
        canonical_url: str = "",
        title_fallback: str = "",
    ) -> SeoContext:
        # SeoContext signature: seo_title (required), seo_description, og_title, og_description, canonical_url, title
        return SeoContext(
            seo_title=seo_title,
            seo_description=seo_description,
            og_title=seo_title,
            og_description=seo_description,
            canonical_url=canonical_url,
            title=title_fallback or seo_title,
        )

    def _seo_context_for_item(self, item, page_url: str) -> SeoContext:
        seo_title = (
            item.seo.seo_title if item.seo and item.seo.seo_title else item.title
        )
        seo_desc = (
            item.seo.seo_description
            if item.seo and item.seo.seo_description
            else item.description[:160]
        )
        canonical = (
            item.seo.canonical_url if item.seo and item.seo.canonical_url else page_url
        )
        return self._make_seo(seo_title, seo_desc, canonical, item.title)

    def render_item(self, item, category_slug: str):
        page_url = f"/menu/{category_slug}/{item.slug}/"
        seo_ctx = self._seo_context_for_item(item, page_url)
        html = self.renderer.render(
            "item.html",
            {
                "item": item,
                "category_slug": category_slug,
                "page_url": page_url,
                "price": str(item.price),
                "is_available": item.is_available,
            },
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html, seo_ctx

    def render_category(self, category, items: List) -> str:
        page_url = f"/menu/{category.slug}/"
        seo_ctx = self._make_seo(
            f"{category.name} — Menu",
            f"Menu category {category.name}",
            page_url,
            category.name,
        )
        html = self.renderer.render(
            "category.html",
            {
                "category": category,
                "items": items,
                "page_url": page_url,
            },
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html

    def render_menu_index(self, categories) -> str:
        page_url = "/menu/"
        seo_ctx = self._make_seo("Menu — Cafe", "Full cafe menu", page_url, "Menu")
        html = self.renderer.render(
            "menu_index.html",
            {
                "categories": categories,
                "page_url": page_url,
            },
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html

    def render_index(self, categories) -> str:
        page_url = "/"
        seo_ctx = self._make_seo("Cafe — Home", "Cafe home with menu", page_url, "Cafe")
        html = self.renderer.render(
            "index.html",
            {
                "categories": categories,
                "page_url": page_url,
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
