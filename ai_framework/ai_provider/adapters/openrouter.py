"""
OpenRouter / OpenAI-compatible Provider Adapter (Stage 3.2).
Handles REST payload creation, HTTP communication via urllib, and error mapping.
"""

import json
import urllib.error
import urllib.request

from ai_framework.ai_provider.contracts import (
    AIError,
    AIProviderProtocol,
    AIRequest,
    AIResponse,
    FinishReason,
    TokenUsage,
)


class OpenRouterAdapter(AIProviderProtocol):
    """Адаптер для работы с OpenRouter и другими OpenAI-совместимыми REST API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1/chat/completions",
        site_url: str | None = None,
        site_name: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("API key не может быть пустым.")

        self.api_key = api_key
        self.base_url = base_url
        self.site_url = site_url
        self.site_name = site_name

    def generate(self, request: AIRequest) -> AIResponse:
        """Отправляет запрос к API и возвращает унифицированный AIResponse."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.site_name:
            headers["X-Title"] = self.site_name

        payload = {
            "model": request.model,
            "messages": [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.messages
            ],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=self.base_url,
            data=data_bytes,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as response:
                body = response.read().decode("utf-8")
                raw_data = json.loads(body)
                return self._parse_response(raw_data)

        except urllib.error.HTTPError as err:
            error_body = ""
            try:
                with err:
                    error_body = err.read().decode("utf-8")
            except Exception:
                pass
            raise AIError(f"HTTP Error {err.code}: {err.reason}. {error_body}") from err

        except urllib.error.URLError as err:
            raise AIError(f"Network connection error: {err.reason}") from err

        except Exception as err:
            raise AIError(f"Unexpected error during AI generation: {str(err)}") from err

    def _parse_response(self, raw_data: dict) -> AIResponse:
        """Преобразует JSON-ответ от API в доменную модель AIResponse."""
        try:
            choices = raw_data.get("choices", [])
            if not choices:
                raise AIError("Пустой ответ от AI-провайдера (нет choices).")

            first_choice = choices[0]
            content = first_choice.get("message", {}).get("content", "")

            raw_finish = first_choice.get("finish_reason", "stop")
            try:
                finish_reason = FinishReason(raw_finish)
            except ValueError:
                finish_reason = FinishReason.STOP

            usage_data = raw_data.get("usage", {})
            prompt_tokens = usage_data.get("prompt_tokens", 0)
            completion_tokens = usage_data.get("completion_tokens", 0)
            total_tokens = usage_data.get(
                "total_tokens", prompt_tokens + completion_tokens
            )

            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

            return AIResponse(
                content=content,
                finish_reason=finish_reason,
                usage=usage,
                raw_response=raw_data,
            )

        except (KeyError, TypeError) as err:
            raise AIError(f"Ошибка парсинга ответа AI: {err}") from err
