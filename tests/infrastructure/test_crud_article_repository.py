import pytest

from ai_framework.crud.engine import UniversalCRUDEngine
from ai_framework.crud.persistence import InMemoryPersistenceProvider
from ai_framework.domain.contracts.repositories import ArticleRepository
from ai_framework.domain.entities.article import Article, ArticleStatus
from ai_framework.domain.value_objects.article_id import ArticleId
from ai_framework.domain.value_objects.content import Content
from ai_framework.domain.value_objects.title import Title
from ai_framework.infrastructure.repositories.article_repository import (
    CRUDArticleRepository,
)


@pytest.fixture
def crud_engine():
    persistence = InMemoryPersistenceProvider()
    return UniversalCRUDEngine(
        persistence_provider=persistence,
    )


def test_crud_article_repository_implements_interface():
    assert issubclass(CRUDArticleRepository, ArticleRepository)


def test_crud_article_repository_add_and_get(crud_engine):
    repo = CRUDArticleRepository(crud_engine=crud_engine)
    article = Article(
        id=ArticleId("article-123"),
        title=Title("Architecture Guide"),
        content=Content("Deep dive into Clean Architecture..."),
    )

    repo.add(article)
    retrieved = repo.get_by_id(ArticleId("article-123"))

    assert retrieved is not None
    assert retrieved.id == article.id
    assert retrieved.title.value == "Architecture Guide"
    assert retrieved.content.value == "Deep dive into Clean Architecture..."
    assert retrieved.status == ArticleStatus.DRAFT


def test_crud_article_repository_update_existing(crud_engine):
    repo = CRUDArticleRepository(crud_engine=crud_engine)
    article = Article(
        id=ArticleId("article-456"),
        title=Title("Draft Title"),
        content=Content("Draft Content"),
    )
    repo.add(article)

    article.publish()
    repo.add(article)

    retrieved = repo.get_by_id(ArticleId("article-456"))
    assert retrieved is not None
    assert retrieved.status == ArticleStatus.PUBLISHED


def test_crud_article_repository_returns_none_if_not_found(crud_engine):
    repo = CRUDArticleRepository(crud_engine=crud_engine)
    assert repo.get_by_id(ArticleId("non-existent")) is None