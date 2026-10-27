"""Publication adapters (stage 3: Telegram only).

``ADAPTERS`` maps a platform name (stored in ``publish_channels.platform``) to a
code adapter; channels themselves stay data rows.  S1 implements Telegram text
publications only - no media, no buttons, no website publisher.
"""
from __future__ import annotations

from .base import AdapterCapabilities, PublisherAdapter
from .registry import ADAPTERS, get_adapter
from .telegram import TelegramAdapter

__all__ = [
    "ADAPTERS",
    "AdapterCapabilities",
    "PublisherAdapter",
    "TelegramAdapter",
    "get_adapter",
]
