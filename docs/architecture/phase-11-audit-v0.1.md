Phase 11 — Audit v0.1 — Error Handling / API Error Contract
Baseline: cd0b9a9 / phase-9-rendering-pipeline-green / 663 passed
Previous: Phase 8 CLOSED/FROZEN 161e23e / 657, Phase 9 CLOSED/FROZEN cd0b9a9 / 663, Phase 10 CLOSED/NO ABSTRACTION ad9bd67 / phase-10-evidence-completion
Type: Audit only — 0 runtime changes
Candidate: Error Handling / API Error Contract — marked MEDIUM in earlier candidate matrix, but decision PENDING EVIDENCE

Purpose
Phase 10 proved architectural principle:

Abstraction is an evidence-driven outcome, not a mandatory deliverable.
≥2 consumers + same semantics + same lifecycle + no security divergence — count alone insufficient.

Phase 11 follows same strict order:

11.1 Audit — inventory real implementations (this doc)
  ↓
11.2 Evidence — 3-consumer + security matrix
  ↓
11.3 Contract discovery
  ↓
  ├─ shared semantics proven → minimal primitive
  └─ structural similarity only → NO ABSTRACTION
  ↓
11.3+/11.4 migration — only if proven
  ↓
guards + regression + freeze
No runtime extraction now. Only inventory.

What to Check in 11.1 — Error Handling
Without code changes, open real files in repo:

