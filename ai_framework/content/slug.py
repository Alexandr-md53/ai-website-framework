from __future__ import annotations
import re
from dataclasses import dataclass

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class Slug:
    """
    Domain value object for content slugs.
    Behavior-preserving: rejects invalid, preserves valid exactly.
    No filesystem rules — those are owned by the output writer layer.
    No auto-lowercase normalization in constructor.
    """

    value: str

    def __post_init__(self):
        raw = self.value
        if not isinstance(raw, str):
            raise ValueError(f"slug must be str, got {type(raw)}")
        trimmed = raw.strip()
        if not trimmed:
            raise ValueError("slug must be non-empty")
        if "/" in trimmed or "\\" in trimmed:
            raise ValueError(f"invalid slug {raw!r}: must not contain / or \\")
        if not _SLUG_RE.match(trimmed):
            raise ValueError(f"invalid slug {raw!r}: must match {_SLUG_RE.pattern}")
        if trimmed != raw:
            object.__setattr__(self, "value", trimmed)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def try_normalize(cls, raw: str) -> "Slug":
        """
        Explicit opt-in normalization, NOT used by constructor.
        Converts "Hello World" -> "hello-world" etc.
        """
        if not isinstance(raw, str):
            raise ValueError("raw must be str")
        normalized = raw.strip().lower()
        normalized = normalized.replace("_", "-").replace(" ", "-")
        normalized = re.sub(r"[^a-z0-9-]", "", normalized)
        normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
        if not normalized:
            raise ValueError(f"cannot normalize {raw!r} to valid slug")
        if not _SLUG_RE.match(normalized):
            raise ValueError(
                f"cannot normalize {raw!r} to valid slug, got {normalized!r}"
            )
        return cls(normalized)

    @property
    def pattern(self) -> str:
        return _SLUG_RE.pattern
