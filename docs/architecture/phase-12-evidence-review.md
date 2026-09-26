# Phase 12 — Architecture Evidence Review

## 1. Baseline and Scope

**Baseline:**

* Events implementation commit: `76ef619`
* Tag: `phase-11-events-v0.1`
* Regression: `669 passed` (666 + 3 events e2e)
* `ai_framework/` diff: `empty` — framework remains frozen
* Existing architecture freeze: valid and unchanged

**Scope of this review:**

This is a documentation-only step (Step 12). Purpose is to:

* fixate accumulated architecture evidence after 4th consumer (`events` v0.1)
* compare cafe stock vs events capacity semantics
* evaluate temporal, repository and rendering primitives
* take formal decision about framework evolution

No new framework abstractions must be introduced. No showcase code must be refactored.

## 2. Consumers Table — 4 Independent Evidence Bases

| Consumer    | Evidence                                | Type | Rendering | Lifecycle | Notes |
| ----------- | --------------------------------------- | ---- | --------- | --------- | ----- |
| `blog_cms`  | rendering                               | C | `JinjaTemplateRenderer`, `SeoContext`, `SeoInjector`, `GeneratedPage`, `StaticSiteWriter`, `Slug` | — | First rendering evidence |
| `docs_site` | rendering + versioned content lifecycle | C | Same primitives | `DRAFT` → `PUBLISHED` versioned docs | Second rendering evidence, versioning showcase-local |
| `cafe`      | rendering + stock/order lifecycle       | C | Same primitives | `Category DRAFT/PUBLISHED`, `MenuItem DRAFT/PUBLISHED + stock`, `Order DRAFT→VALIDATED→CONFIRMED→CANCELLED` | Third rendering evidence + transactional stock + order lifecycle |
| `events`    | rendering + temporal/capacity lifecycle | C | Same primitives, templates in `doc_page.html` style (`<!DOCTYPE html><header><main><article><section><footer><a href="{{ page_url }}">Permalink</a>`) | `Venue` DRAFT/PUBLISHED, `Event` DRAFT→PUBLISHED→CANCELLED, `Rsvp` CONFIRMED→CANCELLED, FULL guard, temporal invariants | Fourth rendering evidence + UTC interval + derived capacity |

All 4 consumers are Type C showcases: runnable, use frozen framework primitives only, have own `app_factory.py` with `FROZEN_ROUTES`, showcase-local Dict persistence + slug index, `StaticSiteWriter` as sole FS boundary.

## 3. Framework Primitives — Real Usage Matrix

| Primitive | Signature / Location | `blog_cms` | `docs_site` | `cafe` | `events` | Divergence |
| --------- | -------------------- | ---------- | ----------- | ------ | -------- | ---------- |
| `Slug` | `ai_framework/value_objects/slug.py` — validation regex | yes | yes | yes | yes | none |
| `JinjaTemplateRenderer` | `ai_framework/rendering/jinja.py` — `render(template_name, context)` | yes | yes | `CafeRenderer` wraps it | `EventsRenderer` wraps it | none |
| `SeoContext` | `ai_framework/rendering/seo.py` — `SeoContext(seo_title, seo_description, og_title, og_description, canonical_url, title)` | yes | yes | yes via `_make_seo()` | yes via `_make_seo()` | none |
| `SeoInjector` | `ai_framework/rendering/seo.py` — `ensure_seo(html, seo_ctx)` | yes | yes | yes | yes | none |
| `GeneratedPage` | `ai_framework/rendering/generated_page.py` — `GeneratedPage(path, html, kind)` | yes | yes | yes | yes | none |
| `StaticSiteWriter` | `ai_framework/rendering/static_writer.py` — `write(pages, out_dir, clean=True)` | yes | yes | yes | yes | none |
| `Publishable` / `list_published` | showcase-local `is_published` + `status` enum | no framework inheritance | no | no | no | intentional — lifecycles are showcase-local |

Conclusion: Rendering evidence is now 4x. No framework-specific divergence detected.

## 4. Cafe Stock vs Events Capacity — Deep Comparison

### 4.1 Cafe Stock Semantics

* Owned by: `MenuItem`
* Decremented at: `confirm_order()` — VALIDATED→CONFIRMED
* Restored at: `cancel_order()`
* Guard: `OutOfStockError`, `InsufficientStockError` → 400
* Ownership: stock belongs to MenuItem, Order references snapshot

### 4.2 Events Capacity Semantics

* Owned by: `Event`
* Derived from: `len(CONFIRMED rsvps)`
* No decrement: count is derived
* FULL guard at: `create_rsvp()` → `CapacityFullError` → 400 FULL
* On cancel: count decreases naturally, no restoration
* Ownership: capacity belongs to Event, RSVP belongs to attendee

### 4.3 Why CapacityManager is NOT justified

* Different owner entity
* Different mutation lifecycle (stock: decrement/restore vs capacity: derived count)
* Different security/ownership
* Different failure modes (OUT_OF_STOCK vs FULL)
* Only structural similarity is `if count >= limit`
* Therefore: CapacityManager MUST NOT be extracted

## 5. Temporal Evidence

* `events` uses `start_time` / `end_time` UTC, invariant `start < end`, `is_upcoming`, sorted by `start_time`
* Only ONE consumer requires interval semantics
* No overlap detection, no scheduler required
* Therefore: TimeRange, OverlapEngine, Scheduler MUST NOT be extracted

## 6. Repository Evidence

* All showcases use Dict + slug_index pattern — structural similarity only
* Lifecycles differ per showcase
* No common persistence lifecycle
* Therefore: GenericRepository, BaseRepository, RepositoryProtocol MUST NOT be extracted

## 7. Architecture Guards

No new guards required. Existing guards remain: pytest, git diff ai_framework empty, git diff --check clean.

## 8. Final Decision

```text
DECISION: NO ABSTRACTION