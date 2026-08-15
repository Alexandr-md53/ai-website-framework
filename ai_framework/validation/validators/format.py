"""
framework/validation/validators/format.py
------------------------------------------
Валидатор для проверки формата строк (email, url, regex).
"""

import re
from typing import Any, Dict, Optional

from ai_framework.validation.context import ValidationContext
from ai_framework.validation.validators.base import Validator


class FormatValidator(Validator):
    """Проверяет соответствие строки формату (email, url или регулярному выражению)."""

    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    URL_REGEX = re.compile(r"^https?://[^\s/$.?#].\S*$", re.IGNORECASE)

    def __init__(self, format_type: str, pattern: Optional[str] = None):
        self.format_type = format_type
        self.custom_regex = re.compile(pattern) if pattern else None

    async def validate(
        self,
        field: str,
        value: Any,
        payload: Dict[str, Any],
        context: Optional[ValidationContext] = None,
    ) -> Optional[Dict[str, Any]]:

        if value is None or not isinstance(value, str) or not value.strip():
            return None

        if self.format_type == "email":
            if not self.EMAIL_REGEX.match(value):
                return {
                    "field": field,
                    "message_key": "validation.invalid_email",
                    "params": {"value": value},
                }

        elif self.format_type == "url":
            if not self.URL_REGEX.match(value):
                return {
                    "field": field,
                    "message_key": "validation.invalid_url",
                    "params": {"value": value},
                }

        elif self.format_type == "regex" and self.custom_regex:
            if not self.custom_regex.match(value):
                return {
                    "field": field,
                    "message_key": "validation.regex_failed",
                    "params": {"pattern": self.custom_regex.pattern},
                }

        return None
