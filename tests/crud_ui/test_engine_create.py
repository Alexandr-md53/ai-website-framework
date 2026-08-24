import pytest
from ai_framework.metadata.models import (
    EntityMetadata,
    FormMetadata,
    FieldMetadata,
    FieldGroupMetadata,
    FieldWidgetType,
)
from ai_framework.crud_ui.engine import CrudUIEngine

def test_build_create_form():
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
                required=True,
            ),
        ),
    )
    form_meta = FormMetadata(
        entity_name="Article",
        title="Create Article",
        groups=(FieldGroupMetadata(name="main", label="Main", field_names=("title",)),),
    )
    engine = CrudUIEngine(metadata=entity_meta)
    form_vm = engine.build_create_form(form_metadata=form_meta)

    assert form_vm.entity_name == "Article"
    assert len(form_vm.fields) == 1
    assert form_vm.fields[0].required is True
    assert form_vm.fields[0].current_value is None
    assert len(form_vm.groups) == 1
    assert form_vm.groups[0].label == "Main"