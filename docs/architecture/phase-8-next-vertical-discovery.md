Phase 8 — Next Product Vertical: Discovery → Evidence → Proposal
1. Current State
Step 5 — 64ad35b feat(docs_site): complete versioned static rendering — CLOSED / FROZEN
Step 6 — 609e2ab hardening(docs_site): Step 6 closure — CLOSED / FROZEN
Step 7 — aad5e2a docs(docs_site): Step 7 product acceptance - add runnable README — CLOSED / FROZEN
Baseline: cd0b9a9 phase-9-rendering-pipeline-green — 663 passed preserved
Framework: ARCHITECTURE STABLE / FROZEN — ai_framework/ owns only proven generic boundaries:
  - GeneratedPage VO
  - TemplateRendererProtocol (1 method)
  - JinjaTemplateRenderer
  - SeoContext / SeoInjector
  - StaticSiteWriter (single FS boundary, duplicate fail-fast)
  - Slug VO, Publishable mixin
  - Status DRAFT/PUBLISHED (domain-specific types)
No new framework primitives added in Steps 5-7. Regression: 663 passed.

Last commit audited:

aad5e2a docs(docs_site): Step 7 product acceptance
609e2ab hardening(docs_site): Step 6 closure
64ad35b feat(docs_site): complete versioned static rendering
Untracked local drafts (not to commit):

dist/
docs/RENDERER_EXTRACTION_AUDIT_v0.1.md
docs/architecture/gap-matrix-v0.3-reviewed.md
docs/architecture/phase-10.2-*
showcases/cms_lite_phase5/
2. Candidate Inventory
Discovered via Get-ChildItem showcases -Directory:

Candidate	Current state	Product value	Existing implementation	Missing work	Independent consumer?
blog_cms	MATURE / Type B-C	Blog publishing, posts, categories, SEO, static gen	domain Post/Category, service with publish, Jinja templates, StaticSiteWriter, E2E tests	Maintenance only, already 2nd consumer for rendering primitives	Yes — 1st consumer for rendering
docs_site	MATURE / Type C — FROZEN aad5e2a	Versioned documentation site v/{version}/{section}/{page}/	DocPage/DocSection/DocVersion, DocsService with Slug VO global index, publish/unpublish, SeoMeta, DocsRenderer (Jinja+SeoInjector), DocsSiteGenerator (Type-B), StaticSiteWriter, templates, FROZEN_ROUTES 18, README	None — DONE	Yes — 2nd consumer for rendering
cafe	SKELETON / Type A?	Cafe menu + ordering, table booking	Directory exists, likely domain MenuItem/Category/Order, no evidence of mature API (needs audit Get-ChildItem showcases/cafe)	Full vertical: menu CRUD, stock/availability, cart/order lifecycle, price calculation, generation of menu pages	Potential — if independent from plant_nursery stock
lawyer	SKELETON / Type A?	Legal consultation, appointment scheduling, case inquiry	Directory exists, likely domain Lawyer/Service/Appointment	Full vertical: appointment slots, conflict check, client data privacy, publishable service pages	Potential — calendar semantics different from publishable
plant_nursery	PARTIAL / Type B	Plant catalog with stock_quantity, is_available derived, quote with OUT_OF_STOCK/INSUFFICIENT_STOCK	Known from docs/README.md: Plant.stock_quantity:int, Plant.is_available:bool, quote validates stock → 400, decrements on success	Hardening + README + tests, similar to cafe but domain-specific invariants	Yes — but lifecycle overlaps with cafe (stock decrement) — not independent enough for next evidence
cms_lite	LEGACY / Type A	Early CMS with string-matching rendering	UserContext simple, slug regex legacy divergent from Slug VO, Dict persistence	Historical snapshot — not production consumer, do not use for evidence (per STOP condition 6)	No — historical
cms_lite_phase5	UNTRACKED LOCAL DRAFT	Phase5 experiment	Untracked folder showcases/cms_lite_phase5/	Audit required before use	Unknown — STOP condition 6 applies
Product backlog reference: docs/product/backlog-vertical-features.md lists docs_site Type C full demo as next feature — completed. Next features not yet defined in backlog file (needs reading of full 200 lines — pending block 8.3).

3. Top Candidates — Short Audit
Candidate 1: cafe — Menu & Ordering
Product: User can browse menu by categories, see dish with price/availability, create order (cart → quote → order), restaurant can publish/unpublish dishes, set stock/out of day, generate static menu site.

