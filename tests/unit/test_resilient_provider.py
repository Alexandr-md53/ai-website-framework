"""
Unit tests for Resilient AI Provider Wrapper (Stage 3.3) — TDD RED Phase.
Tests symmetric retries, timeout resolution priority, and immediate error propagation.
"""

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
from ai_framework.ai_provider.resilient import ResilientProvider


class CountingFailingProvider(AIProviderProtocol):
    """Тестовый провайдер, который падает с AIError заданное количество раз."""

    def __init__(self, fail_count: int, error_msg: str = "Failure") -> None:
        self.fail_count = fail_count
        self.attempts = 0
        self.error_msg = error_msg

    def generate(self, request: AIRequest) -> AIResponse:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise AIError(f"{self.error_msg} (Attempt {self.attempts})")

        return AIResponse(
            content=f"Success on attempt {self.attempts}",
            finish_reason=FinishReason.STOP,
            usage=TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10),
        )


class FatalErrorProvider(AIProviderProtocol):
    """Тестовый провайдер, выбрасывающий фатальное исключение (ValueError)."""

    def __init__(self) -> None:
        self.attempts = 0

    def generate(self, request: AIRequest) -> AIResponse:
        self.attempts += 1
        raise ValueError("Invalid client argument")


class TestResilientProvider:
    """Тесты для ResilientProvider в соответствии зафиксированной спецификацией."""

    def test_implements_ai_provider_protocol(self):
        primary = MockAIProvider()
        resilient = ResilientProvider(primary=primary)
        assert isinstance(resilient, AIProviderProtocol)

    def test_primary_succeeds_first_try(self):
        primary = MockAIProvider(default_response="Primary OK")
        resilient = ResilientProvider(primary=primary)

        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Hello")],
            model="mock-model",
        )
        response = resilient.generate(request)

        assert response.content == "Primary OK"
        assert len(primary.history) == 1

    def test_primary_retries_up_to_max_retries(self):
        # Падает 2 раза, на 3-й успешный запрос при max_retries=3
        primary = CountingFailingProvider(fail_count=2, error_msg="Primary Error")
        resilient = ResilientProvider(
            primary=primary, max_retries=3, backoff_factor=0.0
        )

        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Test Retry")],
            model="mock-model",
        )
        response = resilient.generate(request)

        assert response.content == "Success on attempt 3"
        assert primary.attempts == 3

    def test_symmetric_fallback_retries(self):
        # Primary падает постоянно (исчерпает ровно 2 попытки)
        # Fallback падает 1 раз, на 2-ю попытку выдает результат (успевает в свои 2 попытки)
        primary = CountingFailingProvider(fail_count=99, error_msg="Primary Dead")
        fallback = CountingFailingProvider(fail_count=1, error_msg="Fallback Retry")

        resilient = ResilientProvider(
            primary=primary,
            fallback=fallback,
            max_retries=2,
            backoff_factor=0.0,
        )

        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Fallback Test")],
            model="mock-model",
        )
        response = resilient.generate(request)

        assert response.content == "Success on attempt 2"
        assert primary.attempts == 2
        assert fallback.attempts == 2

    def test_all_retries_exhausted_raises_ai_error(self):
        primary = CountingFailingProvider(fail_count=99, error_msg="Primary Dead")
        fallback = CountingFailingProvider(fail_count=99, error_msg="Fallback Dead")

        resilient = ResilientProvider(
            primary=primary,
            fallback=fallback,
            max_retries=2,
            backoff_factor=0.0,
        )

        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="All Fail")],
            model="mock-model",
        )

        with pytest.raises(AIError) as exc_info:
            resilient.generate(request)

        assert "Fallback Dead" in str(exc_info.value) or "Primary Dead" in str(
            exc_info.value
        )
        assert primary.attempts == 2
        assert fallback.attempts == 2

    def test_fatal_exception_bypasses_retry_immediately(self):
        primary = FatalErrorProvider()
        resilient = ResilientProvider(primary=primary, max_retries=3)

        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Fatal Test")],
            model="mock-model",
        )

        with pytest.raises(ValueError) as exc_info:
            resilient.generate(request)

        assert "Invalid client argument" in str(exc_info.value)
        assert primary.attempts == 1  # Без повторов при ValueError

    def test_timeout_priority_resolution(self):
        class CaptureTimeoutProvider(AIProviderProtocol):
            def __init__(self) -> None:
                self.received_timeout = None

            def generate(self, request: AIRequest) -> AIResponse:
                self.received_timeout = request.timeout
                return AIResponse(
                    content="OK",
                    finish_reason=FinishReason.STOP,
                    usage=TokenUsage(1, 1, 2),
                )

        provider = CaptureTimeoutProvider()
        resilient = ResilientProvider(primary=provider, timeout=10.0)

        # 1. Запрос со своим timeout переопределяет дефолт
        req1 = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Hi")],
            model="m",
            timeout=2.5,
        )
        resilient.generate(req1)
        assert provider.received_timeout == 2.5

        # 2. Запрос с timeout=None берет значение из ResilientProvider
        req2 = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Hi")],
            model="m",
            timeout=None,
        )
        resilient.generate(req2)
        assert provider.received_timeout == 10.0
