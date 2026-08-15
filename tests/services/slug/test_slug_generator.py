"""
TDD Suite: SlugGenerator (ADR-003, Public Contracts)
"""

import pytest
from ai_framework.services.slug import SlugGenerator


@pytest.fixture
def generator() -> SlugGenerator:
    return SlugGenerator()


def test_generate_simple_text(generator: SlugGenerator) -> None:
    """Базовое приведение текста к нижнему регистру и разделению дефисами."""
    assert generator.generate("  Red Rose Bush  ") == "red-rose-bush"


def test_generate_special_characters_and_punctuation(generator: SlugGenerator) -> None:
    """Удаление спецсимволов и пунктуации."""
    assert generator.generate("Hello, World! #1 Product") == "hello-world-1-product"


def test_generate_multiple_separators_normalized(generator: SlugGenerator) -> None:
    """Схлопывание множественных пробелов и дефисов."""
    assert generator.generate("hello---world--test   2026") == "hello-world-test-2026"


def test_generate_leading_trailing_separators(generator: SlugGenerator) -> None:
    """Удаление дефисов с концов строки."""
    assert generator.generate("-hello-world-") == "hello-world"


def test_generate_cyrillic_and_mixed(generator: SlugGenerator) -> None:
    """Генерация slug из кириллицы и смешанного текста."""
    assert generator.generate("Красная Rose #12") == "krasnaya-rose-12"


def test_generate_max_length_default_255(generator: SlugGenerator) -> None:
    """ADR-003: По умолчанию max_length равен 255."""
    long_text = "a" * 300
    result = generator.generate(long_text)
    assert len(result) == 255


def test_generate_max_length_truncation_without_trailing_dash(
    generator: SlugGenerator,
) -> None:
    """ADR-003: Урезание длины не оставляет висячий дефис на конце."""
    text = "very long product description"
    # Без урезания: "very-long-product-description"
    # При max_length=10 попадает на 'very-long-' -> должно стать 'very-long'
    result = generator.generate(text, max_length=10)
    assert result == "very-long"
    assert not result.endswith("-")


def test_generate_unique_calls_availability_callback(generator: SlugGenerator) -> None:
    """Публичный метод generate_unique корректно использует callback доступности."""
    taken = {"flower"}
    is_available = lambda s: s not in taken

    assert generator.generate_unique("flower", is_available=is_available) == "flower-2"


def test_generate_deterministic(generator: SlugGenerator) -> None:
    """Один и тот же ввод всегда даёт идентичный slug."""
    text = "Проверка детерминированности 123"
    assert generator.generate(text) == generator.generate(text)
