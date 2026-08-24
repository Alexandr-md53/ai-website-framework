import pytest
from ai_framework.metadata.models import FieldWidgetType
from ai_framework.crud_ui.models import FormViewModel, FormFieldViewModel


def test_bind_form_errors_is_immutable():
    field = FormFieldViewModel(
        name="title", label="Title", widget_type=FieldWidgetType.TEXT
    )
    form = FormViewModel(entity_name="Article", title="Edit", fields=(field,))

    updated_form = form.bind_form_errors(
        field_errors={"title": ("Field is required",)},
        non_field_errors=("Invalid form state",),
    )

    assert form is not updated_form
    assert form.fields[0].errors == ()
    assert form.non_field_errors == ()
    assert updated_form.fields[0].errors == ("Field is required",)
    assert updated_form.non_field_errors == ("Invalid form state",)
