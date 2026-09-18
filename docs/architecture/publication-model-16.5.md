Publication Model — Phase 16.5 Analysis
Status: DESIGN NOTE, not implementation
Tag: phase-16.5-traceability (49ba7c1)
Context
From git history:

framework/core/contracts.py: PublisherContract(FrameworkComponent) with publish(data) / execute(data)
plugins/telegram/publisher.py: TelegramPublisherPlugin(PublisherPluginContract) — social plugin using TELEGRAM_BOT_TOKEN/CHAT_ID, requests.post, HTML message + inline_keyboard
Both deleted in phase-9-frozen-v2: remove legacy framework/ + 11 tests + plugins/telegram

ai_framework/publisher/ listed in START_HERE.md canonical structure but never existed physically — confirmed by PROJECT_DUMP.md 337 files and git ls-tree -r.

Corrected Classification
Legacy Publisher
Type: HISTORICAL / EXTENSION CONCEPT
What it was: external social publication plugin
What it was NOT: generic website publisher / static-site engine
Contract: PublisherPluginContract — get_metadata(), validate(), publish()
Delivery: direct Telegram HTTP API via requests
Value as reference: plugin metadata pattern (id, title, description, icon, version, category, supports_images/buttons/html), Settings integration, external delivery pattern
Generic Website Publisher
Type: MISSING
Current implementation: none
Required: new design based on current ai_framework (not legacy framework)
Why Word Publisher is Dangerous
Old documentation:

UseCases -> Pipeline -> CRUD -> AssetManager -> Publisher
Conflated:

Site Generator — Domain/ViewModels -> HTML/CSS/assets -> output/
External Publisher Plugin — content -> external channel (Telegram, etc.)
Deployment / Output — where output goes
Telegram plugin only covers #2.

Three Architectures for New Site
A. Dynamic Web Application
UseCase -> API (FastAPI factory C6.1) -> Frontend -> browser
Current Framework already supports this via create_app(registry) + EndpointPipelineAdapter.

B. Static Website
Domain (Article, Category, Plant) -> Content/ViewModels (MetadataEngine, CrudUIEngine) -> Renderer (MISSING) -> HTML/CSS/assets -> output/
Needs Renderer — currently MISSING. showcase_generator.py only generates manifest.json, not HTML.

C. Hybrid (Proposed for AI Website Framework)
API (dynamic)
+ static generation (pre-rendered pages from CRUD)
+ assets (AssetManager + LocalFileStorage, future S3)
+ optional external publishers (Telegram, etc.)
This is most likely, but needs explicit Publication Model decision.

Publication Model — Proposed Separation
                 CURRENT FRAMEWORK (PROVEN 578 GREEN)
                        |
     +------------------+------------------+
     |                  |                  |
     v                  v                  v
Application           CRUD              Assets
 Pipeline          Validation           Metadata
     |                  |                  |
     +------------------+------------------+
                        |
                        v
               Publication Model [NEW — MISSING]
                        |
          +-------------+-------------+
          v                           v
    Website Output              External Publish
    (Site Generator)            (Publisher Plugin)
          |                           |
          v                           v
    SiteOutputContract          ExternalPublishContract
          |                           |
          v                           v
     HTML / CSS / assets        Telegram, Email, etc.
SiteOutputContract (for static/hybrid)
python
class SiteOutputContract(Protocol):
    def generate(self, content: ContentBundle, assets: AssetBundle, metadata: SiteMetadata) -> SiteOutput:
        ...

@dataclass
class SiteOutput:
    pages: List[HtmlPage]
    assets: List[Asset]
    manifest: dict
ExternalPublishContract (for social plugins)
python
class ExternalPublishContract(Protocol):
    def get_metadata(self) -> PluginMetadata: ...
    def validate(self, publication: Publication) -> bool: ...
    def publish(self, publication: Publication, settings: Settings) -> PublishResult: ...
These are DIFFERENT contracts. Old PublisherPluginContract only matches second.

What NOT to Do Now
Do NOT create ai_framework/publisher/ as copy of old Telegram plugin
Do NOT use Telegram plugin as baseline for static site generation
Do NOT start C17 Publisher before defining what first new site should produce (A/B/C)
What to Do Now (Before First New Site)
Define minimal capability set for first new site
Is it dynamic app (uses existing C6 FastAPI factory) or static?
Does it need assets (LocalFileStorage enough or S3)?
Does it need external publishing (Telegram)?
Fix traceability
Update capability-traceability-16.5.md section 9 with HISTORICAL vs MISSING separation (see PATCH file)
Keep C16.6 focused
C16.6 = ai_framework/services/stock/ extraction (typed exceptions, atomic reserve) — this is showcase-specific -> framework extraction, not related to Publisher
Publisher design stays as design note until new site requirements clear
Files to Save
docs/architecture/capability-traceability-16.5.md — append correction patch
docs/architecture/publication-model-16.5.md — this file (design note)
docs/migrations/legacy_telegram_publisher.py — archived recovered code (optional, git show phase-9-frozen-v2^:plugins/telegram/publisher.py)
Next Step
After user confirms first new site type (A/B/C), design:

If A (dynamic): no Publisher needed, use existing ProductFactory
If B (static): design Site Generator + Renderer, no external plugin initially
If C (hybrid): design both SiteOutputContract and ExternalPublishContract separately
Do not implement until decision made.

Generated: 2026-09-18
Tag: phase-16.5-traceability

