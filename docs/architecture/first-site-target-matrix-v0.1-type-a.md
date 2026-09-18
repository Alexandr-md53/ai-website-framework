First-Site Target Capability Matrix v0.1
Type: A — Dynamic Web Application
Checkpoint: phase-16.5-matrix-v0.2 9ca4aba + phase-16.5-first-site-decision
Date: 2026-09-18
Source: FIRST SITE 11-point spec (Site, User, Role, Category, Item, Media, Tag)
Method: Target Requirement → Current Status (from Capability Matrix v0.2 REVIEWED) → Required for v1 → Action
This document is the concrete outcome of the decision point defined in phase-16.5-matrix-v0.2.
It answers: what minimal set does Framework need to build first new site exclusively through Framework, not showcase workarounds.

FIRST SITE Spec Summary
Type A Dynamic:
UseCase → ApplicationPipeline → FastAPI → HTML Frontend → Browser
No static generation, no SiteGenerator, no Renderer, no External Publish for v1.

Entities: Site, User, Role, Category, Item, Media, Tag
Relations: Category 1:N Item, Item N:M Tag, Item 1:N Media, User N:M Role
Rules: draft/published state, only published public, slug unique, publication tracked

Target Capability Matrix
#	Target Capability	Current Status	Required v1	Action	Implementation Path / Evidence
1. Domain					
1.1	Core Entity/VO primitives	READY	YES	reuse	ai_framework/domain/entities/article.py, value_objects/title.py pattern READY. Create new entities Site, User, Role, Category, Item, Media, Tag using same CORE pattern.
1.2	New Domain (Site, Category, Item, Tag, Media, User)	SHOWCASE-SPECIFIC (new showcase)	YES	create new showcase product	New showcases/cms_lite/ or showcases/content_site/ — follows same structure as showcases/plant_shop/, showcases/article/. Uses CORE, not modifies Framework.
1.3	Relations: Category 1:N Item, Item N:M Tag, Item 1:N Media, User N:M Role	PARTIAL / SHOWCASE-SPECIFIC	YES	reuse + extend in showcase	UniversalCRUDEngine handles single entity. Relations handled in showcase use_cases/service layer (like quote + stock). No generic RelationEngine in Framework — MISSING but not required for Type A v1.
1.4	Business rules: draft/published state, slug unique, publication tracking	SHOWCASE-SPECIFIC	YES	implement in showcase domain	SlugOrchestrator READY (ai_framework/crud/slug_orchestrator.py) for unique slug. State draft/published → Value Object ItemStatus + validation. Same pattern as plant stock.
2. Pages					
2.1	Public pages: Home, Category listing, Item listing, Item detail, Search	SHOWCASE-SPECIFIC	YES	create in showcase frontend	No generic PageEngine — pages are showcase product wiring. Uses product/factory.py::build_app_from_product_info READY.
2.2	Admin pages: Dashboard, Item/Category/Tag/Media/User management	SHOWCASE-SPECIFIC	YES	create in showcase frontend	Same as 2.1. CrudUIEngine provides metadata for admin.
2.3	Detail/List CRUD pages	READY / LIMITED	YES	reuse CrudUI + extend	ai_framework/crud_ui/engine.py, config.py, web_adapter.py READY / LIMITED. Enough for list/detail, but forms limited (see 4).
2.4	SEO: title, description, canonical, slug, OG	PARTIAL	YES	extend MetadataEngine	ai_framework/metadata/engine.py READY. SEO fields are metadata. Needs extension: Open Graph fields → new metadata provider.
3. CRUD					
3.1	Universal CRUD for 5 entities	READY	YES	reuse as-is	ai_framework/crud/engine.py::UniversalCRUDEngine, contracts.py, sqlite_persistence.py READY. Verified: 578 GREEN.
3.2	Custom ops: publish/unpublish/duplicate/attach-detach media/search/filter/bulk	SHOWCASE-SPECIFIC	YES	implement as UseCases	Pattern: showcases/plant_shop/use_cases/* — publish/unpublish are UseCases wrapping CRUD. Duplicate = read + create. Search/filter → query provider extension. No new Framework capability.
4. Forms					
4.1	Forms: Item/Category/Tag/User create/edit, Login	LIMITED	YES	extend CrudUI	crud_ui/engine.py READY / LIMITED — basic form rendering minimal. Gap G8. Need: rich form config, relation selects (Category dropdown, Tag multi-select).
4.2	Validation: required, type, length, unique slug, relation, state transition	READY	YES	reuse	ai_framework/validation/engine.py, providers/metadata.py, persistence.py READY. Slug unique via SlugOrchestrator. State transition via custom validator.
4.3	File upload: image upload Media, multiple per Item	READY / LIMITED	YES	reuse AssetManager + extend CrudUI	asset_manager/manager.py, storage.py LocalFileStorage READY. Upload integration in CrudUI LIMITED — needs form file field.
5. Assets					
5.1	Images: Item/Media images	READY	YES	reuse as-is	AssetManager + LocalFileStorage READY.
5.2	Documents	MISSING	NO	defer	Not required v1.
5.3	Storage local / S3	READY / MISSING (G3)	local YES / S3 NO	reuse local, defer S3	G3 S3 MISSING → defer to v2. Local enough for Docker VPS.
6. Authentication					
6.1	Public + admin	LIMITED (G7)	YES	extend	PipelineContext(request_id, metadata) LIMITED — no identity. security/authorization.py, credentials.py, web.py READY/LIMITED — RBAC exists. Gap G7. Required: wire Identity into PipelineContext, admin guard for private API.
6.2	Roles admin/editor	READY / LIMITED	YES	reuse + extend	security/authorization.py has RoleBasedAuthorization. Needs: editor cannot manage User/Role, admin can all. Implement via authorization provider.
7. API					
7.1	Private admin API + public read API published only	READY	YES	reuse	ai_framework/api/fastapi.py::create_app, product/factory.py, pipeline_adapter.py READY. Need two registries or middleware filtering published.
7.2	Error mapping typed	READY / LIMITED (G9)	YES	reuse	Current hard-coded ValueError→400 mapping works. Typed exceptions defer (part of C16.6).
8. Frontend					
8.1	HTML server-rendered	LIMITED / MISSING	YES	minimal extend (showcase)	No Framework frontend contract — intentionally. Showcase builds HTML templates using MetadataEngine + CrudUIEngine. No SPA. Action: create showcases/content_site/templates/ — not Framework change.
8.2	Framework	none	NO Framework change	create in showcase	Use Jinja2/templates similar to existing framework/templates/engine.py legacy pattern, but new implementation in showcase.
9. Output					
9.1	Dynamic	READY	YES	reuse	Type A dynamic = current FastAPI factory path. No SiteGenerator needed. G1/G2/G12 → defer.
10. Deployment					
10.1	Docker + single VPS + local dev	OUT OF SCOPE (infra)	YES	infra only	Not Framework capability. Use existing Dockerfile pattern.
11. External publication					
11.1	None v1 / Telegram deferred	HISTORICAL → MISSING (G4)	NO	defer	G4 ExternalPublishContract → defer. publication-model-16.5.md separation already fixed.
Summary — Minimal Set for Type A v1
REUSE AS-IS (no Framework change) — 7 capabilities
✅ UniversalCRUDEngine
✅ ValidationEngine + Providers
✅ MetadataEngine (basic)
✅ AssetManager LocalFileStorage
✅ SlugOrchestrator / Slug Service
✅ FastAPI factory + Product Assembly + EndpointPipelineAdapter
✅ Security RBAC basic
EXTEND (small, within existing contracts) — 4 gaps
🔧 G8 Forms Rich UI (relation selects, file field)
   - Extend: ai_framework/crud_ui/config.py + web_adapter.py
   - Not rewrite: add field types select/multi-select/file

🔧 G7 PipelineContext Identity
   - Extend: PipelineContext.metadata already has dict → add user_id/roles, or new IdentityContext
   - Wire: security/web.py guard into API

🔧 SEO Metadata extension
   - Extend: metadata provider for OG fields

🔧 Frontend HTML templates (showcase-only, not Framework)
   - New: showcases/content_site/templates/
DEFER (do NOT design now) — intentionally
⏭️ G1 Site Generator
⏭️ G2 Renderer (HTML/CSS/assets)
⏭️ G12 Output / deployment artifact
⏭️ G3 S3 Storage
⏭️ G4 External Publisher / Telegram (HISTORICAL reference kept)
⏭️ G5 Stock Service generalized (C16.6) — NOT required, showcase-specific remains
⏭️ G6 Transaction / UoW — not required for CMS Lite
DON'T GENERALIZE
🚫 Stock Service — remains showcase-specific in plant_shop, no ai_framework/services/stock/ for Type A
🚫 Publisher — no ai_framework/publisher/ for Type A
Decision for C16.6 and C17
C16.6 Stock Service Extraction → DEFERRED — not required for Type A CMS Lite. Keep as SHOWCASE-SPECIFIC. Revisit only if next site is shop.
C17 Publisher / SiteGenerator → DEFERRED — not required for Type A dynamic. G1/G2/G12 remain MISSING by design.
When Type B/C needed, design per publication-model-16.5.md:

ContentBundle + AssetBundle + SiteMetadata → SiteGenerator → Renderer → SiteOutput
vs
ExternalPublishContract → Telegram plugin (separate contract)


## Next Concrete Milestone
phase-16.5-first-site-decision-A
↓
Create showcase: showcases/cms_lite/
├── domain/entities: Site, Category, Item, Tag, Media, User, Role, ItemStatus
├── product_info.py + use_case_map
├── use_cases: publish, unpublish, duplicate, attach_media, search
├── api/ + templates/ (HTML)
├── validation: state transition + slug unique + relation
└── tests: 20-30 new tests (CRUD + publish flow + auth guard)

Constraints:

No new ai_framework/publisher/
No ai_framework/services/stock/ generalization
Only allowed Framework extensions: G7 Identity + G8 Forms (small)
All else via existing READY contracts

This gives real end-to-end validation of Framework through Framework, not workaround.

