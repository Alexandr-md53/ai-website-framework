import pytest
from ai_framework.settings.provider import InMemorySettingsProvider
from ai_framework.settings.manager import SettingsManager


def test_settings_manager_namespace_and_get_set():
    """RED #2a: Проверка изоляции namespace и базовых get/set."""
    provider = InMemorySettingsProvider()
    site_manager = SettingsManager(provider=provider, namespace="site")
    admin_manager = SettingsManager(provider=provider, namespace="admin")

    site_manager.set("title", "My Site")
    admin_manager.set("title", "Admin Portal")

    assert site_manager.get("title") == "My Site"
    assert admin_manager.get("title") == "Admin Portal"
    # Проверка, что в провайдере физически записаны префиксированные ключи
    assert provider.get("site.title") == "My Site"
    assert provider.get("admin.title") == "Admin Portal"


def test_settings_manager_defaults_and_list():
    """RED #2b: Получение дефолтных значений и list()."""
    provider = InMemorySettingsProvider()
    defaults = {"theme": "light", "items_per_page": 10}
    manager = SettingsManager(provider=provider, namespace="site", defaults=defaults)

    # get возвращает default, если в провайдере ничего нет
    assert manager.get("theme") == "light"

    # Переопределяем одно значение
    manager.set("theme", "dark")
    assert manager.get("theme") == "dark"

    # list() объединяет defaults и пользовательские настройки
    assert manager.list() == {"theme": "dark", "items_per_page": 10}


def test_settings_manager_reset():
    """RED #2c: Сброс переопределённой настройки (reset)."""
    provider = InMemorySettingsProvider()
    defaults = {"theme": "light"}
    manager = SettingsManager(provider=provider, namespace="site", defaults=defaults)

    manager.set("theme", "dark")
    assert manager.get("theme") == "dark"

    # Сброс возвращает к дефолту и удаляет ключ из провайдера
    manager.reset("theme")
    assert manager.get("theme") == "light"
    assert provider.has("site.theme") is False