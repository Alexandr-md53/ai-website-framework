import pytest

from ai_framework.metadata.contracts import (
    RawEntityFragment,
    RawFieldFragment,
)
from ai_framework.metadata.engine import MetadataEngine
from ai_framework.metadata.exceptions import InvalidMetadataConfigurationError
from ai_framework.metadata.models import FieldWidgetType


def test_engine_structural_fallback():
    engine = MetadataEngine()

    entity_raw = RawEntityFragment(
        entity_name="article",
        fields=(RawFieldFragment(name="title", data_type="str"),),
    )

    metadata = engine.build_entity_metadata(entity_raw=entity_raw)

    assert metadata.entity_name == "article"
    assert metadata.label == "Article"  # auto-generated from entity_name
    assert len(metadata.fields) == 1
    assert metadata.fields[0].name == "title"
    assert metadata.fields[0].label == "Title"  # auto-generated from field name
    assert metadata.fields[0].widget_type == FieldWidgetType.TEXT


def test_engine_validation_precedence_over_ui():
    engine = MetadataEngine()

    entity_raw = RawEntityFragment(
        entity_name="post", fields=(RawFieldFragment(name="slug", data_type="str"),)
    )
    validation_raw = (RawFieldFragment(name="slug", required=True),)
    ui_raw = (RawFieldFragment(name="slug", required=False, label="Slug URL"),)

    metadata = engine.build_entity_metadata(
        entity_raw=entity_raw,
        validation_fragments=validation_raw,
        ui_fragments=ui_raw,
    )

    field = metadata.get_field_map()["slug"]
    assert field.required is True  # Validation precedence over UI (required=False)
    assert field.label == "Slug URL"  # UI override applied successfully


def test_engine_invalid_widget_raises_error():
    engine = MetadataEngine()

    entity_raw = RawEntityFragment(
        entity_name="item",
        fields=(
            RawFieldFragment(
                name="code", data_type="str", widget_type="non_existent_widget"
            ),
        ),
    )

    with pytest.raises(InvalidMetadataConfigurationError):
        engine.build_entity_metadata(entity_raw=entity_raw)


def test_form_metadata_building():
    engine = MetadataEngine()

    entity_raw = RawEntityFragment(
        entity_name="profile",
        fields=(RawFieldFragment(name="bio", data_type="str", widget_type="textarea"),),
    )

    form = engine.build_form_metadata(entity_raw=entity_raw, title="Edit Profile")

    assert form.entity_name == "profile"
    assert form.title == "Edit Profile"
    assert len(form.fields) == 1
    assert form.fields[0].widget_type == FieldWidgetType.TEXTAREA
