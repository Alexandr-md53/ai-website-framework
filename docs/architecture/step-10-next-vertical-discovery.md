Step 10 — Next Product Vertical Discovery
Status: Discovery / Audit only — no implementation
Frozen state: phase-9-cafe-v0.1 — 666 passed, ai_framework diff empty
Date: 2026-05-13
Principle: Real development creates evidence; evidence permits abstraction.

1. Current Frozen State
Git
phase-12-architecture-stable → architecture stable baseline
aad5e2a → docs_site frozen (663 tests)
949a276 → feat(cafe): implement Menu & Ordering vertical v0.1
phase-9-cafe-v0.1 → tag, 666 passed
Acceptance (last run)
pytest -q → 666 passed in 11.44s
git diff -- ai_framework/ → empty
git diff --check → clean (only ?? untracked)
Cafe E2E → 3/3
Architecture boundary
phase-12-architecture-stable
    ↓
Step 8 discovery (blog_cms, docs_site inventory)
    ↓
Step 9 cafe v0.1 (third consumer)
    ↓
phase-9-cafe-v0.1 FROZEN
All three showcases use frozen primitives:

Slug VO — ai_framework.content.slug
JinjaTemplateRenderer — ai_framework.rendering.jinja
SeoInjector + SeoContext(seo_title, seo_description, og_title, og_description, canonical_url, title)
GeneratedPage(path, html, kind)
StaticSiteWriter.write(pages, out_dir, clean=True) — sole FS boundary
No generic abstractions introduced: No BaseService, No GenericRepository, No StockManager, No OrderProcessor.

Showcase Inventory (from Get-ChildItem showcases -Directory)
Real consumers (evidence):

showcases/blog_cms — first rendering consumer, content publishing lifecycle
showcases/docs_site — second rendering consumer, versioned docs, sections/versions/pages
showcases/cafe — third rendering consumer, transactional: categories, menu items, stock, orders
WIP / Untracked (not evidence yet):

showcases/cms_lite_phase5/ — ?? untracked, per git status --short
dist/ — build output, should be gitignored
Docs (untracked, not product code):

docs/RENDERER_EXTRACTION_AUDIT_v0.1.md
docs/architecture/gap-matrix-v0.3-reviewed.md
docs/architecture/phase-10.2-*
docs/architecture/phase-9-audit-v0.1.md
2. Showcase Inventory — Detailed
blog_cms
Product purpose: Simple blog content management, SEO-friendly static site
Domain entities: Post, Category, Tag?, SeoMeta
Lifecycle: DRAFT → PUBLISHED
API: CRUD posts, publish/unpublish, site/generate
Persistence: Dict + slug index (showcase-local)
Rendering: JinjaTemplateRenderer + SeoInjector + StaticSiteWriter
Security: Public read, admin write (no authz in v0.1)
Tests: E2E generation pipeline
Maturity: Frozen, first evidence for rendering extraction
Evidence type: Content publishing
docs_site (frozen aad5e2a)
Product purpose: Versioned documentation site (like docs for framework)
Domain entities: Section, Version, Page (Doc), SeoMeta
Lifecycle: DRAFT → PUBLISHED, versioned publishing
API: /sections, /versions, /docs|/pages, /docs/{id}/seo, publish/unpublish, /public/pages/{slug}?version=, /site/generate, /site/pages/{path}
Persistence: Dict + global slug index, list_published, get_published_by_slug
Rendering: Same frozen primitives, templates: index, section, page
Security: Public by slug+version, hidden if not published
Tests: E2E frozen route map, generation pipeline G1/G2
Maturity: Frozen Step 7, 663 tests, create_test_app contract
Evidence type: Second rendering consumer — validated that rendering can be reused
cafe v0.1 (frozen phase-9-cafe-v0.1)
Product purpose: Menu & Ordering vertical — cafe menu with stock and simple ordering
Domain entities: MenuCategory, MenuItem (price: Decimal, stock_quantity: int|None, dietary_tags), SeoMeta, Order, OrderLine (price_snapshot), OrderStatus
Lifecycle: MenuItem DRAFT→PUBLISHED, Order DRAFT→VALIDATED→CONFIRMED (decrement stock) →CANCELLED (restore)
API: 22 FROZEN_ROUTES: categories CRUD, items CRUD+seo+publish+availability, public/menu/{slug}, orders CRUD+validate+confirm+cancel, site/generate, site/pages, sitemap.xml
Persistence: Dict + global slug index + cat slug index + orders Dict — showcase-local, no generic repo
Rendering: Same primitives, templates: index.html, menu_index.html, category.html, item.html — minimal per screenshot sample, HTML byte-size NOT contract
Security: Public menu only if published, stock checks: OUT_OF_STOCK, INSUFFICIENT_STOCK
Tests: 3/3: frozen route map smoke, generation pipeline G1/G2, second consumer uses same framework primitives
Maturity: Frozen v0.1, third rendering consumer + first transactional evidence
Evidence type: Transactional/order/stock — cafe-local, NOT generic StockManager
Commonalities that are NOT evidence for abstraction:

