from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeneratedPage:
    """
    Framework-level value object — immutable, no domain deps.
    path: relative output path, e.g. "index.html" or "posts/hello/index.html"
    html: rendered content
    kind: logical kind — index | post | category | tag | rss | sitemap | custom
    """

    path: str
    html: str
    kind: str
