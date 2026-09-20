from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import pathlib, hashlib
from .blog_service import BlogCmsService
from ..domain.models import Post


@dataclass
class GeneratedPage:
    path: str  # relative: e.g., "index.html", "posts/hello-world/index.html"
    html: str
    kind: str  # index | post | category | tag | rss | sitemap


class Renderer:
    """Pure renderer — no IO, testable"""

    def __init__(self, templates_dir: pathlib.Path | None = None):
        self.templates_dir = templates_dir

    def _base(self, title: str, body: str, seo: dict | None = None) -> str:
        seo = seo or {}
        seo_title = seo.get("seo_title") or title
        desc = seo.get("seo_description") or ""
        og_t = seo.get("og_title") or seo_title
        og_d = seo.get("og_description") or desc
        canon = seo.get("canonical_url") or ""
        return f"""<!doctype html><html><head><meta charset="utf-8"><title>{seo_title}</title>
<meta name="description" content="{desc}"><meta property="og:title" content="{og_t}">
<meta property="og:description" content="{og_d}">
{f'<link rel="canonical" href="{canon}">' if canon else ""}
</head><body>{body}</body></html>"""

    def render_post(self, post: Post, category_name: str, author_name: str) -> str:
        body = f"<h1>{post.title}</h1><p><em>{category_name} / {author_name}</em></p><article>{post.content}</article>"
        return self._base(post.title, body, post.to_dict())

    def render_index(self, posts: List[Post]) -> str:
        items = "".join(
            [f'<li><a href="/posts/{p.slug}/">{p.title}</a></li>' for p in posts]
        )
        return self._base("Blog", f"<h1>Blog</h1><ul>{items}</ul>")

    def render_category(self, slug: str, posts: List[Post]) -> str:
        items = "".join(
            [f'<li><a href="/posts/{p.slug}/">{p.title}</a></li>' for p in posts]
        )
        return self._base(
            f"Category {slug}", f"<h1>Category: {slug}</h1><ul>{items}</ul>"
        )

    def render_tag(self, slug: str, posts: List[Post]) -> str:
        items = "".join(
            [f'<li><a href="/posts/{p.slug}/">{p.title}</a></li>' for p in posts]
        )
        return self._base(f"Tag {slug}", f"<h1>Tag: {slug}</h1><ul>{items}</ul>")

    def render_rss(self, posts: List[Post]) -> str:
        items = "".join(
            [
                f"<item><title>{p.title}</title><link>/posts/{p.slug}/</link></item>"
                for p in posts
            ]
        )
        return f'<?xml version="1.0"?><rss><channel><title>Blog</title>{items}</channel></rss>'

    def render_sitemap(self, posts: List[Post]) -> str:
        urls = "".join([f"<url><loc>/posts/{p.slug}/</loc></url>" for p in posts])
        return f'<?xml version="1.0"?><urlset>{urls}<url><loc>/</loc></url></urlset>'


class SiteGenerator:
    """G1/G2/G12: Domain -> Generator -> Renderer -> Output"""

    def __init__(self, service: BlogCmsService, renderer: Renderer):
        self.service = service
        self.renderer = renderer

    def generate(self) -> List[GeneratedPage]:
        pages: List[GeneratedPage] = []
        published = self.service.list_published()
        # G1: index
        pages.append(
            GeneratedPage("index.html", self.renderer.render_index(published), "index")
        )
        # G2: post detail
        for p in published:
            cat = self.service._categories.get(p.category_id)
            auth = self.service._authors.get(p.author_id)
            html = self.renderer.render_post(
                p, cat.name if cat else "", auth.name if auth else ""
            )
            pages.append(GeneratedPage(f"posts/{p.slug}/index.html", html, "post"))
            # enrich post.html_content for domain
            p.html_content = html
        # G12: taxonomy + rss/sitemap
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
        self, pages: List[GeneratedPage], out_dir: pathlib.Path
    ) -> List[pathlib.Path]:
        written = []
        for pg in pages:
            fp = out_dir / pg.path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(pg.html, encoding="utf-8")
            written.append(fp)
        return written
