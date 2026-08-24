from enum import Enum
from dataclasses import dataclass
from ai_framework.crud_ui.exceptions import InvalidActionScopeError


class ActionType(str, Enum):
    CREATE = "CREATE"
    EDIT = "EDIT"
    DELETE = "DELETE"
    BULK_DELETE = "BULK_DELETE"
    CUSTOM = "CUSTOM"


class ActionScope(str, Enum):
    GLOBAL = "GLOBAL"
    SINGLE_ITEM = "SINGLE_ITEM"
    BULK = "BULK"


_VALID_ACTION_SCOPES: dict[ActionType, set[ActionScope]] = {
    ActionType.CREATE: {ActionScope.GLOBAL},
    ActionType.EDIT: {ActionScope.SINGLE_ITEM},
    ActionType.DELETE: {ActionScope.SINGLE_ITEM},
    ActionType.BULK_DELETE: {ActionScope.BULK},
    ActionType.CUSTOM: {ActionScope.GLOBAL, ActionScope.SINGLE_ITEM, ActionScope.BULK},
}


def validate_action_scope(action_type: ActionType, scope: ActionScope) -> None:
    valid_scopes = _VALID_ACTION_SCOPES.get(action_type, set())
    if scope not in valid_scopes:
        raise InvalidActionScopeError(
            f"ActionType '{action_type.value}' cannot be used with ActionScope '{scope.value}'."
        )


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    label: str
    action_type: ActionType
    scope: ActionScope
    target_url_template: str | None = None
    icon: str | None = None

    def __post_init__(self) -> None:
        validate_action_scope(self.action_type, self.scope)
