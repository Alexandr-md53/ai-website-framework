from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ai_framework.content import PublishStatus, Slug

DocStatus = PublishStatus


@dataclass
class SeoMeta:
    seo_title: str | None = None
    seo_description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    canonical_url: str | None = None


@dataclass
class Section:
    id: uuid.UUID
    name: str
    slug: str
    description: str = ""


@dataclass
class Version:
    id: uuid.UUID
    name: str
    slug: str


@dataclass
class DocPage:
    id: uuid.UUID
    title: str
    slug: Slug
    content: str
    section_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    status: PublishStatus = PublishStatus.DRAFT
    seo: SeoMeta = field(default_factory=SeoMeta)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    html_content: str = ""

    def __post_init__(self):
        if isinstance(self.slug, str):
            object.__setattr__(self, "slug", Slug(self.slug))
        if not isinstance(self.status, PublishStatus):
            try:
                v = (
                    self.status.value
                    if hasattr(self.status, "value")
                    else str(self.status)
                )
                object.__setattr__(self, "status", PublishStatus(v.lower()))
            except Exception:
                object.__setattr__(self, "status", PublishStatus.DRAFT)

    def is_published(self) -> bool:
        return self.status == PublishStatus.PUBLISHED

    def publish(self):
        Slug(str(self.slug))
        if not self.title or len(self.title.strip()) < 3:
            raise ValueError("title too short")
        if len(self.content.strip()) < 10:
            raise ValueError("content too short")
        self.status = PublishStatus.PUBLISHED

    def unpublish(self):
        self.status = PublishStatus.DRAFT

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "slug": str(self.slug),
            "content": self.content,
            "section_id": str(self.section_id) if self.section_id else None,
            "version_id": str(self.version_id) if self.version_id else None,
            "status": self.status.value,
            "seo_title": self.seo.seo_title,
            "seo_description": self.seo.seo_description,
            "og_title": self.seo.og_title,
            "og_description": self.seo.og_description,
            "canonical_url": self.seo.canonical_url,
        }
