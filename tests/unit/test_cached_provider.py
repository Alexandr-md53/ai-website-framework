"""
Unit tests for Cached AI Provider Wrapper and Storage (Stage 3.4) — TDD RED Phase.
Tests cache hit/miss behavior, SHA-256 key determinism, TTL expiration, and error exclusion.
"""

import time
import pytest

from ai_framework.ai_provider.contracts import (
    AIError,
    AIProviderProtocol,
    AIRequest,
    AIResponse,
    ChatMessage,
    FinishReason,
    Role,
    TokenUsage,
)
from ai_framework.ai_provider.mock import MockAIProvider
from ai_framework.ai_provider.cache import (
    CachedAIProvider,
    CacheStorageProtocol,
    InMemoryCache,
)


class TestInMemoryCacheStorage:
    """Тесты для базового хранилища InMemoryCache."""

    def test_implements_cache_storage_protocol(self):
        storage = InMemoryCache()
        assert isinstance(storage, CacheStorageProtocol)

    def test_set_and_get_value(self):
        storage = InMemoryCache()
        response = AIResponse(
            content="Cached text",
            finish_reason=FinishReason.STOP,
            usage=TokenUsage(5, 5, 10),
        )

        storage.set("test-key", response)
        cached = storage.get("test-key")

        assert cached is not None
        assert cached.content == "Cached text"

    def test_get_non_existent_key_returns_none(self):
        storage = InMemoryCache()
        assert storage.get("unknown-key") is None

    def test_ttl_expiration(self):
        storage = InMemoryCache()
        response = AIResponse(
            content="Expired soon",
            finish_reason=FinishReason.STOP,
            usage=TokenUsage(1, 1, 2),
        )

        # Устанавливаем TTL 0.05 секунды
        storage.set("short-lived-key", response, ttl=0.05)
        assert storage.get("short-lived-key") is not None

        time.sleep(0.06)
        assert storage.get("short-lived-key") is None

    def test_delete_and_clear(self):
        storage = InMemoryCache()
        resp = AIResponse("OK", FinishReason.STOP, TokenUsage(1, 1, 2))

        storage.set("k1", resp)
        storage.set("k2", resp)

        storage.delete("k1")
        assert storage.get("k1") is None
        assert storage.get("k2") is not None

        storage.clear()
        assert storage.get("k2") is None


class TestCachedAIProvider:
    """Тесты для декоратора CachedAIProvider."""

    def test_implements_ai_provider_protocol(self):
        primary = MockAIProvider()
        cached_provider = CachedAIProvider(provider=primary)
        assert isinstance(cached_provider, AIProviderProtocol)

    def test_cache_miss_then_hit(self):
        primary = MockAIProvider(default_response="Real AI Answer")
        cached_provider = CachedAIProvider(provider=primary)

        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Hello")],
            model="gpt-4o-mini",
            temperature=0.7,
        )

        # 1. Первая генерация — Cache MISS (вызывается внешний провайдер)
        resp1 = cached_provider.generate(request)
        assert resp1.content == "Real AI Answer"
        assert len(primary.history) == 1

        # 2. Вторая генерация — Cache HIT (внешний провайдер НЕ вызывается)
        resp2 = cached_provider.generate(request)
        assert resp2.content == "Real AI Answer"
        assert len(primary.history) == 1  # История вызовов не изменилась!

    def test_different_requests_produce_different_cache_keys(self):
        primary = MockAIProvider(responses=["Answer A", "Answer B"])
        cached_provider = CachedAIProvider(provider=primary)

        req1 = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Topic A")],
            model="gpt-4o-mini",
            temperature=0.7,
        )
        req2 = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Topic B")],
            model="gpt-4o-mini",
            temperature=0.7,
        )

        res1 = cached_provider.generate(req1)
        res2 = cached_provider.generate(req2)

        assert res1.content == "Answer A"
        assert res2.content == "Answer B"
        assert len(primary.history) == 2

    def test_errors_are_not_cached(self):
        primary = MockAIProvider(should_fail=True, error_message="API Outage")
        cached_provider = CachedAIProvider(provider=primary)

        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Test Error")],
            model="gpt-4o-mini",
        )

        # 1. Первый запрос падает
        with pytest.raises(AIError):
            cached_provider.generate(request)

        # Чиним провайдер
        primary.should_fail = False
        primary.default_response = "Recovered Answer"

        # 2. Второй запрос не должен брать ошибку из кэша, а должен заново обратиться к провайдеру
        resp = cached_provider.generate(request)
        assert resp.content == "Recovered Answer"
