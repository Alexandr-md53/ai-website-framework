from ai_framework.application.dto.article_dto import (
    ArchiveArticleRequest,
    ArchiveArticleResponse,
)
from ai_framework.domain.contracts.repositories import ArticleRepository
from ai_framework.domain.value_objects.article_id import ArticleId


class ArchiveArticleUseCase:
    """Use Case оркестрации архивации статьи."""

    def __init__(self, repository: ArticleRepository) -> None:
        self._repository = repository

    def execute(self, request: ArchiveArticleRequest) -> ArchiveArticleResponse:
        article_id = ArticleId(request.article_id)
        article = self._repository.get_by_id(article_id)

        if article is None:
            raise KeyError(f"Article with id {request.article_id} not found.")

        article.archive()
        self._repository.add(article)

        return ArchiveArticleResponse(is_archived=True)
