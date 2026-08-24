from dataclasses import dataclass
from ai_framework.crud_ui.actions import ActionDefinition


@dataclass(frozen=True)
class FieldUIConfig:
    field_name: str
    visible: bool | None = None
    sortable: bool | None = None


@dataclass(frozen=True)
class CrudUIConfig:
    entity_name: str
    field_configs: tuple[FieldUIConfig, ...] = ()
    actions: tuple[ActionDefinition, ...] = ()
