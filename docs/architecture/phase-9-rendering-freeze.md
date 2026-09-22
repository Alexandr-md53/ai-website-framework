Phase 9.4 — Rendering Pipeline v1.0 Freeze
Status: CLOSED
Baseline: f38fc76 / 663 passed
Tag: phase-9.3-blog-rendering-migrated (now phase-9-rendering-pipeline-green)
Previous baseline: 161e23e / 657 passed (phase-8-publishable-lifecycle-green) — unchanged

This document is a freeze of proven state, no new runtime changes.

Rendering Pipeline v1.0 Contract
Domain → Generator → Renderer (Jinja) → Output via StaticSiteWriter
Framework owns (ai_framework/rendering)
GeneratedPage — immutable VO: path: str (relative), html: str, kind: str — frozen, slots — single output value object
TemplateRendererProtocol — render(template_name: str, context: dict) -> str — 1 method, generic
JinjaTemplateRenderer — framework impl of TemplateRendererProtocol, owns templates_dir, no domain semantics
SeoContext — pure data: seo_title, seo_description, og_title, og_description, canonical_url, title — normalize(data: dict, title_fallback) -> SeoContext — no HTML
SeoInjector — pure HTML transformation: ensure_seo(html: str, seo: SeoContext) -> str — empty strings mean do not render tag, except seo_title required fallback
StaticSiteWriter — single generic filesystem boundary — write(pages: List[GeneratedPage], out_dir: Path, clean: bool) -> List[Path]
StaticSiteGeneratorProtocol — generate() -> List[GeneratedPage] — structural Protocol, no write(), no isinstance base class, no factory/registry
Showcases own
domain-specific routes (blog_cms: posts/, categories/, tags/, rss.xml, sitemap.xml; docs_site: guides/, sections/, versions/, sitemap.xml)
page semantics (index | post | category | tag | doc | section | version | rss | sitemap)
domain data/context (Post.to_dict(), DocPage.to_dict(), category_name, author_name, section, version)
blog/docs rendering decisions (which template, which context, _ensure_post_links fallback)
BlogRenderer / DocsRenderer — composition only, no inheritance from framework
Filesystem
StaticSiteWriter is the single generic filesystem boundary.
Generated output must pass through StaticSiteWriter.
duplicate paths fail fast: ValueError: Duplicate GeneratedPage path
absolute / traversal / drive-prefixed paths are rejected:
"/...", "\...", "C:...", ".." in parts, PurePosixPath.is_absolute(), PureWindowsPath.is_absolute()
clean=True removes out_dir before write — deterministic, no stale files
clean=False merges/overwrites
Security checks are Windows-safe (PurePosix + PureWindows)
Generator
generate() -> list[GeneratedPage] — pure, no I/O, deterministic, same domain state → same output
no write() in StaticSiteGeneratorProtocol — I/O outside generator contract
generation remains domain → pages
filesystem I/O remains outside generator contract
Empty published list → still generates index.html (0 items), rss, sitemap — no crash
Explicitly NOT framework
blog URLs (/posts/<slug>/, /categories/<slug>/, /tags/<slug>/)
docs URLs (/guides/<slug>/, /sections/<slug>/, /versions/<slug>/)
taxonomy (categories, tags, sections, versions)
deployment (output dir choice, server, CDN)
identity/auth (X-User-Id, X-User-Role, PipelineContext, UserContext)
factories (create_app, create_test_app, build_cms_lite_app)
frozen routes (FROZEN_ROUTES)
RenderingEngine / BaseRenderer / umbrella rendering abstraction — rejected, no evidence from two consumers
Proof Chain
Phase 6 rendering primitives (Jinja, SeoContext/SeoInjector, GeneratedPage, StaticSiteWriter)
        ↓
Phase 7 second Type B consumer (docs_site + blog_cms both use same primitives)
        ↓
Phase 7.2 StaticSiteGeneratorProtocol + duplicate fail-fast + docs/architecture/type_b_static_site.md
        ↓
Phase 9.2 Rendering Contract v1.0 — f4cd440 / 657 passed
        - GeneratedPage VO, TemplateRendererProtocol 1 method, SeoContext/SeoInjector separation
        - StaticSiteWriter one FS boundary, legacy blog Renderer as migration target, docs_site as reference
        ↓
Phase 9.3 blog migration — f38fc76 / 663 passed
        - BlogRenderer composes JinjaTemplateRenderer+SeoContext+SeoInjector
        - GeneratedPage from framework (no local dataclass)
        - SiteGenerator.write() delegates to StaticSiteWriter one FS boundary
        - duplicate fail-fast and ..//C: guards
        - StaticSiteGeneratorProtocol without write()
        - tests: test_blog_cms_e2e.py (G1/G2/G12) + test_phase9_3_rendering_security.py (5 FS guards)
Previous baseline preserved
phase-8-publishable-lifecycle-green
161e23e / 657 passed
Scope: PublishStatus+Slug+Protocol+list_published
Non-scope: identity/serialization/taxonomy/rendering/FS
Consumers: Post + DocPage
Proof chain: 0606655/629 -> d17af75/639 -> e960a48/648 -> 0c27a29/657 -> 161e23e/657
Status: UNCHANGED — no modifications in Phase 9
Freeze Criteria — Verified
powershell
python -m pytest -q
# 663 passed in ~11s

git status --short
# (clean after commit)

git log --oneline --decorate -5
# f38fc76 (HEAD -> master, tag: phase-9.3-blog-rendering-migrated, origin/master) phase-9.3...
# f4cd440 (tag: phase-9.2-rendering-contract) phase-9.2...
# 161e23e (tag: phase-8-publishable-lifecycle-green) phase-8.6...
ai_framework/rendering does not import blog_cms / docs_site / BlogCmsService / BlogRenderer / DocsService
SeoInjector does not contain hardcoded "/posts/" literal
TemplateRendererProtocol is generic, 1 method
StaticSiteGeneratorProtocol contains generate, does NOT contain write
GeneratedPage defined once in framework (generated_page.py)
StaticSiteWriter generic, no blog deps
Boundary Decisions (Evidence-Based)
No umbrella RenderingEngine — two consumers prove TemplateRenderer + Seo + Writer is sufficient
No BaseRenderer runtime base class — Protocol + composition sufficient, no isinstance
No factory/registry in framework — app_factory.py remains showcase-owned
No deployment logic in framework — out_dir is caller's concern
No taxonomy logic in framework — categories/tags/sections are domain
No slug filesystem rules in framework — Slug VO owns domain validity, StaticSiteWriter owns FS safety
Next Baseline
After this freeze tag:

phase-9-rendering-pipeline-green
Baseline: f38fc76 / 663 passed
Phase 9 CLOSED → Rendering Pipeline v1.0 frozen.

Next architectural candidate must start from baseline f38fc76 / 663 passed, must not extend rendering contract without new evidence from ≥2 consumers, must not reintroduce rejected abstractions (RenderingEngine, BaseRenderer, write() in generator protocol, factory in framework).

No further changes to ai_framework/rendering without documented consumer need.