powershell
# cms_lite
Get-Content showcases/cms_lite/services/cms_service.py | Select-String "NotFound|Validation|PermissionDenied|Error"
Get-Content showcases/cms_lite/services/cms_service_framework_wired.py | Select-String "NotFound|Validation|PermissionDenied|_require"
Get-Content showcases/cms_lite/api/app_factory.py | Select-String "_parse_uuid|HTTPException|status_code|detail|forbidden|not found"
Get-Content showcases/cms_lite/domain/*.py | Select-String "Error|Exception|validate"

# blog_cms
Get-Content showcases/blog_cms/services/blog_service.py | Select-String "NotFoundError|ValidationError|PermissionDeniedError|_require"
Get-Content showcases/blog_cms/api/app_factory.py | Select-String "_parse_uuid|HTTPException|403|404|400|detail"
Get-Content showcases/blog_cms/domain/*.py | Select-String "Error|Exception"

# docs_site
Get-Content showcases/docs_site/services/docs_service.py | Select-String "NotFound|Validation|PermissionDenied|_require"
Get-Content showcases/docs_site/api/app_factory.py | Select-String "_parse_uuid|HTTPException|403|404|400"
Get-Content showcases/docs_site/domain/*.py | Select-String "Error|Exception"
Inventory questions:

1. Error representation
Domain exceptions: NotFoundError, ValidationError, PermissionDeniedError — names, module location, inheritance, payload
Do they carry field, code, detail or just str?
Are they duplicated per showcase or shared?
Example from synced artifacts: final_dual_factory_v7.py defines _parse_uuid(val, field_name) → 400 Invalid {field_name}: {val} and blog_cms_skeleton/app_factory.py defines _parse_uuid(s) → 400 Invalid UUID {s} — different detail format
2. Exception → HTTP mapping
Where is mapping done? In factory (except ValidationError → 400, NotFound → 404, PermissionDenied → 403)?
Message parsing via if "forbidden" in low vs explicit except PermissionDeniedError — fragile string matching vs typed handling
In final_dual_factory_v7.py old app uses if "forbidden" in low or "permission" in low → 403, while new app uses Depends(get_current_user) + explicit excepts
Security behavior: does 403 leak existence? Does 404 for permission check leak?
3. Validation errors
How validation failures represented: ValueError vs ValidationError vs Pydantic field_validator?
HTTP status: 400 vs 422?
Payload schema: {detail: "..."} vs {code, field} vs {errors: []}?
Are slug validations (Slug VO) using ValueError → mapped to 400 consistently?
4. _parse_uuid and parsing helpers
Location: factory helper duplicated in cms_lite/api/app_factory.py and blog_cms/api/app_factory.py
Semantics:
cms_lite new: _parse_uuid(val, field_name="id") → 400 Invalid {field_name}: {val}
blog_cms skeleton: _parse_uuid(s) → 400 Invalid UUID {s}
blog_cms phase61: not in site_generator, but in app_factory
Lifecycle: same — parse path param / body field → raise 400
Security: both 400, no divergence, but detail format differs
Is there also _parse_slug, _parse_status?
5. HTTP semantics differences
status_code usage: 400 for validation, 403 for forbidden, 404 for not found — consistent?
Any showcase returns 401? When missing auth headers?
Any returns 409 for conflict (slug already exists)?
Does GET /public/... return 404 vs 403 differently than admin routes?
6. Error payload/schema
Current observed: HTTPException(status_code=400, detail="Invalid UUID ...") → FastAPI returns {"detail": "..."}
Is there custom error envelope? {"code": "...", "message": "..."}?
Do validation errors return field-level details?
Is there logging/trace_id attached to errors?
7. Differences that would block extraction
If one showcase maps PermissionDenied → 401 and another → 403 → security divergence blocker
If one returns {"detail": str} and another returns {"error": {"code": ...}} → different contract
If one uses string matching if "forbidden" in low and another typed exception, but semantics same → may still be shared if normalized
If lifecycle differs (one does error handling in service, one in factory) → not same lifecycle
Guard — Same as Phase 10
2+ consumers недостаточно. Нужны одинаковая семантика + одинаковый lifecycle + отсутствие security divergence.

Even if all 3 showcases have _parse_uuid, we must prove:

Same semantics: invalid UUID → 400 with same kind of detail (exact message can differ, but status and error class must be same)
Same lifecycle: parsing at API boundary (factory), not deep in domain
No security divergence: no difference between 403 vs 404 leaking info, no 401 vs 403 confusion
Why Error Contract is Interesting Candidate
From Phase 10 evidence:

final_dual_factory_v7.py _parse_uuid duplicated logic + error mapping via string contains — fragile
blog_cms_skeleton/app_factory.py _parse_uuid similar but different signature
Previous candidate matrix marked Error triple + _parse_uuid as MEDIUM interest
Unlike Identity/Auth, error boundary is narrower and potentially more generic (no GENERATOR-type extension)
Can be checked across 3 showcases without runtime change
If shared contract proven, minimal primitive could be: ApiError, ErrorCode, parse_uuid() helper, or exception → http mapper — but only if evidence shows same semantics
However, still PENDING EVIDENCE — may result in NO ABSTRACTION like Phase 10.

Next Step — Evidence Collection
After this audit v0.1, create probe tasks:

powershell
# 11.2 evidence — fill matrix
# Create temporary test file tests/test_phase11_error_probe.py (no prod change)
# Probe invalid UUID, not found, forbidden, validation

python -m pytest tests/test_phase11_error_probe.py -xvs
Matrix template to fill:

Scenario	cms_lite	blog_cms	docs_site	Shared?
invalid UUID param	400 detail?	400 detail?	?	?
not found id	404	404	?	?
forbidden VIEWER create	403	403	?	?
missing auth headers	?	?	?	?
validation empty name	400	400	?	?
slug invalid	400 ValueError?	400 ValidationError?	?	?
duplicate slug	400 or 409?	400?	?	?
Classification:

INTENTIONAL — different error codes for different domain reasons
LEGACY — old string matching if "forbidden" in low
UNKNOWN / SUSPECTED DEFECT — e.g., 403 vs 404 leak
Baseline Preservation
cd0b9a9
phase-9-rendering-pipeline-green
663 passed
Phase 8/9 FROZEN
Phase 10 CLOSED / NO ABSTRACTION ad9bd67
Runtime changes: 0
Candidate: Error/API Error Contract
Decision: PENDING EVIDENCE
This document is audit only, not contract.

Deliverable for 11.1
File: docs/architecture/phase-11-audit-v0.1.md (this file)

Inventory list of real files
Observed duplications: _parse_uuid, exception mapping, HTTPException detail formats
Candidate guard evaluation criteria
No runtime changes, no framework code
Next commit:

git add docs/architecture/phase-11-audit-v0.1.md
git commit -m "phase-11.1: audit v0.1 — baseline cd0b9a9/663, candidate Error/API Error Contract, inventory of _parse_uuid and exception→HTTP mapping, MEDIUM interest, decision PENDING EVIDENCE, no runtime changes"
git tag phase-11-audit-v0.1
