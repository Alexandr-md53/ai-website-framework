Phase 12 — Gap Audit v0.1 — Remaining Duplication / Framework Boundaries
Baseline:
cd0b9a9 / 663 passed / phase-9-rendering-pipeline-green

Previous:
Phase 8 FROZEN 161e23e / 657
Phase 9 FROZEN cd0b9a9 / 663
Phase 10 CLOSED / NO ABSTRACTION ad9bd67 / phase-10-evidence-completion
Phase 11 CLOSED / NO ABSTRACTION c786c11 / phase-11-evidence-completion

Runtime changes:
0

Type:
Audit only — 0 runtime changes

Purpose:

Есть ли вообще ещё framework-level boundary, которая доказана двумя независимыми consumers?

After two consecutive NO ABSTRACTION (Identity/Auth, Error/API), we do not start next extraction blindly. We inventory remaining duplication to decide if architecture is STABLE.

Scope Exclusions — FROZEN / CLOSED
Rendering          → FROZEN (Phase 9)
  JinjaTemplateRenderer, SeoContext.normalize, SeoInjector.ensure_seo, StaticSiteWriter, GeneratedPage
  Location: ai_framework/rendering/jinja.py, seo.py, static_writer.py
  Evidence: framework-level generic, no domain semantics

Publishable        → FROZEN (Phase 8)
  PublishStatus, list_published, publish/unpublish lifecycle
  Evidence: shared semantics proven

Identity/Auth      → CLOSED / NO ABSTRACTION (Phase 10)
  cms_lite: UserContext, UserRole ADMIN/EDITOR/VIEWER
  blog_cms: PipelineContext.from_raw + GENERATOR, UserRole with GENERATOR
  docs_site: NO FILE — absent
  Result: intentional divergence, security divergence (VIEWER vs GENERATOR, UNKNOWN→EDITOR default)
  Guard: no extraction

Error/API Error Contract → CLOSED / NO ABSTRACTION (Phase 11)
  _parse_uuid: cms_lite _parse_uuid(val, field_name) "Invalid {field}: {val}" vs blog_cms _parse_uuid(s) "Invalid UUID {s}" — different contract
  Exception→HTTP: cms_lite string matching "if forbidden/not found in low" fragile/legacy vs blog_cms typed excepts
  docs_site: domain NotFoundError/ValidationError exist, but api/app_factory.py ABSENT — no third HTTP consumer
  Slug: cms_lite SLUG_RE regex vs blog_cms/docs_site Slug VO — different semantics
  Result: partially overlapping 403/404/400 but no common framework contract proven

Taxonomy (Category/Tag/Author/Section/Version) → showcase-specific
Routes / FROZEN_ROUTES → out of scope, per-showcase
Candidates Inventory
1. Factories / Application Composition
Files:

showcases/cms_lite/api/app_factory.py (real)
showcases/cms_lite/app_factory.py (final_dual_factory_v7.py dual factory)
showcases/blog_cms/app_factory.py (real, typed)
showcases/blog_cms/api/app_factory.py (re-export, FROZEN_ROUTES)
showcases/docs_site/api/app_factory.py — ABSENT
Observed:

Aspect	cms_lite	blog_cms	docs_site
Factory function	create_app(service=None), _build_old_app, _build_new_app, build_cms_lite_app dual detection OldService vs NewService	create_app(service, out_dir), create_test_app(), build_cms_lite_app alias, state cache {"pages": []}	NO FILE
Dependency wiring	service detection via isinstance(OldService), fallback _make_user_context, _map_role_str	explicit svc = service or BlogCmsService(), renderer = Renderer(), generator = SiteGenerator(svc, renderer), out = out_dir or Path("showcases/blog_cms/output")	—
Startup lifecycle	Pydantic models SeoUpdateRequest, MediaCreateRequest, Field(max_length=70)	PipelineContext.from_raw via _ctx_from_headers Depends, FROZEN_ROUTES set	—
_to_dict	80+ lines normalization, status enum handling, __dict__ fallback, special handling for "ItemStatus.DRAFT" -> "DRAFT"	10 lines: hasattr(to_dict) → to_dict() else __dict__ filter _, UUID→str, value→value	—
Evidence status:

