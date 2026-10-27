"""Telegram text formatting: escaping, limits and pure split helpers.

The adapter in stage 3 sends ONE message per publication: if the escaped text is
longer than ``TEXT_LIMIT`` the send fails closed before any HTTP request.  The
split helpers exist for future stages and for tests of the pure functions.
"""
from __future__ import annotations

from typing import List

TEXT_LIMIT = 4096
CAPTION_LIMIT = 1024


def escape_html(text: str) -> str:
    """Escape ``&`` first, then ``<`` and ``>`` (no tag allowlist in S1)."""
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _normalize_newlines(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


def split_escaped(escaped: str, limit: int = TEXT_LIMIT) -> List[str]:
    """Greedy split without losing characters: ``"".join(parts) == escaped``."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    text = str(escaped or "")
    if not text:
        return []
    parts: List[str] = []
    start = 0
    total = len(text)
    while total - start > limit:
        window = text[start : start + limit]
        cut = window.rfind("\n\n")
        if cut > 0:
            cut += 2
        else:
            cut = window.rfind("\n")
            if cut > 0:
                cut += 1
            else:
                cut = window.rfind(" ")
                if cut > 0:
                    cut += 1
                else:
                    cut = limit
        parts.append(text[start : start + cut])
        start += cut
    tail = text[start:]
    if tail:
        parts.append(tail)
    return [part for part in parts if part]


def prepare_messages(raw_text: str, limit: int = TEXT_LIMIT) -> List[str]:
    """Escape, normalize newlines, split; pure utility (not used for delivery)."""
    escaped = escape_html(_normalize_newlines(raw_text))
    return split_escaped(escaped, limit)


def caption(raw_text: str, limit: int = CAPTION_LIMIT) -> str:
    """Escaped caption trimmed to ``limit`` characters."""
    escaped = escape_html(_normalize_newlines(raw_text))
    return escaped[: max(0, int(limit))]
