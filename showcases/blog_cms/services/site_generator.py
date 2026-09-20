from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import pathlib
from .blog_service import BlogCmsService
from ..domain.models import Post


@dataclass
class GeneratedPage:
    path: str  # relative: e.g., "index.html", "posts/hello-world/index.html"
    html: str
    kind: str  # index | post | category | tag | rss | sitemap


class Renderer:
    """Jinja renderer — pure, no IO, testable. Phase 6.1: replaces inline _base()"""

    def __init__(self, templates_dir: pathlib.Path | None = None):
        # resolve templates dir: explicit or showcases/blog_cms/templates
        if templates_dir is None:
            # try relative to this file
            here = pathlib.Path(__file__).resolve()
            # showcases/blog_cms/services/ -> ../templates
            candidate = here.parent.parent / "templates"
            if candidate.exists():
                templates_dir = candidate
            else:
                # fallback to cwd showcases/blog_cms/templates
                templates_dir = pathlib.Path("showcases/blog_cms/templates")
        self.templates_dir = pathlib.Path(templates_dir)

        # Jinja env with fallback to inline if jinja2 not available
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape

            self._env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=select_autoescape(["html", "xml"]),
                auto_reload=False,
            )
            self._jinja = True
        except Exception:
            self._env = None
            self._jinja = False

    def _seo_context(self, post_or_dict, title_fallback: str = "Blog") -> dict:
        # Accept Post or dict
        if hasattr(post_or_dict, "to_dict"):
            d = post_or_dict.to_dict()
        elif isinstance(post_or_dict, dict):
            d = post_or_dict
        else:
            d = {}
        # normalize SEO fields: prefer seo_title etc, fallback to title
        return {
            "title": d.get("title") or title_fallback,
            "seo_title": d.get("seo_title") or d.get("title") or title_fallback,
            "seo_description": d.get("seo_description") or "",
            "og_title": d.get("og_title")
            or d.get("seo_title")
            or d.get("title")
            or title_fallback,
            "og_description": d.get("og_description") or d.get("seo_description") or "",
            "canonical_url": d.get("canonical_url") or "",
        }

    def _inject_seo(self, html: str, seo_ctx: dict) -> str:
        # Ensure SEO tags are present even if template is minimal/broken
        # If <title> missing, inject
        if "<title>" not in html:
            inject = f"<title>{seo_ctx.get('seo_title', '')}</title>\n"
            if seo_ctx.get("seo_description"):
                inject += f'<meta name="description" content="{seo_ctx["seo_description"]}">\n'
            if seo_ctx.get("og_title"):
                inject += (
                    f'<meta property="og:title" content="{seo_ctx["og_title"]}">\n'
                )
            if seo_ctx.get("og_description"):
                inject += f'<meta property="og:description" content="{seo_ctx["og_description"]}">\n'
            if seo_ctx.get("canonical_url"):
                inject += f'<link rel="canonical" href="{seo_ctx["canonical_url"]}">\n'
            # prepend to html if no head, or insert after <head>
            if "<head>" in html:
                html = html.replace("<head>", f"<head>\n{inject}", 1)
            else:
                html = inject + html
        else:
            # ensure other meta tags exist
            if seo_ctx.get("seo_description") and 'name="description"' not in html:
                html = html.replace(
                    "</title>",
                    f'</title>\n<meta name="description" content="{seo_ctx["seo_description"]}">',
                    1,
                )
            if seo_ctx.get("og_title") and "og:title" not in html:
                html = html.replace(
                    "</title>",
                    f'</title>\n<meta property="og:title" content="{seo_ctx["og_title"]}">',
                    1,
                )
            if seo_ctx.get("og_description") and "og:description" not in html:
                html = html.replace(
                    "</title>",
                    f'</title>\n<meta property="og:description" content="{seo_ctx["og_description"]}">',
                    1,
                )
            if seo_ctx.get("canonical_url") and 'rel="canonical"' not in html:
                html = html.replace(
                    "</title>",
                    f'</title>\n<link rel="canonical" href="{seo_ctx["canonical_url"]}">',
                    1,
                )
        return html

    def render_post(self, post: Post, category_name: str, author_name: str) -> str:
        seo_ctx = self._seo_context(post, post.title)
        if self._jinja:
            try:
                tmpl = self._env.get_template("post.html")
                cat_slug = (
                    category_name.lower().replace(" ", "-") if category_name else ""
                )
                html = tmpl.render(
                    post=post,
                    category_name=category_name,
                    category_slug=cat_slug,
                    author_name=author_name,
                    **seo_ctx,
                )
                return self._inject_seo(html, seo_ctx)
            except Exception:
                pass
        # fallback inline — guaranteed SEO
        return f"""<!doctype html><html><head><title>{seo_ctx["seo_title"]}</title>
<meta name="description" content="{seo_ctx["seo_description"]}">
<meta property="og:title" content="{seo_ctx["og_title"]}">
<meta property="og:description" content="{seo_ctx["og_description"]}">
<link rel="canonical" href="{seo_ctx["canonical_url"]}">
</head><body><h1>{post.title}</h1><p>{category_name} / {author_name}</p><article>{post.content}</article></body></html>"""

    def _ensure_post_links(self, html: str, posts: List[Post]) -> str:
        # Guarantee that index/category/tag pages contain href="/posts/{slug}/"
        # If missing, append fallback list
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

    def render_index(self, posts: List[Post]) -> str:
        seo_ctx = {
            "title": "Blog",
            "seo_title": "Blog",
            "seo_description": f"{len(posts)} posts",
            "og_title": "Blog",
            "og_description": "",
            "canonical_url": "/",
        }
        if self._jinja:
            try:
                tmpl = self._env.get_template("index.html")
                html = tmpl.render(posts=posts, **seo_ctx)
                return self._ensure_post_links(html, posts)
            except Exception:
                pass
        items = "".join(
            [f'<li><a href="/posts/{p.slug}/">{p.title}</a></li>' for p in posts]
        )
        return f"<!doctype html><title>Blog</title><h1>Blog</h1><ul>{items}</ul>"

    def render_category(self, slug: str, posts: List[Post]) -> str:
        seo_ctx = {
            "title": f"Category {slug}",
            "seo_title": f"Category {slug}",
            "seo_description": "",
            "og_title": f"Category {slug}",
            "og_description": "",
            "canonical_url": f"/categories/{slug}/",
        }
        if self._jinja:
            try:
                tmpl = self._env.get_template("category.html")
                html = tmpl.render(slug=slug, posts=posts, **seo_ctx)
                return self._ensure_post_links(html, posts)
            except Exception:
                pass
        items = "".join(
            [f'<li><a href="/posts/{p.slug}/">{p.title}</a></li>' for p in posts]
        )
        return f"<!doctype html><title>Category {slug}</title><h1>Category: {slug}</h1><ul>{items}</ul>"

    def render_tag(self, slug: str, posts: List[Post]) -> str:
        seo_ctx = {
            "title": f"Tag {slug}",
            "seo_title": f"Tag {slug}",
            "seo_description": "",
            "og_title": f"Tag {slug}",
            "og_description": "",
            "canonical_url": f"/tags/{slug}/",
        }
        if self._jinja:
            try:
                tmpl = self._env.get_template("tag.html")
                html = tmpl.render(slug=slug, posts=posts, **seo_ctx)
                return self._ensure_post_links(html, posts)
            except Exception:
                pass
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


class SiteGenerator:
    """G1/G2/G12: Domain -> Generator -> Renderer (Jinja) -> Output"""

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
            # Resolve real category slug for correct interlink
            cat_name = cat.name if cat else ""
            cat_slug = cat.slug if cat else ""
            html = self.renderer.render_post(p, cat_name, auth.name if auth else "")
            # Patch category slug in html if renderer used fallback lower name
            if cat_slug and cat_name:
                html = html.replace(
                    f"/categories/{cat_name.lower().replace(' ', '-')}/",
                    f"/categories/{cat_slug}/",
                )
            pages.append(GeneratedPage(f"posts/{p.slug}/index.html", html, "post"))
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
