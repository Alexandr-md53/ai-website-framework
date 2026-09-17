API Pipeline — Frozen Contracts
Layers
C6.1: FastAPI factory create_app(registry=None) → FastAPI wiring over frozen EndpointRegistry/Router/APIAdapter (449 passed)
C6.2: extended wiring middlewares+health+lifespan passthrough (454 passed)
C7.2: application boundary freeze (pipeline+adapter+repo+use_cases) (464 passed)
C7.3: product execution boundary freeze CRUDContext/CRUDResult/CRUDError/PersistenceProtocol/UniversalEngine (477 passed)
C8.1: api->application wiring contract tests (8 tests) 485 passed
C8.2: EndpointPipelineAdapter dto_factory+context_factory+pipeline.execute passthrough, new file only (489 passed)
C9.1: fastapi+pipeline wiring contract (6 passed) canonical crud.contracts import 495 passed
C9.2: endpoint pipeline registration helper 5 tests 500 passed
C9.3: full fastapi wiring via helper 4 tests 504 passed
PipelineContext
Frozen in Phase 16.5: PipelineContext contract restored after fix(api) e3933e9 mapping ValueError OUT_OF_STOCK/INSUFFICIENT_STOCK to 400.

Flow for Plant Nursery
PATCH /plants/{id}/stock → dto_factory → CatalogService.update_stock → Plant.stock_quantity → is_available
GET /plants?available=true|false → filter in CatalogService
POST /plants → returns {stock_quantity, is_available}
GET /categories/{id}/plants → each item contains stock fields
POST /quotes {plant_id, quantity} → validation OUT_OF_STOCK/INSUFFICIENT_STOCK → decrement → is_available update
