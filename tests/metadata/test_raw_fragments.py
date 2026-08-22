import pytest
from dataclasses import FrozenInstanceError

from ai_framework.metadata.contracts import (
    RawFieldFragment,
    RawEntityFragment,
)


def test_raw_field_fragment_creation_defaults():
    fragment = RawFieldFragment(name="title")

    assert fragment.name == "title"
    assert fragment.data_type is None
    assert fragment.required is None
    assert fragment.constraints == ()
    assert fragment.label is None
    assert fragment.widget_type is None
    assert fragment.display_order is None
    assert fragment.options == ()


def test_raw_field_fragment_immutability():
    fragment = RawFieldFragment(name="title", required=True)

    with pytest.raises(FrozenInstanceError):
        fragment.required = False  # type: ignore


def test_raw_entity_fragment_creation():
    field_1 = RawFieldFragment(name="id", data_type="int")
    field_2 = RawFieldFragment(name="title", data_type="str")

    entity = RawEntityFragment(
        entity_name="article",
        fields=(field_1, field_2),
        label="Article",
        plural_label="Articles",
        primary_key_field="id",
    )

    assert entity.entity_name == "article"
    assert len(entity.fields) == 2
    assert entity.fields[0].name == "id"
    assert entity.primary_key_field == "id"


def test_raw_entity_fragment_immutability():
    entity = RawEntityFragment(
        entity_name="article",
        fields=(),
    )

    with pytest.raises(FrozenInstanceError):
        entity.entity_name = "user"  # type: ignore
