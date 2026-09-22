Phase 10 Architecture Audit v0.1
Baseline: cd0b9a9 / phase-9-rendering-pipeline-green / 663 passed
Date: 2026-09-22
Type: Audit only — no runtime changes

Frozen Boundaries (must not be reopened without ≥2 consumers evidence)
Phase 8 — Publishable Lifecycle
PublishStatus, Slug, Publishable Protocol, list_published() generic filter
Consumers: Post, DocPage
Tag: phase-8-publishable-lifecycle-green / 161e23e / 657 passed preserved
Non-scope: identity, serialization, taxonomy, rendering, FS, deployment
Phase 9 — Rendering Pipeline v1.0
GeneratedPage VO (frozen, slots), TemplateRendererProtocol (1 method), JinjaTemplateRenderer, SeoContext, SeoInjector, StaticSiteWriter (single FS boundary, duplicate fail-fast, .. / \ C: guards), StaticSiteGeneratorProtocol.generate() -> List[GeneratedPage] (no write)
Consumers: blog_cms, docs_site — two independent Type B generators
Tags: phase-9.2-rendering-contract f4cd440, phase-9.3-blog-rendering-migrated f38fc76, phase-9-rendering-pipeline-green cd0b9a9
Explicitly NOT framework: blog/docs URLs, taxonomy, deployment, identity/auth, factories, frozen routes, RenderingEngine/BaseRenderer umbrella
Current Framework Inventory
ai_framework/
├── content/
│   ├── slug.py — Slug VO, try_normalize(), pattern — framework-owned, no FS
│   ├── publishable.py — PublishStatus Enum, Publishable Protocol, list_published() helper
│   └── seo_meta.py? — SeoMeta domain? Actually SeoMeta in domain, SeoContext in rendering
├── rendering/
│   ├── generated_page.py — GeneratedPage(path, html, kind) — frozen
│   ├── protocols.py — TemplateRendererProtocol + StaticSiteGeneratorProtocol
│   ├── jinja.py — JinjaTemplateRenderer(templates_dir)
│   ├── seo.py — SeoContext.normalize() + SeoInjector.ensure_seo()
│   └── static_writer.py — StaticSiteWriter.write(pages, out_dir, clean=True) — single boundary
├── security? — no dedicated module, guards in StaticSiteWriter + PipelineContext
└── __init__ re-exports

showcases/
├── cms_lite/ — Type A CRUD, body role (Phase 4 old) + header role (Phase 5 new) dual factory
│   ├── domain/user.py — UserContext / PipelineContext? UserRole ADMIN/EDITOR/VIEWER
│   ├── services/cms_service.py — CRUD + media + publish
│   └── api/app_factory.py — final_dual_factory_v7.py reference
├── blog_cms/ — Type B Static/Generated, Phase 9.3 migrated to framework primitives
│   ├── domain/user.py — PipelineContext.from_raw(headers), UserRole ADMIN/EDITOR/GENERATOR/VIEWER
│   ├── domain/models.py — Post, Category, Tag, Author, SeoMeta
│   ├── services/blog_service.py — create_category/tag/author/post, publish, duplicate, list_published(category_slug, tag_slug)
│   ├── services/blog_renderer.py — BlogRenderer composes JinjaTemplateRenderer+SeoContext+SeoInjector — owns posts/, categories/, tags/, rss, sitemap
│   ├── services/site_generator.py — SiteGenerator(generate() + write() delegates to StaticSiteWriter) + Renderer alias
│   └── api/app_factory.py — FROZEN_ROUTES 17 routes, create_app + create_test_app
└── docs_site/ — Type B Static/Generated, reference for Phase 7
    ├── domain/models.py — DocPage, Section, Version, DocStatus, SeoMeta
    └── services/docs_renderer.py + docs_site_generator.py — guides/, sections/, versions/

tests/
├── test_blog_cms_e2e.py — frozen routes smoke + auth guard + G1/G2/G12 generation + SEO persist
├── test_docs_site_e2e.py — second consumer e2e
├── test_phase9_3_rendering_security.py — FS guards: traversal, absolute, drive, delegation
├── test_phase8_*.py — publishable lifecycle guards
└── ~663 total

