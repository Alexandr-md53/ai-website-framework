import pytest
from ai_framework.metadata.models import FieldWidgetType
from ai_framework.crud_ui.models import (
    PaginationSpec,
    TableColumnViewModel,
    FormFieldViewModel,
    FormGroupViewModel,
    FormViewModel,
)


def test_pagination_spec_total_pages():
    assert PaginationSpec(page=1, page_size=10, total_items=0).total_pages == 0
    assert PaginationSpec(page=1, page_size=10, total_items=20).total_pages == 2
    assert PaginationSpec(page=1, page_size=10, total_items=25).total_pages == 3
    assert PaginationSpec(page=1, page_size=0, total_items=10).total_pages == 0


def test_models_immutability():
    column = TableColumnViewModel(
        name="title",
        label="Title",
        data_type="str",
        widget_type=FieldWidgetType.TEXT,
    )
    with pytest.raises(AttributeError):
        column.name = "new_title"  # type: ignore

    group = FormGroupViewModel(name="main", label="Main Info", field_names=("title",))
    form = FormViewModel(
        entity_name="Article",
        title="Create Article",
        fields=(),
        groups=(group,),
    )
    with pytest.raises(AttributeError):
        form.title = "New Title"  # type: ignore