Consumer count: 2 (cms_lite, blog_cms) — docs_site absent
Structural similarity: MEDIUM — both define create_app, _to_dict, _parse_uuid, but implementations differ drastically
Semantic similarity: LOW — cms_lite dual factory (old/new compatibility, body role vs header role), blog_cms single factory with generation pipeline G1/G2/G12 + in-memory state + RSS/sitemap fallback generation
Lifecycle similarity: LOW — cms_lite manages SEO/media/media_ids, blog_cms manages site generation + out_dir + state cache
Security divergence: MEDIUM — cms_lite _make_user_context uuid5 fallback, blog_cms PipelineContext.from_raw with UNKNOWN→EDITOR
Decision: PENDING EVIDENCE but initial signal → structural similarity only, no shared composition semantics
From final_dual_factory_v7.py:

python
def create_app(service=None, *args, **kwargs) -> FastAPI:
    svc = service or kwargs.get("service_override")
    if svc is None:
        if NewService: svc = NewService()
        elif OldService: svc = OldService()
    if OldService and isinstance(svc, OldService):
        return _build_old_app(svc)
    else:
        return _build_new_app(svc)
vs blog_cms/app_factory.py:

python
def create_app(service: Optional[BlogCmsService] = None, out_dir: Path | None = None) -> FastAPI:
    svc = service or BlogCmsService()
    renderer = Renderer()
    generator = SiteGenerator(svc, renderer)
→ Different composition contract, not extractable as generic factory abstraction.

2. UUID / Parsing Helpers
Files:

cms_lite: _parse_uuid(val, field_name="id") → HTTPException 400 Invalid {field}: {val}
blog_cms: _parse_uuid(s) → HTTPException 400 Invalid UUID {s}
docs_site: none
Already proven in Phase 11.2:

Signature differ (field_name vs none)
Detail format differ
docs_site absent
CLOSED / NO ABSTRACTION — do not re-open
Other conversion helpers:

_to_dict: cms_lite 80+ lines with status enum handling, blog_cms 10 lines minimal — different semantics
_map_role_str, _make_user_context: only cms_lite
_ctx_from_headers: only blog_cms
→ No shared parsing boundary
3. Validation Primitives
Files:

ai_framework/content/slug.py — Slug VO
python

@dataclass(frozen=True, slots=True)
class Slug:
value: str
post_init: rejects invalid, no auto-lowercase, pattern ^[a-z0-9]+(?:-[a-z0-9]+)*$
try_normalize: explicit opt-in, lower, replace _/space → -, strip

- cms_lite domain: `SLUG_RE` regex → `ValidationError`
- blog_cms: `Slug(slug)` VO → `ValueError` → mapped to 400
- docs_site: `Slug(slug)` VO → same

**Matrix:**

| Concern | cms_lite | blog_cms | docs_site | Result |
|---|---|---|---|---|
| Slug validation | `SLUG_RE.match(slug)` + `ValidationError` | `Slug VO` + `ValueError` | `Slug VO` | Different lifecycle, but semantics similar (lowercase-kebab) |
| Email validation | Not present in inventory | Not present | Not present | No evidence |
| Pagination/filter | `list_published(category_id, tag_id)` Optional UUID | `list_published(category_slug, tag_slug)` slug-based + framework `list_published` + `framework_list_published` | `list_published(section_slug, version_slug)` | Different contract: UUID vs slug vs section/version |
| Domain validation | `validate()`, `validate_for_draft()` via `ValueError` | `validate()`, `validate_for_draft()` via Slug VO | `title/slug/content invalid` length check `<10` | Structural similarity but different rules |

