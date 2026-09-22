Type B — Static Site: Domain → Generator → Renderer → Output
Baseline: 195ae23 / extraction-rendering-primitives-v0.1-green

Contract
Domain → Generator → Renderer → Output
Components:

GeneratedPage — immutable VO: path (relative), html, kind — single output value object used by both blog_cms and docs_site
TemplateRendererProtocol — render(template_name, context) -> str — generic, 1 method
JinjaTemplateRenderer — framework impl of TemplateRendererProtocol
SeoContext — pure data normalization (dict → SeoContext)
SeoInjector — HTML transformation (html + SeoContext → html)
StaticSiteWriter — one filesystem boundary, FS safety owned here
StaticSiteGeneratorProtocol — generate() -> List[GeneratedPage] — structural, no write(), no isinstance base class
Purity
generate() is pure: same domain state (list_published) → same list of GeneratedPage, no I/O, no side effects
render() is pure: template + context → HTML, no domain deps
SeoContext.normalize() pure: dict → SeoContext
SeoInjector.ensure_seo() pure: html + SeoContext → html
Determinism / Same domain state
Same domain state produces same output — deterministic generation, no timestamps, no random
clean=True removes out_dir before write — no stale files, deterministic FS state
Unique / duplicate fail-fast
StaticSiteWriter must raise ValueError on duplicate paths (fail-fast) — prevents overwriting same file twice in one generation
Duplicate detection via set of normalized paths
FS independence
Generator → GeneratedPage (domain owns URL semantics: posts/, guides/, categories/, sections/, versions/, tags/, rss, sitemap)
Writer → filesystem (one FS boundary, FS safety: reject "..", "/", "", "C:", absolute, anchor, out_dir escape)
No showcase-local write() with raw out_dir / path — must go through StaticSiteWriter
Empty
Empty published list → still generates index.html (with 0 items), rss, sitemap — no crash
write([]) → creates out_dir, writes nothing, returns empty list
Domain Ownership
Blog: BlogSiteGenerator + BlogRenderer — owns posts/, categories/, tags/, rss, sitemap
Docs: DocsSiteGenerator + DocsRenderer — owns guides/, sections/, versions/, sitemap
Framework does NOT own blog URLs, docs URLs, taxonomy, deployment, identity/auth
StaticSiteGeneratorProtocol
Minimal: def generate(self) -> List[GeneratedPage]: ...
Does NOT contain def write — writer is separate
Structural (Protocol), no runtime base class, no isinstance required
Documented here, implemented in ai_framework/rendering/protocols.py
