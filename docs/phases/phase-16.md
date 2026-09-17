Phase 16 — Plant Stock + Quote Integration
Tags: phase-16-c16.1-frozen a67b4ae 564, c16.2 cce1fc7 568, c16.3 b447d62 571, c16.4 f59a162 575, c16.5 e3933e9 HEAD b3c2c2d

C16.1 — PATCH /plants/{id}/stock
Contract: test_c16_1_plant_stock_api.py
API: PATCH /plants/{id}/stock {stock_quantity:int >=0}
Logic:
200 {id, stock_quantity, is_available=True if quantity>0 else False}
0 → is_available=False
negative → 400
not found → 400/404
overwrites previous value
Domain: Plant.stock_quantity, Plant.is_available derived
C16.2 — GET /plants?available filter
Contract: test_c16_2_plant_available_filter_api.py
API: GET /plants?available=true|false
true → only where stock_quantity>0
false → only where stock_quantity==0
no param → returns all (>=3)
combined: ?available=true&min_temp=100 → still works (frost filter passthrough)
C16.3 — stock fields in responses
Contract: test_c16_3_plant_stock_in_responses_api.py
POST /plants → response contains stock_quantity=0, is_available=False
GET /categories/{id}/plants → each item contains stock_quantity, is_available matching setup
PATCH reflected in GET /categories/{id}/plants
C16.4 — quote stock validation
Contract: test_c16_4_quote_stock_validation_api.py
POST /quotes {plant_id, unit_price, quantity, discount_policy}
OUT_OF_STOCK when stock==0 → 400 body contains OUT_OF_STOCK
INSUFFICIENT_STOCK when quantity>stock → 400 INSUFFICIENT_STOCK
sufficient stock → 200 {total}
backward compat: no plant_id → 200 even with quantity 9999 (no stock check)
C16.5 — quote decrement
Contract: test_c16_5_quote_decrement_api.py + fix e3933e9 ValueError→400 mapping, PipelineContext frozen
Success decrement: plant.stock_quantity -= quantity
Exact drain to zero: stock=0, is_available=False
Second quote after zero → 400 OUT_OF_STOCK
API layer maps ValueError OUT_OF_STOCK/INSUFFICIENT_STOCK to 400 (restore frozen PipelineContext contract)
Tests GREEN progression
564 after C16.1
568 after C16.2
571 after C16.3
575 after C16.4
HEAD b3c2c2d after C16.5 (same 575 + new decrement tests)
Next: C16.6
TBD based on quote + stock edge cases (concurrency, transaction, audit)
Should be documented after this catch-up is merged
