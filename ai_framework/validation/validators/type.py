"""
framework/validation/validators/type.py
----------------------------------------
Валидатор для проверки соответствия типа данных значения.
"""

from typing import Any, Dict, Optional, Type, Union

from ai_framework.validation.context import ValidationContext
from ai_framework.validation.validators.base import Validator


class TypeValidator(Validator):
    """Проверяет, соответствует ли значение указанному типу данных."""

    TYPE_MAP: Dict[str, Union[Type, tuple]] = {
        "string": str,
        "integer": int,
        "float": (int, float),
        "numeric": (int, float),
        "boolean": bool,
        "list": list,
        "dict": dict,
    }

    def __init__(self, expected_type: str):
        if expected_type not in self.TYPE_MAP:
            raise ValueError(f"Unsupported type check: {expected_type}")
        self.expected_type_name = expected_type
        self.expected_type = self.TYPE_MAP[expected_type]

    async def validate(
        self,
        field: str,
        value: Any,
        payload: Dict[str, Any],
        context: Optional[ValidationContext] = None,
    ) -> Optional[Dict[str, Any]]:

        # Пропускаем None (за проверку на None отвечает RequiredValidator)
        if value is None:
            return None

        # Отдельный кейс для bool vs int (в Python bool является подтипом int)
        if self.expected_type_name in ("integer", "float", "numeric") and isinstance(
            value, bool
        ):
            return {
                "field": field,
                "message_key": "validation.invalid_type",
                "params": {"expected": self.expected_type_name, "actual": "boolean"},
            }

        if not isinstance(value, self.expected_type):
            return {
                "field": field,
                "message_key": "validation.invalid_type",
                "params": {
                    "expected": self.expected_type_name,
                    "actual": type(value).__name__,
                },
            }

        return None
