"""
Framework settings.

Provides a central configuration object for AI Website Framework.
"""

from typing import Any

from framework.core.exceptions import ConfigurationError


class Settings:
    """
    Stores Framework configuration values.
    """

    def __init__(self, initial_values: dict[str, Any] | None = None):
        self._values: dict[str, Any] = {}

        if initial_values:
            self._values.update(initial_values)

    def set(self, key: str, value: Any) -> None:
        """
        Store or update a configuration value.
        """

        self._values[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Return a configuration value.

        Returns the provided default when the key does not exist.
        """

        return self._values.get(key, default)

    def require(self, key: str) -> Any:
        """
        Return a required configuration value.

        Raises ConfigurationError when the key does not exist.
        """

        if key not in self._values:
            raise ConfigurationError(f"Required setting '{key}' is missing.")

        return self._values[key]

    def has(self, key: str) -> bool:
        """
        Check whether a configuration key exists.
        """

        return key in self._values

    def all(self) -> dict[str, Any]:
        """
        Return a copy of all configuration values.
        """

        return self._values.copy()


settings = Settings()
