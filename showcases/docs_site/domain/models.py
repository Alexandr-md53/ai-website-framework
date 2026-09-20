from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime, timezone


class DocStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


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
    name: str  # e.g. "v2.1"
    slug: str


@dataclass
class DocPage:
    id: uuid.UUID
    title: str
    slug: str  # e.g. "getting-started"
    content: str
    section_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    status: DocStatus = DocStatus.DRAFT
    seo: SeoMeta = field(default_factory=SeoMeta)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    html_content: str = ""

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "slug": self.slug,
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
