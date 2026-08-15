"""
Unit tests for Structured Output Parser (Stage 4.2) — TDD RED Phase.
Tests JSON block extraction, Markdown cleanup, SchemaValidator integration, and OutputParseError wrapping.
"""

import pytest

from ai_framework.pipeline.exceptions import OutputParseError, PromptError
from ai_framework.pipeline.parser import StructuredOutputParser


class TestStructuredOutputParser:
    """Тесты для парсера структурированных ответов AI."""

    @pytest.fixture
    def sample_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "confidence": {"type": "number"},
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["summary", "confidence"],
        }

    def test_parse_clean_json_string(self, sample_schema):
        parser = StructuredOutputParser(schema=sample_schema)
        raw_response = '{"summary": "Plant needs water", "confidence": 0.95}'

        result = parser.parse(raw_response)

        assert result["summary"] == "Plant needs water"
        assert result["confidence"] == 0.95

    def test_parse_json_wrapped_in_markdown_code_block(self, sample_schema):
        parser = StructuredOutputParser(schema=sample_schema)
        raw_response = (
            "Here is the analysis result:\n"
            "```json\n"
            "{\n"
            '    "summary": "Soil is dry",\n'
            '    "confidence": 0.88,\n'
            '    "recommendations": ["Water tomorrow", "Add fertilizer"]\n'
            "}\n"
            "```\n"
            "Hope this helps!"
        )

        result = parser.parse(raw_response)

        assert result["summary"] == "Soil is dry"
        assert len(result["recommendations"]) == 2

    def test_invalid_json_raises_output_parse_error(self, sample_schema):
        parser = StructuredOutputParser(schema=sample_schema)
        raw_response = "This is just raw text without JSON"

        with pytest.raises(OutputParseError) as exc_info:
            parser.parse(raw_response)

        assert "Invalid JSON" in str(exc_info.value) or "No JSON" in str(exc_info.value)

    def test_schema_validation_failure_raises_output_parse_error(self, sample_schema):
        parser = StructuredOutputParser(schema=sample_schema)
        raw_response = '{"summary": 12345}'

        with pytest.raises(OutputParseError) as exc_info:
            parser.parse(raw_response)

        assert "Schema validation failed" in str(exc_info.value)

    def test_inherits_from_prompt_error(self):
        assert issubclass(OutputParseError, PromptError)
