import pytest
from framework.services.slug import SlugService


@pytest.fixture
def slug_service():
    return SlugService(
        reserved_words=["admin", "api", "login", "static"],
        max_length=30,
        separator="-",
        default_fallback="untitled",
    )


def test_slugify_cyrillic_transliteration(slug_service):
    assert slug_service.slugify("Привет Мир") == "privet-mir"


def test_sanitize_extra_separators(slug_service):
    assert slug_service.sanitize("---hello---world---") == "hello-world"


def test_max_length_truncation(slug_service):
    # Длинная строка режется аккуратно по лимиту
    text = "this is a very long sentence that exceeds max length"
    result = slug_service.slugify(text)
    assert len(result) <= 30
    assert result == "this-is-a-very-long-sentence"


def test_fallback_on_invalid_input(slug_service):
    assert slug_service.slugify("!!! ###") == "untitled"


def test_is_reserved(slug_service):
    assert slug_service.is_reserved("admin") is True
    assert slug_service.is_reserved("blog") is False


def test_validate(slug_service):
    assert slug_service.validate("valid-slug-123") is True
    assert slug_service.validate("ADMIN") is False  # В верхнем регистре
    assert slug_service.validate("-invalid-") is False  # Краевые дефисы
    assert slug_service.validate("admin") is False  # Reserved


@pytest.mark.asyncio
async def test_generate_unique_with_collision(slug_service):
    # Мокаем проверку существования (имитируем, что 'article' и 'article-1' уже заняты)
    existing_slugs = {"article", "article-1"}

    async def mock_exists(slug: str) -> bool:
        return slug in existing_slugs

    result = await slug_service.generate("Article", exists_checker=mock_exists)
    assert result == "article-2"


@pytest.mark.asyncio
async def test_generate_unique_reserved_word(slug_service):
    # Резервированное слово должно сразу получить суффикс
    result = await slug_service.generate("admin")
    assert result == "admin-1"
