from __future__ import annotations
import re, uuid
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PostStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


@dataclass
class Author:
    id: uuid.UUID
    name: str
    slug: str
    bio: Optional[str] = None

    def validate(self):
        if not SLUG_RE.match(self.slug):
            raise ValueError(f"invalid slug {self.slug}")


@dataclass
class Category:
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None

    def validate(self):
        if not SLUG_RE.match(self.slug):
            raise ValueError(f"invalid slug {self.slug}")


@dataclass
class Tag:
    id: uuid.UUID
    name: str
    slug: str

    def validate(self):
        if not SLUG_RE.match(self.slug):
            raise ValueError(f"invalid slug {self.slug}")


@dataclass
class SeoMeta:
    seo_title: Optional[str] = None  # max 70
    seo_description: Optional[str] = None  # max 160
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
    slug: str
    content: str  # markdown
    category_id: uuid.UUID
    author_id: uuid.UUID
    tag_ids: List[uuid.UUID] = field(default_factory=list)
    status: PostStatus = PostStatus.DRAFT
    seo: SeoMeta = field(default_factory=SeoMeta)
    # generated
    html_content: Optional[str] = None

    def validate_for_draft(self):
        if not self.title or len(self.title.strip()) < 3:
            raise ValueError("title too short")
        if not SLUG_RE.match(self.slug):
            raise ValueError(f"invalid slug {self.slug}")
        if len(self.content.strip()) < 20:
            raise ValueError("content too short for publish, min 20")
        self.seo.validate()

    def is_published(self) -> bool:
        return self.status == PostStatus.PUBLISHED

    def publish(self):
        self.validate_for_draft()
        if len(self.content.strip()) < 20:
            raise ValueError("publish requires content >=20")
        self.status = PostStatus.PUBLISHED

    def unpublish(self):
        self.status = PostStatus.DRAFT

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "slug": self.slug,
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
