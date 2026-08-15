import pytest
from ai_framework.validation.validators.required import RequiredValidator
from ai_framework.validation.context import ValidationContext


@pytest.fixture
def context():
    """Базовый контекст валидации для тестирования."""
    return ValidationContext()


@pytest.mark.asyncio
async def test_accepts_valid_value(context):
    validator = RequiredValidator()
    result = await validator.validate("test_field", "valid_string", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_rejects_none(context):
    validator = RequiredValidator()
    result = await validator.validate("test_field", None, {}, context)
    assert result is not None
    assert result["field"] == "test_field"


@pytest.mark.asyncio
async def test_rejects_empty_string(context):
    validator = RequiredValidator()
    result = await validator.validate("test_field", "", {}, context)
    assert result is not None


@pytest.mark.asyncio
async def test_rejects_whitespace_string(context):
    validator = RequiredValidator()
    result = await validator.validate("test_field", "   ", {}, context)
    assert result is not None


@pytest.mark.asyncio
async def test_accepts_zero(context):
    validator = RequiredValidator()
    # 0 — валидное числовое значение
    result = await validator.validate("test_field", 0, {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_false(context):
    validator = RequiredValidator()
    # False — валидное булево значение
    result = await validator.validate("test_field", False, {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_empty_list(context):
    validator = RequiredValidator()
    # Пустой список считается переданным значением (для длины используется LengthValidator)
    result = await validator.validate("test_field", [], {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_empty_dict(context):
    validator = RequiredValidator()
    # Пустой словарь считается переданным значением
    result = await validator.validate("test_field", {}, {}, context)
    assert result is None