similar fields (name, slug, description)
similar CRUD (create, list, get, update)
similar Dict storage
similar service methods
similar status names
These are coincidental — per stop conditions, they do NOT justify extraction.

3. Viable Candidates — 2-3 that give NEW evidence
We need evidence that does NOT exist yet:

Existing evidence: content publishing (blog, docs), transactional stock/order (cafe)
Missing evidence: temporal/scheduling, identity/permissions, media-heavy, user-generated, multi-tenant
Candidate A: Events / Meetup Vertical — RECOMMENDED
Product purpose: Community events, meetups, workshops — public event listing with RSVP and capacity

Domain entities: Event, Venue, Organizer, RSVP, Waitlist

Lifecycle:

Event: DRAFT → PUBLISHED → CANCELLED, plus temporal states: UPCOMING, ONGOING, PAST (derived, not stored)
RSVP: PENDING → CONFIRMED → CANCELLED, with capacity guard
API (minimal):

POST/GET /venues, POST/GET /events, PATCH /events/{id}, POST /events/{id}/publish, GET /public/events/{slug}, POST /events/{id}/rsvp, POST /rsvp/{id}/cancel, POST /site/generate
Persistence: Dict + slug index + time index (sorted by start_time)

Rendering: Same primitives, templates: event_index, venue, event detail with time, location, RSVP count

Security divergence risk: Low — public read, RSVP write, capacity check

Tests: Generation pipeline, RSVP capacity invariant (FULL vs AVAILABLE), temporal ordering

Why it gives NEW evidence:

Temporal evidence: start_time, end_time, recurrence?, timezone handling (UTC fix already proven with datetime.now(UTC))
Capacity evidence: different from stock decrement — capacity is time-bound, not inventory decrement with restore, but similar semantics that could be confused
New primitive candidate: TimeSlot VO? But only as candidate, not extraction yet
Product rationale: Real use case for community site, distinct from menu
Reuse existing framework:

Slug, JinjaRenderer, SeoContext, GeneratedPage, StaticSiteWriter.write()
Same FROZEN_ROUTES pattern
Possible new abstraction candidates (as candidates only):

TimeRange VO (start, end, timezone) — needs 2+ consumers before extraction
Capacity guard pattern — cafe stock vs event capacity have different semantics (inventory vs seat), cannot generalize yet per stop conditions
Candidate B: Portfolio / Creative Work Vertical
Product purpose: Designer/photographer portfolio — media-heavy, filtering by tag/category

Domain entities: Project, MediaAsset, Category, Tag

Lifecycle: DRAFT → PUBLISHED, featured flag

API: Similar CRUD + media upload (but FS boundary still via StaticSiteWriter), filtering

Rendering: Gallery templates, image-heavy — gives evidence for media handling in StaticSiteWriter (currently only HTML)

Why it gives NEW evidence:

Media evidence: handling of static assets beyond HTML (images), asset path management
Filtering evidence: tag-based filtering vs category filtering (docs_site already has category, but tag is new)
Risks:

Media upload touches FS boundary — could tempt to modify StaticSiteWriter, which is frozen
Less distinct from blog_cms (content publishing again) — weaker product rationale
Verdict: Viable but less valuable than Events — does not test temporal logic.

Candidate C: Booking / Appointment Vertical (e.g., Barber, Clinic)
Product purpose: Time-slot booking — user books a slot with a provider

Domain entities: Service, Provider, TimeSlot, Booking

Lifecycle: Slot AVAILABLE → RESERVED → CONFIRMED → CANCELLED, with overlap detection

API: Similar to Events but with overlap guard

Why it gives NEW evidence:

Overlap detection evidence: time-slot locking, different from stock and capacity
Could reveal need for generic locking abstraction, but again semantics differ
Risks:

