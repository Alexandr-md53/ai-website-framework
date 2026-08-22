import pytest

from ai_framework.domain.entities.article import ArticleStatus
from ai_framework.domain.exceptions import DomainValidationError
from ai_framework.application.use_cases.create_article import CreateArticleUseCase
from ai_framework.application.dto.article_dto import CreateArticleRequest
from tests.domain.fakes import InMemoryArticleRepository


def test_create_article_use_case_success():
    repo = InMemoryArticleRepository()
    use_case = CreateArticleUseCase(repository=repo)

    request = CreateArticleRequest(
        title="Architecture Principles",
        content="Clean Architecture in Python...",
    )
    response = use_case.execute(request)

    assert response.article_id is not None

    # Проверяем сохранение в репозитории
    created_article = repo.get_by_id(response.article_id)
    assert created_article is not None
    assert created_article.status == ArticleStatus.DRAFT
    assert created_article.title.value == "Architecture Principles"


def test_create_article_use_case_fails_with_empty_title():
    repo = InMemoryArticleRepository()
    use_case = CreateArticleUseCase(repository=repo)

    request = CreateArticleRequest(
        title="",
        content="Valid Content",
    )

    with pytest.raises(DomainValidationError):
        use_case.execute(request)
