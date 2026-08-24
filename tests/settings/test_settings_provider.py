import pytest
from ai_framework.settings.provider import (
    SettingsProviderProtocol,
    InMemorySettingsProvider,
)


def test_in_memory_provider_set_and_get():
    """RED #1a: Сохранение и получение значения по ключу."""
    provider = InMemorySettingsProvider()

    provider.set("site_name", "My AI Site")

    assert provider.get("site_name") == "My AI Site"


def test_in_memory_provider_defaults_and_has():
    """RED #1b: Дефолтные значения и проверка существования ключа."""
    provider = InMemorySettingsProvider(initial_data={"theme": "dark"})

    assert provider.has("theme") is True
    assert provider.has("missing_key") is False
    assert provider.get("missing_key", "default_val") == "default_val"
    assert provider.get_all() == {"theme": "dark"}
