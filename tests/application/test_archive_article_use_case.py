import pytest

from ai_framework.domain.entities.article import Article, ArticleStatus
from ai_framework.domain.value_objects.article_id import ArticleId
from ai_framework.domain.value_objects.title import Title
from ai_framework.domain.value_objects.content import Content
from ai_framework.domain.exceptions import InvalidStateTransitionError
from ai_framework.application.use_cases.archive_article import ArchiveArticleUseCase
from ai_framework.application.dto.article_dto import ArchiveArticleRequest
from tests.domain.fakes import InMemoryArticleRepository


def test_archive_article_use_case_success():
    repo = InMemoryArticleRepository()
    article_id = ArticleId("123e4567-e89b-12d3-a456-426614174000")

    article = Article(
        id=article_id,
        title=Title("Clean Architecture in Python"),
        content=Content("Domain-driven design principles..."),
    )
    article.publish()
    repo.add(article)

    use_case = ArchiveArticleUseCase(repository=repo)
    request = ArchiveArticleRequest(article_id="123e4567-e89b-12d3-a456-426614174000")

    response = use_case.execute(request)

    assert response.is_archived is True

    saved_article = repo.get_by_id(article_id)
    assert saved_article is not None
    assert saved_article.status == ArticleStatus.ARCHIVED


def test_archive_article_use_case_fails_from_draft():
    repo = InMemoryArticleRepository()
    article_id = ArticleId("123e4567-e89b-12d3-a456-426614174000")

    article = Article(
        id=article_id,
        title=Title("Draft Title"),
        content=Content("Draft Content"),
    )
    repo.add(article)

    use_case = ArchiveArticleUseCase(repository=repo)
    request = ArchiveArticleRequest(article_id="123e4567-e89b-12d3-a456-426614174000")

    with pytest.raises(InvalidStateTransitionError):
        use_case.execute(request)
