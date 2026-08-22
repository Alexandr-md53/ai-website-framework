from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any


class FieldWidgetType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    DATE = "date"
    DATETIME = "datetime"
    SLUG = "slug"
    FILE = "file"
    HIDDEN = "hidden"


@dataclass(frozen=True)
class FieldConstraint:
    name: str
    value: Any
    error_message: str | None = None


@dataclass(frozen=True)
class FieldMetadata:
    name: str
    data_type: str
    label: str
    widget_type: FieldWidgetType
    required: bool = False
    read_only: bool = False
    display_order: int = 0
    default_value: Any = None
    constraints: tuple[FieldConstraint, ...] = field(default_factory=tuple)
    choices: tuple[tuple[Any, str], ...] = field(default_factory=tuple)
    help_text: str | None = None
    options: tuple[tuple[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FieldGroupMetadata:
    name: str
    label: str
    field_names: tuple[str, ...]
    display_order: int = 0


@dataclass(frozen=True)
class EntityMetadata:
    entity_name: str
    label: str
    plural_label: str
    primary_key_field: str
    fields: tuple[FieldMetadata, ...] = field(default_factory=tuple)

    def get_field_map(self) -> MappingProxyType[str, FieldMetadata]:
        return MappingProxyType({f.name: f for f in self.fields})


@dataclass(frozen=True)
class FormMetadata:
    entity_name: str
    title: str
    fields: tuple[FieldMetadata, ...] = field(default_factory=tuple)
    groups: tuple[FieldGroupMetadata, ...] = field(default_factory=tuple)
    is_read_only: bool = False