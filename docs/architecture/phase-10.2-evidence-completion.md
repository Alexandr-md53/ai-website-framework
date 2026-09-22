Phase 10.2 — Evidence Completion — Final
Baseline: cd0b9a9 / phase-9-rendering-pipeline-green / 663 passed
Commit: 75857cd / phase-10-audit-v0.1 — docs/architecture/phase-10-audit-v0.1.md
Type: Audit only — 0 runtime changes
Date: 2026-09-22

Real Files Evidence (from Get-Content)
showcases/cms_lite/domain/user.py — ACTUAL
python
from dataclasses import dataclass
import uuid
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

@dataclass
class User:
    id: uuid.UUID
    email: str
    role: UserRole = UserRole.EDITOR
    is_active: bool = True
    def validate(self):
        if "@" not in self.email:
            raise ValueError("validation.invalid_email:email")

@dataclass
class UserContext:
    user_id: str
    role: UserRole

class PermissionDeniedError(Exception):
    pass
Observations:

No from_raw, no PipelineContext, no GENERATOR
User entity with email validation — different from blog_cms (blog has Author separate)
UserContext is simple VO: user_id: str, role: UserRole
Role normalization lives NOT in domain, but in factory final_dual_factory_v7.py:
_map_role_str(None) → EDITOR, upper, try Enum, unknown → VIEWER
_make_user_context(None) → uuid4() random → try UUID → uuid5 fallback
showcases/blog_cms/domain/user.py — ACTUAL
python
class UserRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"
    GENERATOR = "GENERATOR"

class PermissionDeniedError(Exception): pass

@dataclass(frozen=True)
class UserContext:
    user_id: str
    role: UserRole

@dataclass(frozen=True)
class PipelineContext:
    user: UserContext
    trace_id: str

    @staticmethod
    def from_raw(x_user_id, x_user_role, trace_id=None):
        uid = x_user_id or "system-generator"
        try: uuid.UUID(uid) → keep
        except: uuid5(NAMESPACE_DNS, uid)
        role_raw = (x_user_role or "EDITOR").strip().upper()
        try: role = UserRole(role_raw)
        except: role = VIEWER if role_raw=="VIEWER" else EDITOR
        return PipelineContext(user=UserContext(...), trace_id=...)
Observations:

GENERATOR exists — Type B specific
PipelineContext(user, trace_id) — Type B pipeline context
from_raw lives in domain, not only in factory, with system-generator default and UNKNOWN → EDITOR (except VIEWER)
Factory _ctx_from_headers is single header boundary
showcases/docs_site/domain/user.py — ACTUAL
Get-Content : Cannot find path ... because it does not exist.
Critical: Third consumer has NO identity file. Means docs_site either:

reuses blog_cms pattern without its own domain/user.py (shared file missing)
has identity handled elsewhere (maybe no auth, or uses same as blog_cms)
is not a third independent consumer for identity
Thus we have 2 consumers with files, but semantics differ, and third consumer missing — does not satisfy ≥2 consumers + same semantics + same lifecycle + no security divergence.

Filled 3-Consumer Matrix — Actual Behavior
Role normalization
Input	cms_lite domain	cms_lite factory _map_role_str	blog_cms PipelineContext.from_raw	docs_site	Shared?
ADMIN	No normalization in domain	ADMIN (upper try)	ADMIN	NO FILE	No — cms_lite domain has no from_raw
admin	—	ADMIN (upper)	ADMIN	NO FILE	No — domain vs factory location differs
AdMiN	—	ADMIN	ADMIN	NO FILE	No
EDITOR	—	EDITOR	EDITOR	NO FILE	No
VIEWER	—	VIEWER	VIEWER	NO FILE	No
UNKNOWN / HACKER	—	VIEWER (fail-closed)	EDITOR (fail-open except VIEWER)	NO FILE	DIVERGENCE — BLOCKER
"" empty	—	EDITOR (if not role_val)	EDITOR (or "EDITOR")	NO FILE	Similar but location differs
missing header	—	EDITOR	EDITOR	NO FILE	Similar
Identity normalization
Input	cms_lite domain	cms_lite factory _make_user_context	blog_cms from_raw	docs_site	Shared?
valid UUID	No handling in domain	keep	keep	NO FILE	No — domain has no logic
invalid UUID not-a-uuid	—	uuid5 DNS fallback deterministic	uuid5 DNS fallback deterministic	NO FILE	Similar in factories, but domain differs
empty ""	—	uuid4 random	system-generator fixed	NO FILE	DIVERGENCE — random vs fixed
missing	—	uuid4 random	system-generator fixed	NO FILE	DIVERGENCE
Consumer presence
Feature	cms_lite	blog_cms	docs_site	Count
UserRole	ADMIN/EDITOR/VIEWER (3)	ADMIN/EDITOR/VIEWER/GENERATOR (4)	NO FILE	2 with different values
UserContext	yes (user_id, role) simple	yes frozen + PipelineContext wrapper	NO FILE	2 with different frozen semantics
from_raw / _map_role_str	NO — only in factory helper	YES in domain PipelineContext.from_raw	NO FILE	1 in domain, 1 in factory
PipelineContext	NO	YES (user + trace_id)	NO FILE	1
GENERATOR	NO	YES	NO FILE	1
User with email	YES	NO (Author separate)	?	1
PermissionDeniedError	YES	YES	?	2 — shared name but duplicated definition
Divergence Classification — Final (per gate principle)
From review: do not label UNKNOWN → EDITOR as DEFECT until evidence shows intentional vs legacy.