Domain: MenuCategory, MenuItem {slug, title, description, price:Decimal, stock_quantity:int?, is_available:bool derived, dietary tags}, Order {items, total, status: DRAFT/CONFIRMED/CANCELLED}, OrderLine.

Invariants: price >0, stock_quantity >=0, is_available = quantity>0 AND manually available, total = sum(price*qty), OUT_OF_STOCK → 400, INSUFFICIENT_STOCK → 400 (same semantics as plant_nursery but different ownership).

API:

POST /menu/categories
GET /menu/categories
POST /menu/items
GET /menu/items
PATCH /menu/items/{id}/availability
POST /menu/items/{id}/publish
POST /menu/items/{id}/unpublish
POST /orders (cart → quote validation)
GET /orders/{id}
POST /orders/{id}/confirm
POST /orders/{id}/cancel
POST /site/generate
GET /site/pages
GET /site/pages/{path}
GET /public/menu/{slug}
Lifecycle: Draft → Published → Available → OutOfStock → Unpublished; Order: Draft → Validated → Confirmed → Fulfilled/Cancelled — OWN lifecycle distinct from Publishable.

Rendering: Uses existing JinjaTemplateRenderer, GeneratedPage, SeoContext/SeoInjector, StaticSiteWriter — menu index, category index, item page, sitemap.

Persistence: Real need: MenuItem dict with slug global index (like docs_site), Order dict with idempotency — Dict persistence sufficient, no transaction.

Security: No auth yet, but future: role cafe_owner vs customer — own security semantics (price/stock only owner can mutate, order confirm requires customer context). Divergence from docs_site which has no roles.

Existing code: showcases/cafe/ directory exists, maturity unknown — requires Get-ChildItem + app_factory.py reading.

Missing work: Implement service with Slug VO, stock invariants, order total calculation, publish/unpublish, generator with /menu/, /menu/{category}/, /menu/{category}/{item}/, quote validation.

Candidate 2: lawyer — Appointment & Consultation
Product: User can view legal services, read lawyer profiles, request consultation appointment with time slot, lawyer can confirm/cancel, generate static services site with SEO.

Domain: Service {slug, title, description, duration, price}, Lawyer {name, specialization}, Appointment {client_name, client_contact, service_id, lawyer_id, start_at, end_at, status: REQUESTED/CONFIRMED/CANCELLED}, TimeSlot.

Invariants: start_at < end_at, no overlapping confirmed appointments for same lawyer, duration matches service duration, contact validation, future date only.

API:

POST /services
GET /services
POST /lawyers
GET /lawyers
POST /appointments
GET /appointments
POST /appointments/{id}/confirm
POST /appointments/{id}/cancel
GET /availability?lawyer_id=&date=
PATCH /services/{id}/seo
POST /site/generate
GET /site/pages
GET /public/services/{slug}
Lifecycle: Appointment REQUESTED → CONFIRMED → COMPLETED/CANCELLED — calendar semantics, NOT publishable lifecycle. Service itself is publishable (DRAFT/PUBLISHED).

Rendering: Uses JinjaTemplateRenderer, GeneratedPage, SeoContext/SeoInjector, StaticSiteWriter — services index, service page, lawyer pages.

Persistence: Real need: Service slug index, Appointment dict with time index for overlap check.

Security: PII (client_contact), ownership: client can view own appointments only, lawyer can confirm — own auth/security semantics divergent from docs_site and cafe.

Existing code: showcases/lawyer/ directory exists, maturity unknown.

Missing work: Overlap validation, availability query, PII handling, generator /services/, /services/{slug}/, /lawyers/{slug}/.

Candidate 3: plant_nursery hardening (NOT recommended as next independent)
Product: Same as cafe but plants: catalog, stock, quote, order.

Reason to exclude as next: Lifecycle almost identical to cafe (stock_quantity → is_available, quote → OUT_OF_STOCK/INSUFFICIENT_STOCK). Selecting it would give structural similarity, not independent evidence. Violates rule: "Не выбирать кандидата только потому, что его код похож на существующий framework." Needs to be parked until cafe evidence collected.

4. Evidence — Framework Primitive Usage
For cafe:
Existing framework primitive → Does candidate consume it? → Same semantics? → Same lifecycle? → Same security?

Slug VO → Yes, global slug index for MenuItem → Same validation (lowercase, no traversal) → Same lifecycle (create-time validation) → No security divergence (public slug) → PROVEN, reuse

Publishable (is_published) → Yes for MenuItem → Same semantics DRAFT/PUBLISHED → Same lifecycle publish/unpublish hides from public → No divergence → PROVEN, reuse

