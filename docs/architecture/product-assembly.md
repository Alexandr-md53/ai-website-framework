Product Assembly — Phase 11 Closed
Factory
C10.1: product assembly factory 6 tests 510 passed metadata->C9.2->C6 FastAPI no fs scan new file only
Registry: ProductInfo, list_products, get_product, enrichment pyproject_name/version/requires_python, lru_cache
API: api inspect_project export + cli inspect <path> [--json] filesystem-only (C5.5)
CLI: version + product info alias + --json, read-only hooks over C5.2 registry
Showcases via ProductFactory
cafe: api/app_factory.py, dto_factories.py, application/*, domain/menu_item.py, metadata/cafe_metadata.py
lawyer: submit_request_use_case, list_requests_use_case, update_request_status_use_case, M2M validation
plant_nursery: use_cases.py, domain/category.py, domain/plant.py (stock_quantity, is_available), domain/pricing.py, validation/category_rules.py
Tests
test_c10_1_product_factory.py
test_c12_1..c12_4 cafe/lawyer via factory
test_c13_1..c13_4 plant catalog/hierarchy/move/aggregation
