from __future__ import annotations
from typing import List
import pathlib

from .blog_service import BlogCmsService
from ..domain.models import Post
from .blog_renderer import BlogRenderer

# Framework primitives re-exported for backward compat
from ai_framework.rendering import GeneratedPage, StaticSiteWriter


class SiteGenerator:
    """G1/G2/G12: Domain -> Generator -> Renderer (Jinja) -> Output — now using framework primitives via BlogRenderer"""

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
        return self._writer.write(pages, out_dir, clean=clean)


# Backward compat: allow old import path
from .blog_renderer import Renderer

__all__ = ["SiteGenerator", "GeneratedPage", "Renderer"]
