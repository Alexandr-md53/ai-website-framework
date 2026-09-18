Gap Matrix — Phase 16.5 v0.2 Review
Source: Capability Matrix v0.2 REVIEWED
Date: 2026-09-18
Checkpoint: phase-16.5-publication-model 39ce2cd
Classification: MISSING | LIMITED | PARTIAL | UNKNOWN | SHOWCASE-SPECIFIC | HISTORICAL
Added field: Required for first new site? (YES/NO/MAYBE) — per user request to avoid premature implementation.

Gap ID	Capability	Status	Current Location	Required for First New Site?	Notes / Evidence
G1	Generic Website Publisher / Site Generator	MISSING	ai_framework/publisher/ does not exist	YES — depends on site type	Core gap identified in v0.1 audit. showcase_generator.py only manifest.json. No Renderer. Blocks B (static) and C (hybrid).
G2	Static Rendering Subsystem (ViewModel → HTML/CSS/JS)	MISSING	none	YES if B or C	No template engine abstraction beyond framework/templates/engine.py legacy deleted. ai_framework/ has no Renderer contract.
G3	Asset Storage S3 / Remote	MISSING	asset_manager/storage.py LocalFileStorage only	MAYBE	Current LocalFileStorage READY for dev, S3 MISSING. First site may work with local, but deployment needs remote.
G4	External Publish Plugin System (generic)	HISTORICAL → MISSING (current)	Legacy plugins/telegram/publisher.py + PublisherPluginContract deleted, no current contract	MAYBE	Old Telegram plugin HISTORICAL reference, not generic. New ExternalPublishContract needed only if first site requires social publishing.
G5	Stock Service generalized (typed exceptions, atomic reserve, concurrency)	SHOWCASE-SPECIFIC / LIMITED	showcases/plant_shop/domain/services/plant_stock_service.py, ValueError("OUT_OF_STOCK") in use_case	NO — unless first site is shop-like	This is G6 from v0.1 + G10. Needs generalization to ai_framework/services/stock/ with OutOfStockError, InsufficientStockError, check_availability(), reserve(), atomic, concurrency test. Not required for first new site unless site has inventory.
G6	Transaction / Unit of Work abstraction	MISSING / UNKNOWN	ApplicationPipeline has no transaction, PipelineContext no session	MAYBE	For shop site, quote creation + stock decrement needs atomicity. Current tests do not cover concurrency (2 parallel quotes). Might be needed for shop first site.
G7	User Identity / Auth Context in Pipeline	LIMITED	PipelineContext(metadata=dict) only request_id, CRUDContext(tenant_id, locale) separate, no Identity in pipeline	YES if first site has auth	SecurityContext exists but not wired into ApplicationPipeline. First site with authentication needs this.
G8	Forms / Rich CRUD UI	LIMITED	crud_ui/engine.py minimal, no rich form rendering	YES	CrudUIEngine READY / LIMITED — basic, no complex forms, file upload handling limited. First site with forms will hit this.
G9	API Error Mapping typed	LIMITED	api/contracts.py hard-coded ValueError → 400 mapping in e3933e9	NO — can stay as is for now	Needs typed exceptions (OutOfStockError etc.) mapped to 400, but generic mapping already READY. Fix is part of G5/C16.6.
G10	Product Discovery / Bootstrapping	LIMITED	build_app_from_product_info requires explicit use_case_map, no auto-scan	NO	Works, but first new site needs manual wiring. Not blocker, but adds boilerplate.
G11	AI Provider extensibility	LIMITED	OpenRouter + Mock only	NO	Enough for current showcases, not required for first site unless site uses AI generation.
G12	Deployment / Publication Output (output/ directory)	MISSING	none	YES if B/C	No concept of output directory, build artifact, deployment. showcase_generator.py writes to showcases/*/manifest.json only.
Summary Counts
MISSING: G1, G2, G12 (+ G3 partial, G4 current)
HISTORICAL: G4 legacy part (Telegram plugin)
SHOWCASE-SPECIFIC: G5 (stock), plus plant_shop domain
LIMITED: G3, G6, G7, G8, G9, G10, G11
Key Insight per User Note
Not every MISSING must be implemented now.

Only implement if Required for first new site = YES.

From this matrix, the only unconditionally YES for any first site are:

G1/G2 if site is static/hybrid (B/C)
G7 if site needs auth
G8 if site needs forms
G12 if site needs static output
All others are MAYBE or NO.

