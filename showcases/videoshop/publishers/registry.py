"""Publisher registry: platform name -> adapter instance.

Channels are data; adapters are code.  Stage 3 registers only Telegram, and the
registry is the single lookup point for future platforms (website is not part of
S1 and must stay unknown).
"""
from __future__ import annotations

from typing import Dict

from ..domain.catalog import ValidationError
from .base import PublisherAdapter
from .telegram import TelegramAdapter

ADAPTERS: Dict[str, PublisherAdapter] = {"telegram": TelegramAdapter()}


def get_adapter(platform: str) -> PublisherAdapter:
    """Return the adapter for ``platform``; unknown platforms are a validation error."""
    adapter = ADAPTERS.get(str(platform))
    if adapter is None:
        raise ValidationError(f"unsupported publication platform: {platform!r}")
    return adapter


__all__ = ["ADAPTERS", "get_adapter"]
