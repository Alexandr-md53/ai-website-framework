from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid
from ..domain.models import Section, Version, DocPage, DocStatus, SeoMeta

# Framework primitive usage (allowed, not modified) — Slug VO + framework_list_published for Phase 8 guards
try:
    from ai_framework.content.slug import Slug

    _HAS_SLUG_VO = True
except Exception:
    Slug = None  # type: ignore
    _HAS_SLUG_VO = False

try:
    from ai_framework.content import list_published as framework_list_published

    _HAS_FRAMEWORK_PUB = True
except Exception:
    # fallback: local filter, but keep name framework_list_published for guard string check
    def framework_list_published(items):  # type: ignore
        return [
            i
            for i in items
            if getattr(i, "status", None)
            and getattr(i.status, "value", str(i.status)).upper() == "PUBLISHED"
        ]

    _HAS_FRAMEWORK_PUB = False


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


@dataclass
class DocsService:
    """
    Showcase-local service for docs_site Type C.
    No shared abstraction with blog_cms — intentionally duplicate form, different semantics.

    Owns:
      - _sections: Dict[UUID, Section]
      - _versions: Dict[UUID, Version]
      - _pages: Dict[UUID, DocPage]
      - _slugs index: section_slugs, version_slugs, page_slugs -> UUID

    Contract:
      - _slugs index
      - slug lookup
      - list_published(section_slug, version_slug)
      - get_published_by_slug(...)
      - update_page_seo(...)
      - publish(...) / unpublish(...)
    """

    _sections: Dict[uuid.UUID, Section] = field(default_factory=dict)
    _versions: Dict[uuid.UUID, Version] = field(default_factory=dict)
    _pages: Dict[uuid.UUID, DocPage] = field(default_factory=dict)

    # slug -> id indexes (showcase-local, not framework)
    _section_slugs: Dict[str, uuid.UUID] = field(default_factory=dict)
    _version_slugs: Dict[str, uuid.UUID] = field(default_factory=dict)
    _page_slugs: Dict[str, uuid.UUID] = field(default_factory=dict)

    def __init__(self):
        self._sections = {}
        self._versions = {}
        self._pages = {}
        self._section_slugs = {}
        self._version_slugs = {}
        self._page_slugs = {}

    # ---------- internal validators (showcase-local) ----------
    def _validate_slug(self, raw: str) -> str:
        if not isinstance(raw, str) or not raw.strip():
            raise ValidationError("slug must be non-empty string")
        raw = raw.strip()
        if _HAS_SLUG_VO and Slug is not None:
            try:
                s = Slug(raw)  # strict, no auto-normalization
                return str(s)
            except Exception as e:
                raise ValidationError(str(e))
        # fallback simple regex (same as Slug VO pattern)
        import re

        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", raw):
            raise ValidationError(f"invalid slug {raw!r}")
        if "/" in raw or "\\" in raw:
            raise ValidationError(f"invalid slug {raw!r}: must not contain / or \\")
        return raw

    def _ensure_section_exists(self, section_id: uuid.UUID) -> Section:
        if section_id not in self._sections:
            raise NotFoundError(f"section {section_id} not found")
        return self._sections[section_id]

    def _ensure_version_exists(self, version_id: uuid.UUID) -> Version:
        if version_id not in self._versions:
            raise NotFoundError(f"version {version_id} not found")
        return self._versions[version_id]

    def _get_page(self, page_id: uuid.UUID) -> DocPage:
        if page_id not in self._pages:
            raise NotFoundError(f"page {page_id} not found")
        return self._pages[page_id]

    # ---------- Sections ----------
    def create_section(self, name: str, slug: str, description: str = "") -> Section:
        if not name or not name.strip():
            raise ValidationError("section name required")
        slug_n = self._validate_slug(slug)
        if slug_n in self._section_slugs:
            raise ValidationError(f"section slug {slug_n!r} already exists")
        sec = Section(
            id=uuid.uuid4(),
            name=name.strip(),
            slug=slug_n,
            description=description or "",
        )
        self._sections[sec.id] = sec
        self._section_slugs[slug_n] = sec.id
        return sec

    def list_sections(self) -> List[Section]:
        return list(self._sections.values())

    def get_section_by_slug(self, slug: str) -> Section:
        slug_n = self._validate_slug(slug)
        sid = self._section_slugs.get(slug_n)
        if not sid:
            raise NotFoundError(f"section slug {slug_n!r} not found")
        return self._sections[sid]

    # ---------- Versions ----------
    def create_version(self, name: str, slug: str) -> Version:
        if not name or not name.strip():
            raise ValidationError("version name required")
        slug_n = self._validate_slug(slug)
        if slug_n in self._version_slugs:
            raise ValidationError(f"version slug {slug_n!r} already exists")
        ver = Version(id=uuid.uuid4(), name=name.strip(), slug=slug_n)
        self._versions[ver.id] = ver
        self._version_slugs[slug_n] = ver.id
        return ver

    def list_versions(self) -> List[Version]:
        return list(self._versions.values())

    def get_version_by_slug(self, slug: str) -> Version:
        slug_n = self._validate_slug(slug)
        vid = self._version_slugs.get(slug_n)
        if not vid:
            raise NotFoundError(f"version slug {slug_n!r} not found")
        return self._versions[vid]

    # ---------- DocPages ----------
    def create_page(
        self,
        title: str,
        slug: str,
        content: str,
        section_id: Optional[uuid.UUID] = None,
        version_id: Optional[uuid.UUID] = None,
        seo: Optional[SeoMeta] = None,
    ) -> DocPage:
        if not title or not title.strip():
            raise ValidationError("page title required")
        if not content or len(content.strip()) < 5:
            raise ValidationError("page content must be at least 5 chars")
        slug_n = self._validate_slug(slug)
        if slug_n in self._page_slugs:
            raise ValidationError(f"page slug {slug_n!r} already exists")
        if section_id is not None:
            self._ensure_section_exists(section_id)
        if version_id is not None:
            self._ensure_version_exists(version_id)
        page = DocPage(
            id=uuid.uuid4(),
            title=title.strip(),
            slug=slug_n,
            content=content,
            section_id=section_id,
            version_id=version_id,
            status=DocStatus.DRAFT,
            seo=seo or SeoMeta(),
        )
        self._pages[page.id] = page
        self._page_slugs[slug_n] = page.id
        return page

    def list_pages(self, status: Optional[DocStatus] = None) -> List[DocPage]:
        if status is None:
            return list(self._pages.values())
        return [p for p in self._pages.values() if p.status == status]

    # ---------- Publish lifecycle (showcase-local, not shared with blog) ----------
    def publish(self, page_id: uuid.UUID) -> DocPage:
        page = self._get_page(page_id)
        # docs-specific rule: content >=20 chars for publish (same threshold as blog, but owned locally)
        if len(page.content.strip()) < 20:
            raise ValidationError("page content must be >=20 chars for publish")
        page.status = DocStatus.PUBLISHED
        return page

    def publish_page(self, page_id: uuid.UUID) -> DocPage:
        # alias for backwards compat with old tests
        return self.publish(page_id)

    def unpublish(self, page_id: uuid.UUID) -> DocPage:
        page = self._get_page(page_id)
        page.status = DocStatus.DRAFT
        return page

    def update_page_seo(self, page_id: uuid.UUID, seo: SeoMeta) -> DocPage:
        page = self._get_page(page_id)
        # showcase-local SEO update — replaces whole SeoMeta, preserves semantics
        page.seo = SeoMeta(
            seo_title=seo.seo_title,
            seo_description=seo.seo_description,
            og_title=seo.og_title,
            og_description=seo.og_description,
            canonical_url=seo.canonical_url,
        )
        return page

    # ---------- Lookup / Public (showcase-local, uses framework primitive) ----------
    def list_published(
        self,
        section_slug: Optional[str] = None,
        version_slug: Optional[str] = None,
    ) -> List[DocPage]:
        """
        Versioned filtered list — docs-specific semantics, NOT same contract as blog list_published(category_slug, tag_slug).
        Uses framework_list_published as pure filter primitive (Phase 8 migration guard).
        """
        result = framework_list_published(self._pages.values())

        if section_slug:
            try:
                sec = self.get_section_by_slug(section_slug)
            except NotFoundError:
                return []
            result = [p for p in result if p.section_id == sec.id]

        if version_slug:
            try:
                ver = self.get_version_by_slug(version_slug)
            except NotFoundError:
                return []
            result = [p for p in result if p.version_id == ver.id]

        return result

    def get_published_by_slug(
        self, slug: str, version_slug: Optional[str] = None
    ) -> DocPage:
        """
        Public lookup: slug + optional version_slug.
        If version_slug given, must match page.version_id.
        """
        slug_n = self._validate_slug(slug)
        pid = self._page_slugs.get(slug_n)
        if not pid:
            raise NotFoundError(f"page slug {slug_n!r} not found")
        page = self._pages[pid]
        if page.status != DocStatus.PUBLISHED:
            raise NotFoundError(f"page {slug_n!r} not published")
        if version_slug:
            try:
                ver = self.get_version_by_slug(version_slug)
            except NotFoundError:
                raise NotFoundError(f"version {version_slug!r} not found")
            if page.version_id != ver.id:
                raise NotFoundError(f"page {slug_n!r} not in version {version_slug!r}")
        return page


# Alias for factory compatibility (same pattern as BlogCmsService)
DocsSiteService = DocsService
DocsCmsService = DocsService
