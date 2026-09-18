from dataclasses import dataclass, field
from typing import List, Optional
import uuid
from .item_status import ItemStatus, InvalidStateTransitionError
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
    def validate_for_publish(self):
        if not self.title.strip() or not self.content.strip() or not self.slug.strip():
            raise ValueError("Cannot publish without title/content/slug")
    def publish(self):
        self.validate_for_publish()
        if self.status == ItemStatus.ARCHIVED:
            raise InvalidStateTransitionError("Cannot publish archived, duplicate first")
        self.status = ItemStatus.PUBLISHED
    def unpublish(self):
        self.status = ItemStatus.DRAFT
    def is_published(self):
        return self.status == ItemStatus.PUBLISHED
