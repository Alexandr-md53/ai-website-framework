import pytest

from ai_framework.domain.entities.article import Article
from ai_framework.domain.value_objects.article_id import ArticleId
from ai_framework.domain.value_objects.title import Title
from ai_framework.domain.value_objects.content import Content
from tests.domain.fakes import InMemoryArticleRepository


def test_in_memory_repository_add_and_get():
    repo = InMemoryArticleRepository()
    article = Article(
        id=ArticleId("123e4567-e89b-12d3-a456-426614174000"),
        title=Title("Test Article"),
        content=Content("Test Content"),
    )

    repo.add(article)
    retrieved = repo.get_by_id(ArticleId("123e4567-e89b-12d3-a456-426614174000"))

    assert retrieved is not None
    assert retrieved.id == article.id
    assert retrieved.title.value == "Test Article"


def test_in_memory_repository_returns_none_when_not_found():
    repo = InMemoryArticleRepository()
    retrieved = repo.get_by_id(ArticleId("non-existent-id"))
    assert retrieved is None
