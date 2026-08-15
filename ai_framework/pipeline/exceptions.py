"""
Exceptions for AI Pipeline Stage 4.
Isolated from Stage 3 Provider errors.
"""


class PromptError(Exception):
    """Выбрасывается при ошибках формирования промпта (отсутствие переменных контекста и т. д.)."""

    pass


class OutputParseError(PromptError):
    """Выбрасывается при ошибках парсинга и валидации структурированного ответа AI."""

    pass
