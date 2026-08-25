import pytest
from typing import Any, Dict, Optional

from ai_framework.security import (
    Permission,
    Role,
    Identity,
    SecurityContext,
    TokenCredentials,
    InMemoryAuthenticationProvider,
    AuthenticationService,
    RoleBasedAuthorizationProvider,
    AuthorizationService,
)
from ai_framework.security.web import (
    BearerTokenExtractor,
    SecurityWebGuard,
    SecuredViewModelAdapter,
)


# ============================================================================
# 1. Authentication Web Integration Tests
# ============================================================================

def test_bearer_token_extractor_creates_token_credentials():
    headers = {"Authorization": "Bearer valid_token_123"}
    credentials = BearerTokenExtractor.extract(headers)
    assert credentials == TokenCredentials("valid_token_123")


def test_bearer_token_extractor_returns_none_on_missing_or_invalid_header():
    assert BearerTokenExtractor.extract({}) is None
    assert BearerTokenExtractor.extract({"Authorization": "Basic xyz"}) is None
    assert BearerTokenExtractor.extract({"Authorization": "Bearer "}) is None


# ============================================================================
# 2. CRUD Authorization Guard (401 vs 403 vs Deny Execution) Tests
# ============================================================================

def test_security_web_guard_returns_401_for_anonymous_request():
    auth_service = AuthenticationService(providers=[])
    authz_service = AuthorizationService(providers=[RoleBasedAuthorizationProvider()])
    guard = SecurityWebGuard(auth_service, authz_service)

    executed = False

    def mock_crud_action():
        nonlocal executed
        executed = True
        return {"status": "ok"}

    response, status_code = guard.protect(
        headers={},
        permission="article.read",
        action=mock_crud_action,
    )

    assert status_code == 401
    assert response == {"error": "Unauthorized"}
    assert executed is False


def test_security_web_guard_returns_403_for_authenticated_without_permission():
    identity = Identity(id="usr_101", roles=frozenset())
    auth_provider = InMemoryAuthenticationProvider(tokens={"valid_token": identity})
    auth_service = AuthenticationService(providers=[auth_provider])
    authz_service = AuthorizationService(providers=[RoleBasedAuthorizationProvider()])
    guard = SecurityWebGuard(auth_service, authz_service)

    executed = False

    def mock_crud_action():
        nonlocal executed
        executed = True
        return {"status": "ok"}

    response, status_code = guard.protect(
        headers={"Authorization": "Bearer valid_token"},
        permission="article.delete",
        action=mock_crud_action,
    )

    assert status_code == 403
    assert response == {"error": "Forbidden"}
    assert executed is False


def test_security_web_guard_allows_action_when_permission_granted():
    p_delete = Permission("article.delete")
    role = Role("admin", frozenset({p_delete}))
    identity = Identity(id="usr_101", roles=frozenset({role}))
    auth_provider = InMemoryAuthenticationProvider(tokens={"valid_token": identity})
    auth_service = AuthenticationService(providers=[auth_provider])
    authz_service = AuthorizationService(providers=[RoleBasedAuthorizationProvider()])
    guard = SecurityWebGuard(auth_service, authz_service)

    executed = False

    def mock_crud_action():
        nonlocal executed
        executed = True
        return {"status": "deleted"}

    response, status_code = guard.protect(
        headers={"Authorization": "Bearer valid_token"},
        permission="article.delete",
        action=mock_crud_action,
    )

    assert status_code == 200
    assert response == {"status": "deleted"}
    assert executed is True


# ============================================================================
# 3. UI ViewModel Adaptation Tests
# ============================================================================

def test_secured_view_model_adapter_filters_actions_without_mutating_core():
    p_read = Permission("article.read")
    role = Role("viewer", frozenset({p_read}))
    identity = Identity(id="usr_101", roles=frozenset({role}))
    ctx = SecurityContext(identity=identity)

    authz_service = AuthorizationService(providers=[RoleBasedAuthorizationProvider()])
    adapter = SecuredViewModelAdapter(authz_service)

    base_view_model = {
        "entity": "article",
        "actions": ["article.read", "article.update", "article.delete"],
    }

    secured_vm = adapter.adapt(base_view_model, ctx)

    assert secured_vm["allowed_actions"] == ["article.read"]
    assert base_view_model["actions"] == ["article.read", "article.update", "article.delete"]