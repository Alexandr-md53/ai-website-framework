Product Backlog — From cd0b9a9 / Architecture Stable
Baseline:
cd0b9a9 / 663 passed / phase-9-rendering-pipeline-green
Tag: phase-12-architecture-stable (90723b3)

Freeze state:
Framework may own only: content/publishable, rendering (jinja/seo/static_writer/generated_page), Slug VO
Must NOT grow by: structural similarity, one consumer, speculative interfaces, domain-specific semantics, security normalization

Current showcases — inventory from real files:

showcases/cms_lite/
  domain/user.py — UserContext, UserRole ADMIN/EDITOR/VIEWER
  services/cms_service.py + cms_service_framework_wired.py — Dict[UUID, Category/Tag/Item/Media] + FrameworkInMemoryPersistenceProvider + ValidationEngine + AsyncSlugOrchestrator + UniversalCRUDEngine
  api/app_factory.py + app_factory.py (dual Old/New) — body user_role vs header role, _map_role_str, _make_user_context uuid5 fallback, _to_dict 80+ lines, _parse_uuid(field_name)
  State: Type A dynamic CMS, most complete, but has fragile string matching for errors (legacy candidate, not to be promoted)

showcases/blog_cms/
  domain/user.py — PipelineContext.from_raw, UserRole ADMIN/EDITOR/VIEWER/GENERATOR
  domain/models.py — Category, Tag, Author, Post, PostStatus DRAFT/PUBLISHED, SeoMeta
  services/site_generator.py — Renderer (Jinja with fallback inline), _seo_context, _inject_seo, _ensure_post_links, SiteGenerator G1/G2/G12 (index, post detail, categories/tags, rss.xml, sitemap.xml)
  app_factory.py — FROZEN_ROUTES 15 routes, _ctx_from_headers, _to_dict 10 lines, _parse_uuid(s), create_app(service, out_dir) + state cache {"pages": []}, generation endpoints POST /site/generate, GET /site/pages, GET /site/pages/{path}, GET /rss.xml, GET /sitemap.xml
  tests/test_blog_cms_e2e.py — frozen_route_map_smoke, auth guard VIEWER forbidden, static generation pipeline G1/G2/G12
  State: Type B static/generated — functional demo, but output uses showcase/blog_cms/output hardcoded fallback, no CLI/build workflow, no persistence beyond Dict

showcases/docs_site/
  domain/models.py — Section, Version, DocPage, DocStatus DRAFT/PUBLISHED, SeoMeta
  api/app_factory.py — ABSENT (no HTTP layer)
  services/docs_service.py — simple Dict[UUID, Section/Version/DocPage] (from inventory)
  State: Type C docs site — domain exists, but no factory, no generation pipeline, no templates, not runnable as demo
Product question:

Что должен уметь продукт, чего сейчас не умеет?

Options:

Finish blog_cms as полноценный demo (CLI, real output verification, authoring UX)
Finish docs_site (currently ABSENT factory) — make it runnable Type C showcase with versioned docs
New showcase (e.g. landing page, portfolio, changelog)
CLI/build workflow (unified site build across showcases)
Persistence (file-based JSON, SQLite) without changing framework contract
Content authoring (markdown import, content validation UX)
End-to-end user scenario (create category → author → post → publish → generate → verify html files on disk)
All options keep framework frozen.

Recommended Next Vertical Feature — docs_site as Full Type C Showcase
Why this one:

blog_cms already has G1/G2/G12 and e2e test — docs_site is only showcase with NO FILE for factory → incomplete product
Finishing it creates second independent consumer for static generation lifecycle without touching framework (proves generation pattern is reusable but remains showcase-local)
Does NOT require framework abstraction — showcase-local Renderer+Generator similar to blog_cms but domain-specific (Section/Version vs Category/Tag/Author)
Gives real end-to-end scenario for docs: Section + Version + DocPage → publish → generate versioned docs site
Not doing: framework extraction, new primitive, security normalization, shared factory abstraction

Feature Goal
docs_site becomes runnable demo:
  POST /sections, GET /sections
  POST /versions, GET /versions
  POST /pages (title, slug, content, section_id, version_id, seo optional)
  PATCH /pages/{page_id}/seo
  POST /pages/{page_id}/publish / unpublish
  GET /pages?status=...
  GET /public/pages/{slug}?version=... (or version slug in path)
  GET /public/pages?section=&version=
  POST /site/generate — generates versioned docs static site
  GET /site/pages, GET /site/pages/{path}
  GET /sitemap.xml

