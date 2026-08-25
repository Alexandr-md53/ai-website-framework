from dataclasses import FrozenInstanceError
import pytest
from typing import Any, Optional

from ai_framework.security import (
    Permission,
    Role,
    Identity,
    SecurityContext,
    AuthenticationProviderProtocol,
    AuthorizationProviderProtocol,
)


# ============================================================================
# 1. Permission Tests
# ============================================================================

def test_permission_requires_non_empty_name():
    with pytest.raises(ValueError):
        Permission("")

    with pytest.raises(ValueError):
        Permission("   ")


def test_permission_is_immutable_and_hashable():
    perm = Permission("article.read")

    with pytest.raises(FrozenInstanceError):
        perm.name = "article.write"  # type: ignore

    perm_set = {perm, Permission("article.read")}
    assert len(perm_set) == 1


def test_permissions_equality_by_name():
    p1 = Permission("article.read")
    p2 = Permission("article.read")
    p3 = Permission("article.write")

    assert p1 == p2
    assert p1 != p3


# ============================================================================
# 2. Role Tests
# ============================================================================

def test_role_structure_and_immutability():
    p_read = Permission("article.read")
    p_write = Permission("article.write")
    role = Role(name="editor", permissions=frozenset({p_read, p_write}))

    assert role.name == "editor"
    assert p_read in role.permissions
    assert p_write in role.permissions

    with pytest.raises(FrozenInstanceError):
        role.name = "admin"  # type: ignore


# ============================================================================
# 3. Identity Tests
# ============================================================================

def test_identity_structure_and_immutability():
    role = Role(name="editor", permissions=frozenset({Permission("article.read")}))
    identity = Identity(
        id="usr_101",
        roles=frozenset({role}),
        attributes={"email": "user@example.com"}
    )

    assert identity.id == "usr_101"
    assert role in identity.roles
    assert identity.attributes == {"email": "user@example.com"}

    with pytest.raises(FrozenInstanceError):
        identity.id = "usr_102"  # type: ignore


# ============================================================================
# 4. SecurityContext Tests
# ============================================================================

def test_anonymous_security_context_semantics():
    ctx = SecurityContext.anonymous()

    assert ctx.identity is None
    assert ctx.is_authenticated is False


def test_authenticated_security_context_semantics():
    identity = Identity(id="usr_101", roles=frozenset(), attributes={})
    ctx = SecurityContext(identity=identity)

    assert ctx.identity == identity
    assert ctx.is_authenticated is True


# ============================================================================
# 5. Core Protocols Verification
# ============================================================================

def test_authentication_provider_protocol_contract():
    class DummyAuthProvider:
        def authenticate(self, credentials: Any) -> Optional[Identity]:
            if credentials == "valid_token":
                return Identity(id="usr_101", roles=frozenset(), attributes={})
            return None

    provider = DummyAuthProvider()
    assert isinstance(provider, AuthenticationProviderProtocol)

    auth_identity = provider.authenticate("valid_token")
    assert auth_identity is not None
    assert auth_identity.id == "usr_101"

    assert provider.authenticate("invalid") is None


def test_authorization_provider_protocol_contract():
    class DummyAuthorizationProvider:
        def is_allowed(
            self,
            context: SecurityContext,
            permission: str,
            resource: Optional[Any] = None
        ) -> bool:
            if not context.is_authenticated:
                return False
            return permission == "article.read"

    provider = DummyAuthorizationProvider()
    assert isinstance(provider, AuthorizationProviderProtocol)

    anon_ctx = SecurityContext.anonymous()
    auth_ctx = SecurityContext(
        identity=Identity(id="usr_101", roles=frozenset(), attributes={})
    )

    assert provider.is_allowed(anon_ctx, "article.read") is False
    assert provider.is_allowed(auth_ctx, "article.read") is True
    assert provider.is_allowed(auth_ctx, "article.delete") is False