from ai_framework.security import (
    Identity,
    InMemoryAuthenticationProvider,
    UsernamePasswordCredentials,
    TokenCredentials,
)


def test_in_memory_provider_returns_identity_or_none():
    id_1 = Identity(id="1")
    id_2 = Identity(id="2")

    provider = InMemoryAuthenticationProvider(
        users={"admin": ("secret", id_1)},
        tokens={"valid-token": id_2},
    )

    # Valid / Invalid Passwords
    auth_user = provider.authenticate(UsernamePasswordCredentials("admin", "secret"))
    assert auth_user == id_1
    assert provider.authenticate(UsernamePasswordCredentials("admin", "wrong")) is None
    assert (
        provider.authenticate(UsernamePasswordCredentials("unknown", "secret")) is None
    )

    # Valid / Invalid Tokens
    auth_token = provider.authenticate(TokenCredentials("valid-token"))
    assert auth_token == id_2
    assert provider.authenticate(TokenCredentials("invalid-token")) is None
