"""
Templates Engine implementation for AI Website Framework.
"""

import re
from typing import Dict, Any

from framework.core.exceptions import ValidationError
from framework.metadata.payload import PublicationPayload


class TemplateEngine:
    """
    Простой и безопасный движок шаблонизации.
    Заменяет конструкции {{ variable_name }} на значения из контекста.
    """

    @staticmethod
    def render(template_string: str, context: Dict[str, Any]) -> str:
        """
        Рендерит текстовый шаблон, подставляя значения из словаря context.
        """
        if not isinstance(template_string, str):
            raise ValidationError("Шаблон должен быть строковым значением.")

        rendered = template_string

        # Находим все переменные в формате {{ variable_name }}
        matches = re.findall(r"\{\{\s*(\w+)\s*\}\}", template_string)

        for var_name in matches:
            value = context.get(var_name, "")
            # Преобразуем сложные структуры (например, списки тегов) в строку
            if isinstance(value, list):
                value = ", ".join(map(str, value))
            elif value is None:
                value = ""

            rendered = re.sub(
                r"\{\{\s*" + re.escape(var_name) + r"\s*\}\}", str(value), rendered
            )

        return rendered

    @classmethod
    def render_payload(cls, template_string: str, payload: PublicationPayload) -> str:
        """
        Удобный метод-помощник: принимает напрямую объект PublicationPayload.
        """
        if not isinstance(payload, PublicationPayload):
            raise ValidationError("Переданный объект не является PublicationPayload.")

        context = payload.to_dict()
        # Извлекаем дополнительные поля из metadata на верхний уровень контекста
        if payload.metadata:
            context.update(payload.metadata)

        return cls.render(template_string, context)
