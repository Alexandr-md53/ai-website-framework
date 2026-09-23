Phase 11.2 — Evidence Completion — Error / API Error Contract
Baseline:
cd0b9a9 / 663 passed / phase-9-rendering-pipeline-green

Phase 11.1:
1f7b23a / phase-11-audit-v0.1

Runtime changes:
0

Consumers:
showcases/cms_lite
showcases/blog_cms
showcases/docs_site

Candidate:
Error / API Error Contract

Type:
Audit evidence completion — 0 runtime changes

Inventory — Real Files (Get-Content)
powershell
showcases/cms_lite/api/app_factory.py
showcases/cms_lite/services/cms_service.py
showcases/cms_lite/services/cms_service_framework_wired.py
showcases/blog_cms/app_factory.py
showcases/blog_cms/services/blog_service.py
showcases/blog_cms/api/app_factory.py  # re-export
showcases/docs_site/services/docs_service.py
showcases/docs_site/api/app_factory.py  # absent / empty — no HTTP boundary
Evidence from synced artifacts + pasted Get-Content:

cms_lite/api/app_factory.py (real, identical to final_dual_factory_v7.py)
python
def _parse_uuid(val, field_name="id"):
    if isinstance(val, UUID): return val
    if isinstance(val, str):
        try: return UUID(val)
        except: raise HTTPException(400, f"Invalid {field_name}: {val}")
    raise HTTPException(400, f"Invalid {field_name}: {val}")

# OLD app (body role):
if "forbidden" in low or "permission" in low or "unauthorized" in low → 403
if "not found" in low → 404
else → 400

# NEW app (header role Phase 5):
same string matching — fragile / legacy
Domain exceptions:

NotFoundError, ValidationError — local classes
Slug validation: SLUG_RE regex → ValidationError
blog_cms/app_factory.py (real, identical to blog_cms_skeleton)
python
def _parse_uuid(s: str) -> UUID:
    try: return UUID(s)
    except: raise HTTPException(400, f"Invalid UUID {s}")

# mapping — typed:
except PermissionDeniedError → 403
except NotFoundError → 404
except ValidationError, ValueError → 400
Domain:

NotFoundError, ValidationError, PermissionDeniedError — local
Slug: Slug VO → ValueError on invalid → mapped to 400
_require(ctx, allowed) → typed
docs_site/services/docs_service.py
python
def create_section(name, slug, ...): Slug(slug) → ValueError if invalid
def create_page(...): ValidationError / NotFoundError for section/version
def publish_page(page_id): NotFoundError if missing
def get_published_by_slug(slug): Slug(slug) try → NotFoundError
Domain exceptions exist, but:

showcases/docs_site/api/app_factory.py → NO FILE / empty
No HTTP mapping, no _parse_uuid, no 403/404/400 mapping at API boundary
3-Consumer Matrix
Concern	cms_lite	blog_cms	docs_site	Result
_parse_uuid	field_name + custom detail Invalid {field}: {val}	fixed signature/detail Invalid UUID {s}	no factory	No shared contract
Invalid UUID	400	400	no HTTP mapping	Different contract (detail format + signature differ)
Not found	string matching if "not found" in low → 404	typed except NotFoundError → 404	no factory, domain NotFoundError only	Different lifecycle (fragile vs typed vs absent)
Forbidden	string matching if "forbidden" in low → 403	typed except PermissionDeniedError → 403	no auth / no 403 mapping	Security divergence (fragile classification + missing consumer)
Validation	string mapping → 400	typed → 400	no factory, domain ValidationError only	Different lifecycle
Slug validation	regex / ValidationError	Slug VO / ValueError → 400	Slug VO / no HTTP mapping	Different semantics (regex vs VO)
Exception mapping	fragile string inspection if ... in str(e).lower()	typed exceptions	absent	No shared boundary
Guard Evaluation
Не экстрагировать _parse_uuid только потому, что реализация похожа. Сначала доказать одинаковые input/output semantics и одинаковый error contract.

2+ consumers недостаточно. Нужны одинаковая семантика + одинаковый lifecycle + отсутствие security divergence.

Checks:

