import pytest

from ai_framework.domain.entities.article import Article, ArticleStatus
from ai_framework.domain.value_objects.article_id import ArticleId
from ai_framework.domain.value_objects.title import Title
from ai_framework.domain.value_objects.content import Content
from ai_framework.domain.exceptions import DomainValidationError
from ai_framework.application.use_cases.publish_article import PublishArticleUseCase
from ai_framework.application.dto.article_dto import PublishArticleRequest
from tests.domain.fakes import InMemoryArticleRepository


def test_publish_article_use_case_success():
    repo = InMemoryArticleRepository()
    article_id = ArticleId("123e4567-e89b-12d3-a456-426614174000")

    # Готовим исходную черновую статью в репозитории
    draft_article = Article(
        id=article_id,
        title=Title("Clean Architecture in Python"),
        content=Content("Domain-driven design principles..."),
    )
    repo.add(draft_article)

    use_case = PublishArticleUseCase(repository=repo)
    request = PublishArticleRequest(article_id="123e4567-e89b-12d3-a456-426614174000")

    response = use_case.execute(request)

    assert response.is_published is True

    # Проверяем, что статья обновила статус в самом репозитории
    saved_article = repo.get_by_id(article_id)
    assert saved_article is not None
    assert saved_article.status == ArticleStatus.PUBLISHED


def test_publish_article_use_case_raises_error_if_not_found():
    repo = InMemoryArticleRepository()
    use_case = PublishArticleUseCase(repository=repo)
    request = PublishArticleRequest(article_id="non-existent-id")

    with pytest.raises(KeyError):
        use_case.execute(request)
