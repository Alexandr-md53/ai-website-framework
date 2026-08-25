import pytest
from ai_framework.security import UsernamePasswordCredentials, TokenCredentials


def test_credentials_immutability_and_validation():
    creds = UsernamePasswordCredentials(username="admin", password="secret")

    with pytest.raises(Exception):
        creds.username = "hacker"  # type: ignore

    with pytest.raises(ValueError):
        UsernamePasswordCredentials(username="", password="secret")

    with pytest.raises(ValueError):
        TokenCredentials(token="   ")
