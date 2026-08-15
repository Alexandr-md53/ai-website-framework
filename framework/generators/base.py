"""
Base Content Generator Implementation for AI Website Framework.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from framework.ai.service import AIService
from framework.templates.engine import TemplateEngine
from framework.metadata.builder import MetadataBuilder
from framework.metadata.payload import PublicationPayload
from framework.core.exceptions import FrameworkError


class BaseGenerator(ABC):
    """
    Базовый абстрактный класс для всех генераторов контента.
    Автоматизирует цепочку: Данные -> Шаблонизация -> AI -> PublicationPayload.
    """

    def __init__(
        self, ai_service: AIService, template_engine: Optional[TemplateEngine] = None
    ):
        self.ai_service = ai_service
        self.template_engine = template_engine or TemplateEngine()

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Должен возвращать системный промпт (роль/инструкцию для AI).
        """
        pass

    @abstractmethod
    def get_user_prompt_template(self) -> str:
        """
        Должен возвращать шаблон пользовательского промпта с переменными {{ var }}.
        """
        pass

    def generate(self, context: Dict[str, Any]) -> PublicationPayload:
        """
        Главный метод запуска конвейера генерации.
        """
        try:
            # 1. Формируем итоговый промпт через шаблонизатор
            prompt_template = self.get_user_prompt_template()
            rendered_prompt = self.template_engine.render(prompt_template, context)

            # 2. Обращаемся к AI-сервису
            system_prompt = self.get_system_prompt()
            generated_text = self.ai_service.generate(
                prompt=rendered_prompt,
                system_prompt=system_prompt,
                options=context.get("ai_options"),
            )

            # 3. Собираем данные для создания PublicationPayload
            payload_data = {
                "id": context.get("id"),
                "title": context.get("title", "Без названия"),
                "text": generated_text,
                "image": context.get("image"),
                "image_required": context.get("image_required", False),
                "buttons": context.get("buttons", []),
                "metadata": context.get("metadata", {}),
            }

            # 4. Валидируем и возвращаем итоговый объект
            return MetadataBuilder.build_from_dict(payload_data)

        except Exception as err:
            raise FrameworkError(f"Сбой при выполнении генератора: {err}") from err
