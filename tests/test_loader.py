"""
Tests for Framework component loader.
"""

import pytest

from framework.core.contracts import GeneratorContract
from framework.core.exceptions import ModuleLoadError
from framework.core.loader import ComponentLoader
from framework.core.registry import Registry


class TestGenerator(GeneratorContract):
    @property
    def name(self) -> str:
        return "test_generator"

    def generate(self, data):
        return f"generated: {data}"


def test_loader_registers_component():
    registry = Registry()
    loader = ComponentLoader(target_registry=registry)
    component = TestGenerator()

    result = loader.load(
        category="generators",
        component=component,
    )

    assert result is component
    assert registry.get("generators", "test_generator") is component


def test_loader_rejects_invalid_object():
    registry = Registry()
    loader = ComponentLoader(target_registry=registry)

    with pytest.raises(ModuleLoadError):
        loader.load(
            category="generators",
            component=object(),
        )


def test_loader_rejects_empty_component_name():
    class EmptyNameGenerator(GeneratorContract):
        @property
        def name(self) -> str:
            return "   "

        def generate(self, data):
            return data

    registry = Registry()
    loader = ComponentLoader(target_registry=registry)

    with pytest.raises(ModuleLoadError):
        loader.load(
            category="generators",
            component=EmptyNameGenerator(),
        )


def test_loader_rejects_non_string_component_name():
    class InvalidNameGenerator(GeneratorContract):
        @property
        def name(self):
            return 123

        def generate(self, data):
            return data

    registry = Registry()
    loader = ComponentLoader(target_registry=registry)

    with pytest.raises(ModuleLoadError):
        loader.load(
            category="generators",
            component=InvalidNameGenerator(),
        )


def test_loader_wraps_registration_error():
    registry = Registry()
    loader = ComponentLoader(target_registry=registry)

    first_component = TestGenerator()
    second_component = TestGenerator()

    loader.load(
        category="generators",
        component=first_component,
    )

    with pytest.raises(ModuleLoadError):
        loader.load(
            category="generators",
            component=second_component,
        )
