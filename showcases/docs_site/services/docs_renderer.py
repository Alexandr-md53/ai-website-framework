from __future__ import annotations
import pathlib
from typing import List
from ..domain.models import DocPage

from ai_framework.rendering import SeoContext, SeoInjector, JinjaTemplateRenderer


class DocsRenderer:
    """
    Showcase-local renderer for docs_site — uses framework primitives.
    Owns docs-specific URL semantics: guides/, api/, sections/, versions/
    No posts/, categories/, tags/ — proves abstraction universality.
    """

    def __init__(self, templates_dir: pathlib.Path | None = None):
        if templates_dir is None:
            here = pathlib.Path(__file__).resolve()
            candidate = here.parent.parent / "templates"
            templates_dir = (
                candidate
                if candidate.exists()
                else pathlib.Path("showcases/docs_site/templates")
            )
        self.templates_dir = pathlib.Path(templates_dir)
        self.template_renderer = JinjaTemplateRenderer(self.templates_dir)
        self.seo_injector = SeoInjector()

    def _seo_context(self, doc_or_dict, title_fallback: str = "Docs") -> dict:
        if hasattr(doc_or_dict, "to_dict"):
            d = doc_or_dict.to_dict()
        elif isinstance(doc_or_dict, dict):
            d = doc_or_dict
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

    def _seo_obj(self, doc_or_dict, title_fallback: str = "Docs") -> SeoContext:
        if hasattr(doc_or_dict, "to_dict"):
            d = doc_or_dict.to_dict()
        elif isinstance(doc_or_dict, dict):
            d = doc_or_dict
        else:
            d = {}
        return SeoContext.normalize(d, title_fallback=title_fallback)

    def _inject(self, html: str, seo_ctx: dict | SeoContext) -> str:
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

    def _ensure_doc_links(self, html: str, docs: List[DocPage]) -> str:
        # Guarantee guides/<slug>/ links exist — docs-specific convention
        missing = [d for d in docs if f"/guides/{d.slug}/" not in html]
        if missing and docs:
            fallback = "".join(
                [f'<li><a href="/guides/{d.slug}/">{d.title}</a></li>' for d in docs]
            )
            if "</ul>" in html:
                html = html.replace("</ul>", f"{fallback}</ul>", 1)
            else:
                html += f"<ul>{fallback}</ul>"
        return html

    def render_doc(
        self, doc: DocPage, section_name: str = "", version_name: str = ""
    ) -> str:
        seo_obj = self._seo_obj(doc, doc.title)
        seo_dict = self._seo_context(doc, doc.title)
        try:
            html = self.template_renderer.render(
                "doc_page.html",
                {
                    "doc": doc,
                    "page": doc,  # alias for generic templates
                    "section_name": section_name,
                    "version_name": version_name,
                    **seo_dict,
                },
            )
            return self._inject(html, seo_obj)
        except Exception:
            return f"""<!doctype html><html><head><title>{seo_obj.seo_title}</title>
<meta name="description" content="{seo_obj.seo_description}">
<meta property="og:title" content="{seo_obj.og_title}">
<meta property="og:description" content="{seo_obj.og_description}">
<link rel="canonical" href="{seo_obj.canonical_url}">
</head><body><h1>{doc.title}</h1><p>{section_name} / {version_name}</p><article>{doc.content}</article></body></html>"""

    def render_index(self, docs: List[DocPage]) -> str:
        seo_dict = {
            "title": "Docs",
            "seo_title": "Docs",
            "seo_description": f"{len(docs)} pages",
            "og_title": "Docs",
            "og_description": "",
            "canonical_url": "/",
        }
        try:
            html = self.template_renderer.render(
                "index.html", {"docs": docs, "pages": docs, **seo_dict}
            )
            return self._ensure_doc_links(html, docs)
        except Exception:
            items = "".join(
                [f'<li><a href="/guides/{d.slug}/">{d.title}</a></li>' for d in docs]
            )
            return f"<!doctype html><title>Docs</title><h1>Docs</h1><ul>{items}</ul>"

    def render_section(self, slug: str, docs: List[DocPage]) -> str:
        seo_dict = {
            "title": f"Section {slug}",
            "seo_title": f"Section {slug}",
            "seo_description": "",
            "og_title": f"Section {slug}",
            "og_description": "",
            "canonical_url": f"/sections/{slug}/",
        }
        try:
            html = self.template_renderer.render(
                "section.html", {"slug": slug, "docs": docs, "pages": docs, **seo_dict}
            )
            return self._ensure_doc_links(html, docs)
        except Exception:
            items = "".join(
                [f'<li><a href="/guides/{d.slug}/">{d.title}</a></li>' for d in docs]
            )
            return f"<!doctype html><title>Section {slug}</title><h1>Section: {slug}</h1><ul>{items}</ul>"

    def render_version(self, slug: str, docs: List[DocPage]) -> str:
        seo_dict = {
            "title": f"Version {slug}",
            "seo_title": f"Version {slug}",
            "seo_description": "",
            "og_title": f"Version {slug}",
            "og_description": "",
            "canonical_url": f"/versions/{slug}/",
        }
        try:
            html = self.template_renderer.render(
                "version.html", {"slug": slug, "docs": docs, "pages": docs, **seo_dict}
            )
            return self._ensure_doc_links(html, docs)
        except Exception:
            items = "".join(
                [f'<li><a href="/guides/{d.slug}/">{d.title}</a></li>' for d in docs]
            )
            return f"<!doctype html><title>Version {slug}</title><h1>Version: {slug}</h1><ul>{items}</ul>"

    def render_sitemap(self, docs: List[DocPage]) -> str:
        urls = "".join([f"<url><loc>/guides/{d.slug}/</loc></url>" for d in docs])
        return f'<?xml version="1.0"?><urlset>{urls}<url><loc>/</loc></url></urlset>'
