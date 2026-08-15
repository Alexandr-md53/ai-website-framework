"""
AI Service Orchestrator (Stage 4.3).
Coordinates PromptPipeline, AIProvider, and StructuredOutputParser.
"""

from typing import Any

from ai_framework.ai_provider.contracts import AIProviderProtocol
from ai_framework.pipeline.parser import StructuredOutputParser
from ai_framework.pipeline.prompt import PromptPipeline


class AIService:
    """Оркестратор взаимодействия между Pipeline, Provider и Parser."""

    def __init__(
        self,
        provider: AIProviderProtocol,
        pipeline: PromptPipeline,
        parser: StructuredOutputParser | None = None,
    ) -> None:
        self.provider = provider
        self.pipeline = pipeline
        self.parser = parser

    def execute(
        self, context: dict[str, Any], **overrides: Any
    ) -> dict[str, Any] | str:
        """
        Собирает AIRequest, вызывает провайдер и опционально парсит результат.
        Исключения (PromptError, AIError, OutputParseError) пропускаются наверх как есть.
        """
        request = self.pipeline.build(context, **overrides)
        response = self.provider.complete(request)

        if self.parser is not None:
            return self.parser.parse(response.content)

        return response.content
