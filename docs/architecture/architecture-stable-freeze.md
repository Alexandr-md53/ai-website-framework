Architecture Stable — Freeze Checkpoint
Baseline:
cd0b9a9 / 663 passed / phase-9-rendering-pipeline-green

Purpose:
Convert ARCHITECTURE STABLE decision into verifiable repository state.
Stop extraction churn. Framework must not grow without new evidence.

Frozen / Audited State
Baseline: cd0b9a9 / 663 passed

Frozen:
  Phase 8 — Publishable Lifecycle — 161e23e / 657 / phase-8-publishable-lifecycle-green
    ai_framework/content/publishable — PublishStatus, list_published, publish/unpublish invariants

  Phase 9 — Rendering Pipeline — cd0b9a9 / 663 / phase-9-rendering-pipeline-green
    ai_framework/rendering/jinja.py — JinjaTemplateRenderer generic, templates_dir only
    ai_framework/rendering/seo.py — SeoContext.normalize, SeoInjector.ensure_seo, no domain knowledge
    ai_framework/rendering/static_writer.py — StaticSiteWriter, path traversal guards, clean flag
    ai_framework/rendering/generated_page.py — GeneratedPage relative path

Audited / no abstraction (valid success):
  Phase 10 — Identity/Auth — ad9bd67 / phase-10-evidence-completion, audit 75857cd
    cms_lite: UserContext, UserRole ADMIN/EDITOR/VIEWER simple
    blog_cms: PipelineContext.from_raw, UserRole ADMIN/EDITOR/VIEWER/GENERATOR, UNKNOWN→EDITOR
    docs_site: NO FILE — absent
    Result: INTENTIONAL divergence, security divergence, different lifecycle → NO ABSTRACTION
    Guard: not same semantics + lifecycle + security → no extraction
    String-based role handling remains showcase-local

  Phase 11 — Error/API Contract — c786c11 / phase-11-evidence-completion, audit 1f7b23a
    cms_lite: _parse_uuid(val, field_name) "Invalid {field}: {val}" + string matching "if forbidden/not found in low" fragile/legacy
    blog_cms: _parse_uuid(s) "Invalid UUID {s}" + typed except PermissionDeniedError→403, NotFoundError→404, ValidationError/ValueError→400
    docs_site: domain NotFoundError/ValidationError exist, but api/app_factory.py ABSENT — no third HTTP consumer
    Slug: cms_lite SLUG_RE regex vs blog_cms/docs_site Slug VO — different semantics
    Result: partially overlapping 403/404/400 in two consumers, but no common framework contract proven
    Guard: identical semantics not proven → NO ABSTRACTION

