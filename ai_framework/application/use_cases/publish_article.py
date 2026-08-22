from ai_framework.application.dto.article_dto import (
    PublishArticleRequest,
    PublishArticleResponse,
)
from ai_framework.domain.contracts.repositories import ArticleRepository
from ai_framework.domain.value_objects.article_id import ArticleId


class PublishArticleUseCase:
    """Use Case оркестрации публикации статьи."""

    def __init__(self, repository: ArticleRepository) -> None:
        self._repository = repository

    def execute(self, request: PublishArticleRequest) -> PublishArticleResponse:
        article_id = ArticleId(request.article_id)
        article = self._repository.get_by_id(article_id)

        if article is None:
            raise KeyError(f"Article with id {request.article_id} not found.")

        article.publish()
        self._repository.add(article)

        return PublishArticleResponse(is_published=True)
