from dataclasses import dataclass, field
from typing import List, Optional
import uuid
import re
from .item_status import ItemStatus, InvalidStateTransitionError

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

@dataclass
class Item:
    id: uuid.UUID
    title: str
    slug: str
    content: str
    category_id: uuid.UUID
    status: ItemStatus = ItemStatus.DRAFT
    tag_ids: List[uuid.UUID] = field(default_factory=list)
    media_ids: List[uuid.UUID] = field(default_factory=list)
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    canonical_url: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    author_id: Optional[uuid.UUID] = None

    def validate_for_draft(self):
        if not self.title or not self.title.strip():
            raise ValueError("validation.required:title")
        if not self.slug or not self.slug.strip():
            raise ValueError("validation.required:slug")
        if not SLUG_RE.match(self.slug):
            raise ValueError("validation.invalid_slug_format:slug")
        if not self.category_id:
            raise ValueError("validation.required:category_id")

    def validate_for_publish(self):
        self.validate_for_draft()
        if not self.content or not self.content.strip():
            raise ValueError("validation.required:content - cannot publish empty content")
        if len(self.content.strip()) < 20:
            raise ValueError("validation.too_short:content - publish requires >=20 chars")

    def publish(self):
        self.validate_for_publish()
        if self.status == ItemStatus.ARCHIVED:
            raise InvalidStateTransitionError("Cannot publish ARCHIVED, duplicate first")
        self.status = ItemStatus.PUBLISHED

    def unpublish(self):
        if self.status == ItemStatus.PUBLISHED:
            self.status = ItemStatus.DRAFT

    def archive(self):
        self.status = ItemStatus.ARCHIVED

    def is_published(self) -> bool:
        return self.status == ItemStatus.PUBLISHED
