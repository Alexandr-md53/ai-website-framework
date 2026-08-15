"""
TDD Suite: Edge Cases and Exception Hierarchy (ADR-006, ADR-007)
"""

import pytest
from ai_framework.core.exceptions import AIFrameworkError
from ai_framework.services.slug import (
    SlugError,
    SlugGenerationError,
    SlugCollisionError,
    SlugGenerator,
)


def test_exception_hierarchy_adr_006() -> None:
    """ADR-006: Все исключения модуля наследуются от AIFrameworkError."""
    assert issubclass(SlugError, AIFrameworkError)
    assert issubclass(SlugGenerationError, SlugError)
    assert issubclass(SlugCollisionError, SlugError)


def test_empty_input_raises_slug_generation_error() -> None:
    """Пустой ввод вызывает SlugGenerationError."""
    generator = SlugGenerator()
    with pytest.raises(SlugGenerationError, match="Empty text"):
        generator.generate("")


def test_whitespace_only_raises_slug_generation_error() -> None:
    """Строка только из пробелов вызывает SlugGenerationError."""
    generator = SlugGenerator()
    with pytest.raises(SlugGenerationError):
        generator.generate("   \t\n ")


def test_no_sluggable_characters_raises_slug_generation_error() -> None:
    """Строка без допустимых символов вызывает SlugGenerationError."""
    generator = SlugGenerator()
    with pytest.raises(SlugGenerationError, match="No valid characters"):
        generator.generate("!!! $$$ ### @@@")
