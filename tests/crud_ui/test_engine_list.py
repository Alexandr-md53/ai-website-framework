import pytest
from ai_framework.metadata.models import EntityMetadata, FieldMetadata, FieldWidgetType
from ai_framework.crud_ui.engine import CrudUIEngine
from ai_framework.crud_ui.config import CrudUIConfig, FieldUIConfig
from ai_framework.crud_ui.models import PaginationSpec


def test_build_list_view_defaults():
    meta = EntityMetadata(
        entity_name="Article",
        plural_label="Articles",
        primary_key_field="id",
        label="Articles",
        fields=(
            FieldMetadata(
                name="id",
                label="ID",
                data_type="int",
                widget_type=FieldWidgetType.NUMBER,
                display_order=1,
            ),
            FieldMetadata(
                name="title",
                label="Title",
                data_type="str",
                widget_type=FieldWidgetType.TEXT,
                display_order=2,
            ),
        ),
    )
    engine = CrudUIEngine(metadata=meta)
    list_vm = engine.build_list_view(
        items=[{"id": 1, "title": "First"}], pagination=PaginationSpec(1, 10, 1)
    )

    assert list_vm.entity_name == "Article"
    assert len(list_vm.columns) == 2
    assert list_vm.items[0]["title"] == "First"


def test_build_list_view_config_overrides():
    meta = EntityMetadata(
        entity_name="Article",
        plural_label="Articles",
        primary_key_field="id",
        label="Articles",
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
    config = CrudUIConfig(
        entity_name="Article",
        field_configs=(FieldUIConfig(field_name="title", sortable=True),),
    )
    engine = CrudUIEngine(metadata=meta, config=config)
    list_vm = engine.build_list_view()

    assert list_vm.columns[0].sortable is True
