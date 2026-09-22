Phase 8 — Publishable Content Lifecycle v1.0
Status: FROZEN
Baseline: 0c27a29 / 657 passed
Tag: phase-8-publishable-lifecycle-green
Date: 2026-09-21
Parent: phase-8.5-architecture-guards-green (0c27a29)

1. Scope — What Phase 8 Owns
Phase 8 introduces a minimal, framework-level abstraction for publishable content.

1.1 PublishStatus
python
class PublishStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
Location: ai_framework/content/publish_status.py
Behavior: enum only, no side effects, no I/O
Methods: is_published(), is_draft() — pure predicates
1.2 Slug — Domain Value Object
python
@dataclass(frozen=True, slots=True)
class Slug:
    value: str  # regex ^[a-z0-9]+(?:-[a-z0-9]+)*$
Location: ai_framework/content/slug.py
Semantics: behavior-preserving reject, not normalize
Constructor rejects invalid (Hello World, hello/world, empty) via ValueError
No auto-lowercase, no trimming to valid — preserves valid exactly, trims whitespace only
Explicit opt-in normalization: Slug.try_normalize("Hello World") -> Slug("hello-world")
Boundary: No filesystem rules — those are owned by StaticSiteWriter / output writer layer
No PurePath, is_absolute, shutil, GeneratedPage, out_dir in slug.py
Pattern: ^[a-z0-9]+(?:-[a-z0-9]+)*$
1.3 PublishableProtocol — Narrow Protocol
python
class PublishableProtocol(Protocol):
    @property
    def status(self) -> PublishStatus: ...
    @property
    def slug(self) -> Slug | str: ...
Location: ai_framework/content/protocols.py
Declared contract: exactly status + slug
Forbidden members (must NOT appear): id, title, content, to_dict, seo, publish, unpublish, html_content, category_id, author_id, section_id, version_id
Implementation via @property, so __annotations__ may be empty — structural check via inspect.getmembers + source
1.4 list_published() — Pure Generic Filtering
python
def list_published(items: Iterable[Publishable]) -> List[Publishable]:
    return [i for i in items if i.status == PUBLISHED]
Location: ai_framework/content/published.py
Pure function: no I/O, no side effects, no domain kwargs
Must NOT have category_slug, tag_slug, section_slug, version_slug — those stay in showcase services
Consumers call it as framework_list_published
2. Explicit Non-Scope — What Phase 8 Does NOT Own
Phase 8 deliberately excludes:

identity: id, uuid, primary keys
serialization: to_dict(), from_dict(), JSON, ORM mapping
domain-specific validation: title length, content length, category existence, version semantics
URL semantics: /posts/{slug}/, /docs/{slug}/, canonical URL generation
taxonomy: categories, tags, sections, versions filtering
rendering: Jinja, HTML generation, SEO injection, RSS/sitemap
filesystem/path safety: PurePath checks, .. traversal, is_absolute, shutil.rmtree, out_dir cleaning
deployment: writing to disk, static hosting, CDN
transactions / UoW: UnitOfWork, repository transactions, commit/rollback
Architectural contract: Publishable lifecycle abstraction covers only publication status, domain-valid slug, and generic published filtering. It does not own identity, serialization, domain-specific validation, URL semantics, taxonomy, rendering, or filesystem safety.

3. Consumers
3.1 blog_cms.Post
Location: showcases/blog_cms/domain/models.py
Migrated in Phase 8.4: PostStatus -> PublishStatus, str slug -> Slug
to_dict() serializes slug as str for rendering compatibility
Validation: rejects invalid slug (Hello World -> ValueError) — intended breaking change documented
3.2 docs_site.DocPage
Location: showcases/docs_site/domain/models.py
Migrated in Phase 8.4: DocStatus -> PublishStatus, str slug -> Slug
Validation now enforced: DocPage(slug="Hello World") rejects
4. Services
4.1 BlogCmsService.list_published()
Location: showcases/blog_cms/services/blog_service.py
Uses from ai_framework.content import framework_list_published as list_published
Generic filtering via framework, then domain-specific filtering (category_slug, tag_slug) in showcase layer
4.2 DocsService.list_published()
Location: showcases/docs_site/services/docs_service.py
Same pattern: framework generic + domain section_slug, version_slug filtering in showcase
Guarantee: ai_framework/content/published.py remains domain-agnostic — no taxonomy params.

