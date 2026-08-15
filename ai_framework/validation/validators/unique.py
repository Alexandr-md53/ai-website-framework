"""
framework/validation/validators/unique.py
------------------------------------------
Валидатор для проверки уникальности значения поля в базе данных / хранилище.
"""

from typing import Any, Dict, Optional

from ai_framework.validation.context import ValidationContext
from ai_framework.validation.validators.base import Validator


class UniquenessValidator(Validator):
    """Проверяет, является ли значение поля уникальным в рамках сущности."""

    def __init__(self, entity_name: str, field_name: Optional[str] = None):
        self.entity_name = entity_name
        self.field_name = field_name  # Если None, используется имя проверяемого поля

    async def validate(
        self,
        field: str,
        value: Any,
        payload: Dict[str, Any],
        context: Optional[ValidationContext] = None,
    ) -> Optional[Dict[str, Any]]:

        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        if not context or not context.persistence_provider:
            # Если провайдер не передан в контексте, пропускаем проверку уникальности
            return None

        target_field = self.field_name or field
        exclude_id = payload.get(
            "id"
        )  # Чтобы при обновлении сущности не считать ошибкой совпадение с собственным ID

        is_unique = await context.persistence_provider.is_unique(
            entity_name=self.entity_name,
            field_name=target_field,
            value=value,
            exclude_id=exclude_id,
        )

        if not is_unique:
            return {
                "field": field,
                "message_key": "validation.not_unique",
                "params": {"value": value, "entity": self.entity_name},
            }

        return None
