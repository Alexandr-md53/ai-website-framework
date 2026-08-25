import pytest
from ai_framework.security import (
    Permission,
    Role,
    Identity,
    SecurityContext,
    RoleBasedAuthorizationProvider,
)


def test_rbac_provider_allows_permission_from_single_or_multiple_roles():
    p_read = Permission("article.read")
    p_write = Permission("article.write")
    p_publish = Permission("article.publish")

    role_editor = Role("editor", frozenset({p_read, p_write}))
    role_publisher = Role("publisher", frozenset({p_publish}))

    identity = Identity(id="usr_1", roles=frozenset({role_editor, role_publisher}))
    ctx = SecurityContext(identity=identity)

    provider = RoleBasedAuthorizationProvider()

    assert provider.is_allowed(ctx, "article.read") is True
    assert provider.is_allowed(ctx, "article.write") is True
    assert provider.is_allowed(ctx, "article.publish") is True
    assert provider.is_allowed(ctx, "article.delete") is False


def test_rbac_provider_default_deny_semantics():
    provider = RoleBasedAuthorizationProvider()

    # 1. Anonymous context
    assert provider.is_allowed(SecurityContext.anonymous(), "article.read") is False

    # 2. Context with identity = None explicitly
    assert provider.is_allowed(SecurityContext(identity=None), "article.read") is False

    # 3. Authenticated user with empty roles
    empty_identity = Identity(id="usr_2", roles=frozenset())
    auth_ctx = SecurityContext(identity=empty_identity)
    assert provider.is_allowed(auth_ctx, "article.read") is False


def test_rbac_provider_ignores_resource_argument_in_basic_rbac():
    p_read = Permission("article.read")
    role = Role("reader", frozenset({p_read}))
    ctx = SecurityContext(identity=Identity(id="usr_3", roles=frozenset({role})))

    provider = RoleBasedAuthorizationProvider()

    assert provider.is_allowed(ctx, "article.read", resource={"id": 123}) is True
    assert provider.is_allowed(ctx, "article.delete", resource={"id": 123}) is False