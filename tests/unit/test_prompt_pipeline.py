"""
Unit tests for Prompt Pipeline (Stage 4.1) — TDD RED Phase.
Tests message ordering, template variable validation, history truncation, and parameter overrides.
"""

import pytest

from ai_framework.ai_provider.contracts import (
    AIRequest,
    ChatMessage,
    Role,
)
from ai_framework.pipeline.exceptions import PromptError
from ai_framework.pipeline.prompt import PromptPipeline


class TestPromptPipeline:
    """Тестовый набор для проверки сборщика промптов (PromptPipeline)."""

    def test_builds_valid_ai_request_with_defaults(self):
        pipeline = (
            PromptPipeline(model="openai/gpt-4o-mini", temperature=0.7, timeout=10.0)
            .add_system_prompt("You are a helpful assistant for {domain}.")
            .add_user_prompt("How do I care for {plant}?")
        )

        request = pipeline.build(context={"domain": "botany", "plant": "Monstera"})

        assert isinstance(request, AIRequest)
        assert request.model == "openai/gpt-4o-mini"
        assert request.temperature == 0.7
        assert request.timeout == 10.0
        assert len(request.messages) == 2
        assert request.messages[0].role == Role.SYSTEM
        assert request.messages[0].content == "You are a helpful assistant for botany."
        assert request.messages[1].role == Role.USER
        assert request.messages[1].content == "How do I care for Monstera?"

    def test_missing_variable_raises_prompt_error(self):
        pipeline = PromptPipeline(model="gpt-4o-mini").add_system_prompt(
            "Target domain: {domain}, role: {role}"
        )

        with pytest.raises(PromptError) as exc_info:
            pipeline.build(context={"domain": "finance"})  # 'role' отсутствует

        assert "role" in str(exc_info.value)

    def test_strict_message_ordering(self):
        # Порядок: SYSTEM -> CONTEXT/FEW-SHOT -> HISTORY -> USER
        pipeline = (
            PromptPipeline(model="gpt-4o-mini")
            .add_system_prompt("System instruction")
            .add_context_message("Reference context: {doc}")
            .add_history_injector(max_history_messages=10)
            .add_user_prompt("User query: {query}")
        )

        history = [
            ChatMessage(role=Role.USER, content="Prev Q"),
            ChatMessage(role=Role.ASSISTANT, content="Prev A"),
        ]

        request = pipeline.build(
            context={
                "doc": "Plant Manual",
                "query": "Watering schedule?",
                "history": history,
            }
        )

        messages = request.messages
        assert len(messages) == 5

        # 1. System
        assert messages[0].role == Role.SYSTEM
        assert messages[0].content == "System instruction"

        # 2. Context / Few-shot
        assert (
            messages[1].role == Role.SYSTEM
        )  # или Role.USER в зависимости от контекста
        assert messages[1].content == "Reference context: Plant Manual"

        # 3. History
        assert messages[2].content == "Prev Q"
        assert messages[3].content == "Prev A"

        # 4. User
        assert messages[4].role == Role.USER
        assert messages[4].content == "User query: Watering schedule?"

    def test_history_truncation_with_max_messages(self):
        pipeline = PromptPipeline(model="gpt-4o-mini").add_history_injector(
            max_history_messages=2
        )

        history = [
            ChatMessage(role=Role.USER, content="Msg 1"),
            ChatMessage(role=Role.ASSISTANT, content="Msg 2"),
            ChatMessage(role=Role.USER, content="Msg 3"),
            ChatMessage(role=Role.ASSISTANT, content="Msg 4"),
        ]

        request = pipeline.build(context={"history": history})

        # Должны остаться только 2 последних сообщения из истории (Msg 3 и Msg 4)
        assert len(request.messages) == 2
        assert request.messages[0].content == "Msg 3"
        assert request.messages[1].content == "Msg 4"

    def test_optional_history_omitted_when_absent(self):
        pipeline = (
            PromptPipeline(model="gpt-4o-mini")
            .add_system_prompt("System Prompt")
            .add_history_injector(max_history_messages=5)
            .add_user_prompt("User Prompt")
        )

        # Контекст без поля 'history'
        request = pipeline.build(context={})

        assert len(request.messages) == 2
        assert request.messages[0].content == "System Prompt"
        assert request.messages[1].content == "User Prompt"

    def test_build_parameter_overrides(self):
        pipeline = PromptPipeline(
            model="default-model",
            temperature=0.5,
            max_tokens=100,
            timeout=5.0,
        ).add_user_prompt("Test")

        # Переопределяем параметры прямо при сборке
        request = pipeline.build(
            context={},
            temperature=0.9,
            max_tokens=500,
            timeout=30.0,
        )

        assert request.temperature == 0.9
        assert request.max_tokens == 500
        assert request.timeout == 30.0
        assert request.model == "default-model"
