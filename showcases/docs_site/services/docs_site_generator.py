from __future__ import annotations

import pathlib
from typing import List

from ai_framework.rendering import GeneratedPage, StaticSiteWriter

from ..domain.models import DocPage
from .docs_renderer import DocsRenderer
from .docs_service import DocsService


class DocsSiteGenerator:
    """
    Type-B docs generator.

    Domain -> GeneratedPage.
    Filesystem output remains delegated to StaticSiteWriter.
    """

    def __init__(
        self,
        service: DocsService,
        renderer: DocsRenderer,
    ):
        self.service = service
        self.renderer = renderer
        self._writer = StaticSiteWriter()

    @staticmethod
    def _page_url(
        page: DocPage,
        sections,
        versions,
    ) -> str:
        version = versions.get(page.version_id) if page.version_id else None
        section = sections.get(page.section_id) if page.section_id else None

        if version and section:
            return f"/v/{version.slug}/{section.slug}/{page.slug}/"

        if version:
            return f"/v/{version.slug}/{page.slug}/"

        return f"/pages/{page.slug}/"

    @staticmethod
    def _directory_url(path: str) -> str:
        if path == "index.html":
            return "/"

        if path.endswith("/index.html"):
            return f"/{path[: -len('index.html')]}"

        return f"/{path}"

    def generate(self) -> List[GeneratedPage]:
        pages: List[GeneratedPage] = []

        published = self.service.list_published()

        sections = {section.id: section for section in self.service.list_sections()}

        versions = {version.id: version for version in self.service.list_versions()}

        page_urls = {
            str(page.id): self._page_url(
                page,
                sections,
                versions,
            )
            for page in published
        }

        # Root index.
        pages.append(
            GeneratedPage(
                "index.html",
                self.renderer.render_index(
                    published,
                    page_urls,
                ),
                "index",
            )
        )

        # Version indexes and section indexes.
        for version in self.service.list_versions():
            version_docs = self.service.list_published(
                version_slug=version.slug,
            )

            pages.append(
                GeneratedPage(
                    f"v/{version.slug}/index.html",
                    self.renderer.render_version(
                        version,
                        version_docs,
                        page_urls,
                    ),
                    "version",
                )
            )

            version_sections = [
                section
                for section in self.service.list_sections()
                if any(page.section_id == section.id for page in version_docs)
            ]

            for section in version_sections:
                section_docs = [
                    page for page in version_docs if page.section_id == section.id
                ]

                pages.append(
                    GeneratedPage(
                        f"v/{version.slug}/{section.slug}/index.html",
                        self.renderer.render_section(
                            section,
                            version,
                            section_docs,
                            page_urls,
                        ),
                        "section",
                    )
                )

        # Page indexes.
        for page in published:
            version = versions.get(page.version_id) if page.version_id else None
            section = sections.get(page.section_id) if page.section_id else None

            if version and section:
                path = f"v/{version.slug}/{section.slug}/{page.slug}/index.html"
            elif version:
                path = f"v/{version.slug}/{page.slug}/index.html"
            else:
                path = f"pages/{page.slug}/index.html"

            page_url = page_urls[str(page.id)]

            html = self.renderer.render_doc(
                page,
                section=section,
                version=version,
                page_url=page_url,
            )

            pages.append(
                GeneratedPage(
                    path,
                    html,
                    "page",
                )
            )

            page.html_content = html

        # Sitemap contains public URLs, not filesystem paths.
        sitemap_paths = [
            self._directory_url(page.path)
            for page in pages
            if page.path != "sitemap.xml"
        ]

        sitemap_paths = sorted(set(sitemap_paths))

        pages.append(
            GeneratedPage(
                "sitemap.xml",
                self.renderer.render_sitemap(sitemap_paths),
                "sitemap",
            )
        )

        return pages

    def write(
        self,
        pages: List[GeneratedPage],
        out_dir: pathlib.Path,
        clean: bool = True,
    ) -> List[pathlib.Path]:
        return self._writer.write(
            pages,
            out_dir,
            clean=clean,
        )
