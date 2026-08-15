"""
Tests for Framework settings.
"""

import pytest

from framework.core.exceptions import ConfigurationError
from framework.core.settings import Settings


def test_set_and_get_setting():
    settings = Settings()

    settings.set("language", "ru")

    assert settings.get("language") == "ru"


def test_get_returns_default_for_unknown_key():
    settings = Settings()

    assert settings.get("language", "en") == "en"


def test_initial_values_are_available():
    settings = Settings(
        {
            "language": "ro",
            "debug": True,
        }
    )

    assert settings.get("language") == "ro"
    assert settings.get("debug") is True


def test_require_returns_existing_value():
    settings = Settings(
        {
            "api_key": "test-key",
        }
    )

    assert settings.require("api_key") == "test-key"


def test_require_raises_error_for_unknown_key():
    settings = Settings()

    with pytest.raises(ConfigurationError):
        settings.require("api_key")


def test_has_checks_key_existence():
    settings = Settings()

    settings.set("debug", False)

    assert settings.has("debug") is True
    assert settings.has("language") is False


def test_all_returns_copy_of_values():
    settings = Settings(
        {
            "language": "ru",
        }
    )

    result = settings.all()
    result["language"] = "en"

    assert settings.get("language") == "ru"
