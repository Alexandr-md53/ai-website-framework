"""
AI Provider Layer Contracts (Stage 3.1).
Defines abstract domain models, exceptions, prompt templating, and provider interface.
"""

from dataclasses import dataclass, field
from enum import Enum
import string
from typing import Any, Protocol, runtime_checkable


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    ERROR = "error"


class AIError(Exception):
    """Базовое исключение для ошибок AI Provider Layer."""

    pass


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class AIRequest:
    messages: list[ChatMessage]
    model: str
    temperature: float = 0.7
    max_tokens: int | None = None
    timeout: float | None = None  # Новое поле: таймаут на уровне конкретного запроса


@dataclass(frozen=True)
class AIResponse:
    content: str
    finish_reason: FinishReason
    usage: TokenUsage
    raw_response: dict[str, Any] | None = None


class PromptTemplate:
    """Шаблонизатор промптов с валидацией входных переменных."""

    def __init__(self, template: str) -> None:
        self.template = template
        self._formatter = string.Formatter()

    @property
    def variables(self) -> set[str]:
        """Возвращает набор плейсхолдеров, найденных в шаблоне."""
        parsed = self._formatter.parse(self.template)
        return {field_name for _, field_name, _, _ in parsed if field_name is not None}

    def render(self, **kwargs: Any) -> str:
        """
        Рендерит шаблон переданными переменными.
        Выбрасывает ValueError, если не хватает обязательных ключей.
        """
        missing = self.variables - kwargs.keys()
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise ValueError(
                f"Отсутствуют обязательные переменные для шаблона: {missing_str}"
            )

        # Выбираем только те переменные, которые присутствуют в шаблоне
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in self.variables}
        return self.template.format(**filtered_kwargs)

    def to_message(self, role: Role, **kwargs: Any) -> ChatMessage:
        """Рендерит шаблон и сразу возвращает объект ChatMessage."""
        content = self.render(**kwargs)
        return ChatMessage(role=role, content=content)


@runtime_checkable
class AIProviderProtocol(Protocol):
    """Протокол (интерфейс) для всех адаптеров AI-провайдеров."""

    def generate(self, request: AIRequest) -> AIResponse: ...
