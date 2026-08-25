from dataclasses import dataclass


@dataclass(frozen=True)
class UsernamePasswordCredentials:
    username: str
    password: str

    def __post_init__(self) -> None:
        if not self.username or not self.username.strip():
            raise ValueError("Username cannot be empty or whitespace.")
        if not self.password or not self.password.strip():
            raise ValueError("Password cannot be empty or whitespace.")


@dataclass(frozen=True)
class TokenCredentials:
    token: str

    def __post_init__(self) -> None:
        if not self.token or not self.token.strip():
            raise ValueError("Token cannot be empty or whitespace.")
