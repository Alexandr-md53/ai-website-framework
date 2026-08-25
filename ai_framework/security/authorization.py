from __future__ import annotations
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ai_framework.security import SecurityContext


class RoleBasedAuthorizationProvider:
    def is_allowed(
        self,
        context: SecurityContext,
        permission: str,
        resource: Optional[Any] = None,
    ) -> bool:
        if not context.is_authenticated or context.identity is None:
            return False

        for role in context.identity.roles:
            for perm in role.permissions:
                if perm.name == permission:
                    return True
        return False


class AuthorizationService:
    def __init__(self, providers: List[Any]) -> None:
        self._providers = providers

    def is_allowed(
        self,
        context: SecurityContext,
        permission: str,
        resource: Optional[Any] = None,
    ) -> bool:
        for provider in self._providers:
            if provider.is_allowed(context, permission, resource):
                return True
        return False