Divergence	cms_lite	blog_cms	Classification
UNKNOWN → VIEWER vs EDITOR	VIEWER	EDITOR	UNKNOWN / SUSPECTED SECURITY DEFECT — blocker, cannot extract normalize_role()
missing identity → uuid4 random vs system-generator fixed	random	fixed	UNKNOWN — could be INTENTIONAL (random for anon user, fixed for generator service account) or LEGACY
missing role → EDITOR	EDITOR	EDITOR	UNKNOWN — could be INTENTIONAL for test/dev convenience or LEGACY
GENERATOR role presence	absent	present	INTENTIONAL — Type-B-specific, blog_cms only
PipelineContext vs UserContext	UserContext only	PipelineContext(user, trace_id)	INTENTIONAL — Type-B pipeline needs trace_id
from_raw location	factory only (_make_user_context)	domain (PipelineContext.from_raw)	INTENTIONAL / LEGACY — different layering
User with email validation	present	absent (Author model)	INTENTIONAL — different domain models
Principle respected: Not normalizing behavior just to get common contract. Existing behavior fixed as fact, not changed.

Architectural Guard Evaluation
Guard 1: ≥2 consumers + same semantics + same lifecycle + no security divergence

Consumers with identity files: 2 (cms_lite, blog_cms) — but docs_site missing
Same semantics: NO — role values differ (GENERATOR), unknown handling diverges (VIEWER vs EDITOR), identity defaults diverge (random vs fixed), location differs (domain vs factory)
Same lifecycle: NO — cms_lite UserContext per-request without trace_id, blog_cms PipelineContext with trace_id for generation pipeline
No security divergence: NO — UNKNOWN → VIEWER vs EDITOR is security divergence
Guard 2: Do not count consumers as enough proof

Count = 2, but semantics differ → count insufficient
Guard 3: Do not normalize behavior to get contract

We keep UNKNOWN → EDITOR as existing fact in blog_cms, not changing to VIEWER in this phase
Separate security migration would be needed if we decide to change to fail-closed, with its own rationale, tests, and commit boundary
Decision — Outcome B
text
cms_lite  ── semantics A: UserContext(user_id, role), UserRole 3 values, no from_raw in domain, _map_role_str unknown→VIEWER, _make_user_context missing→uuid4 random
blog_cms  ── semantics B: UserContext + PipelineContext(user, trace_id), UserRole 4 values + GENERATOR, from_raw in domain unknown→EDITOR, missing→system-generator
docs_site ── semantics C: NO FILE — no identity contract
Structural similarity exists (both have UserRole, UserContext, PermissionDeniedError, upper normalization, uuid5 fallback), but behavioral semantics differ (GENERATOR, PipelineContext, unknown handling, identity defaults, location).

Conclusion: Outcome B — No abstraction. Identity stays showcase-local.

This is valid audit result. Goal of Phase 10.2 was not necessarily to find abstraction, but to prove whether one is needed.

What is NOT extracted
UserRole / UserContext — keep local (values and frozen semantics differ, third consumer missing)
normalize_role() — blocked by security divergence VIEWER vs EDITOR
normalize_user_id() — blocked by divergence random vs system-generator
_require() — stays showcase-local (policy lists per operation differ, GENERATOR only in blog_cms)
GENERATOR — Type-B-specific, stays in blog_cms
PipelineContext — Type-B-specific, stays in blog_cms
Shared candidates that are genuinely same (case-insensitive upper, uuid5 fallback) are too small and coupled to divergent defaults to justify framework primitive without third consumer confirmation.

Final Gate 10.2 Checklist
┌─────────────────────────────────────┐
│ Phase 10.2 Evidence Completion      │
├─────────────────────────────────────┤
│ ✓ 3 real consumers inspected        │
│   cms_lite: file exists, no from_raw│
│   blog_cms: file exists, with GENERATOR + PipelineContext + from_raw │
│   docs_site: NO FILE — does not exist │
│ ✓ real security probes (via code review) │
│   role: ADMIN/admin/AdMiN → upper in both factories │
│   role: UNKNOWN/HACKER → VIEWER vs EDITOR divergence │
│   identity: invalid UUID → uuid5 fallback shared │
│   identity: missing → uuid4 vs system-generator divergence │
│ ✓ identity normalization matrix filled │
│ ✓ role normalization matrix filled │
│ ✓ divergence classification         │
│   INTENTIONAL (GENERATOR, PipelineContext, uuid5) │
│   UNKNOWN (missing role→EDITOR, missing identity defaults) │
│   UNKNOWN / SUSPECTED SECURITY DEFECT (UNKNOWN→EDITOR vs VIEWER) │
│ ✓ intentional vs legacy separated   │
│ ✓ behavior changes NOT mixed in     │
│   HACKER→EDITOR not fixed in this phase │
│   No normalization for contract     │
└─────────────────────────────────────┘
                 │
                 ▼
        Contract decision
          A: shared proven — NOT MET
          B: no abstraction — SELECTED
                 │
                 ▼
        Phase 10 CLOSED — identity remains showcase-local
Baseline Preservation
text
cd0b9a9
phase-9-rendering-pipeline-green
75857cd / phase-10-audit-v0.1 (docs/architecture/phase-10-audit-v0.1.md)
663 passed — runtime 0 changes
No UserRole/UserContext created in framework
No normalize_role() extracted
No _require() moved to framework
No GENERATOR generalized
No rendering / Publishable / taxonomy touched (frozen)
Next Steps
Commit this evidence completion as phase-10.2-evidence-completion with no runtime changes
Tag phase-10-evidence-completion or phase-10-closed-no-abstraction if Outcome B selected
If future third consumer appears with same semantics (e.g., docs_site adds user.py with same contract as one of existing), re-evaluate with same gate
If security migration decided separately (UNKNOWN → VIEWER fail-closed), do it as dedicated commit with rationale, tests, and security review, not as part of abstraction extraction
End of Phase 10.2 Evidence Completion — Outcome B.