docs/architecture/
├── type_b_static_site.md — Purity / Determinism / Unique / FS independence / Empty
├── phase-9-rendering-freeze.md — Phase 9 CLOSED contract
├── gap-matrix-v0.3-reviewed.md — historical
└── RENDERER_EXTRACTION_AUDIT_v0.1.md — historical
Consumer Matrix (behavior, not fields)
Feature	cms_lite	blog_cms	docs_site	Framework already has?
Identity from headers	X-User-Id/Role → UserContext	X-User-Id/Role → PipelineContext	X-User-Id/Role → ?	No — two different Context classes
Auth guard	_require_roles	_require() + service._require	similar	No — duplicated pattern
Factory dual	create_app / create_test_app + old body-role vs new header-role	create_app / create_test_app	similar	No — each showcase owns
Frozen routes	CMS routes	17 routes BLOG	DOCS routes	No — showcase-owned
CRUD Category/Tag	Category, Tag	Category, Tag, Author	Section, Version	No — looks similar but semantics differ (Phase 8 lesson)
Publishable	ItemStatus	PostStatus	DocStatus	Yes — PublishStatus + Protocol + list_published generic — frozen
Rendering	N/A Type A	BlogRenderer + SiteGenerator	DocsRenderer + DocsSiteGenerator	Yes — rendering pipeline frozen
SEO	seo_title etc in Item	SeoMeta in Post + SeoContext/SeoInjector	SeoMeta in DocPage + same	Framework: SeoContext/SeoInjector generic, SeoMeta domain
Media/Assets	media attach/detach	N/A	N/A	No — only cms_lite
Slug handling	Slug VO?	slug field in Category/Tag/Post	slug in Section/Version/DocPage	Yes — Slug VO framework
FS boundary	no FS	StaticSiteWriter	StaticSiteWriter	Yes — frozen
Validation	ValidationError, NotFoundError, PermissionDeniedError	same triple	same triple	Duplicated — each service defines own?
Shared-Pattern Evidence (deep scan, not field-name similarity)
1. Auth / UserContext — HIGH interest
Where: showcases/cms_lite/domain/user.py (UserContext, UserRole ADMIN/EDITOR/VIEWER), showcases/blog_cms/domain/user.py (PipelineContext.from_raw(headers), UserRole ADMIN/EDITOR/GENERATOR/VIEWER), showcases/docs_site/domain/user.py (similar)
Consumers: 3 showcases, all use X-User-Id, X-User-Role headers → Context → _require_roles / _require
Same semantics? Yes — header normalization, role hierarchy, permission denied 403, viewer forbidden for write. Difference: blog_cms has extra GENERATOR role for /site/generate.
Same lifecycle? Yes — created per request at API boundary, passed to service methods, not stored.
Framework contains analogue? No — framework has no identity module. Security guards are in StaticSiteWriter only.
Security / correctness implications: HIGH — auth is security-critical, centralizing wrong could leak role escalation. Current duplication risks inconsistent normalization (from_raw vs direct). Evidence shows final_dual_factory_v7.py had _make_user_context and _map_role_str duplicating logic.
Extraction risk: MEDIUM-HIGH — if we extract PipelineContext too early we may freeze wrong role set. Need to check if GENERATOR role is generic or blog-specific.
Verdict: Candidate, but needs contract audit: PipelineContext.from_raw(), UserRole, _require() protocol.
2. Factories — MEDIUM
Where: blog_cms/api/app_factory.py create_app + create_test_app with state cache, cms_lite/api/app_factory.py dual factory old/new, docs_site/api/app_factory.py
Consumers: 3
Same semantics? Partial — all create FastAPI, expose service + generator in app.state, define FROZEN_ROUTES. Differences: blog_cms has out_dir + state pages cache, cms_lite has media.
Framework analogue? No.
Risk: Factories contain showcase-specific DI (renderer, out_dir). Generic factory would become umbrella.
Verdict: MEDIUM — pattern exists but abstraction would likely become RenderingEngine-style umbrella, which Phase 9 forbade. Keep local, maybe extract tiny helper create_test_client? Not yet.
3. Routes / Registration — MEDIUM
Where: FROZEN_ROUTES sets in each factory, repeated @app.post("/categories") etc.
Consumers: 3
Same semantics? No — routes are domain-specific (blog has /site/generate, cms_lite has /media). Shared is FastAPI boilerplate, not domain behavior.
Verdict: MEDIUM but OUT OF SCOPE for framework — FastAPI already provides routing.
4. Forms / Validation — MEDIUM
Where: ValidationError, NotFoundError, PermissionDeniedError repeated in each service, slug validation via Slug VO vs inline lower().replace()
Consumers: 3 services define same triple error classes.
Same semantics? Yes — validation → 400, not found → 404, permission → 403 mapping in factories _to_dict helpers.
Framework analogue? Partial — Slug VO exists, but error triple is duplicated.
Security: Low — but inconsistency risks.
Verdict: MEDIUM — tiny extraction candidate: shared exception hierarchy + _parse_uuid helper. However Phase 8 non-scope explicitly said identity/serialization not in scope. Could be small.
5. Assets / Storage — MEDIUM (cms_lite only)
Where: cms_lite media attach/detach, blog_cms no assets, docs_site maybe assets?
Consumers: 1 (cms_lite) — not enough for framework.
Verdict: SHOWCASE-SPECIFIC — 1 consumer → local implementation.
6. Transactions / UoW — LOW/MEDIUM
Where: Services use in-memory dicts _categories, _authors, etc., no DB, no transaction. No UoW pattern yet.
Consumers: 1 pattern per service, not shared.
Verdict: LOW — no evidence, out of scope.
7. Taxonomy — Category/Tag/Section/Version — DO NOT TOUCH
Where: blog_cms has Category, Tag, Author; docs_site has Section, Version; cms_lite has Category, Tag
Consumers: 3, fields look similar (id, name, slug, description)
Same semantics? NO — Phase 8 lesson: Category in blog is taxonomy for published filtering, Section in docs is grouping with different lifecycle, Version has no description. Generic BaseTaxonomy would collapse different invariants.
Framework analogue? No, and should stay no.
Verdict: SHOWCASE-SPECIFIC — historical trap, explicitly deferred.
8. Rendering — CLOSED
Frozen in Phase 9. Do not reopen.
9. Publishable — CLOSED
Frozen in Phase 8. Do not reopen.
Untracked Audit Files Classification (current git status)
?? docs/RENDERER_EXTRACTION_AUDIT_v0.1.md
?? docs/architecture/gap-matrix-v0.3-reviewed.md
?? docs/architecture/phase-9-audit-v0.1.md
?? showcases/cms_lite_phase5/
docs/RENDERER_EXTRACTION_AUDIT_v0.1.md — HISTORICAL — Phase 6 extraction notes, superseded by Phase 9.2 contract + Phase 9.3 migration + Phase 9 freeze. Contains field-level similarity, not behavior contract. Classification: SUPERSEDED / EVIDENCE — keep as evidence, do not commit as contract.
docs/architecture/gap-matrix-v0.3-reviewed.md — HISTORICAL — gap analysis pre-Phase 9, now superseded by type_b_static_site.md + phase-9-rendering-freeze.md. SUPERSEDED.
docs/architecture/phase-9-audit-v0.1.md — EVIDENCE — Phase 9 audit that led to contract. Now HISTORICAL, preserved as evidence, but not a living contract.
docs/architecture/phase-9-rendering-freeze.md — CURRENT — frozen contract, should be committed (already done in cd0b9a9? Actually cd0b9a9 includes freeze? git log shows phase-9.4 freeze includes type_b + freeze doc). Classification: CURRENT.
showcases/cms_lite_phase5/ — UNKNOWN — likely old Phase 5 snapshot, not part of main showcases. Check if duplicate of cms_lite. Classification: USEFUL FOR PHASE 10 to verify identity patterns? Or SAFE TO DELETE if superseded by showcases/cms_lite. Need to list contents before deleting.
Candidate Matrix (Phase 10)
Candidate	Consumers	Same semantics	Same lifecycle	Framework has analogue?	Security / correctness	Extraction risk	Interest
Auth / PipelineContext / UserRole + _require + header normalization	3 (cms_lite, blog_cms, docs_site)	Yes (except GENERATOR role)	Yes (per-request)	No	HIGH (403/401)	MEDIUM-HIGH (role set)	HIGH
Error triple ValidationError/NotFoundError/PermissionDeniedError + _parse_uuid + _to_dict	3	Yes	Yes (per-request mapping to HTTP)	No (Slug VO only)	LOW	LOW	MEDIUM
Factories create_app/create_test_app + FROZEN_ROUTES pattern	3	Partial	Per-test	No	LOW	HIGH (umbrella)	MEDIUM — deferred
Routes registration boilerplate	3	No (domain routes differ)	N/A	No	LOW	HIGH	OUT OF SCOPE
Forms/validation request payload → domain	3	Partial	Per-request	Slug VO only	MEDIUM	MEDIUM	MEDIUM — deferred
Assets/media attach/detach	1	N/A	N/A	No	MEDIUM	HIGH	SHOWCASE-SPECIFIC
Transactions/UoW	0 real	No	N/A	No	N/A	HIGH	LOW
Taxonomy generic	3 field-similar but semantic-diff	No	Different	No	LOW	HIGH (Phase 8 lesson)	SHOWCASE-SPECIFIC — do not touch
Rendering	2	Yes	Frozen	Yes frozen	N/A	N/A	CLOSED
Publishable	2	Yes	Frozen	Yes frozen	N/A	N/A	CLOSED
Selected Phase 10 Target (proposed, not decided yet)
HIGH interest: Auth / Identity boundary

