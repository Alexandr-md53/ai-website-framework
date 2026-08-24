import json
from datetime import datetime, date
from uuid import UUID
from enum import Enum

from ai_framework.metadata.models import FieldWidgetType
from ai_framework.crud_ui.models import (
    ListViewModel,
    FormViewModel,
    FormFieldViewModel,
    PaginationSpec,
)
from ai_framework.crud_ui.web_adapter import WebResponseAdapter


class CustomStatus(Enum):
    ACTIVE = "active"


def test_adapter_converts_list_view_model_to_context():
    view_model = ListViewModel(
        entity_name="Article",
        title="Articles",
        items=(),
        pagination=PaginationSpec(page=1, page_size=20),
    )

    adapter = WebResponseAdapter()
    context = adapter.to_context(view_model)

    assert isinstance(context, dict)
    assert context["entity_name"] == "Article"
    assert context["title"] == "Articles"
    assert context["pagination"]["page"] == 1


def test_adapter_converts_form_view_model_with_nested_fields():
    field_vm = FormFieldViewModel(
        name="title",
        label="Title",
        widget_type="text",
        required=True,
        current_value="Test Title",
    )
    view_model = FormViewModel(
        entity_name="Article",
        title="Edit Article",
        fields=(field_vm,),
        groups=(),
    )

    adapter = WebResponseAdapter()
    context = adapter.to_context(view_model)

    assert isinstance(context, dict)
    assert isinstance(context["fields"], (list, tuple))
    assert isinstance(context["fields"][0], dict)
    assert context["fields"][0]["name"] == "title"
    assert context["fields"][0]["current_value"] == "Test Title"


def test_adapter_converts_view_model_to_json():
    view_model = ListViewModel(
        entity_name="Article",
        title="Articles",
        items=(),
        pagination=PaginationSpec(page=1, page_size=20),
    )

    adapter = WebResponseAdapter()
    json_output = adapter.to_json(view_model)

    assert isinstance(json_output, str)
    parsed = json.loads(json_output)
    assert parsed["entity_name"] == "Article"
    assert parsed["title"] == "Articles"
    assert parsed["pagination"]["page"] == 1


def test_adapter_serializes_complex_types_in_json():
    view_model = ListViewModel(
        entity_name="Article",
        title="Articles",
        items=(
            {
                "id": UUID("12345678-1234-5678-1234-567812345678"),
                "created_at": datetime(2026, 8, 23, 12, 0, 0),
                "published_date": date(2026, 8, 23),
                "status": CustomStatus.ACTIVE,
            },
        ),
        pagination=PaginationSpec(page=1, page_size=20),
    )

    adapter = WebResponseAdapter()
    json_output = adapter.to_json(view_model)

    assert isinstance(json_output, str)
    parsed = json.loads(json_output)
    assert parsed["items"][0]["status"] == "active"
    assert parsed["items"][0]["id"] == "12345678-1234-5678-1234-567812345678"
    assert parsed["items"][0]["created_at"] == "2026-08-23T12:00:00"
    assert parsed["items"][0]["published_date"] == "2026-08-23"