Output structure:
  index.html (list sections/versions)
  v/{version_slug}/index.html
  v/{version_slug}/{section_slug}/index.html
  v/{version_slug}/{section_slug}/{page_slug}/index.html
  sitemap.xml

Uses existing frozen framework:
  ai_framework/rendering/jinja.py, seo.py, static_writer.py, generated_page.py — via showcase-local Renderer wrapper (same pattern as blog_cms, not shared factory)
  ai_framework/content/slug.py — Slug VO for validation

Does NOT use:
  No new framework code, no change to cd0b9a9 baseline
Affected Files (only showcase-local)
showcases/docs_site/domain/models.py — already exists, keep (add to_dict already there)
showcases/docs_site/domain/user.py — NEW, showcase-local (reuse PipelineContext pattern but docs-specific, or simple UserContext — leave local, do not promote)
showcases/docs_site/services/docs_service.py — extend: add _slugs index, list_published(section_slug, version_slug), get_published_by_slug, update_page_seo, publish/unpublish
showcases/docs_site/services/site_generator.py — NEW, showcase-local Renderer + SiteGenerator (versioned docs)
  - Renderer: templates_dir resolution similar to blog_cms (here.parent.parent / "templates" fallback)
  - _seo_context, _inject_seo similar but no blog-specific logic
  - render_page, render_section, render_version, render_index, render_sitemap
  - SiteGenerator.generate() → List[GeneratedPage]
  - write() via StaticSiteWriter (framework frozen writer)
showcases/docs_site/app_factory.py — NEW, showcase-local factory (similar to blog_cms/app_factory.py but docs-specific FROZEN_ROUTES)
showcases/docs_site/templates/ — NEW, optional minimal Jinja templates (index.html, page.html, section.html, version.html) — fallback inline if missing
showcases/docs_site/api/app_factory.py — NEW re-export for compatibility if needed
tests/test_docs_site_e2e.py — NEW e2e similar to blog_cms: frozen route smoke, auth guard, generation pipeline versioned
Explicitly NOT affected:

