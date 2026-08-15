"""
framework/validation/validators/slug.py
----------------------------------------
Валидатор для проверки формата URL-слагов (slug) и их уникальности в хранилище.
"""

import re
from typing import Any, Dict, Optional

from ai_framework.validation.context import ValidationContext
from ai_framework.validation.validators.base import Validator


class SlugValidator(Validator):
    """Проверяет формат slug (например, 'my-page-title') и его уникальность."""

    SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def __init__(self, entity_name: Optional[str] = None):
        self.entity_name = entity_name

    async def validate(
        self,
        field: str,
        value: Any,
        payload: Dict[str, Any],
        context: Optional[ValidationContext] = None,
    ) -> Optional[Dict[str, Any]]:

        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        # Фаза 1: Проверка синтаксического формата slug
        if not isinstance(value, str) or not self.SLUG_REGEX.match(value):
            return {
                "field": field,
                "message_key": "validation.invalid_slug_format",
                "params": {"value": value},
            }

        # Фаза 2: Проверка уникальности slug через контекст
        if context and context.persistence_provider and self.entity_name:
            is_unique = await context.persistence_provider.is_unique(
                entity_name=self.entity_name,
                field_name=field,
                value=value,
                exclude_id=payload.get("id"),
            )

            if not is_unique:
                return {
                    "field": field,
                    "message_key": "validation.slug_taken",
                    "params": {"slug": value},
                }

        return None
