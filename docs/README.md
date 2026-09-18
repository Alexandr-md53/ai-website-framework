AI Website Framework — Documentation Index (Phase 16.5)
HEAD: b3c2c2d feat(C16.5) | Tests: 578 GREEN | Status: CANONICAL

Structure
docs/
├── README.md (this index)
├── architecture/
│   ├── overview.md
│   ├── dependency-rules.md
│   ├── api-pipeline.md
│   └── product-assembly.md
├── contracts/
│   ├── frozen-contracts.md
│   └── api-contracts.md
├── phases/
│   ├── phase-09.md
│   ├── phase-10.md
│   ├── phase-11.md
│   ├── phase-12.md
│   ├── phase-13.md
│   ├── phase-14.md
│   ├── phase-15.md
│   └── phase-16.md
└── migrations/
    └── 01_plant_migration_contract.md
Quick Links
START_HERE.md — frozen v2 baseline (Phase 9.1)
AGENTS.md — dependency model CORE→ENGINE→EXTENSION→SHOWCASE
IMPORT_MAP_FROZEN_V2.md — 0 violations
CHANGELOG.md — history up to Phase 9.1 (needs update to Phase 16.5, see phases/)
Current State (Phase 16.5)
Core: ai_framework/ only source of truth
Showcases: cafe, lawyer, plant_nursery via ProductFactory
API: FastAPI factory create_app(registry=None) over frozen EndpointRegistry/Router/APIAdapter
Pipeline: EndpointPipelineAdapter (dto_factory+context_factory+pipeline.execute)
Stock domain: Plant.stock_quantity:int, Plant.is_available:bool (derived quantity>0)
Quote: validates OUT_OF_STOCK / INSUFFICIENT_STOCK → 400, decrements stock on success
- architecture/capability-traceability-16.5.md — Strict traceability v0.2: impl → contract → test → boundary (337 files audit)