**Evidence status:**
- Slug VO already framework-level in `ai_framework/content/slug.py` — FROZEN? Not yet tagged but exists as shared primitive
- But usage differs: cms_lite still uses regex, not VO — legacy divergence
- Email, pagination, generic validation: no 3-consumer shared semantics proven
- Decision: PENDING — Slug VO is only proven shared primitive, but already extracted, not new candidate

### 4. Repository / Persistence Boundaries

**Files to check (not yet in 9 synced artifacts, need Get-Content):**
- `showcases/cms_lite/infrastructure/persistence_adapter.py`
- `showcases/cms_lite/services/cms_service.py` `_categories`, `_tags`, `_items` Dict[UUID, ...] in-memory
- `showcases/blog_cms/services/blog_service.py` same pattern
- `showcases/docs_site/services/docs_service.py` same pattern

Observed from pasted files:

```python
# cms_lite framework wired
self._categories: Dict[uuid.UUID, Category] = {}
self._tags: Dict[uuid.UUID, Tag] = {}
self._items: Dict[uuid.UUID, Item] = {}
self._media: Dict[uuid.UUID, Media] = {}
self._category_slugs: Dict[str, uuid.UUID] = {}
# + FrameworkInMemoryPersistenceProvider, ValidationEngine, SlugOrchestrator, UniversalCRUDEngine

# blog_cms
self._slugs: Dict[str, Dict[str, uuid.UUID]] = {"category": {}, "tag": {}, "author": {}, "post": {}}

# docs_site
self._sections: Dict[uuid.UUID, Section] = {}
self._versions: Dict[uuid.UUID, Version] = {}
self._pages: Dict[uuid.UUID, DocPage] = {}
Evidence status:

Structural similarity: HIGH — all use Dict[UUID, Entity] + slug index
Semantic similarity: MEDIUM — but CRUD patterns differ:
cms_lite: framework-wired service uses FrameworkInMemoryPersistenceProvider, ValidationEngine, AsyncSlugOrchestrator, UniversalCRUDEngine — Phase 6+ complexity
blog_cms: simple Dict + framework_list_published
docs_site: simple Dict + framework_list_published
Lifecycle: DIFFERENT — cms_lite has transaction/session-like async orchestration, blog_cms/docs_site simple sync
Security: no divergence, but lifecycle divergence blocks
Decision: PENDING — looks like structural similarity, but not same domain contract (Item vs Post vs DocPage have different fields, SEO handling differs)
5. Configuration / Environment Handling
Files:

showcases/blog_cms/services/site_generator.py templates_dir resolution:
python

here = Path(file).resolve()
candidate = here.parent.parent / "templates"
if candidate.exists(): templates_dir = candidate
else: templates_dir = Path("showcases/blog_cms/templates")

- `extraction_pr/ai_framework/rendering/jinja.py`:
```python
def __init__(self, templates_dir: Path | str | None = None):
  if templates_dir is None: templates_dir = Path("templates")
showcases/cms_lite/api/app_factory.py no config, hardcoded titles
showcases/blog_cms/app_factory.py out_dir: Path | None = None → Path("showcases/blog_cms/output") vs test temp dir
Evidence status:

Consumer count: 2 at most (blog_cms factory + rendering)
Structural similarity: LOW — each has different fallback logic
Semantic: different — templates_dir resolution vs output dir vs no config
No env vars, no settings object, no shared contract
Decision: NO CANDIDATE — showcase-local config, no framework boundary
Summary Matrix
Candidate	Consumer count	Structural similarity	Semantic similarity	Lifecycle similarity	Security divergence	Evidence status	Decision
Factories / composition	2 (cms_lite, blog_cms), docs_site absent	MEDIUM — both have create_app, _to_dict, _parse_uuid	LOW — dual factory vs single + generation pipeline	LOW — SEO/media vs generation state cache	MEDIUM — uuid5 fallback vs from_raw UNKNOWN→EDITOR	Partial inventory, no shared contract proven	PENDING — likely NO ABSTRACTION
UUID / parsing helpers	2, docs_site absent	MEDIUM	LOW — different signatures/details	LOW — different _to_dict	None	Already CLOSED Phase 11.2	CLOSED / NO ABSTRACTION — do not re-open
Validation primitives — Slug VO	2-3 but cms_lite uses regex legacy	MEDIUM	MEDIUM — same pattern regex	LOW — VO vs regex	None	Slug VO already exists in ai_framework/content/slug.py, but cms_lite not using it — legacy	Existing primitive, no new extraction
Validation — email/pagination/filter	1-2, not consistent	LOW	LOW	LOW	None	No evidence	NO CANDIDATE
Repository / persistence	3 structurally, but	HIGH structurally Dict+index	MEDIUM — different entities	LOW — framework-wired async orchestrator vs simple Dict	None	Structural similarity only, different domain contracts	PENDING — likely NO ABSTRACTION, needs deeper inventory
Configuration / env	1-2	LOW	LOW	LOW	None	No shared settings object	NO CANDIDATE
Main Result — Phase 12 Gap Audit
Not necessarily extraction. Two valid outcomes:

