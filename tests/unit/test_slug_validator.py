from unittest.mock import AsyncMock, MagicMock
import pytest
from ai_framework.validation.validators.slug import SlugValidator
from ai_framework.validation.context import ValidationContext


@pytest.fixture
def context():
    """Базовый контекст валидации для тестирования."""
    return ValidationContext()


@pytest.mark.asyncio
async def test_accepts_valid_slug(context):
    validator = SlugValidator()
    result = await validator.validate("slug", "valid-slug-123", {}, context)
    assert result is None


@pytest.mark.asyncio
async def test_rejects_uppercase(context):
    validator = SlugValidator()
    result = await validator.validate("slug", "Invalid-Slug", {}, context)
    assert result is not None
    assert result["message_key"] == "validation.invalid_slug_format"


@pytest.mark.asyncio
async def test_rejects_spaces(context):
    validator = SlugValidator()
    result = await validator.validate("slug", "invalid slug", {}, context)
    assert result is not None
    assert result["message_key"] == "validation.invalid_slug_format"


@pytest.mark.asyncio
async def test_rejects_unicode(context):
    validator = SlugValidator()
    result = await validator.validate("slug", "слаг-заголовок", {}, context)
    assert result is not None
    assert result["message_key"] == "validation.invalid_slug_format"


@pytest.mark.asyncio
async def test_accepts_empty_and_none(context):
    validator = SlugValidator()
    assert await validator.validate("slug", None, {}, context) is None
    assert await validator.validate("slug", "", {}, context) is None
    assert await validator.validate("slug", "   ", {}, context) is None


@pytest.mark.asyncio
async def test_unique_slug_with_provider(context):
    mock_provider = MagicMock()
    mock_provider.is_unique = AsyncMock(return_value=True)
    context.persistence_provider = mock_provider

    validator = SlugValidator(entity_name="article")
    result = await validator.validate("slug", "my-article", {"id": 10}, context)

    assert result is None
    mock_provider.is_unique.assert_called_once_with(
        entity_name="article",
        field_name="slug",
        value="my-article",
        exclude_id=10,
    )


@pytest.mark.asyncio
async def test_duplicate_slug_with_provider(context):
    mock_provider = MagicMock()
    mock_provider.is_unique = AsyncMock(return_value=False)
    context.persistence_provider = mock_provider

    validator = SlugValidator(entity_name="article")
    result = await validator.validate("slug", "taken-slug", {}, context)

    assert result is not None
    assert result["message_key"] == "validation.slug_taken"
    assert result["params"]["slug"] == "taken-slug"
