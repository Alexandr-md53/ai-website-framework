from dataclasses import dataclass
from ai_framework.domain.value_objects.article_id import ArticleId


@dataclass(frozen=True)
class PublishArticleRequest:
    article_id: str


@dataclass(frozen=True)
class PublishArticleResponse:
    is_published: bool


@dataclass(frozen=True)
class CreateArticleRequest:
    title: str
    content: str


@dataclass(frozen=True)
class CreateArticleResponse:
    article_id: ArticleId


@dataclass(frozen=True)
class ArchiveArticleRequest:
    article_id: str


@dataclass(frozen=True)
class ArchiveArticleResponse:
    is_archived: bool
