"""
Tests for the Framework Registry.
"""

import pytest

from framework.core.exceptions import (
    DuplicateRegistrationError,
    ItemNotFoundError,
)
from framework.core.registry import Registry


def test_register_and_get_item():
    registry = Registry()

    test_item = object()

    registry.register(
        category="generators",
        name="plant",
        item=test_item,
    )

    result = registry.get(
        category="generators",
        name="plant",
    )

    assert result is test_item


def test_duplicate_registration_raises_error():
    registry = Registry()

    registry.register(
        category="generators",
        name="plant",
        item=object(),
    )

    with pytest.raises(DuplicateRegistrationError):
        registry.register(
            category="generators",
            name="plant",
            item=object(),
        )


def test_unknown_item_raises_error():
    registry = Registry()

    with pytest.raises(ItemNotFoundError):
        registry.get(
            category="generators",
            name="unknown",
        )


def test_has_registered_item():
    registry = Registry()

    registry.register(
        category="generators",
        name="plant",
        item=object(),
    )

    assert registry.has("generators", "plant") is True
    assert registry.has("generators", "unknown") is False


def test_list_returns_registered_items():
    registry = Registry()

    first_item = object()
    second_item = object()

    registry.register(
        category="generators",
        name="plant",
        item=first_item,
    )

    registry.register(
        category="generators",
        name="article",
        item=second_item,
    )

    result = registry.list("generators")

    assert result == {
        "plant": first_item,
        "article": second_item,
    }