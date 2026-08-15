"""
framework/validation/validators/required.py
--------------------------------------------
Валидатор для проверки наличия и непустоты значения поля.
"""

from typing import Any, Dict, Optional

from ai_framework.validation.context import ValidationContext
from ai_framework.validation.validators.base import Validator


class RequiredValidator(Validator):
    """Проверяет, что значение поля передано и не является пустым."""

    async def validate(
        self,
        field: str,
        value: Any,
        payload: Dict[str, Any],
        context: Optional[ValidationContext] = None,
    ) -> Optional[Dict[str, Any]]:
        # Если значение вообще не передано (None)
        if value is None:
            return {"field": field, "message_key": "validation.required", "params": {}}

        # Если передана пустая строка или строка из одних пробелов
        if isinstance(value, str) and not value.strip():
            return {"field": field, "message_key": "validation.required", "params": {}}

        return None
