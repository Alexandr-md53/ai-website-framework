import pytest
from ai_framework.validation.validators.type import TypeValidator
from ai_framework.validation.context import ValidationContext


@pytest.fixture
def context():
    """Базовый контекст валидации для тестирования."""
    return ValidationContext()


@pytest.mark.asyncio
async def test_accepts_valid_string(context):
    validator = TypeValidator("string")
    result = await validator.validate("test_field", "hello", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_valid_int(context):
    validator = TypeValidator("integer")
    result = await validator.validate("test_field", 42, {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_valid_float(context):
    validator = TypeValidator("float")
    result = await validator.validate("test_field", 3.14, {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_valid_boolean(context):
    validator = TypeValidator("boolean")
    result = await validator.validate("test_field", True, {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_valid_list(context):
    validator = TypeValidator("list")
    result = await validator.validate("test_field", [1, 2, 3], {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_valid_dict(context):
    validator = TypeValidator("dict")
    result = await validator.validate("test_field", {"key": "val"}, {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_rejects_invalid_type(context):
    validator = TypeValidator("integer")
    result = await validator.validate("test_field", "not_an_int", {}, context)
    assert result is not None
    assert result["message_key"] == "validation.invalid_type"
    assert result["params"]["actual"] == "str"


@pytest.mark.asyncio
async def test_rejects_bool_for_numeric_types(context):
    # Защита от особенности Python: bool не должен проходить как integer/float
    validator = TypeValidator("integer")
    result = await validator.validate("test_field", True, {}, context)
    assert result is not None
    assert result["params"]["actual"] == "boolean"


@pytest.mark.asyncio
async def test_accepts_none(context):
    # None пропускается TypeValidator'ом (за него отвечает RequiredValidator)
    validator = TypeValidator("string")
    result = await validator.validate("test_field", None, {}, context)
    assert result is None


def test_raises_error_on_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported type check"):
        TypeValidator("unsupported_type")