400 invalid UUID: both return 400, but:
cms_lite: _parse_uuid(val, field_name) → Invalid {field}: {val}
blog_cms: _parse_uuid(s) → Invalid UUID {s}
→ input/output semantics differ (signature + detail)
→ fails guard "identical semantics"
404 / 403 / 400 mapping:
cms_lite: string-based classification — fragile, legacy candidate, may misclassify
blog_cms: typed exception mapping — clean
docs_site: no HTTP boundary — no third consumer
→ different lifecycle, security divergence (string matching can leak or misclassify)
Slug validation:
cms_lite: SLUG_RE regex + ValidationError
blog_cms/docs_site: Slug VO + ValueError
→ different semantics, though both map to 400 in HTTP consumers that exist
Third consumer:
docs_site has domain exceptions but HTTP boundary absent
→ fails "3 real consumers with same HTTP semantics"
Classification
Divergence	Classification
_parse_uuid signature field_name vs fixed	DIFFERENT CONTRACT — no shared primitive
Invalid {field}: {val} vs Invalid UUID {s} detail format	DIFFERENT CONTRACT — not identical output
NotFoundError string matching vs typed	DIFFERENT LIFECYCLE — fragile vs typed
PermissionDeniedError string matching vs typed, docs_site absent	SECURITY DIVERGENCE + missing consumer
Slug regex vs VO	DIFFERENT SEMANTICS
Exception mapping fragile vs typed vs absent	NO SHARED BOUNDARY — LEGACY vs INTENTIONAL vs ABSENT
docs_site/api/app_factory.py NO FILE	NO THIRD HTTP CONSUMER — blocks framework extraction
Important observation (your correction):

In two consumers there is partially overlapping mapping semantics (403/404/400), but common framework contract is not proven due to absence of third HTTP consumer and differences in lifecycle/security behavior.

Not "only candidate with same semantics" — only partially overlapping.

Final Outcome
Outcome B — NO ABSTRACTION

_parse_uuid:
  remain showcase-local
  cms_lite: _parse_uuid(val, field_name) with custom detail
  blog_cms: _parse_uuid(s) with fixed detail
  docs_site: no factory

exception → HTTP mapping:
  remain showcase-local
  cms_lite: string-based classification → fragile / legacy candidate → NOT fixed during extraction audit
  blog_cms: typed exception mapping → existing behavior → NOT promoted to framework contract
  docs_site: domain exceptions exist → HTTP boundary absent → no third consumer

typed exception primitives (NotFoundError, ValidationError, PermissionDeniedError):
  remain showcase-local per showcase — no framework extraction

Runtime:
  0 changes
Separate observations (preserved, not fixed in audit)
cms_lite:
  string-based exception classification
  → fragile / legacy candidate
  → NOT fixed during extraction audit
  → potential future cleanup workstream (replace string inspection with typed handling)

blog_cms:
  typed exception mapping
  → existing behavior
  → NOT promoted to framework contract
  → remains showcase-local

docs_site:
  domain exceptions exist (NotFoundError, ValidationError)
  → HTTP boundary absent (no api/app_factory.py)
  → no third consumer
  → blocks framework boundary proof
Principle preserved:

Do not turn local cleanup into framework abstraction.

This aligns with Phase 10 lesson: abstraction is evidence-driven outcome, not mandatory deliverable.

Baseline Preservation
cd0b9a9
phase-9-rendering-pipeline-green
663 passed
Phase 8 CLOSED / FROZEN 161e23e / 657
Phase 9 CLOSED / FROZEN cd0b9a9 / 663
Phase 10 CLOSED / NO ABSTRACTION ad9bd67
Phase 11.1 AUDIT v0.1 1f7b23a
Phase 11.2 EVIDENCE COMPLETION — this doc
Runtime changes: 0
Candidate: Error/API Error Contract
Decision: NO ABSTRACTION (Outcome B)
Commit
powershell
Copy-Item phase-11.2-evidence-completion.md docs/architecture/phase-11.2-evidence-completion.md
git add docs/architecture/phase-11.2-evidence-completion.md
git commit -m "phase-11.2: evidence completion — 3-consumer matrix cms_lite string-matching vs blog_cms typed vs docs_site NO FACTORY, _parse_uuid field_name vs fixed signature different contract, forbidden/not found string mapping vs typed different lifecycle, slug regex vs VO different semantics, guard identical semantics not proven, outcome B no abstraction, remain showcase-local, no runtime changes"
git tag phase-11-evidence-completion
git push origin master --tags
After this, Phase 11 CLOSED as successful audit — same as Phase 10.2.

Next runtime extraction only with new audit/evidence cycle.

