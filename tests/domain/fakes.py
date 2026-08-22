from typing import Dict, Optional

from ai_framework.domain.contracts.repositories import ArticleRepository
from ai_framework.domain.entities.article import Article
from ai_framework.domain.value_objects.article_id import ArticleId


class InMemoryArticleRepository(ArticleRepository):
    """In-memory реализация контракта ArticleRepository для изолированного тестирования."""

    def __init__(self) -> None:
        self._storage: Dict[str, Article] = {}

    def add(self, article: Article) -> None:
        self._storage[article.id.value] = article

    def get_by_id(self, article_id: ArticleId) -> Optional[Article]:
        return self._storage.get(article_id.value)
