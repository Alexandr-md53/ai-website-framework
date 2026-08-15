"""
TDD Suite: Collision Resolver (ADR-004, ADR-005)
"""

import pytest
from ai_framework.services.slug import DefaultCollisionResolver, SlugCollisionError


@pytest.fixture
def resolver() -> DefaultCollisionResolver:
    return DefaultCollisionResolver()


def test_collision_resolver_no_collision(resolver: DefaultCollisionResolver) -> None:
    """Если базовый slug свободен, возвращается он же без суффиксов."""
    is_available = lambda slug: slug == "red-rose"
    result = resolver.resolve("red-rose", is_available=is_available)
    assert result == "red-rose"


def test_collision_resolver_single_collision(
    resolver: DefaultCollisionResolver,
) -> None:
    """ADR-004: Если базовый slug занят, добавляется суффикс -2."""
    taken = {"red-rose"}
    is_available = lambda slug: slug not in taken

    result = resolver.resolve("red-rose", is_available=is_available)
    assert result == "red-rose-2"


def test_collision_resolver_multiple_collisions(
    resolver: DefaultCollisionResolver,
) -> None:
    """ADR-004: Итеративное увеличение суффикса: -2, -3, -4."""
    taken = {"red-rose", "red-rose-2", "red-rose-3"}
    is_available = lambda slug: slug not in taken

    result = resolver.resolve("red-rose", is_available=is_available)
    assert result == "red-rose-4"


def test_collision_resolver_exhaustion_raises_error(
    resolver: DefaultCollisionResolver,
) -> None:
    """ADR-005: Превышение 100 попыток вызывает SlugCollisionError."""
    is_available = lambda slug: False  # Все заняты

    with pytest.raises(SlugCollisionError, match="100 attempts"):
        resolver.resolve("red-rose", is_available=is_available)


def test_collision_resolver_respects_max_length(
    resolver: DefaultCollisionResolver,
) -> None:
    """ADR-003 + ADR-004: Разрешение коллизий учитывает max_length, урезая базовую часть."""
    base_slug = "very-long-product-name"  # 22 chars
    # Урезанный базовый слаг ("very-long-product-na") и "-2" заняты
    taken = {"very-long-product-na", "very-long-product-2"}
    is_available = lambda slug: slug not in taken

    # Ограничение 20 символов: резолвер должен урезать базу и выдать 'very-long-product-3'
    result = resolver.resolve(base_slug, is_available=is_available, max_length=20)
    assert result == "very-long-product-3"
    assert len(result) <= 20
    assert not result.endswith("-")
