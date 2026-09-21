from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

from ai_framework.content import PublishStatus, Slug

PostStatus = PublishStatus
SLUG_RE = None


@dataclass
class Author:
    id: uuid.UUID
    name: str
    slug: str
    bio: Optional[str] = None

    def validate(self):
        Slug(self.slug)


@dataclass
class Category:
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None

    def validate(self):
        Slug(self.slug)


@dataclass
class Tag:
    id: uuid.UUID
    name: str
    slug: str

    def validate(self):
        Slug(self.slug)


@dataclass
class SeoMeta:
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    canonical_url: Optional[str] = None

    def validate(self):
        if self.seo_title and len(self.seo_title) > 70:
            raise ValueError("seo_title > 70")
        if self.seo_description and len(self.seo_description) > 160:
            raise ValueError("seo_description > 160")
        if self.canonical_url and not (
            self.canonical_url.startswith("http://")
            or self.canonical_url.startswith("https://")
            or self.canonical_url.startswith("/")
        ):
            raise ValueError("canonical_url must start with http(s):// or /")


@dataclass
class Post:
    id: uuid.UUID
    title: str
    slug: Slug
    content: str
    category_id: uuid.UUID
    author_id: uuid.UUID
    tag_ids: List[uuid.UUID] = field(default_factory=list)
    status: PublishStatus = PublishStatus.DRAFT
    seo: SeoMeta = field(default_factory=SeoMeta)
    html_content: Optional[str] = None

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

    def validate_for_draft(self):
        if not self.title or len(self.title.strip()) < 3:
            raise ValueError("title too short")
        Slug(str(self.slug))
        if len(self.content.strip()) < 20:
            raise ValueError("content too short for publish, min 20")
        self.seo.validate()

    def is_published(self) -> bool:
        return self.status == PublishStatus.PUBLISHED

    def publish(self):
        self.validate_for_draft()
        if len(self.content.strip()) < 20:
            raise ValueError("publish requires content >=20")
        self.status = PublishStatus.PUBLISHED

    def unpublish(self):
        self.status = PublishStatus.DRAFT

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "slug": str(self.slug),
            "content": self.content,
            "category_id": str(self.category_id),
            "author_id": str(self.author_id),
            "tag_ids": [str(t) for t in self.tag_ids],
            "status": self.status.value,
            "seo_title": self.seo.seo_title,
            "seo_description": self.seo.seo_description,
            "og_title": self.seo.og_title,
            "og_description": self.seo.og_description,
            "canonical_url": self.seo.canonical_url,
            "html_content": self.html_content,
        }
