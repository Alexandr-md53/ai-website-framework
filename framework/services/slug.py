"""
SlugService

Core Service responsible for generating human-readable,
URL-safe and unique slugs.

The service contains no knowledge about:
- ORM / Database models
- Entities
- Business domain

Uniqueness is delegated to an external callback implementing SlugExistsChecker.
"""

import re
from typing import Optional, Protocol, Sequence


class SlugExistsChecker(Protocol):
    """Protocol for checking if a slug already exists in a storage layer."""

    async def __call__(self, slug: str) -> bool: ...


class SlugService:
    """Core Service for slug generation, normalization, and validation."""

    # Таблица транслитерации кириллицы
    TRANSLIT_DICT = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }

    def __init__(
        self,
        reserved_words: Optional[Sequence[str]] = None,
        max_length: int = 80,
        separator: str = "-",
        default_fallback: str = "untitled",
    ) -> None:
        self.reserved_words = set(reserved_words or [])
        self.max_length = max_length
        self.separator = separator
        self.default_fallback = default_fallback

    def slugify(self, text: str) -> str:
        """Преобразует произвольный текст в базoвый slug."""
        if not text:
            return self.default_fallback

        text = text.lower().strip()

        # Транслитерация кириллицы
        transliterated = []
        for char in text:
            transliterated.append(self.TRANSLIT_DICT.get(char, char))
        text = "".join(transliterated)

        # Замена символов, не являющихся буквами/цифрами, на separator
        text = re.sub(r"[^a-z0-9]+", self.separator, text)

        slug = self.sanitize(text)

        if not slug:
            return self.default_fallback

        # Обрезка по max_length (с сохранением границ слов)
        if len(slug) > self.max_length:
            truncated = slug[: self.max_length]
            if self.separator in truncated:
                slug = truncated.rsplit(self.separator, 1)[0]
            else:
                slug = truncated

        return self.sanitize(slug) or self.default_fallback

    def sanitize(self, slug: str) -> str:
        """Очищает slug от дубликатов и краевых разделителей."""
        sep = re.escape(self.separator)
        # Схлопывание повторов разделителя
        slug = re.sub(f"{sep}+", self.separator, slug)
        # Обрезка с краев
        return slug.strip(self.separator)

    def is_reserved(self, slug: str) -> bool:
        """Проверяет, зарезервирован ли slug."""
        return slug.lower() in self.reserved_words

    def validate(self, slug: str) -> bool:
        """Проверяет slug на соответствие формату и правилам."""
        if not slug or len(slug) > self.max_length:
            return False

        if self.is_reserved(slug):
            return False

        # Валидны только буквы, цифры и указанный separator
        sep = re.escape(self.separator)
        pattern = f"^[a-z0-9]+({sep}[a-z0-9]+)*$"
        return bool(re.match(pattern, slug))

    async def generate(
        self,
        text: str,
        exists_checker: Optional[SlugExistsChecker] = None,
    ) -> str:
        """Генерирует гарантированно уникальный slug."""
        base_slug = self.slugify(text)
        candidate = base_slug

        counter = 1
        while True:
            # Slug непригоден, если он зарезервирован или уже существует в базе
            is_taken = self.is_reserved(candidate)
            if not is_taken and exists_checker:
                is_taken = await exists_checker(candidate)

            if not is_taken:
                return candidate

            candidate = f"{base_slug}{self.separator}{counter}"
            counter += 1