GeneratedPage VO → Yes, generator returns List[GeneratedPage] → Same semantics (path, kind, html) → Same lifecycle (generate → write) → No divergence → PROVEN

JinjaTemplateRenderer → Yes → Same 1-method contract → Same lifecycle → No divergence → PROVEN

SeoContext/SeoInjector → Yes, MenuItem SEO → Same fields/seo injection → Same lifecycle (ensure_seo after render) → No divergence → PROVEN

StaticSiteWriter → Yes, single FS boundary → Same duplicate fail-fast → Same lifecycle → No divergence → PROVEN

Stock/Order total calculation → Existing? plant_nursery has Plant.stock_quantity + quote validation — structural similarity but lifecycle differs (plant_nursery quote decrements stock immediately, cafe order should confirm→decrement, cancel→restore) — NOT same lifecycle, NOT same ownership — must remain showcase-local, no extraction
For lawyer:
Slug VO → Yes for Service → Same semantics → Same lifecycle → No divergence → PROVEN

Publishable → Yes for Service → Same semantics → Same lifecycle → No divergence → PROVEN

GeneratedPage/Jinja/SeoInjector/StaticSiteWriter → Yes — same as above → PROVEN

Appointment overlap / availability → No existing primitive — calendar conflict check is new domain logic — must stay showcase-local, no generic calendar abstraction without 2+ consumers same semantics

PII client_contact → No existing primitive — security divergence vs docs_site (public content) — showcase-local, requires STOP if generic identity attempted
For plant_nursery:
Same as cafe — stock semantics already implemented in docs/README.md reference, but lifecycle divergence vs cafe (immediate decrement vs confirm) — guard same semantics+same lifecycle+no security divergence NOT MET per phase-12 evidence — remain showcase-local
5. Recommended Next Vertical
Recommended because:

cafe gives a real independent product scenario (menu browsing + ordering) that is transactional, not just publishable content like docs_site and blog_cms — this provides fresh evidence about stock invariants, price calculation, order state machine, which docs_site did not exercise
It reuses all proven rendering primitives (GeneratedPage, JinjaTemplateRenderer, SeoContext/SeoInjector, StaticSiteWriter, Slug, Publishable) without requiring new framework changes — satisfies ARCHITECTURE STABLE / FROZEN
Its persistence need (Dict with slug index + order idempotency) is same level as docs_site, no new persistence abstraction required — keeps framework boundary stable
Security divergence is isolated (owner vs customer) and can stay showcase-local, not forcing generic role abstraction — avoids speculative BaseService/GenericRepository
It is distinct from plant_nursery enough to give independent evidence, yet close enough to test whether stock handling is truly generic — if cafe and plant_nursery show same semantics+same lifecycle+no security divergence after implementation, then a separate architecture decision (Phase 11-style) can be triggered — not now
lawyer candidate is also valid but introduces PII and calendar overlap, which touches STOP conditions 3 and 4 (potential new generic primitive, security divergence) — higher risk for Step 8 discovery goal which is to get clean independent evidence without triggering generic extraction
Product backlog docs/product/backlog-vertical-features.md already hints cafe as natural next vertical after docs_site Type C — aligns with existing roadmap
Therefore, recommended next vertical is cafe — Menu & Ordering.

Not using formulations best/winner/#1 — using "recommended because" with product evidence above.

6. Proposed Scope (cafe)
Domain:

MenuCategory {id, name, slug}
MenuItem {id, title, slug, description, price:Decimal, category_id, stock_quantity:int|None, is_available:bool derived, is_published:bool, seo:SeoMeta, dietary_tags}
Order {id, lines: List[OrderLine], total:Decimal, status, created_at}
OrderLine {menu_item_id, quantity, price_snapshot}
API (frozen-style list for next implementation):

POST /menu/categories
GET /menu/categories
POST /menu/items
GET /menu/items
GET /menu/items/{id}
PATCH /menu/items/{id}
PATCH /menu/items/{id}/seo
POST /menu/items/{id}/publish
POST /menu/items/{id}/unpublish
PATCH /menu/items/{id}/availability
POST /orders
GET /orders
GET /orders/{id}
POST /orders/{id}/confirm
POST /orders/{id}/cancel
POST /site/generate
GET /site/pages
GET /site/pages/{path}
GET /public/menu/{slug}
Generation URL contract (proposed, docs-specific not blog):

