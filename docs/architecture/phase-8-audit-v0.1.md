Phase 8 Architecture Audit v0.1 — FINAL (with clarification)
Baseline: 2191b1a / phase-7-2-static-site-generator-protocol-green / 629 passed
Date: Phase 8.1 — analysis only, no runtime changes
Phase 8.2 — contract design only, no runtime changes

Principle preserved
Сначала второй реальный consumer → затем abstraction.

Accepted target — NARROW Publishable Content Lifecycle
Previous wide draft rejected:

python
class PublishableProtocol(Protocol):
    id, title, slug, status, to_dict()
Correct narrow per review:

text
PublishStatus: DRAFT / PUBLISHED
Slug: domain VO (domain rules only, no filesystem)
PublishableProtocol: status + slug only
list_published(items): pure generic function
Taxonomy remains second candidate (same shape, different semantics) — DO NOT extract yet.

Slug nuance — behavior-preserving decision
Existing Post contract: SLUG_RE = ^[a-z0-9]+(?:-[a-z0-9]+)*$ — REQUIRES lowercase, REJECTS "Hello World", does NOT auto-lowercase.

If we introduce lowercase normalized VO that auto-converts "Hello World" → "hello-world", we CHANGE behavior.

Decision for Phase 8.2:

Initial Slug VO: REJECT "Hello World" (preserve existing valid → preserved exactly, invalid → rejected)
Normalization as explicit opt-in method Slug.try_normalize() only, not default
Normalization added later only if proven as established domain contract
Also: Content slug semantics ≠ Filesystem path safety

Slug: non-empty, regex, no / (single segment)
StaticSiteWriter owns: no .., no absolute, no drive, duplicate fail-fast (already in 7.2)
Capability Matrix v0.2
Capability	cms_lite	blog_cms	docs_site	Framework
CRUD	yes	yes	yes	domain-local
Publish status DRAFT/PUBLISHED	yes	yes	yes	NOT extracted — candidate narrow
Slug VO	partial (SLUG_RE in blog)	yes	no validation	NOT extracted — candidate narrow
Taxonomy grouping	no	yes	yes	NOT extracted — second candidate
Rendering pipeline	no	yes	yes	Extracted 7.2
SEO	yes	yes	yes	Extracted
Forms / Rich UI	yes	partial	no	1 consumer → DO NOT EXTRACT
PipelineContext / Identity	yes	no	no	1 consumer → DO NOT EXTRACT
Assets / Storage	yes	no	no	1 consumer → DO NOT EXTRACT
G12 Deployment	-	deferred	deferred	DO NOT EXTRACT
G6 UoW	deferred	deferred	deferred	DO NOT EXTRACT
Phase 8 cycle (same discipline as Phase 7)
Phase 8.1: analysis only (this file) — 2191b1a / 629 passed unchanged
Phase 8.2: contract design (phase-8.2-publishable-contract.md) — line-by-line Post/DocPage, exact contracts, no code
Phase 8.3: minimal abstraction ai_framework/content/ — PublishStatus, Slug (reject not normalize), narrow protocol, pure list_published
Phase 8.4: migrate 2 consumers (Post, DocPage)
Phase 8.5: guards + regression
Phase 8.6: freeze/tag
DO NOT EXTRACT list
Forms / Rich UI — need second UI consumer
PipelineContext / Identity — need second Type A
Assets / Media — need second media consumer
G12 Deployment — deferred, separate from rendering
G6 UoW — deferred
Wide PublishableProtocol with id/title/to_dict — over-abstraction
Slug with filesystem semantics (.. , absolute) — owned by writer
Commit
Baseline remains:

2191b1a
629 passed
Phase 8.1 = analysis only, runtime unchanged
Phase 8.2 = contract design only, runtime unchanged
Implementation starts only after 8.2 approval.

Artifacts:

docs/architecture/phase-8-audit-v0.1.md (this file)
docs/architecture/phase-8.2-publishable-contract.md (4 things: line-by-line, PublishStatus, Slug without FS, narrow protocol + list_published decision)
