"""Publisher adapter contract (platform-agnostic).

Stage 3 defines the shape only: an adapter is a pure function of
``send(channel, text, media)``.  It does not touch the database, does not read
job rows and never retries - the runner (stage 4) owns the queue policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..domain.publications import Channel, PublishResult


@dataclass(frozen=True)
class AdapterCapabilities:
    """What a platform can do; used by the formatter and the admin UI later."""

    platform: str
    supports_html: bool
    supports_images: bool
    supports_buttons: bool
    max_text_len: int
    max_caption_len: int


@runtime_checkable
class PublisherAdapter(Protocol):
    """Minimal adapter protocol: validate first, then send exactly once."""

    platform: str
    capabilities: AdapterCapabilities

    def validate(self, channel: Channel, text: str) -> None:
        """Raise ValidationError when the channel/text cannot be published."""

    def send(self, channel: Channel, text: str, media: Any = None) -> PublishResult:
        """Publish one message; never retries and never writes to the database."""
