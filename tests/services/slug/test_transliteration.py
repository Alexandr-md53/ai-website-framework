"""
TDD Suite: Transliteration Engine (ADR-001, ADR-002)
"""

import pytest
from ai_framework.services.slug import DefaultTransliterationEngine


@pytest.fixture
def engine() -> DefaultTransliterationEngine:
    return DefaultTransliterationEngine()


def test_transliteration_latin_and_diacritics(
    engine: DefaultTransliterationEngine,
) -> None:
    """Проверка очистки диакритики для латиницы."""
    assert engine.transliterate("Café") == "Cafe"
    assert engine.transliterate("Crème brûlée") == "Creme brulee"


def test_transliteration_cyrillic_ru_default(
    engine: DefaultTransliterationEngine,
) -> None:
    """ADR-001: Базовая транслитерация кириллицы (ru по умолчанию)."""
    assert engine.transliterate("Москва") == "Moskva"
    assert engine.transliterate("Красная роза") == "Krasnaya roza"
    assert engine.transliterate("Подъезд и съезд") == "Podezd i sezd"  # ь, ъ -> ""
    assert engine.transliterate("Жираф, Щука, Чайка") == "Zhiraf, Shchuka, Chayka"


def test_transliteration_cyrillic_uk_locale(
    engine: DefaultTransliterationEngine,
) -> None:
    """ADR-002: Специфичные правила для украинского языка (locale='uk')."""
    text = "Україна, Київ, Ґанок"
    result = engine.transliterate(text, locale="uk")
    assert result == "Ukrayina, Kyyiv, Ganok"


def test_transliteration_german_de_locale(engine: DefaultTransliterationEngine) -> None:
    """ADR-002: Специфичные правила для немецкого языка (locale='de')."""
    text = "Großes Ärgernis Überall"
    result = engine.transliterate(text, locale="de")
    assert result == "Grosses Aergernis Ueberall"


def test_transliteration_unknown_locale_fallback(
    engine: DefaultTransliterationEngine,
) -> None:
    """Неизвестная локаль не ломает выполнение, а использует дефолтный маппинг."""
    result = engine.transliterate("Привет", locale="xyz")
    assert result == "Privet"
