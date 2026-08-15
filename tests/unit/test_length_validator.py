import pytest
from ai_framework.validation.validators.length import LengthValidator
from ai_framework.validation.context import ValidationContext


@pytest.fixture
def context():
    """Базовый контекст валидации для тестирования."""
    return ValidationContext()


@pytest.mark.asyncio
async def test_accepts_inside_range(context):
    validator = LengthValidator(min_length=3, max_length=5)
    result = await validator.validate("test_field", "abcd", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_min_boundary(context):
    validator = LengthValidator(min_length=3, max_length=5)
    result = await validator.validate("test_field", "abc", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_max_boundary(context):
    validator = LengthValidator(min_length=3, max_length=5)
    result = await validator.validate("test_field", "abcde", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_rejects_below_min(context):
    validator = LengthValidator(min_length=3, max_length=5)
    result = await validator.validate("test_field", "ab", {}, context)
    assert result is not None
    assert result["message_key"] == "validation.too_short"
    assert result["params"]["min_length"] == 3
    assert result["params"]["actual"] == 2


@pytest.mark.asyncio
async def test_rejects_above_max(context):
    validator = LengthValidator(min_length=3, max_length=5)
    result = await validator.validate("test_field", "abcdef", {}, context)
    assert result is not None
    assert result["message_key"] == "validation.too_long"
    assert result["params"]["max_length"] == 5
    assert result["params"]["actual"] == 6


@pytest.mark.asyncio
async def test_accepts_empty_string_if_min_is_zero(context):
    validator = LengthValidator(min_length=0, max_length=5)
    result = await validator.validate("test_field", "", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_none(context):
    # None пропускается (за него отвечает RequiredValidator)
    validator = LengthValidator(min_length=3, max_length=5)
    result = await validator.validate("test_field", None, {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_ignores_non_sized_object(context):
    # Числа и объекты без __len__ пропускаются (за них отвечает TypeValidator)
    validator = LengthValidator(min_length=3, max_length=5)
    result = await validator.validate("test_field", 12345, {}, context)
    assert result is None
