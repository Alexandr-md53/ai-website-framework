from typing import Any, Callable, Dict, Optional, Tuple

from ai_framework.security import (
    AuthenticationService,
    AuthorizationService,
    SecurityContext,
    TokenCredentials,
)


class BearerTokenExtractor:
    @staticmethod
    def extract(headers: Dict[str, str]) -> Optional[TokenCredentials]:
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header:
            return None

        parts = auth_header.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
            return TokenCredentials(token=parts[1].strip())

        return None


class SecurityWebGuard:
    def __init__(
        self,
        authentication_service: AuthenticationService,
        authorization_service: AuthorizationService,
    ) -> None:
        self._auth_service = authentication_service
        self._authz_service = authorization_service

    def protect(
        self,
        headers: Dict[str, str],
        permission: str,
        action: Callable[[], Any],
    ) -> Tuple[Any, int]:
        credentials = BearerTokenExtractor.extract(headers)
        if credentials:
            ctx = self._auth_service.authenticate(credentials)
        else:
            ctx = SecurityContext.anonymous()

        if not ctx.is_authenticated:
            return {"error": "Unauthorized"}, 401

        if not self._authz_service.is_allowed(ctx, permission):
            return {"error": "Forbidden"}, 403

        result = action()
        return result, 200


class SecuredViewModelAdapter:
    def __init__(self, authorization_service: AuthorizationService) -> None:
        self._authz_service = authorization_service

    def adapt(
        self,
        view_model: Dict[str, Any],
        context: SecurityContext,
    ) -> Dict[str, Any]:
        actions = view_model.get("actions", [])
        allowed_actions = [
            act for act in actions if self._authz_service.is_allowed(context, act)
        ]

        adapted_vm = dict(view_model)
        adapted_vm["allowed_actions"] = allowed_actions
        return adapted_vm
