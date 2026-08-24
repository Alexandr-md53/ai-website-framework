import pytest
from ai_framework.settings.provider import InMemorySettingsProvider
from ai_framework.settings.manager import SettingsManager
from ai_framework.settings.ui_bridge import SettingsUIBridge


def test_build_form_maps_types_and_defaults():
    """RED #3a: Построение UI-формы с маппингом типов (bool->checkbox, int->number, str->text)."""
    defaults = {
        "site_title": "My Website",
        "items_per_page": 25,
        "maintenance_mode": False,
    }
    provider = InMemorySettingsProvider()
    manager = SettingsManager(provider=provider, namespace="site", defaults=defaults)
    bridge = SettingsUIBridge(manager=manager)

    form_vm = bridge.get_form_model()

    assert len(form_vm["fields"]) == 3

    # Проверка маппинга полей
    fields_by_name = {f["name"]: f for f in form_vm["fields"]}

    assert fields_by_name["site_title"]["widget_type"] == "text"
    assert fields_by_name["site_title"]["value"] == "My Website"

    assert fields_by_name["items_per_page"]["widget_type"] == "number"
    assert fields_by_name["items_per_page"]["value"] == 25

    assert fields_by_name["maintenance_mode"]["widget_type"] == "checkbox"
    assert fields_by_name["maintenance_mode"]["value"] is False


def test_form_uses_current_manager_values_over_defaults():
    """RED #3b: Поля формы отражают переопределённые пользователем значения из SettingsManager."""
    defaults = {"theme": "light"}
    provider = InMemorySettingsProvider()
    manager = SettingsManager(provider=provider, namespace="site", defaults=defaults)
    manager.set("theme", "dark")

    bridge = SettingsUIBridge(manager=manager)
    form_vm = bridge.get_form_model()

    field = form_vm["fields"][0]
    assert field["name"] == "theme"
    assert field["value"] == "dark"


def test_namespace_does_not_leak_into_field_names():
    """RED #3c: Имена полей формы не содержат префикс namespace."""
    provider = InMemorySettingsProvider()
    manager = SettingsManager(provider=provider, namespace="admin_panel")
    manager.set("page_size", 50)

    bridge = SettingsUIBridge(manager=manager)
    form_vm = bridge.get_form_model()

    field_names = [f["name"] for f in form_vm["fields"]]
    assert "page_size" in field_names
    assert "admin_panel.page_size" not in field_names


def test_submit_updates_settings_manager():
    """RED #3d: Отправка формы (POST) сохраняет преобразованные значения в SettingsManager."""
    defaults = {
        "title": "Old Title",
        "items_per_page": 10,
        "is_active": True,
    }
    provider = InMemorySettingsProvider()
    manager = SettingsManager(provider=provider, namespace="site", defaults=defaults)
    bridge = SettingsUIBridge(manager=manager)

    submitted_data = {
        "title": "New Title",
        "items_per_page": "50",  # Из HTTP формы значения часто приходят строками
        "is_active": "false",
    }

    result = bridge.handle_submit(submitted_data)

    assert result["success"] is True
    assert manager.get("title") == "New Title"
    assert manager.get("items_per_page") == 50
    assert manager.get("is_active") is False


def test_submit_preserves_unsubmitted_settings():
    """RED #3e: Частичный POST не приводит к удалению или сбросу отсутствующих в форме настроек."""
    defaults = {"title": "Default Title", "lang": "en"}
    provider = InMemorySettingsProvider()
    manager = SettingsManager(provider=provider, namespace="site", defaults=defaults)
    manager.set("title", "Custom Title")

    bridge = SettingsUIBridge(manager=manager)

    # Отправляем только язык
    bridge.handle_submit({"lang": "fr"})

    assert manager.get("title") == "Custom Title"
    assert manager.get("lang") == "fr"
