"""
tests/test_validation.py
-------------------------
Модульные тесты для модуля framework/validation.
"""

import pytest
from ai_framework.validation import ValidationEngine, ValidationResult


@pytest.mark.unit
@pytest.mark.validation
def test_validation_engine_init():
    """Проверяет корректную инициализацию ValidationEngine."""
    engine = ValidationEngine()
    assert engine is not None


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.validation
async def test_valid_html_passes(mock_valid_payload, passing_rules):
    """Проверяет, что валидный payload и успешные правила возвращают valid=True."""
    engine = ValidationEngine()
    result = await engine.validate(mock_valid_payload, passing_rules)

    assert result is not None
    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert len(result.errors) == 0


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.validation
async def test_invalid_html_fails(mock_invalid_payload, failing_rules):
    """Проверяет, что невалидные правила или payload возвращают valid=False и корректный список ошибок."""
    engine = ValidationEngine()
    result = await engine.validate(mock_invalid_payload, failing_rules)

    assert result is not None
    assert isinstance(result, ValidationResult)
    assert result.valid is False
    assert len(result.errors) == 1

    error = result.errors[0]
    assert error.field == "html_content"
    assert error.message_key == "validation.mock_error"