Why:

3 real consumers, same behavior contract (header → Context → _require → 403)
Duplicated _make_user_context, _map_role_str, PipelineContext.from_raw, UserContext, UserRole — evidence in final_dual_factory_v7.py + app_factory.py
Security-critical — inconsistency in normalization could cause privilege escalation (e.g., lowercase handling, GENERATOR role)
Framework currently has no identity primitive, but all showcases need it
Small primitive possible: PipelineContext VO + UserRole + PermissionDeniedError + from_raw() — no umbrella
Why alternatives deferred:

Factories: would become RenderingEngine-style umbrella, violates Phase 9 rule against umbrella abstraction
Routes: FastAPI already provides, no domain behavior
Taxonomy: Phase 8 lesson — field similarity ≠ same semantics, would repeat BaseX mistake
Assets: only 1 consumer
Validation error triple: low risk, could be done together with Auth as tiny shared kernel, but not as standalone target — would be too small to justify phase
Non-goals for Phase 10.2 (if Auth selected):

No generic BaseService
No AuthService
No RoleHierarchy complex inheritance
No factory abstraction
No rendering changes
No taxonomy generic
No DB/transaction changes
Next Steps (Phase 10.1 → 10.2)
Classify remaining ?? files: move to docs/architecture/evidence/ or delete after verification
Open each domain/user.py in 3 showcases, diff from_raw, UserRole values, _require logic — produce behavior contract table
Write docs/architecture/phase-10-audit-v0.1.md — this file — commit with No runtime changes tag phase-10-audit-v0.1
If Auth candidate confirmed by evidence (2 consumers + same semantics), proceed to Phase 10.2 Contract — minimal primitive: PipelineContext frozen VO + UserRole + protocol RequiresRoles
Add guards: test_phase10_auth_security.py — header normalization, role case-insensitivity, GENERATOR only for blog_cms, viewer forbidden
Freeze: phase-10-identity-boundary-green only after 2 consumers migrated to framework primitive, 663 passed preserved + new guards
No runtime changes in this audit document.

