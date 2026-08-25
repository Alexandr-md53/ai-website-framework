from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    FrozenSet,
    List,
    Optional,
    Protocol,
    Tuple,
    runtime_checkable,
)

from ai_framework.security.credentials import (
    UsernamePasswordCredentials,
    TokenCredentials,
)


@dataclass(frozen=True)
class Permission:
    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Permission name cannot be empty or whitespace.")


@dataclass(frozen=True)
class Role:
    name: str
    permissions: FrozenSet[Permission] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Identity:
    id: str
    roles: FrozenSet[Role] = field(default_factory=frozenset)
    attributes: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SecurityContext:
    identity: Optional[Identity] = None

    @property
    def is_authenticated(self) -> bool:
        return self.identity is not None

    @classmethod
    def anonymous(cls) -> "SecurityContext":
        return cls(identity=None)


@runtime_checkable
class AuthenticationProviderProtocol(Protocol):
    def authenticate(self, credentials: Any) -> Optional[Identity]: ...


@runtime_checkable
class AuthorizationProviderProtocol(Protocol):
    def is_allowed(
        self,
        context: SecurityContext,
        permission: str,
        resource: Optional[Any] = None,
    ) -> bool: ...


class InMemoryAuthenticationProvider:
    def __init__(
        self,
        users: Optional[Dict[str, Tuple[str, Identity]]] = None,
        tokens: Optional[Dict[str, Identity]] = None,
    ) -> None:
        self._users = users or {}
        self._tokens = tokens or {}

    def authenticate(self, credentials: Any) -> Optional[Identity]:
        if isinstance(credentials, UsernamePasswordCredentials):
            record = self._users.get(credentials.username)
            if record and record[0] == credentials.password:
                return record[1]
        elif isinstance(credentials, TokenCredentials):
            return self._tokens.get(credentials.token)
        return None


class AuthenticationService:
    def __init__(self, providers: List[AuthenticationProviderProtocol]) -> None:
        self._providers = providers

    def authenticate(self, credentials: Any) -> SecurityContext:
        for provider in self._providers:
            identity = provider.authenticate(credentials)
            if identity is not None:
                return SecurityContext(identity=identity)
        return SecurityContext.anonymous()


from ai_framework.security.authorization import (
    RoleBasedAuthorizationProvider,
    AuthorizationService,
)