High security divergence: provider-specific authz, double-booking prevention — easy to over-generalize into generic reservation system prematurely
Overlaps with Events candidate — should choose one temporal vertical, not both
Verdict: Strong but higher complexity, better after Events proves temporal evidence.

4. Evidence for Each Candidate
Candidate	Existing evidence reused	New evidence produced	Reuse score	Novelty score	Risk
Events	rendering (3 consumers), slug, SEO, StaticSiteWriter	temporal (start/end, UTC, past/upcoming), capacity guard distinct from stock, RSVP lifecycle	High	High	Low
Portfolio	rendering, slug	media asset handling, tag filtering	High	Medium	Medium (FS boundary)
Booking	rendering, slug	overlap detection, slot locking	High	High	High (authz)
All candidates reuse ai_framework frozen primitives — no framework change needed for v0.1.

5. Product Rationale for Selected Vertical
Selected: Candidate A — Events / Meetup Vertical

Rationale:

Real product need: Community sites need event listing — distinct from blog/docs/cafe, not artificial
New evidence type: Temporal — start_time/end_time, timezone-aware datetime.now(UTC) already fixed in cafe, but not yet used for scheduling logic
Avoids false generalization: After cafe, easiest mistake is to generalize stock → generic inventory. Events gives capacity that looks similar but has different semantics (time-bound seats vs inventory). This tests stop condition: 2+ consumers with same semantics required before abstraction. Cafe stock vs Event capacity are NOT same semantics, so we should NOT extract generic StockManager — this discovery proves it.
Minimal implementation: Can be Type C runnable like cafe, Dict + slug + time index, no framework change
Framework reuse: Uses all existing primitives, validates third time that rendering is reusable for non-content product
Stop conditions respected: Does not introduce identity/auth, does not touch StaticSiteWriter FS boundary beyond existing write(pages, out_dir)
What it is NOT:

Not a generic calendar abstraction
Not a generic reservation system
Not a reason to extract TimeSlot VO yet — only candidate
6. Proposed Minimal Scope — Events v0.1 (if approved as Step 11)
Type C runnable — showcase-local, no framework changes

Domain (models_v01.py):

Venue: id, name, slug, address, capacity
Event: id, title, slug, description, venue_id, start_time (datetime UTC), end_time, capacity (int|None), is_published, status (DRAFT/PUBLISHED/CANCELLED), seo
RSVP: id, event_id, attendee_name, status (PENDING/CONFIRMED/CANCELLED), created_at
Service (Dict):

create_venue, list_venues, get_venue
create_event, list_events (filter upcoming), list_published (sorted by start_time), get_event, get_published_by_slug, update_event, publish, unpublish
create_rsvp (capacity check → FULL), cancel_rsvp (restore), list_rsvp for event
No BaseService, no GenericRepository
Renderer (CafeRenderer pattern):

JinjaTemplateRenderer + SeoInjector + SeoContext
Templates: index.html (upcoming events), events/index.html, venue/index.html, event detail (time, venue, RSVP count, capacity)
Generator:

GeneratedPage(path, html, kind), deterministic sorted, duplicate fail-fast, uses list_published sorted by start_time
Pages: index.html, events/index.html, events/{venue_slug}/index.html, events/{venue_slug}/{event_slug}/index.html, sitemap.xml
App Factory:

FROZEN_ROUTES ~20: venues CRUD, events CRUD+publish+seo, public/events/{slug}, RSVP create/cancel/list, site/generate, site/pages, sitemap.xml
StaticSiteWriter.write(pages, out_dir, clean=True) — sole FS boundary
Tests (3, like cafe):

frozen route map smoke
generation pipeline G1/G2: venue→event→publish→RSVP→generate→verify html contains time
second consumer uses same framework primitives + capacity invariant FULL vs AVAILABLE
Out of scope for v0.1:

Recurrence, timezone conversion UI, auth, waitlist, email notifications, media upload
7. Existing Framework Primitives It Can Reuse (no changes)
ai_framework.content.slug.Slug — validation regex same as docs_site/cafe
ai_framework.rendering.jinja.JinjaTemplateRenderer
ai_framework.rendering.seo.SeoInjector + SeoContext
ai_framework.rendering.generated_page.GeneratedPage
ai_framework.rendering.static_writer.StaticSiteWriter.write()
All already proven with 3 consumers.

8. Possible New Abstraction Candidates — ONLY as candidates, NO extraction
After Events v0.1, we will have 4 consumers — we can AUDIT, not extract yet.

