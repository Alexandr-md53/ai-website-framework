from dataclasses import dataclass
from enum import Enum

from ai_framework.domain.exceptions import (
    DomainValidationError,
    InvalidStateTransitionError,
)
from ai_framework.domain.value_objects.article_id import ArticleId
from ai_framework.domain.value_objects.content import Content
from ai_framework.domain.value_objects.title import Title


class ArticleStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


@dataclass
class Article:
    id: ArticleId
    title: Title
    content: Content
    status: ArticleStatus = ArticleStatus.DRAFT

    def publish(self) -> None:
        if self.title.is_empty:
            raise DomainValidationError("Article title cannot be empty on publish.")
        if self.content.is_empty:
            raise DomainValidationError("Article content cannot be empty on publish.")

        self.status = ArticleStatus.PUBLISHED

    def archive(self) -> None:
        if self.status != ArticleStatus.PUBLISHED:
            raise InvalidStateTransitionError(
                "Cannot archive article unless it is PUBLISHED."
            )

        self.status = ArticleStatus.ARCHIVED

    def update_title(self, new_title: Title) -> None:
        if self.status != ArticleStatus.DRAFT:
            raise DomainValidationError("Cannot update title of a non-draft article.")
        self.title = new_title

    def update_content(self, new_content: Content) -> None:
        if self.status != ArticleStatus.DRAFT:
            raise DomainValidationError("Cannot update content of a non-draft article.")
        self.content = new_content
