"""
framework/validation/validators/length.py
------------------------------------------
Валидатор для проверки минимальной и максимальной длины значений (строк, списков и т.д.).
"""

from typing import Any, Dict, Optional

from ai_framework.validation.context import ValidationContext
from ai_framework.validation.validators.base import Validator


class LengthValidator(Validator):
    """Проверяет, попадает ли длина значения в диапазон [min_length, max_length]."""

    def __init__(
        self, min_length: Optional[int] = None, max_length: Optional[int] = None
    ):
        self.min_length = min_length
        self.max_length = max_length

    async def validate(
        self,
        field: str,
        value: Any,
        payload: Dict[str, Any],
        context: Optional[ValidationContext] = None,
    ) -> Optional[Dict[str, Any]]:

        if value is None:
            return None

        if not hasattr(value, "__len__"):
            return None  # Игнорируем типы без длины (за типы отвечает TypeValidator)

        actual_len = len(value)

        if self.min_length is not None and actual_len < self.min_length:
            return {
                "field": field,
                "message_key": "validation.too_short",
                "params": {"min_length": self.min_length, "actual": actual_len},
            }

        if self.max_length is not None and actual_len > self.max_length:
            return {
                "field": field,
                "message_key": "validation.too_long",
                "params": {"max_length": self.max_length, "actual": actual_len},
            }

        return None
