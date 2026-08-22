from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class RawFieldFragment:
    name: str
    data_type: str | None = None
    required: bool | None = None
    default_value: Any = None
    constraints: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    label: str | None = None
    widget_type: str | None = None
    display_order: int | None = None
    options: tuple[tuple[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RawEntityFragment:
    entity_name: str
    fields: tuple[RawFieldFragment, ...] = field(default_factory=tuple)
    label: str | None = None
    plural_label: str | None = None
    primary_key_field: str | None = None


class StructuralSourceProtocol(Protocol):
    def extract_raw_entity(self, target: type) -> RawEntityFragment: ...


class ValidationSourceProtocol(Protocol):
    def extract_raw_constraints(
        self, entity_name: str
    ) -> tuple[RawFieldFragment, ...]: ...


class UISourceProtocol(Protocol):
    def extract_raw_ui_overrides(
        self, entity_name: str
    ) -> tuple[RawFieldFragment, ...]: ...