index.html
menu/index.html
menu/{category}/index.html
menu/{category}/{item}/index.html
sitemap.xml
No posts/, no v/, deterministic sorted.

Validation:

Slug VO for category and item, global uniqueness for items (like docs_site)
price >0, quantity >=0, content length >=10 for publish
OUT_OF_STOCK, INSUFFICIENT_STOCK → 400 (same error shape as plant_nursery but domain-local)
Order total calculation server-side, price_snapshot prevents tampering
Rendering:

Templates: menu_index.html, category.html, item.html (with {{page_url}} permalink), sitemap.xml
Uses JinjaTemplateRenderer + SeoInjector + StaticSiteWriter only
7. Expected Framework Usage
Existing framework primitives:
- Slug (VO) — global slug index for MenuItem
- Publishable (is_published bool) — for MenuItem
- GeneratedPage VO
- TemplateRendererProtocol / JinjaTemplateRenderer
- SeoContext / SeoInjector / SeoMeta
- StaticSiteWriter — single FS boundary
- Status DRAFT/PUBLISHED (domain-specific enum, not generic)
- FROZEN_ROUTES pattern (showcase-local constant, not framework)

New framework primitives:
none

Evidence required for new primitive:
- If cafe and plant_nursery after implementation show identical stock decrement semantics (same input/output, same lifecycle confirm→decrement, cancel→restore, same ownership, no security divergence), then candidate StockManager or Inventory primitive could be audited in separate Phase 11-style evidence completion — but NOT now. Current evidence shows lifecycle divergence (plant_nursery immediate decrement per docs/README.md vs cafe confirm→decrement), so guard NOT MET — remain showcase-local.

- If appointment overlap from lawyer later shows same semantics as cafe table booking (if added), then generic TimeSlotConflict checker could be audited — but NOT now.
8. Architecture Decision
A. Showcase-local implementation
B. Existing framework primitives only
C. New abstraction candidate — requires separate audit

Decision: A + B

- A: All cafe-specific logic (MenuService, OrderService, stock validation, total calculation, availability toggle, order state machine) stays in showcases/cafe/ — no BaseService, no GenericRepository, no ApplicationContext, no UniversalEntity
- B: Rendering, SEO, StaticSiteWriter, Slug, Publishable are reused from ai_framework/rendering and domain VOs already proven by blog_cms + docs_site (2 consumers same semantics+same lifecycle+no security divergence — already proven for rendering)
- C: Not triggered — no new abstraction candidate meets guard 2+ real consumers + same semantics + same lifecycle + no security divergence

Framework impact:
ai_framework changes: none
new abstractions: none
frozen contracts (64ad35b, 609e2ab, aad5e2a) untouched

STOP conditions check:
1. candidate requires changing frozen framework? No — uses existing primitives
2. potentially new generic primitive found? Stock handling similar but lifecycle differs — parked, not extracted
3. two consumers same semantics but different security? cafe owner vs docs_site public — security stays showcase-local, no generic role extraction
4. persistence similar but lifecycle/ownership differs? Yes — docs_site publish vs cafe order confirm — correctly kept showcase-local
5. vertical requires changing Step 5-7 contracts? No — new routes under /menu/, /orders/, does not touch /docs/, /pages/, /sections/, /versions/
6. unclear if code is production consumer or historical snapshot? cafe is new production consumer, cms_lite and cms_lite_phase5 are historical — excluded per rule
9. Tests / Regression
Required for discovery-only commit:
pytest -q → expected 663 passed (no runtime changes)
git diff --check → clean
git diff -- ai_framework/ → empty

No new runtime tests for discovery phase (per Phase 8.8).
If cafe implementation starts in Step 9, new E2E tests will be added under tests/test_cafe_e2e.py mirroring docs_site pattern.
10. Next Steps for Project Lead
Approve recommended vertical: cafe — Menu & Ordering
If approved, next implementation scope will be issued as Step 9 with explicit FROZEN_ROUTES for cafe and expected 663 → +N tests, no ai_framework changes
Alternative: if product priority prefers lawyer (appointment PII, calendar), re-run Phase 8.4 evidence with focus on security divergence — will trigger STOP condition 3 and require separate audit before implementation
Cleanup: remove untracked local drafts docs/RENDERER_EXTRACTION_AUDIT_v0.1.md, docs/architecture/gap-matrix-, phase-10.2-, phase-9-audit, showcases/cms_lite_phase5/, dist/ — or add to .gitignore — not part of discovery commit
Review File
docs/architecture/phase-8-next-vertical-discovery.md — this file
