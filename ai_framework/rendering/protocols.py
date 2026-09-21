from __future__ import annotations
from typing import Protocol, List

from .generated_page import GeneratedPage


class TemplateRendererProtocol(Protocol):
    def render(self, template_name: str, context: dict) -> str: ...


class StaticSiteGeneratorProtocol(Protocol):
    """
    Framework-level minimal contract for Type-B static site generation.
    Justified by two independent real consumers:
      - BlogSiteGenerator (posts/categories/tags/rss/sitemap)
      - DocsSiteGenerator (guides/sections/versions/sitemap)

    Architecture preserved:
        Domain
          ↓
        Generator (pure)
          ↓
        List[GeneratedPage] (immutable value object)
          ↓
        StaticSiteWriter (I/O boundary, validated)
          ↓
        filesystem

    Semantics (contract, not immediate impl optimization):
    - Purity: generate() must not access filesystem, network, or global state. Domain state -> pages only.
    - FS independence: must be testable without temp dirs.
    - Unique relative paths: generate() SHOULD produce unique relative paths (no.., no absolute, no empty).
      StaticSiteWriter MUST reject duplicate paths with ValueError (fail-fast, no silent overwrite).
    - Determinism: Same domain state -> same ordered List[GeneratedPage] with identical content.
      Insertion-order dicts are acceptable as baseline, but ordering must be stable for same state.
    - Empty content: Must not raise on empty published set. Returns index.html + sitemap.xml with zero entries (deterministic).
    - No write() in protocol: I/O is separate concern owned by StaticSiteWriter.
    """

    def generate(self) -> List[GeneratedPage]: ...
