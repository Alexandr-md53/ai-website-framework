"""
Mock AI Provider implementation for unit testing (Stage 3.1).
"""

from typing import Sequence

from ai_framework.ai_provider.contracts import (
    AIError,
    AIProviderProtocol,
    AIRequest,
    AIResponse,
    ChatMessage,
    FinishReason,
    TokenUsage,
)


class MockAIProvider(AIProviderProtocol):
    """Тестовый провайдер, симулирующий генерацию ответов AI."""

    def __init__(
        self,
        default_response: str = "Тестовый ответ AI",
        responses: Sequence[str] | None = None,
        should_fail: bool = False,
        error_message: str = "Mock AI Error",
    ) -> None:
        self.default_response = default_response
        self._responses = list(responses) if responses else []
        self.should_fail = should_fail
        self.error_message = error_message
        self.history: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResponse:
        if self.should_fail:
            raise AIError(self.error_message)

        self.history.append(request)

        content = self._responses.pop(0) if self._responses else self.default_response

        prompt_tokens = self._count_tokens_for_messages(request.messages)
        completion_tokens = max(1, len(content.split()))
        total_tokens = prompt_tokens + completion_tokens

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        return AIResponse(
            content=content,
            finish_reason=FinishReason.STOP,
            usage=usage,
            raw_response={"mock": True},
        )

    def _count_tokens_for_messages(self, messages: Sequence[ChatMessage]) -> int:
        tokens = 0
        for msg in messages:
            tokens += max(1, len(msg.content.split()))
        return tokens
