from typing import Any, Optional
from ai_framework.security import (
    Identity,
    SecurityContext,
    AuthorizationService,
)


class MockAuthorizationProvider:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.called = False

    def is_allowed(
        self,
        context: SecurityContext,
        permission: str,
        resource: Optional[Any] = None,
    ) -> bool:
        self.called = True
        return self.allowed


def test_authorization_service_composite_or_behavior():
    provider_deny = MockAuthorizationProvider(allowed=False)
    provider_allow = MockAuthorizationProvider(allowed=True)
    provider_unreachable = MockAuthorizationProvider(allowed=True)

    service = AuthorizationService(
        providers=[provider_deny, provider_allow, provider_unreachable]
    )
    ctx = SecurityContext(identity=Identity(id="usr_1"))

    result = service.is_allowed(ctx, "article.update")

    assert result is True
    assert provider_deny.called is True
    assert provider_allow.called is True
    # Проверяем остановку цепочки (Short-circuit): первый True прерывает вычисления
    assert provider_unreachable.called is False


def test_authorization_service_all_deny_returns_false():
    p1 = MockAuthorizationProvider(allowed=False)
    p2 = MockAuthorizationProvider(allowed=False)

    service = AuthorizationService(providers=[p1, p2])
    ctx = SecurityContext(identity=Identity(id="usr_2"))

    assert service.is_allowed(ctx, "article.read") is False
    assert p1.called is True
    assert p2.called is True


def test_authorization_service_empty_providers_defaults_to_deny():
    service = AuthorizationService(providers=[])
    ctx = SecurityContext(identity=Identity(id="usr_1"))

    assert service.is_allowed(ctx, "article.read") is False
