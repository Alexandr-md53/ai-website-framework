"""
Unit tests for OpenRouter/OpenAI Adapter (Stage 3.2) — TDD RED Phase.
Tests payload formatting, HTTP handling, response parsing, and error mapping.
"""

from unittest.mock import MagicMock, patch

import pytest

from ai_framework.ai_provider.adapters.openrouter import OpenRouterAdapter
from ai_framework.ai_provider.contracts import (
    AIError,
    AIProviderProtocol,
    AIRequest,
    AIResponse,
    ChatMessage,
    FinishReason,
    Role,
)


class TestOpenRouterAdapter:
    """Тесты для OpenRouterAdapter: трансформация запроса, парсинг ответа и обработка HTTP-ошибок."""

    def test_implements_ai_provider_protocol(self):
        adapter = OpenRouterAdapter(api_key="test-key")
        assert isinstance(adapter, AIProviderProtocol)

    @patch("urllib.request.urlopen")
    def test_successful_request_formatting_and_parsing(self, mock_urlopen):
        # Настройка mock HTTP-ответа от OpenRouter
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"""{
            "choices": [
                {
                    "message": {"content": "Hello from OpenRouter!"},
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }"""
        mock_urlopen.return_value.__enter__.return_value = mock_response

        adapter = OpenRouterAdapter(api_key="sk-or-v1-testkey")
        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Hi")],
            model="openai/gpt-4o-mini",
            temperature=0.5,
        )

        response = adapter.generate(request)

        assert isinstance(response, AIResponse)
        assert response.content == "Hello from OpenRouter!"
        assert response.finish_reason == FinishReason.STOP
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5
        assert response.usage.total_tokens == 15

    @patch("urllib.request.urlopen")
    def test_http_error_mapped_to_ai_error(self, mock_urlopen):
        import io
        import urllib.error

        err_fp = io.BytesIO(b"Unauthorized")
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=err_fp,
        )

        adapter = OpenRouterAdapter(api_key="invalid-key")
        request = AIRequest(
            messages=[ChatMessage(role=Role.USER, content="Test")],
            model="openai/gpt-4o-mini",
        )

        with pytest.raises(AIError) as exc_info:
            adapter.generate(request)

        assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)

    def test_missing_api_key_raises_value_error(self):
        with pytest.raises(ValueError):
            OpenRouterAdapter(api_key="")
