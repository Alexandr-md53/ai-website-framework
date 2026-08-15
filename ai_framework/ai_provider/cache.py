"""
AI Caching Layer (Stage 3.4).
Provides deterministic SHA-256 cache key calculation, TTL expiration, and storage protocols.
"""

import hashlib
import time
from typing import Any, Protocol, runtime_checkable

from ai_framework.ai_provider.contracts import (
    AIProviderProtocol,
    AIRequest,
    AIResponse,
)


@runtime_checkable
class CacheStorageProtocol(Protocol):
    """Протокол для реализации хранилищ кэша (InMemory, Redis, DB и т. д.)."""

    def get(self, key: str) -> AIResponse | None: ...

    def set(self, key: str, value: AIResponse, ttl: float | None = None) -> None: ...

    def delete(self, key: str) -> None: ...

    def clear(self) -> None: ...


class InMemoryCache(CacheStorageProtocol):
    """In-Memory хранилище кэша с поддержкой TTL."""

    def __init__(self) -> None:
        # Храним словарь {key: (AIResponse, expire_at_timestamp | None)}
        self._store: dict[str, tuple[AIResponse, float | None]] = {}

    def get(self, key: str) -> AIResponse | None:
        if key not in self._store:
            return None

        response, expire_at = self._store[key]
        if expire_at is not None and time.monotonic() > expire_at:
            del self._store[key]
            return None

        return response

    def set(self, key: str, value: AIResponse, ttl: float | None = None) -> None:
        expire_at = (time.monotonic() + ttl) if ttl is not None else None
        self._store[key] = (value, expire_at)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


class CachedAIProvider(AIProviderProtocol):
    """Декоратор для кэширования ответов AI-провайдера."""

    def __init__(
        self,
        provider: AIProviderProtocol,
        storage: CacheStorageProtocol | None = None,
        default_ttl: float | None = None,
    ) -> None:
        self.provider = provider
        self.storage = storage if storage is not None else InMemoryCache()
        self.default_ttl = default_ttl

    def generate(self, request: AIRequest) -> AIResponse:
        """
        Генерирует ответ, используя кэш при наличии совпадения.
        При ошибках провайдера ничего не сохраняет в кэш.
        """
        cache_key = self._compute_cache_key(request)

        cached_response = self.storage.get(cache_key)
        if cached_response is not None:
            return cached_response

        # Cache MISS: обращаемся к провайдеру
        response = self.provider.generate(request)

        # Сохраняем в кэш только успешный ответ
        self.storage.set(cache_key, response, ttl=self.default_ttl)
        return response

    def _compute_cache_key(self, request: AIRequest) -> str:
        """
        Формирует детерминированный SHA-256 хэш на основе model, temperature и messages.
        """
        messages_str = "|".join(
            f"{msg.role.value}:{msg.content}" for msg in request.messages
        )
        raw_key = f"{request.model}|{request.temperature}|{messages_str}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
