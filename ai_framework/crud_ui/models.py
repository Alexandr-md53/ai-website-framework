from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence
from ai_framework.metadata.models import FieldWidgetType


@dataclass(frozen=True)
class PaginationSpec:
    page: int = 1
    page_size: int = 20
    total_items: int = 0

    @property
    def total_pages(self) -> int:
        if self.total_items <= 0 or self.page_size <= 0:
            return 0
        return (self.total_items + self.page_size - 1) // self.page_size


@dataclass(frozen=True)
class TableColumnViewModel:
    name: str
    label: str
    data_type: str
    widget_type: FieldWidgetType
    display_order: int = 0
    visible: bool = True
    sortable: bool = False


@dataclass(frozen=True)
class ListViewModel:
    entity_name: str
    title: str
    columns: tuple[TableColumnViewModel, ...] = ()
    items: tuple[dict[str, Any], ...] = ()
    pagination: PaginationSpec = field(default_factory=PaginationSpec)
    actions: tuple[Any, ...] = ()


@dataclass(frozen=True)
class DetailFieldViewModel:
    name: str
    label: str
    value: Any
    data_type: str
    widget_type: FieldWidgetType
    display_order: int = 0


@dataclass(frozen=True)
class DetailSectionViewModel:
    name: str
    label: str
    fields: tuple[DetailFieldViewModel, ...] = ()
    display_order: int = 0


@dataclass(frozen=True)
class DetailViewModel:
    entity_name: str
    title: str
    sections: tuple[DetailSectionViewModel, ...] = ()
    actions: tuple[Any, ...] = ()


@dataclass(frozen=True)
class FormFieldViewModel:
    name: str
    label: str
    widget_type: FieldWidgetType
    required: bool = False
    current_value: Any = None
    help_text: str | None = None
    options: tuple[tuple[Any, str], ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormGroupViewModel:
    name: str
    label: str
    field_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormViewModel:
    entity_name: str
    title: str
    fields: tuple[FormFieldViewModel, ...] = ()
    groups: tuple[FormGroupViewModel, ...] = ()
    actions: tuple[Any, ...] = ()
    non_field_errors: tuple[str, ...] = ()

    def bind_form_errors(
        self,
        field_errors: Mapping[str, Sequence[str]] | None = None,
        non_field_errors: Sequence[str] | None = None,
    ) -> "FormViewModel":
        field_errs = field_errors or {}
        new_fields = [
            replace(f, errors=tuple(field_errs[f.name])) if f.name in field_errs else f
            for f in self.fields
        ]
        new_non_field_errors = tuple(non_field_errors) if non_field_errors else ()

        return replace(
            self,
            fields=tuple(new_fields),
            non_field_errors=new_non_field_errors,
        )