Candidates to watch:

TimeRange VO (start: datetime UTC, end: datetime UTC)
Cafe does NOT use it (only created_at)
Events would be first consumer → need 2+ real consumers with same semantics before extraction
Stop condition: requires same lifecycle, no security divergence — not met yet
Capacity guard pattern
Cafe: stock_quantity decrement/restore on CONFIRMED/CANCELLED, OUT_OF_STOCK, INSUFFICIENT_STOCK
Events: capacity decrement on RSVP CONFIRMED, restore on CANCELLED, FULL
Semantics differ: inventory (restockable, multiple orders) vs seats (time-bound, not restockable same way)
Stop condition fails: same lifecycle? No — Order lifecycle vs RSVP lifecycle differ
Decision: DO NOT extract StockManager/CapacityManager — keep showcase-local
Slug + Publishable pattern
Already used in 3 consumers but with different gates: blog post publish, doc page publish, menu item publish (description>=10, price>0), event publish (start_time in future? venue exists?)
Each has different validation — cannot generalize Publishable yet
Keep local
Dict + slug index + list_published + get_published_by_slug
Pattern repeats in docs_site, cafe, would repeat in events
Looks like GenericRepository, but stop condition: 2+ real consumers + same semantics + same lifecycle + no security divergence
Security divergence: public read vs private? Cafe items require is_published, Events require start_time filter, Docs require version filter — semantics differ
Decision: DO NOT extract — keep showcase-local Dict
All candidates remain candidates — no extraction in Step 10.

9. Architecture Decision
Decision: Step 10 = Discovery only, Step 11 = Events v0.1 Implementation (if approved)

Freeze cafe: phase-9-cafe-v0.1 — no post-hoc improvements
Define next vertical via evidence, not speculation
Select Events as next vertical because it gives NEW temporal evidence, avoids false generalization of stock, and reuses existing framework without changes
Keep framework frozen: git diff -- ai_framework/ must stay empty during discovery
Acceptance for this doc: pytest -q 666 passed, git diff --check clean, git diff -- ai_framework/ empty
Deliverable: This file only — no code, no framework change.

Next steps (Step 11, separate):

Evidence: implement Events v0.1 Type C, Dict persistence, frozen routes, E2E tests
Audit: after 4 consumers, run RENDERER_EXTRACTION_AUDIT + new temporal audit
Decision: only if 2+ consumers share same semantics/lifecycle/no divergence, consider extraction — otherwise keep local
10. Stop Conditions / Risks
Stop conditions that prevent abstraction (must be respected):

similar fields → NOT evidence
similar CRUD → NOT evidence
similar Dict storage → NOT evidence
similar service methods → NOT evidence
similar status names → NOT evidence

Requires ALL:
2+ real consumers
+ same semantics
+ same lifecycle
+ no security divergence
Risks after Cafe:

False generalization of stock: Most dangerous — seeing stock_quantity and thinking generic StockManager can handle cafe inventory, event capacity, booking slots. Mitigation: keep showcase-local, document semantic differences.
Generic repository temptation: Dict + slug index appears in 3 places — easy to extract GenericRepository. Mitigation: security divergence (docs version filter vs cafe published vs events time filter) fails stop condition.
Time abstraction temptation: After fixing utcnow() → now(UTC), easy to create TimeRange VO prematurely. Mitigation: only one consumer (events would be first), need second.
HTML byte-size contract: Already avoided in cafe — must continue: contract is rendering pipeline, paths, links/SEO, deterministic generation, product behavior.
Untracked files pollution: git status --short shows ?? dist/, ?? docs/architecture/phase-10.2-*, ?? showcases/cms_lite_phase5/ — these must NOT be committed as part of Step 10. Keep .gitignore.
Scope creep: Events v0.1 must stay minimal — no recurrence, no auth, no waitlist, no email. Out of scope must be explicit.
Acceptance for this discovery doc:

powershell
pytest -q
# 666 passed

git diff --check
# clean

git diff -- ai_framework/
# empty
And commit:

text
docs(architecture): define next product vertical — Events

- inventory of 3 frozen consumers
- 3 candidates evaluated
- Events selected for temporal evidence
- minimal scope defined
- no framework change, no extraction
Principle reaffirmed:

Real development creates evidence; evidence permits abstraction.

We have 3 evidences, we need 4th (Events) before any new abstraction audit. Framework stays frozen.

