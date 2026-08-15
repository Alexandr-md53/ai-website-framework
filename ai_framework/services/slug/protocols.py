"""
Public Protocols for Slug Service (SLG_01).
"""

from typing import Callable, Optional, Protocol


class TransliterationEngineProtocol(Protocol):
    def transliterate(self, text: str, locale: Optional[str] = None) -> str: ...


class CollisionResolverProtocol(Protocol):
    def resolve(
        self,
        base_slug: str,
        is_available: Callable[[str], bool],
        max_length: Optional[int] = None,
    ) -> str: ...


class SlugGeneratorProtocol(Protocol):
    def generate(
        self,
        text: str,
        *,
        locale: Optional[str] = None,
        max_length: Optional[int] = 255,
    ) -> str: ...

    def generate_unique(
        self,
        text: str,
        *,
        is_available: Callable[[str], bool],
        locale: Optional[str] = None,
        max_length: Optional[int] = 255,
    ) -> str: ...
