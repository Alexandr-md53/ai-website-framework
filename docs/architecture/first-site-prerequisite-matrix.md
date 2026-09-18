First New Site — Prerequisite Matrix (Target Capability Set)
Date: 2026-09-18
Checkpoint: phase-16.5-publication-model 39ce2cd
Purpose: Define what first new site needs BEFORE designing Publisher
Method per user: define FIRST NEW SITE requirements, then map CURRENT → TARGET
Step 3 from user route: Fix requirements of first new site
Per user:

FIRST NEW SITE
├── content/domain
├── pages
├── CRUD
├── forms
├── assets
├── authentication
├── API
├── frontend
├── static/dynamic output
└── deployment/publication
We must NOT assume shop. We need to define minimal target.

Template for Target Capability Set (to be filled by user/product decision)
1. Content / Domain
 What entities? (e.g., Article, Product, Page, User?)
 Value Objects? (Title, Slug, Content, Price?)
 Relations? (Category, Tags?)
 Decision: reuse Article domain or new domain?
2. Pages
 How many page types? (list, detail, form, dashboard?)
 Rendering: dynamic (API + frontend) or static pre-rendered?
 SEO needed?
3. CRUD
 Standard CRUD enough (engine.py) or custom logic?
 Current UniversalCRUDEngine READY — can reuse as-is
 Need SlugOrchestrator? YES likely
4. Forms
 What forms? (create/edit entity, contact, checkout?)
 File upload? (needs AssetManager)
 Validation: existing ValidationEngine READY, but rich UI LIMITED (G8)
 Prerequisite: G8 LIMITED → need to decide if current CrudUI enough
5. Assets
 Images? Documents?
 Current AssetManager + LocalFileStorage READY for dev
 S3 needed? (G3) — if deployment to remote, then YES
6. Authentication
 Auth required? (public site vs admin)
 If YES → G7 PipelineContext needs Identity (currently LIMITED)
 security/authorization.py READY / LIMITED — RBAC exists but not wired to pipeline
7. API
 API needed? (for frontend or mobile)
 Current create_app(registry) + EndpointPipelineAdapter READY
 Can build new product_info + use_case_map
8. Frontend
 What frontend? (none, simple HTML, SPA, Next.js?)
 Framework currently has no frontend contract — MISSING
 If static → needs Renderer (G2)
9. Static / Dynamic Output
This is the critical decision A/B/C from publication-model-16.5.md:

 A. Dynamic web application: UseCase → API → Frontend → browser — CURRENT FRAMEWORK supports via C6 factory, NO Publisher needed
 B. Static website: Domain → View Models → Renderer → HTML/CSS/assets → output/ — NEEDS Site Generator (G1/G2/G12) — MISSING
 C. Hybrid: API + static + assets + optional external publishers — NEEDS both
Old Telegram Publisher irrelevant for A/B/C choice.

10. Deployment / Publication
 Where to deploy? (local, Vercel, S3+CloudFront, Docker?)
 If static → needs output/ concept (G12 MISSING)
 If external publish (Telegram etc.) → needs ExternalPublishContract (G4)
Step 4: Current ↔ Target Mapping
CURRENT FRAMEWORK
        │
        ├── READY ────────────────► use as-is
        ├── LIMITED ──────────────► decide: extend or work around?
        ├── SHOWCASE-SPECIFIC ───► generalize if required for first site
        └── MISSING ─────────────► design only if Required = YES
Mapping Table (to be filled after first site type chosen)
Target Requirement	Current Status	Action	Required for First Site?
CRUD Engine	READY	use as-is	YES
Validation Engine	READY	use as-is	YES
Metadata / CrudUI	READY / LIMITED	use, extend if forms complex	YES
AssetManager Local	READY	use as-is	YES if assets
AssetManager S3	MISSING (G3)	design only if deployment remote	MAYBE
API Factory	READY	use as-is	YES if dynamic/hybrid
PipelineContext Identity	LIMITED (G7)	extend if auth needed	MAYBE
Forms Rich UI	LIMITED (G8)	extend if needed	MAYBE
Site Generator / Renderer	MISSING (G1/G2)	design only if B/C	YES if B/C
Output / Deployment	MISSING (G12)	design only if B/C	YES if B/C
External Publisher	HISTORICAL → MISSING (G4)	design only if Telegram etc needed	NO initially
Stock Service generalized	SHOWCASE-SPECIFIC (G5)	do NOT generalize unless first site is shop	NO
Transaction / UoW	MISSING (G6)	design only if atomic inventory needed	NO unless shop
Minimal Set Principle
«Вот минимальный набор capabilities, который Framework должен иметь, чтобы первый новый сайт был построен исключительно через Framework, а не через обходные showcase-specific механизмы»

This means for first new site we must avoid:

Direct plant.stock_quantity -= quantity (showcase-specific) — use framework service if needed, or avoid shop logic entirely
Direct requests.post in use_case (like old Telegram plugin)
Custom wiring bypassing product/factory.py
All new site code must go through:

ProductInfo → build_registry_from_map → create_app → ApplicationPipeline → CRUDEngine → AssetManager
If this chain is insufficient, then gap is real and must be designed.

Next Concrete Step
User/Product decides: first new site type A/B/C and fills checklist above (content, pages, CRUD, forms, assets, auth, API, frontend, output, deployment)
Then we can fill Mapping Table with YES/NO
Then we know if we need Site Generator (G1/G2/G12) or if dynamic app (A) is enough with current READY capabilities
ONLY THEN design Publisher (if needed) — split into Renderer / SiteGenerator / Deployment / ExternalPublisher
No code until step 1 decided.

