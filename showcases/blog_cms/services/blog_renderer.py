from __future__ import annotations
import pathlib
from typing import List
from ..domain.models import Post

# Framework primitives
from ai_framework.rendering import (
    GeneratedPage,
    SeoContext,
    SeoInjector,
    JinjaTemplateRenderer,
)


class BlogRenderer:
    """
    Showcase owner of blog semantics:
    - Post -> SeoContext mapping
    - Post -> template context (category_name, author_name, etc.)
    - posts/<slug>/, categories/<slug>/, tags/<slug>/ URL conventions
    - RSS, Sitemap, _ensure_post_links
    Uses framework primitives for generic rendering.
    """

    def __init__(self, templates_dir: pathlib.Path | None = None):
        if templates_dir is None:
            here = pathlib.Path(__file__).resolve()
            candidate = here.parent.parent / "templates"
            templates_dir = (
                candidate
                if candidate.exists()
                else pathlib.Path("showcases/blog_cms/templates")
            )
        self.templates_dir = pathlib.Path(templates_dir)
        self.template_renderer = JinjaTemplateRenderer(self.templates_dir)
        self.seo_injector = SeoInjector()
        # Backward compat for old code that checks _jinja
        self._jinja = self.template_renderer._available
        self._env = (
            self.template_renderer._env
            if hasattr(self.template_renderer, "_env")
            else None
        )

    def _seo_context(self, post_or_dict, title_fallback: str = "Blog") -> dict:
        # Keep old dict return for backward compat with existing tests that expect dict
        # But internally use SeoContext.normalize
        if hasattr(post_or_dict, "to_dict"):
            d = post_or_dict.to_dict()
        elif isinstance(post_or_dict, dict):
            d = post_or_dict
        else:
            d = {}
        seo = SeoContext.normalize(d, title_fallback=title_fallback)
        return {
            "title": seo.title,
            "seo_title": seo.seo_title,
            "seo_description": seo.seo_description,
            "og_title": seo.og_title,
            "og_description": seo.og_description,
            "canonical_url": seo.canonical_url,
        }

    def _seo_context_obj(
        self, post_or_dict, title_fallback: str = "Blog"
    ) -> SeoContext:
        if hasattr(post_or_dict, "to_dict"):
            d = post_or_dict.to_dict()
        elif isinstance(post_or_dict, dict):
            d = post_or_dict
        else:
            d = {}
        return SeoContext.normalize(d, title_fallback=title_fallback)

    def _inject_seo(self, html: str, seo_ctx: dict | SeoContext) -> str:
        if isinstance(seo_ctx, dict):
            seo = SeoContext(
                seo_title=seo_ctx.get("seo_title", ""),
                seo_description=seo_ctx.get("seo_description", ""),
                og_title=seo_ctx.get("og_title", ""),
                og_description=seo_ctx.get("og_description", ""),
                canonical_url=seo_ctx.get("canonical_url", ""),
                title=seo_ctx.get("title", ""),
            )
        else:
            seo = seo_ctx
        return self.seo_injector.ensure_seo(html, seo)

    def _ensure_post_links(self, html: str, posts: List[Post]) -> str:
        missing = [p for p in posts if f"/posts/{p.slug}/" not in html]
        if missing and posts:
            fallback = "".join(
                [f'<li><a href="/posts/{p.slug}/">{p.title}</a></li>' for p in posts]
            )
            if "</ul>" in html:
                html = html.replace("</ul>", f"{fallback}</ul>", 1)
            else:
                html += f"<ul>{fallback}</ul>"
        return html

    def render_post(self, post: Post, category_name: str, author_name: str) -> str:
        seo_obj = self._seo_context_obj(post, post.title)
        seo_dict = self._seo_context(post, post.title)
        try:
            cat_slug = category_name.lower().replace(" ", "-") if category_name else ""
            html = self.template_renderer.render(
                "post.html",
                {
                    "post": post,
                    "category_name": category_name,
                    "category_slug": cat_slug,
                    "author_name": author_name,
                    **seo_dict,
                },
            )
            return self._inject_seo(html, seo_obj)
        except Exception:
            # fallback — guaranteed SEO, behavior-preserving
            return f"""<!doctype html><html><head><title>{seo_obj.seo_title}</title>
<meta name="description" content="{seo_obj.seo_description}">
<meta property="og:title" content="{seo_obj.og_title}">
<meta property="og:description" content="{seo_obj.og_description}">
<link rel="canonical" href="{seo_obj.canonical_url}">
</head><body><h1>{post.title}</h1><p>{category_name} / {author_name}</p><article>{post.content}</article></body></html>"""

    def render_index(self, posts: List[Post]) -> str:
        seo_dict = {
            "title": "Blog",
            "seo_title": "Blog",
            "seo_description": f"{len(posts)} posts",
            "og_title": "Blog",
            "og_description": "",
            "canonical_url": "/",
        }
        seo_obj = SeoContext.normalize(
            {
                "title": "Blog",
                "seo_title": "Blog",
                "seo_description": f"{len(posts)} posts",
            },
            title_fallback="Blog",
        )
        try:
            html = self.template_renderer.render(
                "index.html", {"posts": posts, **seo_dict}
            )
            return self._ensure_post_links(html, posts)
        except Exception:
            items = "".join(
                [f'<li><a href="/posts/{p.slug}/">{p.title}</a></li>' for p in posts]
            )
            return f"<!doctype html><title>Blog</title><h1>Blog</h1><ul>{items}</ul>"

    def render_category(self, slug: str, posts: List[Post]) -> str:
        seo_dict = {
            "title": f"Category {slug}",
            "seo_title": f"Category {slug}",
            "seo_description": "",
            "og_title": f"Category {slug}",
            "og_description": "",
            "canonical_url": f"/categories/{slug}/",
        }
        try:
            html = self.template_renderer.render(
                "category.html", {"slug": slug, "posts": posts, **seo_dict}
            )
            return self._ensure_post_links(html, posts)
        except Exception:
            items = "".join(
                [f'<li><a href="/posts/{p.slug}/">{p.title}</a></li>' for p in posts]
            )
            return f"<!doctype html><title>Category {slug}</title><h1>Category: {slug}</h1><ul>{items}</ul>"

    def render_tag(self, slug: str, posts: List[Post]) -> str:
        seo_dict = {
            "title": f"Tag {slug}",
            "seo_title": f"Tag {slug}",
            "seo_description": "",
            "og_title": f"Tag {slug}",
            "og_description": "",
            "canonical_url": f"/tags/{slug}/",
        }
        try:
            html = self.template_renderer.render(
                "tag.html", {"slug": slug, "posts": posts, **seo_dict}
            )
            return self._ensure_post_links(html, posts)
        except Exception:
            items = "".join(
                [f'<li><a href="/posts/{p.slug}/">{p.title}</a></li>' for p in posts]
            )
            return f"<!doctype html><title>Tag {slug}</title><h1>Tag: {slug}</h1><ul>{items}</ul>"

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


# Backward compat alias: old code imported Renderer from site_generator
Renderer = BlogRenderer
