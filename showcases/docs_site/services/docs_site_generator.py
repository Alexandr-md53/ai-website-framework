from __future__ import annotations
from typing import List
import pathlib

from .docs_service import DocsService
from .docs_renderer import DocsRenderer
from ai_framework.rendering import GeneratedPage, StaticSiteWriter


class DocsSiteGenerator:
    """Type-B for docs: Domain -> Generator -> Renderer -> Output, using same framework primitives as blog_cms"""

    def __init__(self, service: DocsService, renderer: DocsRenderer):
        self.service = service
        self.renderer = renderer
        self._writer = StaticSiteWriter()

    def generate(self) -> List[GeneratedPage]:
        pages: List[GeneratedPage] = []
        published = self.service.list_published()
        # index
        pages.append(
            GeneratedPage("index.html", self.renderer.render_index(published), "index")
        )
        # guides/<slug>/
        for doc in published:
            sec = self.service._sections.get(doc.section_id) if doc.section_id else None
            ver = self.service._versions.get(doc.version_id) if doc.version_id else None
            sec_name = sec.name if sec else ""
            ver_name = ver.name if ver else ""
            html = self.renderer.render_doc(doc, sec_name, ver_name)
            pages.append(GeneratedPage(f"guides/{doc.slug}/index.html", html, "doc"))
            doc.html_content = html
        # sections/<slug>/
        for sec in self.service.list_sections():
            docs = self.service.list_published(section_slug=sec.slug)
            pages.append(
                GeneratedPage(
                    f"sections/{sec.slug}/index.html",
                    self.renderer.render_section(sec.slug, docs),
                    "section",
                )
            )
        # versions/<slug>/
        for ver in self.service.list_versions():
            docs = self.service.list_published(version_slug=ver.slug)
            pages.append(
                GeneratedPage(
                    f"versions/{ver.slug}/index.html",
                    self.renderer.render_version(ver.slug, docs),
                    "version",
                )
            )
        # sitemap
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
