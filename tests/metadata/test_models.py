from types import MappingProxyType
import pytest
from dataclasses import FrozenInstanceError

from ai_framework.metadata.models import (
    EntityMetadata,
    FieldConstraint,
    FieldGroupMetadata,
    FieldMetadata,
    FieldWidgetType,
    FormMetadata,
)


def test_field_metadata_immutability():
    field_meta = FieldMetadata(
        name="title",
        data_type="str",
        label="Title",
        widget_type=FieldWidgetType.TEXT,
        required=True,
    )

    with pytest.raises(FrozenInstanceError):
        field_meta.required = False  # type: ignore


def test_entity_metadata_get_field_map():
    f1 = FieldMetadata(
        name="id", data_type="int", label="ID", widget_type=FieldWidgetType.NUMBER
    )
    f2 = FieldMetadata(
        name="title", data_type="str", label="Title", widget_type=FieldWidgetType.TEXT
    )

    entity = EntityMetadata(
        entity_name="article",
        label="Article",
        plural_label="Articles",
        primary_key_field="id",
        fields=(f1, f2),
    )

    field_map = entity.get_field_map()
    assert isinstance(field_map, MappingProxyType)
    assert field_map["id"].data_type == "int"
    assert field_map["title"].label == "Title"

    with pytest.raises(TypeError):
        field_map["new"] = f1  # type: ignore


def test_form_metadata_creation():
    f1 = FieldMetadata(
        name="title", data_type="str", label="Title", widget_type=FieldWidgetType.TEXT
    )
    group = FieldGroupMetadata(name="main", label="Main Info", field_names=("title",))

    form = FormMetadata(
        entity_name="article",
        title="Edit Article",
        fields=(f1,),
        groups=(group,),
    )

    assert form.entity_name == "article"
    assert len(form.groups) == 1
    assert form.groups[0].field_names == ("title",)
