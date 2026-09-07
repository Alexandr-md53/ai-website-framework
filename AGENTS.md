# AGENTS.md - AI Website Framework - Architecture Model Frozen V2

## Phase 10.1 Status: A1+A2+B2+B1 GREEN - 395 passed

### Dependency Model (official)
CORE -> ENGINE -> EXTENSION -> SHOWCASE

CORE:
- core/
- domain/
- services/slug/
- validation/
- crud/contracts.py
Rules:
- must NOT import api, crud_ui, application, infrastructure, showcases
- may import stdlib, core itself, domain primitives

ENGINE:
- crud/engine.py (UniversalCRUDEngine)
- crud/crud_engine.py (CRUDEngine schema-aware)
- crud/persistence.py, sqlite_persistence.py
- pipeline/
Rules:
- reads slug_config for schema
- implements PersistenceProviderProtocol
- must NOT depend on api or showcases

EXTENSION:
- api/ (Delivery Adapter)
- crud_ui/
- application/ (if exists)
- infrastructure/ (if exists)
Rules:
- may depend on CORE and ENGINE via public API
- must NOT be imported by CORE
- must NOT import showcases

SHOWCASE:
- showcases/
Rules:
- MAY depend on framework
- FRAMEWORK must NEVER depend on showcase


### Role

AGENTS.md = System Instruction for AI agent (how AI must work)
START_HERE.md = WHAT is this project
framework-structure.md = HOW packages are structured
MIGRATION_MAP.md = WHERE we move
REFERENCE_PROJECT_ANALYSIS.md = WHAT and WHY we extract
DEVELOPMENT_WORKFLOW.md = HOW full dev cycle works

After this save, AGENTS.md is frozen. Do not change without architectural reason.

### Invariants locked by tests

- tests/test_architecture.py:
    - test_core_no_forbidden_dependencies
    - test_framework_never_depends_on_showcase
    - test_crud_boundary_still_respected
- docs/IMPORT_MAP_FROZEN_V2.md: 0 violations frozen

### Boundaries (A1)

- ai_framework/crud/__init__.py canonical public API: CRUDContext, CRUDResult, CRUDError, PersistenceProviderProtocol, UniversalCRUDEngine, CRUDEngine, InMemoryPersistenceProvider, SQLitePersistenceProvider
- ai_framework/pipeline/__init__.py single source Engine
- ai_framework/api/__init__.py single source Delivery Adapter
- No application/crud, application/pipeline, application/api duplicates

### Baseline
395 passed in âˆ¼2.8s

### Next

C1 - CLI skeleton
