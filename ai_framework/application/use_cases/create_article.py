import uuid

from ai_framework.application.dto.article_dto import (
    CreateArticleRequest,
    CreateArticleResponse,
)
from ai_framework.domain.contracts.repositories import ArticleRepository
from ai_framework.domain.entities.article import Article
from ai_framework.domain.exceptions import DomainValidationError
from ai_framework.domain.value_objects.article_id import ArticleId
from ai_framework.domain.value_objects.content import Content
from ai_framework.domain.value_objects.title import Title


class CreateArticleUseCase:
    """Use Case создания новой доменной статьи в статусе DRAFT."""

    def __init__(self, repository: ArticleRepository) -> None:
        self._repository = repository

    def execute(self, request: CreateArticleRequest) -> CreateArticleResponse:
        title = Title(request.title)
        content = Content(request.content)

        if title.is_empty:
            raise DomainValidationError("Article title cannot be empty on creation.")
        if content.is_empty:
            raise DomainValidationError("Article content cannot be empty on creation.")

        article_id = ArticleId(str(uuid.uuid4()))
        article = Article(
            id=article_id,
            title=title,
            content=content,
        )

        self._repository.add(article)

        return CreateArticleResponse(article_id=article_id)
