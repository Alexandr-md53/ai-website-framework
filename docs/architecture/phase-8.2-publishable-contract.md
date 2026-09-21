Phase 8.2 — Publishable Contract Design
Baseline: 2191b1a / 629 passed
Status: design only, no runtime changes to ai_framework/content/ or consumers
Depends on: phase-8-audit-v0.1.md clarification (narrow protocol status+slug)

Evidence → Contract discipline
Phase 7 cycle: evidence → contract → minimal abstraction → 2 consumers → guards → freeze
Phase 8 same.

1. Line-by-line comparison Post / DocPage
Post (showcases/blog_cms/domain/models.py — real code)
python
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

class PostStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"

@dataclass
class Post:
    id: uuid.UUID
    title: str
    slug: str                          # domain field
    content: str
    category_id: uuid.UUID
    author_id: uuid.UUID
    tag_ids: List[uuid.UUID]
    status: PostStatus = DRAFT         # lifecycle field
    seo: SeoMeta
    html_content: Optional[str]

    def validate_for_draft(self):      # title>=3, SLUG_RE.match(slug), content>=20
    def is_published(self) -> bool:    # status == PUBLISHED
    def publish(self):                 # validate + status=PUBLISHED
    def unpublish(self):               # status=DRAFT
    def to_dict(self):                 # serialization with seo_*
Evidence: Post REQUIRES lowercase via regex, does NOT auto-convert. Slug("Hello World") would be rejected by validate_for_draft().

DocPage (showcases/docs_site/domain/models.py — real code)
python
class DocStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"

@dataclass
class DocPage:
    id: uuid.UUID
    title: str
    slug: str                          # domain field, NO validation at all
    content: str
    section_id: Optional[UUID]
    version_id: Optional[UUID]
    status: DocStatus = DRAFT          # lifecycle field
    seo: SeoMeta
    created_at: datetime
    html_content: str = ""

    def to_dict(self):                 # similar shape, different FK fields
    # NO validate, NO is_published, NO publish/unpublish, NO SLUG_RE
Evidence: DocPage currently allows any string as slug — gap, but existing data in tests uses lowercase slugs like getting-started.

Diff Table
Aspect	Post	DocPage	Common lifecycle?
id	UUID	UUID	NO — identity, not lifecycle
title	str	str	NO — display
slug field	str + SLUG_RE	str no validation	YES — but validation differs
slug validation	^[a-z0-9]+(?:-[a-z0-9]+)*$ reject otherwise	none	YES — candidate for unified VO
content	str	str	NO — content
status enum	PostStatus DRAFT/PUBLISHED	DocStatus DRAFT/PUBLISHED	YES — identical values, duplicated
status field	PostStatus	DocStatus	YES — core lifecycle
is_published	status==PUBLISHED	none	YES — should be generic
publish/unpublish	validate + set status	none	YES — should be generic with hook
category/section	category_id	section_id	NO — taxonomy specific
tags/version	tag_ids	version_id	NO — taxonomy specific
seo	SeoMeta	SeoMeta	YES but already extracted (SeoContext)
html_content	Optional	str	NO — rendering cache
to_dict	serialization	serialization	NO — not lifecycle
Conclusion: Only status + slug are truly common publish lifecycle. id, title, to_dict() explicitly excluded.

2. Exact PublishStatus contract
Duplication evidence: two enums with identical members.

python
# ai_framework/content/publish_status.py
from __future__ import annotations
from enum import Enum

class PublishStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"

    def is_published(self) -> bool:
        return self == PublishStatus.PUBLISHED
Replaces both PostStatus and DocStatus (can keep aliases for backward compat: PostStatus = PublishStatus)
No filesystem semantics
Pure value object, frozen by Enum nature
3. Exact Slug contract — WITHOUT filesystem semantics, behavior-preserving
Decision on Slug("Hello World") → reject? or normalize → "hello-world"?
Existing contract evidence:

Post: SLUG_RE.match(slug) — requires lowercase, rejects "Hello World" (because regex fails on space and uppercase)
DocPage: no validation, but all existing fixtures are lowercase (getting-started, hello-world)
Behavior-preserving extraction rule:

existing valid slug → preserved exactly
existing invalid slug → rejected
Normalization (lowercase normalized) is convenient but CHANGES behavior. If we auto-convert "Hello World" → "hello-world", we would silently accept what Post currently rejects.

Therefore Phase 8.2 decision:

Initial Slug VO: REJECT "Hello World", do NOT auto-normalize
Normalization may be added later ONLY if proven as part of established domain contract (e.g., service layer already lowercases before validation)
This preserves existing behavior.

Slug contract (domain-only)
python
# ai_framework/content/slug.py
from __future__ import annotations
import re
from dataclasses import dataclass

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # from real Post code, domain-only

