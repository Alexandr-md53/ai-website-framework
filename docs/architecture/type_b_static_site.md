# Type B — Static / Generated Site

## Overview
Type B showcases generate static sites from domain state.
Domain
↓
Generator (pure)
↓
List (immutable value object)
↓
StaticSiteWriter (I/O boundary, validated)
↓
filesystem[GeneratedPage]

## Primitives (ai_framework/rendering)
- `GeneratedPage` — immutable: path (relative), html, kind
- `SeoContext` + `SeoInjector` — generic SEO, no domain knowledge
- `JinjaTemplateRenderer` — generic template_name + context
- `StaticSiteWriter` — generic writer with safety: relative only, no.., no absolute, no duplicate paths (fail-fast)

## StaticSiteGeneratorProtocol (Phase 7.2)
Minimal contract justified by two independent consumers:
- BlogSiteGenerator: posts/<slug>/, categories/<slug>/, tags/<slug>/, rss.xml, sitemap.xml
- DocsSiteGenerator: guides/<slug>/, sections/<slug>/, versions/<slug>/, sitemap.xml

```python
class StaticSiteGeneratorProtocol(Protocol):
    def generate(self) -> list[GeneratedPage]:...
    Intentionally does NOT include write(). I/O is separate concern owned by StaticSiteWriter.

Semantics (contract)
Purity / FS independence:

generate() must not access filesystem, network, or global state.
Testable without temp dirs.
Unique relative paths:

generate() SHOULD produce unique relative paths (no.., no absolute, no empty).
StaticSiteWriter MUST reject duplicate paths with ValueError (fail-fast, no silent overwrite).
Determinism (contract, not immediate impl):

Same domain state → same ordered List with identical content.[GeneratedPage]
Current services using insertion-order dicts are acceptable as baseline as long as ordering is stable for same state.
No requirement to rewrite domain services immediately for sorting; sorting can be added only if it does not change expected output.
Empty content:

Must not raise on empty published set.
Returns at least index.html + sitemap.xml with zero entries (deterministic).
URL independence:

Framework does not know about posts/, guides/, categories/, tags/, sections/, versions/.
Those conventions are owned by showcase-local Renderers.
Showcase-local ownership
BlogRenderer owns posts/, categories/, tags/, rss/sitemap
DocsRenderer owns guides/, sections/, versions/, sitemap
Both use same framework primitives
Anti-goals
No base class Generator
No factory/registry
No domain logic extraction in Phase 7.2
No write() in protocol