A — найден новый доказанный candidate
    → отдельный Phase 13 extraction with evidence

B — framework boundaries уже достаточно минимальны
    → ARCHITECTURE STABLE / FREEZE
Current signal after inventory of 9 synced artifacts + real factory files from previous steps:

Factories / application composition — previously marked MEDIUM, but consciously postponed. Now inventory shows different composition semantics (dual Old/New service detection vs single service + renderer + generator + out_dir). No identical input/output semantics. Not a framework boundary.
Repository / persistence — structural similarity (Dict[UUID, Entity] + slug index) but different lifecycle (cms_lite uses FrameworkInMemoryPersistenceProvider + ValidationEngine + AsyncSlugOrchestrator + UniversalCRUDEngine, blog_cms/docs_site simple). Different domain contracts (Item with media_ids vs Post with author_id/category_id vs DocPage with section_id/version_id). No shared contract proven yet.
Validation primitives — Slug VO already exists, but cms_lite still uses legacy regex. Email/pagination not shared.
Configuration — no shared boundary.
Preliminary assessment: Framework boundaries already minimal after Phase 8/9. Remaining duplication is showcase-specific or structural similarity only, not same semantics + same lifecycle + no security divergence.

But to make final decision B (STABLE/FREEZE), need to check remaining files not in 9 synced artifacts:

powershell
Get-Content showcases/cms_lite/infrastructure/persistence_adapter.py -ErrorAction SilentlyContinue
Get-Content showcases/cms_lite/domain/*.py | Select-String "validate|SLUG_RE"
Get-Content showcases/blog_cms/domain/*.py | Select-String "validate|Slug"
Get-Content showcases/docs_site/domain/*.py | Select-String "validate"
Get-Content showcases/cms_lite/services/cms_service.py | Select-String "_categories|_items|_slugs"
If those also show only structural similarity, then Outcome B — ARCHITECTURE STABLE / FREEZE is justified.

Next Step — Concrete
Create only:

docs/architecture/phase-12-gap-audit-v0.1.md  — this file
Inventory all remaining candidates with status:

candidate
consumer count
structural similarity
semantic similarity
lifecycle similarity
security divergence
evidence status
decision: PENDING / CLOSED / NO CANDIDATE
Runtime: 0 changes.

This gives much stronger next point than picking next abstraction by inertia.

Commit
powershell
Copy-Item phase-12-gap-audit-v0.1.md docs/architecture/phase-12-gap-audit-v0.1.md
git add docs/architecture/phase-12-gap-audit-v0.1.md
git commit -m "phase-12.1: gap audit v0.1 — baseline cd0b9a9/663, factories composition different semantics dual vs single+generator, uuid helpers CLOSED Phase 11, slug VO existing primitive cms_lite regex legacy, repository structural similarity but lifecycle divergence async orchestrator vs simple Dict, config no shared boundary, preliminary ARCHITECTURE STABLE signal, runtime 0"
git tag phase-12-gap-audit-v0.1
git push origin master --tags
After this, decide Phase 13 or FREEZE based on evidence.

