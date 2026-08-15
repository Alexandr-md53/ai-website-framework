"""
Unit tests for Metadata Engine.
"""

import pytest
from framework.metadata.builder import MetadataBuilder
from framework.core.exceptions import ValidationError


def test_build_payload_success():
    data = {
        "title": "Тестовый заголовок",
        "text": "Тестовый текст",
        "image": "https://example.com/image.jpg",
    }
    payload = MetadataBuilder.build_from_dict(data)
    assert payload.title == "Тестовый заголовок"
    assert payload.text == "Тестовый текст"
    assert payload.image == "https://example.com/image.jpg"


def test_build_payload_validation_error():
    data = {"title": "", "text": ""}
    with pytest.raises(ValidationError):
        MetadataBuilder.build_from_dict(data)
