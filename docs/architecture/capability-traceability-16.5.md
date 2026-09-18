Capability Traceability — Phase 16.5
Version: v0.2 merged (Optimistic Matrix + Evidence Audit v0.1)
Checkpoint: phase-16.5-docs-catchup -> e4262e6 (local, not proven by dump)
Dump: PROJECT_DUMP.md 337 files ~911KB, docs/README.md HEAD=b3c2c2d inside dump
Baseline Note: dump reflects state before/at Docs Catch Up, e4262e6 accepted as local baseline per user git show, not independently proven by dump content.
Tests: 578 GREEN claimed, 557 named test_* functions in dump
This document implements the strict layer: Capability -> exact implementation -> exact contract -> exact test(s) -> framework/showcase boundary -> limitation (READY/LIMITED/MISSING/PARTIAL)

1. Architecture
CORE -> ENGINE -> EXTENSION -> SHOWCASE
Implementation: ai_framework/core/, domain/, services/slug/, validation/, crud/contracts.py, crud/engine.py, pipeline/, api/, application/, infrastructure/, showcases/*/
Contract: docs/architecture/dependency-rules.md, docs/IMPORT_MAP_FROZEN_V2.md (0 violations), AGENTS.md frozen
Tests: tests/test_architecture.py::test_core_no_forbidden_dependencies, test_framework_never_depends_on_showcase, test_crud_boundary_still_respected
Boundary: FRAMEWORK
Limitation: READY — enforced statically via imports
Product Assembly (explicit)
Implementation: ai_framework/product/factory.py::build_app_from_product_info, ai_framework/api/product_pipeline_wiring.py::build_registry_from_map, ai_framework/api/fastapi.py::create_app
Contract: C10.1 product assembly factory metadata->C9.2->C6 no fs scan new file only, docs/architecture/product-assembly.md
Tests: tests/test_c10_1_product_factory.py 6 tests, tests/test_c9_2_endpoint_pipeline_registration.py 5 tests, tests/test_c9_3_fastapi_product_wiring.py 4 tests
Boundary: FRAMEWORK
Limitation: READY / LIMITED — requires explicit use_case_map: Dict[Tuple[str,str], Tuple[UseCase, dto_factory]], no automatic product discovery/bootstrapping
2. API / FastAPI
FastAPI factory
Impl: ai_framework/api/fastapi.py:create_app(registry=None)
Contract: C6.1, C6.2, docs/architecture/api-pipeline.md
Tests: test_c6_1_fastapi_factory, test_c6_2_fastapi_wiring
Boundary: FRAMEWORK
Limitation: READY — wiring only, middlewares+health+lifespan passthrough
EndpointRegistry / Router / APIAdapter
Impl: ai_framework/api/registry.py, router.py, adapter.py, endpoint.py
Contract: C5.1, C5.2 registry enrichment lru_cache, docs/contracts/frozen-contracts.md
Tests: test_c5_registry, test_c5_2_enrichment, registry/router tests, tests/api/
Boundary: FRAMEWORK
Limitation: READY / LIMITED — Router is simple matcher, APIAdapter not full FastAPI routing replacement, two registry concepts: ai_framework.api.registry vs ai_framework.product_registry
EndpointPipelineAdapter
Impl: ai_framework/api/pipeline_adapter.py — dto_factory + context_factory + pipeline.execute passthrough
Contract: C8.2 new file only, C9.1, docs/architecture/api-pipeline.md
Tests: test_c8_2_pipeline_adapter_impl, test_c9_1_fastapi_pipeline_wiring
Boundary: FRAMEWORK
Limitation: READY
HTTP error mapping
Impl: ai_framework/api/contracts.py::APIResponse, ResponseAdapter, ai_framework/application/pipeline/
Contract: docs/contracts/api-contracts.md — PATCH/POST mapping, C16.5 fix e3933e9 ValueError OUT_OF_STOCK/INSUFFICIENT_STOCK -> 400
Tests: test_c16_4_quote_stock_validation_api.py, test_c16_5_quote_decrement_api.py, tests/test_api_response.py
Boundary: FRAMEWORK (mapping partly generic, partly hard-coded in showcase use_cases)
Limitation: READY / LIMITED
3. Application Pipeline
PipelineContext
Impl: ai_framework/application/pipeline/contracts.py::PipelineContext(request_id, metadata=dict)
Contract: C8/C16.5 frozen, docs/architecture/api-pipeline.md
Tests: test_c8_1_api_application_wiring 8 tests
Boundary: FRAMEWORK
Limitation: READY / LIMITED — execution context only, not full app context: no user identity, transaction, tenant, locale, persistence session. CRUDContext(tenant_id, locale) is separate abstraction.
Application Pipeline chain
Impl: ai_framework/application/pipeline/executor.py::ApplicationPipeline, adapter.py::UseCaseHandlerAdapter, contracts.py::ApplicationHandlerProtocol, MiddlewareProtocol
Contract: C7.2 application boundary freeze, C7.3 product execution boundary
Tests: test_c7_2_application_contract, test_c7_3_product_execution
Boundary: FRAMEWORK
Limitation: READY — middleware sequence + handler, but no transaction abstraction
4. Generic CRUD
UniversalCRUDEngine
Impl: ai_framework/crud/engine.py, crud_engine.py, contracts.py::CRUDContext, CRUDResult, CRUDError, PersistenceProviderProtocol
Contract: C7.3, docs/architecture/overview.md
Tests: tests/crud/, tests/test_crud_*.py
Boundary: FRAMEWORK
Limitation: READY — create/get/list/update/delete + validation + slug orchestration
Persistence
Impl: ai_framework/crud/persistence.py::InMemoryPersistenceProvider, sqlite_persistence.py::SQLitePersistenceProvider
Contract: PersistenceProviderProtocol — insert/fetch/fetch_all/update_record/delete_record/is_unique
Tests: persistence tests
Boundary: FRAMEWORK
Limitation: InMemory READY, SQLite LIMITED — _init_db() contains pass, no generic schema/migration/bootstrap layer, not full DB provisioning subsystem
5. Validation Engine
Impl: ai_framework/validation/__init__.py::ValidationEngine, context.py::ValidationContext, result.py::ValidationResult, validators: validators/type.py::TypeValidator, required.py, length.py, format.py, unique.py::UniquenessValidator, slug.py
Contract: docs/architecture/overview.md, extensibility example
Tests: tests/unit/test_type_validator.py, test_uniqueness_validator.py, test_validation_engine.py
Boundary: FRAMEWORK + showcase extension point
Limitation: READY — supports schema compile -> validators -> entity validation, custom validator registration. Plant adds showcases/plant_nursery/validation/category_rules.py::CategoryHierarchyValidator as good extensibility example.
6. Slug
Impl: ai_framework/services/slug/generator.py::SlugGenerator, engine.py::DefaultTransliterationEngine (de, uk, cyrillic, unicode NFD), resolver.py::DefaultCollisionResolver.iter_candidates, crud/slug_orchestrator.py::AsyncSlugOrchestrator
Contract: ADR-001, ADR-002, SLG_01
Tests: tests/services/slug/test_slug_generator.py, test_collision_resolver.py, test_transliteration.py, test_edge_cases.py
Boundary: FRAMEWORK
Limitation: READY
7. Metadata / CRUD UI
Metadata Engine
Impl: ai_framework/metadata/engine.py::MetadataEngine, registry.py::MetadataRegistry, models.py::EntityMetadata, FieldMetadata, FormMetadata, FieldConstraint, FieldWidgetType (TEXT, TEXTAREA, NUMBER, BOOLEAN, SELECT, DATE, DATETIME, SLUG, FILE, HIDDEN)
Contract: Phase 10-11 docs
Tests: tests/metadata/test_architecture.py, test_metadata_*.py
Boundary: FRAMEWORK
Limitation: READY
CRUD UI view-model generation
Impl: ai_framework/crud_ui/engine.py::CrudUIEngine builds ListViewModel, DetailViewModel, FormViewModel with columns/visibility/sorting/pagination/actions/forms/groups/widgets
Contract: docs/phases/phase-10.md
Tests: tests/crud_ui/test_architecture.py
Boundary: FRAMEWORK
Limitation: READY / LIMITED — view-model generation only, no frontend renderer/application shell
8. Assets
Generic AssetManager
Impl: ai_framework/asset_manager/contracts.py::Asset, FileUploadInput, AssetValidationConfig, AssetStorageProtocol, AssetManagerProtocol, manager.py::AssetManager, storage.py::LocalFileStorage
Contract: Asset capabilities from Phase 9
Tests: tests/asset_manager/
Boundary: FRAMEWORK
Limitation: READY / LIMITED — supports upload/metadata/download/delete/list + max size/MIME/extension. Metadata stored as dict[str, Asset] in memory, physical storage LocalFileStorage only. MISSING: database-backed metadata, S3/object storage adapter, persistent asset index, image processing/resizing pipeline
Plant Nursery Gallery (SHOWCASE-SPECIFIC)
Impl: showcases/plant_nursery/services/catalog_service.py::_gallery: Dict[UUID, List[str]], add_image_to_plant limit 5 + main_image auto, get_images returns count, remove_image_from_plant main promotion
Contract: C14.1 6e103bb 543, C14.2 48e1cbd 546, C14.3 d7b53af 550, docs/contracts/api-contracts.md: POST /plants/{id}/images, GET /plants/{id}/images, DELETE /plants/{id}/images/{image_id}
Tests: test_c14_1..3, tests/showcases/plant_nursery/test_catalog_service.py
Boundary: SHOWCASE-SPECIFIC — works with image_id list, not generic image gallery subsystem
Limitation: SHOWCASE-SPECIFIC
9. Publishing / Static Website Generation
Publisher
Impl: NOT FOUND in ai_framework/ — no publisher/ directory. Historical reference plugins/telegram/publisher.py deleted in Phase 9.1. Only ai_framework/showcase_generator.py generates manifest.json/showcase structure.
Contract: Phase 9 claims UseCases -> Pipeline -> CRUD -> AssetManager -> Publisher as complete static website generation, but current code tree does not confirm
Tests: None for generic publishing
Boundary: MISSING
Limitation: MISSING / NOT PROVEN — Framework proven as application/API/product framework with asset capabilities, but not as finished static-site publishing framework. This is the most important documentation vs code mismatch to fix as gap, not feature.
10. Product Registry / CLI
Product discovery
Impl: ai_framework/api/registry.py::list_products(), get_product(), reads showcases/*/manifest.json, enrichment from pyproject.toml (pyproject_name/version/requires_python), lru_cache
Contract: C5.1-C5.5, docs/contracts/frozen-contracts.md
Tests: test_c5_registry, test_c5_2_enrichment, test_c5_3_cli, test_c5_4_cli, test_c5_5_inspect
Boundary: FRAMEWORK
Limitation: READY / LIMITED — two registry concepts coexist: api.registry vs product_registry, different historical roles
CLI
Impl: ai_framework/cli/main.py — version, product list/showcase list/info, inspect <path> [--json] filesystem-only
Contract: C5.3, C5.4, C5.5
Tests: cli tests
Boundary: FRAMEWORK
Limitation: READY
11. Security / RBAC
Impl: ai_framework/security/authorization.py::Permission, Role, Identity, SecurityContext, AuthorizationService, RoleBasedAuthorizationProvider, credentials.py::AuthenticationService, InMemoryAuthenticationProvider, web.py::BearerTokenExtractor, SecurityWebGuard, crud_ui/web_adapter.py::SecuredViewModelAdapter
Contract: RBAC from Phase 12/15, docs/phases/phase-12.md, phase-15.md
Tests: security tests, test_c12_4_lawyer_list_rbac, test_c15_1 PENDING->APPROVED|REJECTED->COMPLETED RBAC
Boundary: FRAMEWORK (abstraction) + SHOWCASE-SPECIFIC policies (attorney isolation, managing partner access)
Limitation: READY for generic authorization/RBAC (anonymous 401, no permission 403, permission granted), MISSING for production identity: persistent users, password hashing/storage, OAuth/OIDC, JWT verification, sessions, database-backed roles, policy engine
12. Plant Nursery — Catalog & Hierarchy (SHOWCASE-SPECIFIC)
Category hierarchy & Move & Aggregation
Impl: showcases/plant_nursery/domain/category.py::Category, validation/category_rules.py::CategoryHierarchyValidator, services/catalog_service.py::_get_all_categories(), _collect_descendant_ids BFS, find_plants_by_category(include_descendants)
Contract: C13.1 4f7daf4 524 catalog via factory, C13.2 1e52432 528 hierarchy validation via ValidationEngine, C13.3 37a1209 533 MoveCategory via ValidationEngine, C13.4 dfb64d2 538 aggregation descendants BFS, docs/phases/phase-13.md
Tests: test_c13_1_plant_nursery_catalog.py, test_category_hierarchy.py, showcase conftest InMemoryCategoryRepository
Boundary: SHOWCASE-SPECIFIC — no generic hierarchy engine in framework
Limitation: SHOWCASE-SPECIFIC
Pricing
Impl: showcases/plant_nursery/domain/pricing.py::DiscountPolicy(NONE,VOLUME,SEASONAL), PriceCalculator.calculate_total — VOLUME threshold >=10 fixed C14.4
Contract: C14.4 c4fe436 554, docs/contracts/api-contracts.md POST /quotes
Tests: test_c14_4, test_plant_pricing.py
Boundary: SHOWCASE-SPECIFIC
Limitation: SHOWCASE-SPECIFIC — no generic QuoteEngine
Stock & Availability & Quotes (C16.1-C16.5)
Impl:
Domain: showcases/plant_nursery/domain/plant.py: stock_quantity:int=0, is_available property
Service: services/catalog_service.py: update_stock(plant_id, qty) validates >=0 overwrites returns {id, stock_quantity, is_available}, find_frost_resistant_plants
UseCases: application/use_cases.py: AddPlantUseCase returns stock_quantity=0,is_available=False, ListFrostResistantUseCase filters available bool parsing true/false/1/0/yes/no, QuoteUseCase validates OUT_OF_STOCK when stock==0, INSUFFICIENT_STOCK when quantity>stock, backward compat no plant_id -> 200, decrement stock_quantity -= quantity, zero -> is_available=False
DTOs: api/dto_factories.py: update_plant_stock_dto_factory, frost_filter_dto_factory parses available, quote_dto_factory with plant_id optional, add_plant_dto_factory, etc.
API: api/app_factory.py: _make_use_case_map includes (PATCH /plants/{id}/stock, UpdatePlantStockUseCase), (GET /plants, ListFrostResistantUseCase), (POST /quotes, QuoteUseCase)
Contract: docs/contracts/api-contracts.md Plant Nursery section + Quote Stock Rules, docs/phases/phase-16.md Tags a67b4ae 564, cce1fc7 568, b447d62 571, f59a162 575, b3c2c2d, docs/architecture/api-pipeline.md Flow for Plant Nursery
Tests: tests/test_c16_1_plant_stock_api.py 5 tests, test_c16_2_plant_available_filter_api.py, test_c16_3_plant_stock_in_responses_api.py, test_c16_4_quote_stock_validation_api.py 4 tests OUT_OF_STOCK/INSUFFICIENT_STOCK/sufficient/backward compat, test_c16_5_quote_decrement_api.py 3 tests decrement success/exact drain to zero/second quote fails
Boundary: SHOWCASE-SPECIFIC
Limitation: SHOWCASE-SPECIFIC — Framework has no generic StockEngine/InventoryEngine/QuoteEngine/ReservationEngine. Current implementation uses ValueError("OUT_OF_STOCK") strings mapped to 400 in api/fastapi.py e3933e9, direct plant.stock_quantity -= quantity no concurrency control, no audit/history, no transaction.
13. Other Showcases (SHOWCASE-SPECIFIC)
Cafe
Impl: showcases/cafe/domain/menu_item.py::MenuItem, services/cafe_service.py, api/app_factory.py, lifecycle DRAFT->ACTIVE->ARCHIVED
Contract: C12.1 c579197, C12.2 d0ff074, docs/phases/phase-12.md
Tests: test_c12_1_cafe_showcase_via_factory, test_c12_2_cafe_status_transition
Boundary: SHOWCASE-SPECIFIC
Limitation: SHOWCASE-SPECIFIC — no generic StatusLifecycleEngine/PriceModifierEngine
Lawyer / Service
Impl: showcases/lawyer/services/lawyer_service.py, application/use_cases: submit_consultation_request, list_requests, update_request_status, M2M validation, RBAC filtering, attorney isolation
Contract: C12.3 9249dff, C12.4 b49c3eb, C15.1 3d3b2a8 lifecycle PENDING->[APPROVED|REJECTED]->COMPLETED RBAC, docs/phases/phase-12.md, phase-15.md
Tests: test_c12_3, test_c12_4, test_c15_1
Boundary: SHOWCASE-SPECIFIC
Limitation: SHOWCASE-SPECIFIC — not generic consultation engine
14. AI Capability
Impl: ai_framework/ai_provider/contracts.py::Role, FinishReason, AIError, ChatMessage, TokenUsage, AIRequest, AIResponse, PromptTemplate, AIProviderProtocol, mock.py::MockAIProvider, adapters/openrouter.py::OpenRouterAdapter, resilient.py::ResilientProvider, cache.py::CachedAIProvider, InMemoryCache, CacheStorageProtocol, pipeline/: PipelineStep, StructuredOutputParser, PromptPipeline, AIService
Contract: Stage 3.1, 3.2 AI Provider Layer
Tests: tests/ai_provider/test_*.py, test_structured_output_parser.py, test_prompt_pipeline.py
Boundary: FRAMEWORK
Limitation: READY for providers/mock/resilient/cached, prompt pipeline, structured output, orchestration. OpenRouter adapter READY/LIMITED.
15. Gap Matrix
Gap ID	Capability	Current	Required for new site	Priority
G1	Publisher / Static Website Generation	MISSING — no ai_framework/publisher/, only showcase_generator.py for manifest	Decision: keep as MISSING and fix docs, or implement generic Publisher	HIGH — docs vs code mismatch
G2	SQLite provisioning	LIMITED — _init_db pass, no migration/bootstrap	Generic schema/migration layer if DB needed for new site	MEDIUM
G3	Asset persistent metadata & S3	LIMITED — dict in memory, LocalFileStorage only	DB-backed Asset metadata, S3 adapter, image processing if site needs uploads	MEDIUM
G4	Product auto discovery	LIMITED — explicit use_case_map required	Automatic site assembly from business description if goal is generative	LOW — current explicit assembly works
G5	Pipeline transaction/context lifecycle	LIMITED — PipelineContext small, separate CRUDContext	Unified context with user identity, transaction, tenant, locale, session	MEDIUM
G6	Generic Stock/Inventory/Quote/Reservation Engine	MISSING — only showcase-specific in plant_nursery	Extract to ai_framework/services/stock/ with StockServiceProtocol, typed exceptions OutOfStockError/InsufficientStockError, atomic reserve, audit log	HIGH — for C16.6 before new site if inventory needed
G7	Generic StatusLifecycleEngine	MISSING — cafe/lawyer lifecycles showcase-specific	Generic lifecycle engine if new site needs status transitions	LOW
G8	Production identity infrastructure	MISSING — generic RBAC READY, but no persistent users, password hashing, OAuth/OIDC, JWT, sessions	Decide if new site needs auth — currently InMemory auth only	HIGH if site needs login
G9	Frontend renderer for CRUD UI	MISSING — CrudUIEngine generates view-models only	Frontend shell/renderer if new site needs admin UI	MEDIUM
G10	Framework Services	PARTIAL — slug READY, stock MISSING	ai_framework/services/ currently 82 bytes init.py, needs stock_service.py per C16.6 plan	HIGH
16. Conclusions from v0.1 Audit (preserved)
Framework is real application framework: API -> Pipeline -> UseCase -> Domain -> Persistence + CRUD + validation + metadata + security + AI
ProductFactory is real boundary but assembles existing product, not creates site from business description
Showcase capabilities (stock, availability, quotes, consultations, gallery, status lifecycle) cannot be automatically considered Framework capabilities — currently proven at showcase level only
Most significant historical/documentation mismatch — Publisher — Phase 9 claims CRUD->AssetManager->Publisher but current ai_framework/ has no publisher implementation
SQLite capability has explicit limitation — persistence adapter exists but no DB init/schema lifecycle
Generic AssetManager exists, generic publishing does not
Test base strong — 557 named test_* functions in dump, parameterized cases, consistent with 578 claimed, C4-C16.5 have separate contract tests
17. Next Step (from v0.1)
Build strict layer: Capability -> exact implementation -> exact contract -> exact test(s) -> framework/showcase boundary -> limitation

This file IS that layer. Next action: decide which MISSING/LIMITED capabilities must exist in Framework before first new site creation, without starting code changes yet.

Generated: 2026-09-18 from PROJECT_DUMP.md 337 files + user audit v0.1 + optimistic matrix
File to save: docs/architecture/capability-traceability-16.5.md

