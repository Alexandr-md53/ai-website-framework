"""
Universal Localization Engine for AI Website Framework.
SOP Step 6: Core Implementation (Zero Domain Knowledge)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from framework.core.exceptions import FrameworkError


class LocalizationError(FrameworkError):
    """Ошибки модуля локализации."""

    pass


class LocalizationEngine:
    """
    Универсальный движок локализации текстов UI и контента.
    Не содержит привязок к конкретным бизнес-доменам.
    """

    def __init__(self, default_locale: str = "ru", fallback_locale: str = "ru"):
        self.default_locale = default_locale
        self.fallback_locale = fallback_locale
        self._translations: Dict[str, Dict[str, str]] = {}

    def load_from_dict(self, locale: str, data: Dict[str, str]) -> None:
        """Загружает словарь переводов для указанной локали."""
        if locale not in self._translations:
            self._translations[locale] = {}
        self._translations[locale].update(data)

    def load_from_json(self, locale: str, file_path: str | Path) -> None:
        """Загружает переводы из JSON-файла."""
        path = Path(file_path)
        if not path.exists():
            raise LocalizationError(f"Файл локализации не найден: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.load_from_dict(locale, data)
        except json.JSONDecodeError as err:
            raise LocalizationError(
                f"Ошибка чтения JSON локализации {path}: {err}"
            ) from err

    def translate(self, key: str, locale: Optional[str] = None, **kwargs: Any) -> str:
        """
        Возвращает переведенную строку по ключу.
        Поддерживает форматирование перевода через kwargs и безопасный fallback.
        """
        target_locale = locale or self.default_locale

        # 1. Поиск в целевой локали
        text = self._translations.get(target_locale, {}).get(key)

        # 2. Fallback на резервный язык
        if text is None and target_locale != self.fallback_locale:
            text = self._translations.get(self.fallback_locale, {}).get(key)

        # 3. Если перевод не найден — возвращаем сам ключ
        if text is None:
            return key

        # Подстановка динамических переменных
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text

        return text

    def get(self, key: str, locale: Optional[str] = None, **kwargs: Any) -> str:
        """Алиас для короткого вызова метода translate."""
        return self.translate(key, locale=locale, **kwargs)
