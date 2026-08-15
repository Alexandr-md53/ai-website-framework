"""
Structured Output Parser for AI Responses (Stage 4.2).
Extracts JSON from response text, validates against schema or ValidationEngine, and handles parsing errors.
"""

import json
import re
from typing import Any

from ai_framework.pipeline.exceptions import OutputParseError
from ai_framework.validation.exceptions import ValidationException


class StructuredOutputParser:
    """Парсер структурированных JSON-ответов AI с интеграцией валидации."""

    def __init__(
        self,
        schema: dict[str, Any] | None = None,
        validation_engine: Any | None = None,
        entity_type: str | None = None,
    ) -> None:
        self.schema = schema or {}
        self.validation_engine = validation_engine
        self.entity_type = entity_type

    def parse(self, response_text: str) -> dict[str, Any]:
        """
        Извлекает JSON из текста, парсит его и валидирует по схеме или через ValidationEngine.
        При ошибке форматирования или несоответствии схеме выбрасывает OutputParseError.
        """
        cleaned_json_str = self._extract_json_string(response_text)

        try:
            data = json.loads(cleaned_json_str)
        except json.JSONDecodeError as err:
            raise OutputParseError(
                f"Invalid JSON format in AI response: {err}"
            ) from err

        if not isinstance(data, dict):
            raise OutputParseError("Extracted JSON must be an object/dict.")

        self._validate_data(data)
        return data

    def _validate_data(self, data: dict[str, Any]) -> None:
        """Проверяет данные через ValidationEngine или встроенную валидацию схемы."""
        if self.validation_engine and self.entity_type:
            try:
                result = self.validation_engine.validate(self.entity_type, data)
                if hasattr(result, "is_valid") and not result.is_valid:
                    errors = getattr(result, "errors", [])
                    raise OutputParseError(f"Schema validation failed: {errors}")
            except ValidationException as err:
                raise OutputParseError(f"Schema validation failed: {err}") from err

        if self.schema:
            required = self.schema.get("required", [])
            for field in required:
                if field not in data:
                    raise OutputParseError(
                        f"Schema validation failed: Missing required field '{field}'"
                    )

            properties = self.schema.get("properties", {})
            for field, spec in properties.items():
                if field in data and "type" in spec:
                    expected_type = spec["type"]
                    val = data[field]
                    if expected_type == "string" and not isinstance(val, str):
                        raise OutputParseError(
                            f"Schema validation failed: Field '{field}' must be a string."
                        )
                    elif expected_type in ("number", "integer") and not isinstance(
                        val, (int, float)
                    ):
                        raise OutputParseError(
                            f"Schema validation failed: Field '{field}' must be a number."
                        )
                    elif expected_type == "array" and not isinstance(val, list):
                        raise OutputParseError(
                            f"Schema validation failed: Field '{field}' must be an array."
                        )

    def _extract_json_string(self, text: str) -> str:
        """
        Извлекает JSON-блок из Markdown-тегов ```json ... ```
        или ищет первый подходящий JSON-объект { ... }.
        """
        json_code_block = re.search(
            r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL
        )
        if json_code_block:
            return json_code_block.group(1).strip()

        curly_brackets_block = re.search(r"(\{.*\})", text, re.DOTALL)
        if curly_brackets_block:
            return curly_brackets_block.group(1).strip()

        return text.strip()