Gap audit:
  Phase 12.1 — 5b4fac9 / phase-12-gap-audit-v0.1 — inventory of remaining candidates
    Factories / composition: dual OldService/NewService vs single + Renderer+Generator+state cache — different composition semantics
    UUID helpers: CLOSED Phase 11
    Validation: Slug VO existing primitive ai_framework/content/slug.py, cms_lite regex legacy
    Repository: structural Dict[UUID, Entity] + slug index, but lifecycle async orchestrator vs simple Dict
    Config: no shared boundary, templates_dir fallback different

  Phase 12.2 — 3d98ce0 / phase-12-evidence-completion
    Remaining: infrastructure/persistence_adapter.py + domain/*.py
    Persistence adapter: FrameworkInMemoryPersistenceProvider+ValidationEngine+AsyncSlugOrchestrator+UniversalCRUDEngine (cms_lite) vs simple Dict (blog_cms/docs_site)
      — framework infra vs showcase impl, async vs sync, different transaction/error/ownership semantics, security divergence
    Domain: Slug VO existing, SeoMeta same fields different validation Pydantic max_length vs dataclass, Status DRAFT/PUBLISHED same names different types domain-specific, content invariants different per domain
    Guard: 2+ consumers + same semantics + same lifecycle + no security divergence = candidate → NOT MET
    Outcome B — ARCHITECTURE STABLE / FREEZE
    Runtime changes: 0
Repository verification (to be filled by local run):

powershell
pytest -q
# Expected: 663 passed

git status --short
# Expected: no runtime changes, only this doc if not yet committed

git log --oneline --decorate -12
# Expected: 3d98ce0 phase-12.2, 5b4fac9 phase-12.1, c786c11 phase-11.2, 1f7b23a phase-11.1, ad9bd67 phase-10.2, 75857cd phase-10.1, cd0b9a9 phase-9, 161e23e phase-8

git tag --list "phase-*"
# Expected: phase-8-publishable-lifecycle-green, phase-9-rendering-pipeline-green,
#           phase-10-audit-v0.1, phase-10-evidence-completion,
#           phase-11-audit-v0.1, phase-11-evidence-completion,
#           phase-12-gap-audit-v0.1, phase-12-evidence-completion
What Framework May Own
Framework may own only proven generic boundaries:
  content/publishable — PublishStatus, publish/unpublish lifecycle, list_published contract
  rendering — JinjaTemplateRenderer, SeoContext.normalize, SeoInjector.ensure_seo, StaticSiteWriter, GeneratedPage
  proven existing primitives — Slug VO (ai_framework/content/slug.py) — frozen, no filesystem rules, no auto-lowercase

Evidence requirement for any new boundary:
  2+ independent consumers (real showcases/domains, not one)
  + same semantics (identical input/output, identical error contract, identical detail format)
  + same lifecycle (same sync/async, same transaction, same ownership)
  + no security divergence (same role handling, same auth placement, no fragile string inspection)
What Framework Must NOT Grow By
Framework must NOT grow by:
  structural similarity (same field names id/name/slug, similar CRUD, same Dict pattern)
  one consumer (single showcase/domain, or docs_site NO FILE)
  speculative interfaces (factory that looks similar but composes different services)
  domain-specific semantics (ItemStatus vs PostStatus vs DocStatus, Item.media_ids vs Post.author_id vs DocPage.section_id)
  security normalization (VIEWER vs GENERATOR, UNKNOWN→EDITOR vs uuid5 fallback, string matching "forbidden"/"not found")
  local cleanup (cms_lite string-based exception classification → fragile/legacy candidate, NOT fixed during audit, not promoted to framework)
  parsing helper similarity (_parse_uuid different signatures/details, _to_dict 80+ lines vs 10 lines)
New Abstraction Rule
New abstraction requires a new independent consumer/domain and a fresh Audit → Evidence → Contract → Decision cycle.

Process:

Feature work / bug fixes / new showcase/domain
        │
        ▼
Real duplication appears in 2+ independent consumers with same semantics+lifecycle+no security divergence
        │
        ▼
Audit — inventory real files via Get-Content, prove consumers, matrix structural/semantic/lifecycle/security
        │
        ▼
Evidence — docs/architecture/phase-XX-audit-v0.1.md + evidence-completion with 3-consumer matrix
        │
        ▼
Contract — document identical input/output, error contract, lifecycle, security
        │
        ▼
Abstraction decision — if proven → minimal extraction, else NO ABSTRACTION (valid success)
Regime change:

Before: «Что ещё можно обобщить?»
After:  «Ничего не обобщаем, пока реальный development не даст evidence для обобщения»
Baseline Preservation
cd0b9a9 / 663 passed remains working baseline
Runtime changes since baseline: 0
Architecture Stable checkpoint: phase-12-architecture-stable (not extraction tag)
Next architectural commit only on new evidence
Commit + Tag
powershell
Copy-Item architecture-stable-freeze.md docs/architecture/architecture-stable-freeze.md
git add docs/architecture/architecture-stable-freeze.md
git commit -m "freeze: architecture stable checkpoint — baseline cd0b9a9/663, Phase 8/9 frozen, Phase 10/11 no abstraction, Phase 12 gap audit stable, framework may own only proven generic boundaries publishable+rendering+Slug VO, must NOT grow by structural similarity/one consumer/speculative interfaces/domain semantics/security normalization, new abstraction requires new consumer + fresh Audit→Evidence→Contract→Decision, regime change nothing generalizes until real development gives evidence, runtime 0"
git tag phase-12-architecture-stable
git push origin master --tags
After this, extraction work stops. Product work continues.

Architecture Stable
       │
       ├── feature work
       ├── bug fixes
       ├── tests
       └── новый showcase/domain
               │
               ▼
      появляется реальный повторный pattern
               │
               ▼
      Audit → Evidence → Contract → Decision
