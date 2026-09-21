from __future__ import annotations
from enum import Enum


class PublishStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

    def is_published(self) -> bool:
        return self == PublishStatus.PUBLISHED

    def is_draft(self) -> bool:
        return self == PublishStatus.DRAFT
