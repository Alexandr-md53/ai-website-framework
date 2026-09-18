Capability Matrix v0.2 — Strict Traceability
Source: docs/architecture/capability-traceability-16.5.md + patch 2026-09-18 + publication-model-16.5.md
Method: Capability → implementation symbol → contract → exact test → boundary → limitation
Checkpoint: phase-16.5-publication-model 39ce2cd, 578 GREEN, 337 files audit
Date: 2026-09-18
This is the REVIEWED version per user request. Each line verified against PROJECT_DUMP.md and git history.

#	Capability	Implementation Symbol (exact)	Contract (exact)	Exact Test(s)	Boundary	Limitation
1. Architecture						
1.1	CORE → ENGINE → EXTENSION → SHOWCASE dependency rule	ai_framework/core/, domain/, services/slug/, validation/, crud/contracts.py, crud/engine.py, pipeline/, api/, application/	docs/architecture/dependency-rules.md, docs/IMPORT_MAP_FROZEN_V2.md (0 violations), AGENTS.md frozen	tests/test_architecture.py::test_core_no_forbidden_dependencies, test_framework_never_depends_on_showcase	FRAMEWORK	READY — statically enforced
1.2	Product Assembly (explicit)	ai_framework/product/factory.py::build_app_from_product_info, ai_framework/api/product_pipeline_wiring.py::build_registry_from_map, ai_framework/api/fastapi.py::create_app	C10.1 product factory metadata→C9.2→C6 no fs scan, docs/architecture/product-assembly.md	test_c10_1_product_factory.py (6), test_c9_2_endpoint_pipeline_registration.py (5), test_c9_3_fastapi_product_wiring.py (4)	FRAMEWORK	READY / LIMITED — requires explicit use_case_map: Dict[Tuple[str,str], Tuple[UseCase, dto_factory]], no auto-discovery
2. API / FastAPI						
2.1	FastAPI factory	ai_framework/api/fastapi.py:create_app(registry=None)	C6.1, C6.2, docs/architecture/api-pipeline.md	test_c6_1_fastapi_factory, test_c6_2_fastapi_wiring	FRAMEWORK	READY
2.2	EndpointRegistry / Router / APIAdapter	ai_framework/api/registry.py, router.py, adapter.py, endpoint.py	C5.1, C5.2 registry enrichment lru_cache, docs/contracts/frozen-contracts.md	test_c5_registry, test_c5_2_enrichment, tests/api/	FRAMEWORK	READY / LIMITED — Router simple matcher, two registry concepts
2.3	EndpointPipelineAdapter	ai_framework/api/pipeline_adapter.py	C8.2 new file only, C9.1	test_c8_2_pipeline_adapter_impl, test_c9_1_fastapi_pipeline_wiring	FRAMEWORK	READY
2.4	HTTP error mapping	ai_framework/api/contracts.py::APIResponse, ResponseAdapter, application/pipeline/	docs/contracts/api-contracts.md, C16.5 fix e3933e9 ValueError OUT_OF_STOCK/INSUFFICIENT_STOCK → 400	test_c16_4_quote_stock_validation_api.py, test_c16_5_quote_decrement_api.py	FRAMEWORK (partly generic, partly hard-coded in showcase use_cases)	READY / LIMITED — mapping hard-coded, needs typed exceptions (G10)
3. Application Pipeline						
3.1	PipelineContext	ai_framework/application/pipeline/contracts.py::PipelineContext(request_id, metadata=dict)	C8/C16.5 frozen	test_c8_1_api_application_wiring 8 tests	FRAMEWORK	READY / LIMITED — no user identity, transaction, tenant, locale
3.2	Application Pipeline chain	ai_framework/application/pipeline/executor.py::ApplicationPipeline, adapter.py::UseCaseHandlerAdapter	C7.2, C7.3	test_c7_2_application_contract, test_c7_3_product_execution	FRAMEWORK	READY — no transaction abstraction
4. Generic CRUD						
4.1	UniversalCRUDEngine	ai_framework/crud/engine.py, crud_engine.py, contracts.py::CRUDContext, CRUDResult, PersistenceProviderProtocol	C2 generic CRUD, docs/contracts/crud-contracts.md	tests/test_crud_*.py, test_c2_crud_engine.py	FRAMEWORK	READY
4.2	SQLitePersistence / InMemory	ai_framework/crud/sqlite_persistence.py, persistence.py	PersistenceProviderProtocol	test_sqlite_persistence.py, test_crud_persistence.py	FRAMEWORK	READY
4.3	SlugOrchestrator	ai_framework/crud/slug_orchestrator.py, services/slug/generator.py	SlugGenerator, DefaultCollisionResolver	test_slug_orchestrator.py, test_slug_service.py	FRAMEWORK	READY
5. Validation						
5.1	ValidationEngine + Providers	ai_framework/validation/engine.py, providers/metadata.py, providers/persistence.py, validators/*	ValidationProviderProtocol, ValidationContext, ValidationResult	tests/validation/, test_validation_engine.py	FRAMEWORK	READY
6. Metadata / CrudUI						
6.1	MetadataEngine / Normalizer / Registry	ai_framework/metadata/engine.py, normalizer.py, registry.py, models.py	MetadataEngineContract, C3 metadata	test_metadata_engine.py, test_c3_*.py	FRAMEWORK	READY
6.2	CrudUIEngine / Config / WebAdapter	ai_framework/crud_ui/engine.py, config.py, web_adapter.py, web.py	CrudUIConfig, C4	test_crud_ui_*.py, test_c4_*.py	FRAMEWORK	READY / LIMITED — form rendering minimal, no rich UI
6.3	AssetManager + Storage	ai_framework/asset_manager/manager.py, storage.py, contracts.py	AssetManagerContract, StorageProviderProtocol	test_asset_manager.py, test_c11_asset_manager.py	FRAMEWORK	READY / LIMITED — LocalFileStorage only, S3 MISSING
7. Services						
7.1	Slug Service	ai_framework/services/slug/engine.py, generator.py, resolver.py, protocols.py	SlugServiceProtocol	test_slug_service.py	FRAMEWORK	READY
7.2	Stock Service (current state pre-C16.6)	showcases/plant_shop/domain/services/plant_stock_service.py (showcase-specific) — ai_framework/services/stock/ DOES NOT EXIST	No framework contract — showcase ValueError("OUT_OF_STOCK")	test_c16_4_quote_stock_validation_api.py, test_c16_5_quote_decrement.py	SHOWCASE-SPECIFIC (G6)	SHOWCASE-SPECIFIC / LIMITED — no typed exceptions, no atomic reserve, no concurrency test
8. Domain						
8.1	Article Entity / Value Objects	ai_framework/domain/entities/article.py, value_objects/title.py, content.py, article_id.py	Domain Entity Contract	test_article_entity.py, test_value_objects.py	FRAMEWORK	READY
8.2	Showcase Domains (Plant, Category, Quote)	showcases/plant_shop/domain/entities/plant.py, category.py, quote.py, value_objects/*	RepositoryProtocol	tests/showcases/plant_shop/	SHOWCASE	SHOWCASE-SPECIFIC — not generalized
9. Publishing / Site Output — CORRECTED per 2026-09-18						
9.1	Legacy Publisher / External Publication (Historical)	plugins/telegram/publisher.py deleted — TelegramPublisherPlugin(PublisherPluginContract) + framework/core/contracts.py::PublisherContract deleted	Legacy PublisherPluginContract — get_metadata(), validate(), publish()	none in current — legacy test_framework_* removed	HISTORICAL / EXTENSION	HISTORICAL — Telegram-specific social plugin, NOT generic publisher. Reference for metadata pattern only.
9.2	Generic Website Publisher	NONE — ai_framework/publisher/ does not exist (confirmed by PROJECT_DUMP.md 337 files, git ls-tree)	NONE	NONE	N/A	MISSING — requires new design
9.3	Site Generator / Renderer	ai_framework/showcase_generator.py generates manifest.json only (C3.2)	showcase_manifest.py::KNOWN_SHOWCASES	test_c3_2_manifest_generator.py	SHOWCASE / FRAMEWORK boundary unclear	MISSING — no HTML/CSS/JS generation, no View/Content Model → Renderer
9.4	Static Output / Deployment	NONE	NONE	NONE	N/A	MISSING
10. Product / Showcase Wiring						
10.1	Plant Shop Product wiring	showcases/plant_shop/product_info.py, use_cases/*, api/*, application/dto/*	ProductInfo + use_case_map	tests/showcases/plant_shop/test_* + API tests	SHOWCASE	SHOWCASE-SPECIFIC — plant_shop only, quote decrement logic showcase-specific
10.2	Article Showcase	showcases/article/	—	tests/showcases/article/	SHOWCASE	SHOWCASE-SPECIFIC
11. Security / Settings / AI Provider						
11.1	Security / RBAC / Credentials	ai_framework/security/authorization.py, credentials.py, web.py	AuthorizationProviderProtocol	test_role_based_authorization.py, test_security_*.py	FRAMEWORK	READY / LIMITED
11.2	Settings Manager	ai_framework/settings/manager.py, provider.py, ui_bridge.py	SettingsProviderProtocol	test_settings_manager.py	FRAMEWORK	READY
11.3	AI Provider / Pipeline Service	ai_framework/ai_provider/contracts.py, adapters/openrouter.py, mock.py, resilient.py, pipeline/service.py	AIProviderProtocol, PromptPipeline, StructuredOutputParser	test_ai_provider_*.py, test_pipeline_service.py	FRAMEWORK	READY / LIMITED — OpenRouter + Mock, no other providers
Verified symbols: All implementation symbols checked against PROJECT_DUMP.md file list (except new docs added after dump). No ai_framework/publisher/ exists.
Tests: 578 GREEN claimed at phase-16.5-publication-model, 557 test_* funcs named in dump.

