"""
Main SlugGenerator implementation (SLG_01).
"""

import re
from typing import Callable, Optional

from .engine import DefaultTransliterationEngine
from .exceptions import SlugGenerationError
from .protocols import (
    CollisionResolverProtocol,
    TransliterationEngineProtocol,
)
from .resolver import DefaultCollisionResolver


class SlugGenerator:
    def __init__(
        self,
        transliteration_engine: Optional[TransliterationEngineProtocol] = None,
        collision_resolver: Optional[CollisionResolverProtocol] = None,
    ) -> None:
        self._transliteration_engine = (
            transliteration_engine or DefaultTransliterationEngine()
        )
        self._collision_resolver = collision_resolver or DefaultCollisionResolver()

    def generate(
        self,
        text: str,
        *,
        locale: Optional[str] = None,
        max_length: Optional[int] = 255,
    ) -> str:
        if not text or not text.strip():
            raise SlugGenerationError("Empty text provided")

        # 1. Transliterate
        transliterated = self._transliteration_engine.transliterate(text, locale=locale)

        # 2. Lowercase and replace non-alphanumeric with separators
        lowered = transliterated.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")

        if not slug:
            raise SlugGenerationError("No valid characters for slug generation")

        # 3. Truncate to max_length without trailing dash
        if max_length and len(slug) > max_length:
            slug = slug[:max_length].rstrip("-")

        return slug

    def generate_unique(
        self,
        text: str,
        *,
        is_available: Callable[[str], bool],
        locale: Optional[str] = None,
        max_length: Optional[int] = 255,
    ) -> str:
        base_slug = self.generate(text, locale=locale, max_length=max_length)
        return self._collision_resolver.resolve(
            base_slug, is_available=is_available, max_length=max_length
        )
