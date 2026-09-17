Architecture Overview — Phase 16.5
Dependency Model (from AGENTS.md frozen)
CORE -> ENGINE -> EXTENSION -> SHOWCASE
CORE:

ai_framework/core/, domain/, services/slug/, validation/, crud/contracts.py
must NOT import api, crud_ui, application, infrastructure, showcases
ENGINE:

crud/engine.py (UniversalCRUDEngine), crud/crud_engine.py, persistence.py, sqlite_persistence.py, pipeline/
reads slug_config, implements PersistenceProviderProtocol
must NOT depend on api or showcases
EXTENSION:

api/ (Delivery Adapter), crud_ui/, application/, infrastructure/
may depend on CORE and ENGINE via public API
must NOT be imported by CORE
SHOWCASE:

showcases/ (cafe, lawyer, plant_nursery)
MAY depend on framework, framework NEVER depends on showcase
Runtime Flow
API delivery (FastAPI)
  ↓
EndpointRegistry (frozen)
  ↓
Router / APIAdapter
  ↓
EndpointPipelineAdapter (dto_factory, context_factory, pipeline.execute passthrough)
  ↓
ApplicationPipeline
  ↓
UseCase (e.g. ChangeStatus, CreateMenuItem, SubmitRequest, CatalogService)
  ↓
Domain / Repository Contracts
  ↓
Infrastructure (InMemory repo in tests, SQLite in prod)
Product Assembly (C10.1)
ProductFactory: metadata -> C9.2 registration helper -> C6 FastAPI wiring
No FS scan, new file only principle since Phase 11
metadata/ per showcase (cafe_metadata.py, plant_metadata.py)
tests: test_c10_1_product_factory.py 6 tests 510 passed
Invariants locked by tests
test_core_no_forbidden_dependencies
test_framework_never_depends_on_showcase
test_crud_boundary_still_respected
IMPORT_MAP_FROZEN_V2.md: 0 violations
