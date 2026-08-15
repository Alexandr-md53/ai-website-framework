"""
Unit tests for AI Provider Layer (Stage 3.1) — TDD RED Phase.
Covers PromptTemplate validation/rendering and MockAIProvider behavior.
"""

import pytest

from ai_framework.ai_provider.contracts import (
    AIError,
    AIProviderProtocol,
    AIRequest,
    AIResponse,
    ChatMessage,
    FinishReason,
    PromptTemplate,
    Role,
    TokenUsage,
)
from ai_framework.ai_provider.mock import MockAIProvider


class TestPromptTemplate:
    """Тесты для PromptTemplate: автоматическое извлечение переменных, рендеринг и валидация."""

    def test_extract_variables_from_template(self):
        template_str = "Привет, {name}! Твоя роль: {role}."
        template = PromptTemplate(template_str)

        assert set(template.variables) == {"name", "role"}

    def test_successful_render(self):
        template_str = "Запрос от пользователя {user}: {query}"
        template = PromptTemplate(template_str)
        rendered = template.render(user="Alex", query="Расскажи про TDD")

        assert rendered == "Запрос от пользователя Alex: Расскажи про TDD"

    def test_missing_variable_raises_value_error(self):
        template_str = "Привет, {name}! Ваш баланс: {balance}"
        template = PromptTemplate(template_str)

        with pytest.raises(ValueError) as exc_info:
            template.render(name="Alex")

        assert "balance" in str(exc_info.value)

    def test_extra_variables_ignored_or_handled(self):
        template_str = "Тема: {topic}"
        template = PromptTemplate(template_str)
        rendered = template.render(topic="Python", unused_var="test")

        assert rendered == "Тема: Python"

    def test_to_chat_message(self):
        template = PromptTemplate("Системная инструкция: {instruction}")
        msg = template.to_message(role=Role.SYSTEM, instruction="Будь лаконичен")

        assert isinstance(msg, ChatMessage)
        assert msg.role == Role.SYSTEM
        assert msg.content == "Системная инструкция: Будь лаконичен"


class TestMockAIProvider:
    """Тесты для MockAIProvider: генерация, симуляция ошибок, очереди ответов и учет токенов."""

    def test_mock_provider_implements_protocol(self):
        provider = MockAIProvider()
        assert isinstance(provider, AIProviderProtocol)

    def test_successful_default_generation(self):
        provider = MockAIProvider(default_response="Тестовый ответ AI")
        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Привет")],
            model="mock-model",
        )

        response = provider.generate(request)

        assert isinstance(response, AIResponse)
        assert response.content == "Тестовый ответ AI"
        assert response.finish_reason == FinishReason.STOP
        assert response.usage.prompt_tokens > 0
        assert response.usage.completion_tokens > 0
        assert (
            response.usage.total_tokens
            == response.usage.prompt_tokens + response.usage.completion_tokens
        )

    def test_mock_provider_tracks_history(self):
        provider = MockAIProvider()
        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Запрос 1")],
            model="mock-model",
        )

        assert len(provider.history) == 0
        provider.generate(request)
        assert len(provider.history) == 1
        assert provider.history[0] == request

    def test_mock_provider_emulates_ai_error(self):
        provider = MockAIProvider(should_fail=True, error_message="API Rate Limit")
        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Привет")],
            model="mock-model",
        )

        with pytest.raises(AIError) as exc_info:
            provider.generate(request)

        assert "API Rate Limit" in str(exc_info.value)

    def test_mock_provider_canned_responses_queue(self):
        provider = MockAIProvider(responses=["Ответ 1", "Ответ 2"])
        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Тест")],
            model="mock-model",
        )

        res1 = provider.generate(request)
        res2 = provider.generate(request)

        assert res1.content == "Ответ 1"
        assert res2.content == "Ответ 2"

    def test_mock_provider_calculates_tokens(self):
        provider = MockAIProvider()
        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Hello World")],
            model="mock-model",
        )

        response = provider.generate(request)
        assert response.usage.total_tokens > 0
