"""
Unit tests for Localization Engine.
SOP Step 7: Unit Testing (Target Coverage >= 90%)
"""

import pytest
from framework.core.localization import LocalizationEngine, LocalizationError


def test_localization_basic():
    loc = LocalizationEngine(default_locale="ru")
    loc.load_from_dict("ru", {"welcome": "Добро пожаловать!"})
    loc.load_from_dict("en", {"welcome": "Welcome!"})

    assert loc.translate("welcome", locale="ru") == "Добро пожаловать!"
    assert loc.translate("welcome", locale="en") == "Welcome!"


def test_localization_fallback():
    loc = LocalizationEngine(default_locale="en", fallback_locale="ru")
    loc.load_from_dict("ru", {"only_ru": "Только по-русски"})

    # При отсутствии ключа в en срабатывает fallback на ru
    assert loc.translate("only_ru", locale="en") == "Только по-русски"


def test_localization_formatting():
    loc = LocalizationEngine(default_locale="ru")
    loc.load_from_dict("ru", {"hello_user": "Привет, {name}!"})

    assert loc.get("hello_user", name="Алексей") == "Привет, Алексей!"


def test_localization_missing_key():
    loc = LocalizationEngine(default_locale="ru")
    assert loc.translate("non_existing_key") == "non_existing_key"


def test_localization_json_error(tmp_path):
    loc = LocalizationEngine()
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{bad json", encoding="utf-8")

    with pytest.raises(LocalizationError):
        loc.load_from_json("ru", invalid_file)
