"""
Tests for Framework contracts.
"""

import pytest

from framework.core.contracts import (
    FrameworkComponent,
    GeneratorContract,
    PublisherContract,
)


def test_framework_component_cannot_be_created_directly():
    with pytest.raises(TypeError):
        FrameworkComponent()


def test_generator_contract_cannot_be_created_without_required_methods():
    with pytest.raises(TypeError):
        GeneratorContract()


def test_publisher_contract_cannot_be_created_without_required_methods():
    with pytest.raises(TypeError):
        PublisherContract()


def test_generator_execute_calls_generate():
    class TestGenerator(GeneratorContract):
        @property
        def name(self) -> str:
            return "test_generator"

        def generate(self, data):
            return f"generated: {data}"

    generator = TestGenerator()

    result = generator.execute("content")

    assert generator.name == "test_generator"
    assert result == "generated: content"


def test_publisher_execute_calls_publish():
    class TestPublisher(PublisherContract):
        @property
        def name(self) -> str:
            return "test_publisher"

        def publish(self, data):
            return f"published: {data}"

    publisher = TestPublisher()

    result = publisher.execute("content")

    assert publisher.name == "test_publisher"
    assert result == "published: content"
