from __future__ import annotations
import uuid
from typing import List, Dict, Optional
from ..domain.models import DocPage, Section, Version, DocStatus, SeoMeta


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class DocsService:
    """In-memory docs domain — Type-B, similar to BlogCmsService but docs-specific"""

    def __init__(self):
        self._sections: Dict[uuid.UUID, Section] = {}
        self._versions: Dict[uuid.UUID, Version] = {}
        self._pages: Dict[uuid.UUID, DocPage] = {}

    # Sections
    def create_section(self, name: str, slug: str, description: str = "") -> Section:
        if not name or not slug:
            raise ValidationError("name/slug required")
        sec = Section(id=uuid.uuid4(), name=name, slug=slug, description=description)
        self._sections[sec.id] = sec
        return sec

    def list_sections(self) -> List[Section]:
        return list(self._sections.values())

    # Versions
    def create_version(self, name: str, slug: str) -> Version:
        if not name or not slug:
            raise ValidationError("name/slug required")
        ver = Version(id=uuid.uuid4(), name=name, slug=slug)
        self._versions[ver.id] = ver
        return ver

    def list_versions(self) -> List[Version]:
        return list(self._versions.values())

    # Pages
    def create_page(
        self,
        title: str,
        slug: str,
        content: str,
        section_id: uuid.UUID | None = None,
        version_id: uuid.UUID | None = None,
        seo: SeoMeta | None = None,
    ) -> DocPage:
        if not title or not slug or len(content) < 10:
            raise ValidationError("title/slug/content invalid")
        if section_id and section_id not in self._sections:
            raise NotFoundError("section not found")
        if version_id and version_id not in self._versions:
            raise NotFoundError("version not found")
        page = DocPage(
            id=uuid.uuid4(),
            title=title,
            slug=slug,
            content=content,
            section_id=section_id,
            version_id=version_id,
            seo=seo or SeoMeta(),
        )
        self._pages[page.id] = page
        return page

    def publish_page(self, page_id: uuid.UUID) -> DocPage:
        page = self._pages.get(page_id)
        if not page:
            raise NotFoundError("page not found")
        page.status = DocStatus.PUBLISHED
        return page

    def list_pages(self, status: DocStatus | None = None) -> List[DocPage]:
        if status:
            return [p for p in self._pages.values() if p.status == status]
        return list(self._pages.values())

    def list_published(
        self, section_slug: str | None = None, version_slug: str | None = None
    ) -> List[DocPage]:
        pages = [p for p in self._pages.values() if p.status == DocStatus.PUBLISHED]
        if section_slug:
            sec_ids = [s.id for s in self._sections.values() if s.slug == section_slug]
            pages = [p for p in pages if p.section_id in sec_ids]
        if version_slug:
            ver_ids = [v.id for v in self._versions.values() if v.slug == version_slug]
            pages = [p for p in pages if p.version_id in ver_ids]
        return pages

    def get_published_by_slug(self, slug: str) -> DocPage:
        for p in self._pages.values():
            if p.slug == slug and p.status == DocStatus.PUBLISHED:
                return p
        raise NotFoundError(f"doc {slug} not found")

    def update_page_seo(self, page_id: uuid.UUID, seo: SeoMeta) -> DocPage:
        page = self._pages.get(page_id)
        if not page:
            raise NotFoundError("page not found")
        page.seo = seo
        return page
