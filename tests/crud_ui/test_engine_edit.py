import pytest
from ai_framework.metadata.models import (
    EntityMetadata,
    FormMetadata,
    FieldMetadata,
    FieldGroupMetadata,
    FieldWidgetType,
)
from ai_framework.crud_ui.engine import CrudUIEngine

def test_build_edit_form_populates_values():
    entity_meta = EntityMetadata(
        entity_name="Article",
        plural_label="Articles",
        primary_key_field="id",
        label="Article",
        fields=(
            FieldMetadata(
                name="title",
                label="Title",
                data_type="str",
                widget_type=FieldWidgetType.TEXT,
            ),
            FieldMetadata(
                name="missing_field",
                label="Missing",
                data_type="str",
                widget_type=FieldWidgetType.TEXT,
            ),
        ),
    )
    form_meta = FormMetadata(
        entity_name="Article",
        title="Edit Article",
        groups=(
            FieldGroupMetadata(
                name="main",
                label="Main",
                field_names=("title", "missing_field"),
            ),
        ),
    )
    engine = CrudUIEngine(metadata=entity_meta)
    instance = {"title": "Existing Title"}

    form_vm = engine.build_edit_form(form_metadata=form_meta, instance_data=instance)

    assert form_vm.fields[0].current_value == "Existing Title"
    assert form_vm.fields[1].current_value is None
    assert instance == {"title": "Existing Title"}