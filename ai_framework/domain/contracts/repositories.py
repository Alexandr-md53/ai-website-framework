from abc import ABC, abstractmethod
from typing import Optional

from ai_framework.domain.entities.article import Article
from ai_framework.domain.value_objects.article_id import ArticleId


class ArticleRepository(ABC):
    """Абстрактный контракт репозитория для сущности Article."""

    @abstractmethod
    def add(self, article: Article) -> None:
        """Сохранить новую или обновлённую сущность."""
        pass

    @abstractmethod
    def get_by_id(self, article_id: ArticleId) -> Optional[Article]:
        """Получить сущность по ID."""
        pass