@dataclass(frozen=True, slots=True)
class Slug:
    value: str

    def __post_init__(self):
        # behavior-preserving: no auto-lower, no strip-to-lower conversion that changes valid set
        # only minimal trimming of surrounding whitespace for robustness? Even that changes behavior,
        # so we keep strict: reject if not matching regex exactly, except we allow surrounding whitespace trim as input hygiene
        # Decision: trim surrounding whitespace, then validate, but preserve case for rejection
        raw = self.value
        if not raw or not raw.strip():
            raise ValueError("slug must be non-empty")
        # Note: we do NOT lower() here — "Hello" fails regex and is rejected
        if not _SLUG_RE.match(raw.strip()):
            raise ValueError(f"invalid slug {raw!r}: must match {_SLUG_RE.pattern}")
        # Store trimmed version (trim is not normalization to lower, only whitespace hygiene)
        # To keep frozen dataclass, need object.__setattr__ if we want to store trimmed
        # Alternative: store as-is if it already matches, else reject

    def __str__(self) -> str:
        return self.value.strip()

    @classmethod
    def try_normalize(cls, raw: str) -> "Slug":
        """
        Explicit opt-in normalization, NOT used by default validation.
        Use only when domain contract explicitly allows case-insensitive input.
        """
        normalized = raw.strip().lower().replace(" ", "-").replace("_", "-")
        # collapse multiple hyphens, remove invalid chars
        normalized = re.sub(r"[^a-z0-9-]", "", normalized)
        normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
        if not _SLUG_RE.match(normalized):
            raise ValueError(f"cannot normalize {raw!r} to valid slug")
        return cls(normalized)
Domain rules enforced by Slug:

non-empty
matches ^[a-z0-9]+(?:-[a-z0-9]+)*$
no / (because regex excludes /) — domain reason: slug is single segment
no empty, no leading/trailing hyphen (enforced by regex)
NOT enforced by Slug (filesystem concerns, owned by StaticSiteWriter):

.. — path traversal check is in writer
absolute path /... — writer concern
drive C: — writer concern
duplicate path — writer concern (fail-fast already in 7.2)
Tests for Slug (behavior-preserving)
Slug("getting-started") → preserved exactly
Slug("hello-world") → preserved
Slug("Hello World") → reject (ValueError) — NOT auto-normalized
Slug("Hello") → reject
Slug("") → reject
Slug("a/b") → reject (domain, because / not allowed in single segment)
Slug("a..b") → reject? No, regex allows a..b? Actually .. contains . which regex rejects — so rejects for domain reason, not filesystem. But .. alone would be rejected by regex too. Still, explicit filesystem .. check stays in writer, not here — separation preserved.
Slug.try_normalize("Hello World") → "hello-world" (explicit opt-in)
4. Exact narrow PublishableProtocol + list_published() decision
Narrow protocol (as clarified)
python
# ai_framework/content/protocols.py
from __future__ import annotations
from typing import Protocol
from .publish_status import PublishStatus
from .slug import Slug

class PublishableProtocol(Protocol):
    @property
    def status(self) -> PublishStatus: ...
    @property
    def slug(self) -> Slug | str: ...  # allow str for backward compat, will be validated via Slug when needed

    # Optional: is_published as property for convenience, but can be derived from status
    # We keep protocol minimal: only status + slug required
Explicitly NOT including: id, title, content, seo, to_dict(), category_id/section_id.

Rationale: those are identity/display/serialization/taxonomy — not publish lifecycle.

list_published() decision
Both services have:

python
def list_published(self): return [p for p in self._posts.values() if p.status == PUBLISHED]
Common behavior proven — pure filter.

Should we extract?

Yes, as pure generic function, NOT as method, to avoid base class.

python
# ai_framework/content/published.py
from __future__ import annotations
from typing import Iterable, TypeVar
from .protocols import PublishableProtocol
from .publish_status import PublishStatus

T = TypeVar("T", bound=PublishableProtocol)

def list_published(items: Iterable[T]) -> list[T]:
    return [i for i in items if i.status == PublishStatus.PUBLISHED]

def is_published(item: PublishableProtocol) -> bool:
    return item.status == PublishStatus.PUBLISHED
Pure, no IO, no filesystem, no taxonomy
Works for both Post and DocPage
Taxonomy filtering (category_slug, section_slug) stays showcase-local — NOT generalized yet
What we do NOT create in Phase 8.3
No factory/registry
No base class PublishableBase
No wide protocol with id/title/to_dict
No filesystem path validation inside Slug
No taxonomy abstraction
File layout for Phase 8.3 (create only after 8.2 approval)
ai_framework/content/
├── __init__.py (exports PublishStatus, Slug, PublishableProtocol, list_published, is_published)
├── publish_status.py
├── slug.py
├── protocols.py
└── published.py
Guards for Phase 8.5 (future)
test_publish_status_single_definition: only one enum in ai_framework/content/publish_status.py, PostStatus/DocStatus are aliases or replaced
test_slug_behavior_preserving: Slug("Hello World") rejected, Slug("hello-world") preserved, Slug.try_normalize explicit
test_slug_no_filesystem_semantics: Slug does NOT check .. as filesystem traversal — that check lives only in StaticSiteWriter
test_publishable_protocol_narrow: protocol has only status + slug, no id/title/to_dict
test_list_published_pure: same input → same output, no filesystem access
regression: 629 + new tests green
Baseline unchanged until implementation
2191b1a / 629 passed — Phase 8.1 analysis only
Phase 8.2 design — this file, no runtime changes
Phase 8.3 — minimal abstraction implementation
Phase 8.4 — migrate 2 consumers
Phase 8.5 — guards
Phase 8.6 — freeze
Evidence → contract → minimal abstraction → 2 consumers → guards → freeze — same discipline as Phase 7.

