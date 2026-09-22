from __future__ import annotations
from typing import List
import pathlib

from .blog_service import BlogCmsService
from .blog_renderer import BlogRenderer

# Re-export for backward compatibility with app_factory.py
# Old code did: from .services.site_generator import SiteGenerator, Renderer, GeneratedPage
from ai_framework.rendering import GeneratedPage, StaticSiteWriter

# Compatibility aliases — app_factory imports Renderer from site_generator
Renderer = BlogRenderer

__all__ = ["BlogRenderer", "Renderer", "SiteGenerator", "GeneratedPage"]


class SiteGenerator:
    """G1/G2/G12: Domain -> Generator -> Renderer (framework) -> Output via StaticSiteWriter (one FS boundary)"""

    def __init__(self, service: BlogCmsService, renderer: BlogRenderer):
        self.service = service
        self.renderer = renderer
        self._writer = StaticSiteWriter()

    def generate(self) -> List[GeneratedPage]:
        pages: List[GeneratedPage] = []
        published = self.service.list_published()
        pages.append(
            GeneratedPage("index.html", self.renderer.render_index(published), "index")
        )
        for p in published:
            cat = self.service._categories.get(p.category_id)
            auth = self.service._authors.get(p.author_id)
            cat_name = cat.name if cat else ""
            cat_slug = cat.slug if cat else ""
            html = self.renderer.render_post(p, cat_name, auth.name if auth else "")
            if cat_slug and cat_name:
                html = html.replace(
                    f"/categories/{cat_name.lower().replace(' ', '-')}/",
                    f"/categories/{cat_slug}/",
                )
            pages.append(GeneratedPage(f"posts/{p.slug}/index.html", html, "post"))
            p.html_content = html
        for cat in self.service.list_categories():
            posts = self.service.list_published(category_slug=cat.slug)
            pages.append(
                GeneratedPage(
                    f"categories/{cat.slug}/index.html",
                    self.renderer.render_category(cat.slug, posts),
                    "category",
                )
            )
        for tag in self.service.list_tags():
            posts = self.service.list_published(tag_slug=tag.slug)
            pages.append(
                GeneratedPage(
                    f"tags/{tag.slug}/index.html",
                    self.renderer.render_tag(tag.slug, posts),
                    "tag",
                )
            )
        pages.append(
            GeneratedPage("rss.xml", self.renderer.render_rss(published), "rss")
        )
        pages.append(
            GeneratedPage(
                "sitemap.xml", self.renderer.render_sitemap(published), "sitemap"
            )
        )
        return pages

    def write(
        self, pages: List[GeneratedPage], out_dir: pathlib.Path, clean: bool = True
    ) -> List[pathlib.Path]:
        # Security: single filesystem boundary — all writes via StaticSiteWriter
        return self._writer.write(pages, out_dir, clean=clean)
