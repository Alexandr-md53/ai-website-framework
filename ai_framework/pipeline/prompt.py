"""
Prompt Pipeline Builder (Stage 4.1).
Provides fluent API for constructing validated AIRequests with strict role ordering and history injection.
"""

from typing import Any

from ai_framework.ai_provider.contracts import (
    AIRequest,
    ChatMessage,
    Role,
)
from ai_framework.pipeline.contracts import PipelineStep
from ai_framework.pipeline.exceptions import PromptError


class PromptPipeline:
    """Сборщик и валидатор AIRequest на основе шаблонов промптов и контекста."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._steps: list[PipelineStep] = []

    def add_system_prompt(self, template: str) -> "PromptPipeline":
        """Добавляет системное сообщение в начало цепочки."""
        self._steps.append(
            PipelineStep(kind="system", template=template, role=Role.SYSTEM)
        )
        return self

    def add_context_message(
        self, template: str, role: Role = Role.SYSTEM
    ) -> "PromptPipeline":
        """Добавляет контекст или few-shot пример после системного сообщения."""
        self._steps.append(PipelineStep(kind="context", template=template, role=role))
        return self

    def add_history_injector(
        self, max_history_messages: int = 10
    ) -> "PromptPipeline":
        """Добавляет инжектор истории диалога перед сообщением пользователя."""
        self._steps.append(
            PipelineStep(
                kind="history", max_history_messages=max_history_messages
            )
        )
        return self

    def add_user_prompt(self, template: str) -> "PromptPipeline":
        """Добавляет пользовательское сообщение в конец цепочки."""
        self._steps.append(
            PipelineStep(kind="user", template=template, role=Role.USER)
        )
        return self

    def build(
        self,
        context: dict[str, Any],
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> AIRequest:
        """
        Собирает и рендерит итоговый AIRequest на основе переданного контекста.
        Выбрасывает PromptError при отсутствии необходимых переменных.
        """
        messages: list[ChatMessage] = []

        for step in self._steps:
            if step.kind in ("system", "context", "user"):
                if step.template is None:
                    continue
                rendered_text = self._render_template(step.template, context)
                messages.append(ChatMessage(role=step.role, content=rendered_text))

            elif step.kind == "history":
                raw_history = context.get("history")
                if raw_history and isinstance(raw_history, list):
                    limit = step.max_history_messages or len(raw_history)
                    truncated_history = raw_history[-limit:]
                    for msg in truncated_history:
                        if isinstance(msg, ChatMessage):
                            messages.append(msg)

        eff_temperature = (
            temperature if temperature is not None else self.temperature
        )
        eff_max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        eff_timeout = timeout if timeout is not None else self.timeout

        return AIRequest(
            messages=messages,
            model=self.model,
            temperature=eff_temperature,
            max_tokens=eff_max_tokens,
            timeout=eff_timeout,
        )

    def _render_template(self, template: str, context: dict[str, Any]) -> str:
        """Форматирует шаблон контекстом и выбрасывает PromptError при отсутствии ключа."""
        try:
            return template.format(**context)
        except KeyError as err:
            missing_key = str(err).strip("'\"")
            raise PromptError(
                f"Отсутствует обязательная переменная '{missing_key}' для шаблона промпта."
            ) from err