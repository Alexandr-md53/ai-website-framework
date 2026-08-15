"""
Unit tests for AIService Orchestrator (Stage 4.3) — TDD RED Phase.
Tests orchestration between PromptPipeline, AIProvider, and StructuredOutputParser.
"""

from unittest.mock import MagicMock
import pytest

from ai_framework.ai_provider.contracts import (
    AIError,
    AIRequest,
    AIResponse,
    FinishReason,
    TokenUsage,
)
from ai_framework.pipeline.exceptions import OutputParseError, PromptError
from ai_framework.pipeline.service import AIService


class TestAIService:
    """Тестовый набор для оркестратора AIService."""

    @pytest.fixture
    def sample_usage(self) -> TokenUsage:
        return TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20)

    def test_execute_orchestrates_pipeline_and_provider_without_parser(
        self, sample_usage
    ):
        mock_pipeline = MagicMock()
        mock_provider = MagicMock()

        fake_request = AIRequest(messages=[], model="openai/gpt-4o-mini")
        fake_response = AIResponse(
            content="Raw AI response",
            finish_reason=FinishReason.STOP,
            usage=sample_usage,
            raw_response={},
        )

        mock_pipeline.build.return_value = fake_request
        mock_provider.complete.return_value = fake_response

        service = AIService(provider=mock_provider, pipeline=mock_pipeline)
        result = service.execute(context={"user_input": "hello"})

        mock_pipeline.build.assert_called_once_with({"user_input": "hello"})
        mock_provider.complete.assert_called_once_with(fake_request)
        assert result == "Raw AI response"

    def test_execute_with_parser_returns_structured_data(self, sample_usage):
        mock_pipeline = MagicMock()
        mock_provider = MagicMock()
        mock_parser = MagicMock()

        fake_request = AIRequest(messages=[], model="openai/gpt-4o-mini")
        fake_response = AIResponse(
            content='{"key": "value"}',
            finish_reason=FinishReason.STOP,
            usage=sample_usage,
            raw_response={},
        )

        mock_pipeline.build.return_value = fake_request
        mock_provider.complete.return_value = fake_response
        mock_parser.parse.return_value = {"key": "value"}

        service = AIService(
            provider=mock_provider,
            pipeline=mock_pipeline,
            parser=mock_parser,
        )
        result = service.execute(context={})

        mock_parser.parse.assert_called_once_with('{"key": "value"}')
        assert result == {"key": "value"}

    def test_passes_overrides_to_pipeline_build(self, sample_usage):
        mock_pipeline = MagicMock()
        mock_provider = MagicMock()

        mock_pipeline.build.return_value = AIRequest(
            messages=[], model="openai/gpt-4o-mini"
        )
        mock_provider.complete.return_value = AIResponse(
            content="ok",
            finish_reason=FinishReason.STOP,
            usage=sample_usage,
            raw_response={},
        )

        service = AIService(provider=mock_provider, pipeline=mock_pipeline)
        service.execute(context={}, temperature=0.2, timeout=15.0)

        mock_pipeline.build.assert_called_once_with({}, temperature=0.2, timeout=15.0)

    def test_transparently_raises_prompt_error(self):
        mock_pipeline = MagicMock()
        mock_provider = MagicMock()

        mock_pipeline.build.side_effect = PromptError("Missing key 'domain'")

        service = AIService(provider=mock_provider, pipeline=mock_pipeline)

        with pytest.raises(PromptError) as exc_info:
            service.execute(context={})

        assert "Missing key 'domain'" in str(exc_info.value)

    def test_transparently_raises_ai_error(self):
        mock_pipeline = MagicMock()
        mock_provider = MagicMock()

        mock_pipeline.build.return_value = AIRequest(
            messages=[], model="openai/gpt-4o-mini"
        )
        mock_provider.complete.side_effect = AIError("Provider API unavailable")

        service = AIService(provider=mock_provider, pipeline=mock_pipeline)

        with pytest.raises(AIError) as exc_info:
            service.execute(context={})

        assert "Provider API unavailable" in str(exc_info.value)

    def test_transparently_raises_output_parse_error(self, sample_usage):
        mock_pipeline = MagicMock()
        mock_provider = MagicMock()
        mock_parser = MagicMock()

        mock_pipeline.build.return_value = AIRequest(
            messages=[], model="openai/gpt-4o-mini"
        )
        mock_provider.complete.return_value = AIResponse(
            content="invalid json",
            finish_reason=FinishReason.STOP,
            usage=sample_usage,
            raw_response={},
        )
        mock_parser.parse.side_effect = OutputParseError("Invalid JSON format")

        service = AIService(
            provider=mock_provider,
            pipeline=mock_pipeline,
            parser=mock_parser,
        )

        with pytest.raises(OutputParseError) as exc_info:
            service.execute(context={})

        assert "Invalid JSON format" in str(exc_info.value)
