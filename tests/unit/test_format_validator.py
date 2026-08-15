import re
import pytest
from ai_framework.validation.validators.format import FormatValidator
from ai_framework.validation.context import ValidationContext


@pytest.fixture
def context():
    """Базовый контекст валидации для тестирования."""
    return ValidationContext()


@pytest.mark.asyncio
async def test_accepts_valid_email(context):
    validator = FormatValidator("email")
    result = await validator.validate("email", "user@example.com", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_rejects_invalid_email(context):
    validator = FormatValidator("email")
    result = await validator.validate("email", "invalid-email-address", {}, context)
    assert result is not None
    assert result["message_key"] == "validation.invalid_email"
    assert result["params"]["value"] == "invalid-email-address"


@pytest.mark.asyncio
async def test_accepts_valid_url(context):
    validator = FormatValidator("url")
    result = await validator.validate("url", "https://example.com", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_rejects_invalid_url(context):
    validator = FormatValidator("url")
    result = await validator.validate("url", "not_a_url", {}, context)
    assert result is not None
    assert result["message_key"] == "validation.invalid_url"


@pytest.mark.asyncio
async def test_accepts_valid_custom_regex(context):
    validator = FormatValidator("regex", pattern=r"^\d{3}-\d{2}$")
    result = await validator.validate("code", "123-45", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_rejects_invalid_custom_regex(context):
    validator = FormatValidator("regex", pattern=r"^\d{3}-\d{2}$")
    result = await validator.validate("code", "abc-de", {}, context)
    assert result is not None
    assert result["message_key"] == "validation.regex_failed"


def test_raises_error_on_invalid_regex_pattern():
    with pytest.raises(re.error):
        FormatValidator("regex", pattern=r"[unclosed-bracket")


@pytest.mark.asyncio
async def test_accepts_none(context):
    validator = FormatValidator("email")
    result = await validator.validate("email", None, {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_non_string(context):
    # Нестроковые значения пропускаются (за них отвечает TypeValidator)
    validator = FormatValidator("email")
    result = await validator.validate("email", 12345, {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_accepts_empty_string(context):
    # Пустая строка пропускается (за нее отвечает RequiredValidator)
    validator = FormatValidator("email")
    result = await validator.validate("email", "   ", {}, context)
    assert result is None
