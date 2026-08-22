import asyncio
from typing import Any, Optional

from ai_framework.domain.contracts.repositories import ArticleRepository
from ai_framework.domain.entities.article import Article, ArticleStatus
from ai_framework.domain.value_objects.article_id import ArticleId
from ai_framework.domain.value_objects.content import Content
from ai_framework.domain.value_objects.title import Title


def _run_sync(func, *args, **kwargs):
    """Synchronously execute an async CRUD engine method."""
    coro = func(*args, **kwargs)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as executor:
        return executor.submit(asyncio.run, coro).result()


class CRUDArticleRepository(ArticleRepository):
    """Infrastructure adapter for ArticleRepository using UniversalCRUDEngine."""

    RESOURCE_NAME = "article"

    def __init__(self, crud_engine: Any = None) -> None:
        self._crud_engine = crud_engine

    def add(self, article: Article) -> None:
        if self._crud_engine is None:
            return

        payload = {
            "id": article.id.value,
            "title": article.title.value,
            "content": article.content.value,
            "status": article.status.value,
        }

        existing = _run_sync(
            self._crud_engine.get,
            self.RESOURCE_NAME,
            article.id.value,
        )

        if existing.success:
            _run_sync(
                self._crud_engine.update,
                self.RESOURCE_NAME,
                article.id.value,
                payload,
            )
        else:
            _run_sync(
                self._crud_engine.create,
                self.RESOURCE_NAME,
                payload,
            )

    def get_by_id(self, article_id: ArticleId) -> Optional[Article]:
        if self._crud_engine is None:
            return None

        result = _run_sync(
            self._crud_engine.get,
            self.RESOURCE_NAME,
            article_id.value,
        )

        if not result.success or result.data is None:
            return None

        data = result.data

        return Article(
            id=ArticleId(data["id"]),
            title=Title(data["title"]),
            content=Content(data["content"]),
            status=ArticleStatus(data["status"]),
        )