5. Proof Chain
Phase	Tag	Commit	Tests	Scope
8.1–8.2	phase-8-architecture-audit-v0.1 + phase-8.2-publishable-contract	0606655	629 passed	Architecture audit + narrow protocol design, no runtime changes, baseline 2191b1a
8.3	phase-8.3-content-primitives-green	d17af75	639 passed	Content primitives: PublishStatus, Slug VO reject-not-normalize, narrow PublishableProtocol, pure list_published, 10 framework tests
8.4	phase-8.4-consumers-migrated-green	e960a48	648 passed	Post and DocPage migrated to PublishStatus+Slug, services to framework list_published, 9 migration tests, rendering untouched
8.5	phase-8.5-architecture-guards-green	0c27a29	657 passed	Guards: framework isolation, slug boundary (no FS code), narrow protocol via properties status+slug, Post/DocPage, services use framework generic, intended DocPage slug reject
8.6	phase-8-publishable-lifecycle-green	HEAD	657 passed	Freeze: this document
Baseline evolution:

2191b1a / 629
  -> 0606655 / 629 (audit + contract design)
  -> d17af75 / 639 (+10 primitives)
  -> e960a48 / 648 (+9 migration)
  -> 0c27a29 / 657 (+9 guards, one extra guard counted as 28 for phase suite)
  -> freeze / 657 (no code changes)
6. Architecture Guarantees (Verified by tests/test_phase8_5_architecture_guards.py)
Framework isolation: ai_framework/content/* contains no from showcases, import showcases, from blog_cms, from docs_site, from cms_lite
Slug boundary: ai_framework/content/slug.py contains no PurePath, PurePosixPath, PureWindowsPath, is_absolute, shutil, StaticSiteWriter, GeneratedPage, out_dir, resolve() — filesystem safety owned by writer
Protocol narrowness: PublishableProtocol declares exactly status + slug via @property, forbids id, title, content, to_dict, seo, publish, unpublish
Generic filtering domain-agnostic: ai_framework/content/published.py has def list_published with Iterable, no category_slug, tag_slug, section_slug, version_slug
Rendering pipeline unchanged: ai_framework/rendering/* does not define slug regex, does not depend on content primitives for path safety
7. Intended Breaking Changes
Post(slug="Hello World") and DocPage(slug="Hello World") now raise ValueError — previously docs_site allowed it, blog_cms normalized
Slug("Hello World") rejects — use Slug.try_normalize("Hello World") for explicit opt-in
This is intentional per Phase 8 contract: behavior-preserving reject semantics
8. Freeze Rules
After phase-8-publishable-lifecycle-green:

Do NOT add anything to Phase 8 — no new primitives, no new consumers, no rendering changes under this tag
Any further content lifecycle changes belong to Phase 9 Architecture Audit with new Gap Matrix
This document is the source of truth for what Phase 8 owns
9. Verification
bash
python -m pytest tests/test_phase8_3_content_primitives.py tests/test_phase8_4_migration.py tests/test_phase8_5_architecture_guards.py -v
# 28 passed (10 + 9 + 9)

python -m pytest -q
# 657 passed
Tag verification:

bash
git log --oneline -5
# HEAD (tag: phase-8-publishable-lifecycle-green) phase-8.6: freeze publishable content lifecycle v1.0
# 0c27a29 (tag: phase-8.5-architecture-guards-green) phase-8.5: ...
# e960a48 (tag: phase-8.4-consumers-migrated-green) phase-8.4: ...
# d17af75 (tag: phase-8.3-content-primitives-green) phase-8.3: ...
# 0606655 (tag: phase-8.2-publishable-contract) phase-8.1-8.2: ...
