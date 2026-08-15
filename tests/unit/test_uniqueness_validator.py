from unittest.mock import AsyncMock, MagicMock
import pytest
from ai_framework.validation.context import ValidationContext
from ai_framework.validation.validators.unique import UniquenessValidator


@pytest.fixture
def context():
    """Базовый контекст валидации."""
    return ValidationContext()


@pytest.mark.asyncio
async def test_accepts_none_and_empty_string(context):
    validator = UniquenessValidator(entity_name="user")

    assert await validator.validate("email", None, {}, context) is None
    assert await validator.validate("email", "", {}, context) is None
    assert await validator.validate("email", "   ", {}, context) is None


@pytest.mark.asyncio
async def test_skips_validation_without_provider(context):
    # Если контекст пуст или нет persistence_provider, валидатор ничего не блокирует
    validator = UniquenessValidator(entity_name="user")
    result = await validator.validate("email", "user@example.com", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_passes_when_value_is_unique(context):
    mock_provider = MagicMock()
    mock_provider.is_unique = AsyncMock(return_value=True)
    context.persistence_provider = mock_provider

    validator = UniquenessValidator(entity_name="user")
    result = await validator.validate("email", "new@example.com", {"id": 5}, context)

    assert result is None
    mock_provider.is_unique.assert_called_once_with(
        entity_name="user",
        field_name="email",
        value="new@example.com",
        exclude_id=5,
    )


@pytest.mark.asyncio
async def test_fails_when_value_is_not_unique(context):
    mock_provider = MagicMock()
    mock_provider.is_unique = AsyncMock(return_value=False)
    context.persistence_provider = mock_provider

    validator = UniquenessValidator(entity_name="user")
    result = await validator.validate("email", "taken@example.com", {}, context)

    assert result is not None
    assert result["message_key"] == "validation.not_unique"
    assert result["field"] == "email"
    assert result["params"]["value"] == "taken@example.com"
    assert result["params"]["entity"] == "user"


@pytest.mark.asyncio
async def test_uses_explicit_field_name_override(context):
    mock_provider = MagicMock()
    mock_provider.is_unique = AsyncMock(return_value=True)
    context.persistence_provider = mock_provider

    # Явно указываем custom_email в качестве поля DB
    validator = UniquenessValidator(entity_name="user", field_name="db_email_column")
    await validator.validate("email_form_field", "test@example.com", {}, context)

    mock_provider.is_unique.assert_called_once_with(
        entity_name="user",
        field_name="db_email_column",
        value="test@example.com",
        exclude_id=None,
    )
