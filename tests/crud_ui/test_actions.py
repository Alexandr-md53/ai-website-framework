import pytest
from ai_framework.crud_ui.actions import (
    ActionType,
    ActionScope,
    ActionDefinition,
    validate_action_scope,
)
from ai_framework.crud_ui.exceptions import InvalidActionScopeError


@pytest.mark.parametrize(
    "action_type, scope",
    [
        (ActionType.CREATE, ActionScope.GLOBAL),
        (ActionType.EDIT, ActionScope.SINGLE_ITEM),
        (ActionType.DELETE, ActionScope.SINGLE_ITEM),
        (ActionType.BULK_DELETE, ActionScope.BULK),
        (ActionType.CUSTOM, ActionScope.GLOBAL),
        (ActionType.CUSTOM, ActionScope.SINGLE_ITEM),
        (ActionType.CUSTOM, ActionScope.BULK),
    ],
)
def test_valid_action_scope_combinations(action_type: ActionType, scope: ActionScope):
    validate_action_scope(action_type, scope)
    action = ActionDefinition(
        name="test", label="Test", action_type=action_type, scope=scope
    )
    assert action.action_type == action_type
    assert action.scope == scope


@pytest.mark.parametrize(
    "action_type, scope",
    [
        (ActionType.CREATE, ActionScope.SINGLE_ITEM),
        (ActionType.CREATE, ActionScope.BULK),
        (ActionType.EDIT, ActionScope.GLOBAL),
        (ActionType.EDIT, ActionScope.BULK),
        (ActionType.DELETE, ActionScope.GLOBAL),
        (ActionType.DELETE, ActionScope.BULK),
        (ActionType.BULK_DELETE, ActionScope.GLOBAL),
        (ActionType.BULK_DELETE, ActionScope.SINGLE_ITEM),
    ],
)
def test_invalid_action_scope_combinations_raise_error(
    action_type: ActionType, scope: ActionScope
):
    with pytest.raises(InvalidActionScopeError):
        validate_action_scope(action_type, scope)
