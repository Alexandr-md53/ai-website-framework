import pytest
from ai_framework.metadata.models import EntityMetadata, FieldMetadata, FieldWidgetType
from ai_framework.crud_ui.engine import CrudUIEngine


def test_build_detail_view():
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
                display_order=1,
            ),
        ),
    )
    engine = CrudUIEngine(metadata=entity_meta)
    detail_vm = engine.build_detail_view(instance_data={"title": "Detail View Test"})

    assert detail_vm.entity_name == "Article"
    assert len(detail_vm.sections) >= 1
    assert detail_vm.sections[0].fields[0].value == "Detail View Test"
    assert detail_vm.sections[0].fields[0].data_type == "str"