ai_framework/* — frozen, no changes
showcases/blog_cms/* — no changes
showcases/cms_lite/* — no changes
Acceptance Criteria
1. pytest -q still 663 + new docs_site tests (e.g. 663 + 3 = 666) — no existing test break
2. create_test_app() for docs_site works, no FS side effects (temp out_dir)
3. Flow:
   section = POST /sections {"name":"Getting Started","slug":"getting-started"}
   version = POST /versions {"name":"v2.1","slug":"v2-1"}
   page = POST /pages {"title":"Install","slug":"install","content":"Long enough content >=20 chars for docs","section_id":section.id,"version_id":version.id}
   POST /pages/{id}/publish → status PUBLISHED
   POST /site/generate → generated >= 4 (index + version + section + page + sitemap)
   GET /site/pages → contains "index.html", "v/v2-1/index.html", "v/v2-1/getting-started/index.html", "v/v2-1/getting-started/install/index.html", "sitemap.xml"
   GET /site/pages/v/v2-1/getting-started/install/index.html → html contains title "Install" and SEO if set
   GET /public/pages/install?version=v2-1 → 200
4. SEO persists: PATCH /pages/{id}/seo {"seo_title":"Install Guide"} + regenerate → html contains SEO title
5. Rendering uses framework StaticSiteWriter with path traversal guard (same as blog_cms)
6. No framework changes — git diff -- ai_framework/ empty
7. FROZEN_ROUTES documented in factory, smoke test verifies routes exist
Tests
tests/test_docs_site_e2e.py
  test_frozen_route_map_smoke — normalize {path:path} → {path}, check subset, compare api vs main FROZEN_ROUTES
  test_auth_guard_viewer_forbidden_and_headers_normalization — VIEWER cannot create section, EDITOR can (if auth used) — or simple no-auth if docs_site has no roles (decide locally)
  test_versioned_generation_pipeline_V1_V2_V3 — setup section/version/page, publish, generate, assert paths, public read, SEO persist after regen

If auth not needed for docs_site Type C (docs authoring is editor-only), skip VIEWER test and keep simple — showcase-local decision, not framework.
Implementation Order
Step 1 — Baseline verification (no code):
  git status --short — clean
  pytest -q — 663 passed
  git log -1 --oneline — cd0b9a9 or 90723b3 freeze

Step 2 — Domain/Service extension (showcase-local only):
  showcases/docs_site/services/docs_service.py — add _slugs index, list_categories/tags/authors pattern adapted to sections/versions/pages, list_published(section_slug, version_slug), get_published_by_slug, update_page_seo, publish/unpublish
  Keep Dict-based in-memory, sync, no transaction — same lifecycle as blog_cms

Step 3 — Site generator (showcase-local):
  showcases/docs_site/services/site_generator.py — Renderer + SiteGenerator
  Copy pattern from blog_cms Phase 6.1 but adapt to docs: no Author, no Tag, but Section+Version
  Use ai_framework/rendering/jinja.py + seo.py + static_writer.py via composition, not inheritance

Step 4 — App factory (showcase-local):
  showcases/docs_site/app_factory.py — create_app(service, out_dir), create_test_app(), FROZEN_ROUTES
  _to_dict, _parse_uuid showcase-local (10 lines style, not 80+)
  Endpoints: sections, versions, pages CRUD + seo + publish + public + generation

Step 5 — Templates (optional, minimal):
  showcases/docs_site/templates/index.html, page.html, section.html, version.html — minimal with <title> and {{ content }}, fallback inline if Jinja missing (same as blog_cms)

Step 6 — E2E test:
  tests/test_docs_site_e2e.py — 3 tests, uses TestClient, temp out_dir

Step 7 — Manual end-to-end scenario:
  python -m showcases.docs_site.manual_demo (optional script) — creates section/version/page, publishes, generates to showcases/docs_site/output, list files

Step 8 — Regression + commit boundaries:
  pytest -q — 663 + new
  git status --short — only showcases/docs_site/* + tests/test_docs_site_e2e.py
  Commit 1: docs_site service extension
  Commit 2: docs_site site_generator
  Commit 3: docs_site app_factory + templates
  Commit 4: tests + docs
Commit Boundaries (small, vertical)
commit 1: docs_site service — _slugs, list_published, publish/unpublish, update seo
commit 2: docs_site generator — Renderer + SiteGenerator versioned, uses frozen framework writer
commit 3: docs_site factory — FROZEN_ROUTES, create_app, create_test_app, endpoints
commit 4: tests — test_docs_site_e2e.py + README update
Each commit: pytest -q passes, no ai_framework changes.

Architectural Signal Tracking (during feature)
Do NOT refactor immediately if two showcases look similar.

Track:

Consumer A: blog_cms — SiteGenerator G1/G2/G12, Renderer with _seo_context/_inject_seo/_ensure_post_links, FROZEN_ROUTES 15 routes, out_dir handling
Consumer B: docs_site — SiteGenerator V1/V2/V3 versioned, Renderer with _seo_context/_inject_seo, FROZEN_ROUTES docs-specific, out_dir handling

Check:
  same semantics? — both generate static pages via GeneratedPage + StaticSiteWriter, but taxonomy different (Category/Tag/Author vs Section/Version) → different semantics
  same lifecycle? — both sync Dict + temp out_dir + state cache → similar lifecycle, but not identical contract (different page kinds)
  same contract? — _parse_uuid detail format same (if we use same), but FROZEN_ROUTES different, page paths different → different contract
  security divergence? — blog_cms has GENERATOR role, docs_site maybe no role — divergence

Result: Even after finishing docs_site, guard NOT MET → remain showcase-local, NO extraction. This is expected.

Only if new showcase/domain appears with identical semantics+lifecycle+no security divergence → open new Audit cycle.
What NOT to do in this feature
- No framework changes (ai_framework/* frozen)
- No shared factory abstraction between blog_cms and docs_site
- No promotion of _to_dict / _parse_uuid to framework (different lifecycles proven in Phase 11)
- No security normalization (VIEWER vs GENERATOR stays showcase-local)
- No speculative CLI framework — if CLI needed, make it showcase-local script first
- No persistence change (stay in-memory Dict, same as blog_cms)
Next Action
Choose one:

A) Start docs_site vertical feature as described — I will implement Step 2 (service extension) first, showcase-local only, no framework changes

B) Choose different vertical (e.g. finish blog_cms CLI/build workflow — `python -m showcases.blog_cms.cli build --out output`)

C) Show existing README/TODO first — provide Get-Content of README.md, TODO.md, docs/architecture/*.md to refine backlog
Default recommendation: A) docs_site Type C full demo — closes only showcase with ABSENT factory, gives second static generation consumer, keeps freeze verified.

Baseline remains cd0b9a9 / 663 passed, next commit only after pytest -q passes.

