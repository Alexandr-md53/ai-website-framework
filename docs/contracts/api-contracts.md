API Contracts — Phase 16.5
Plant Nursery
PATCH /plants/{id}/stock {stock_quantity:int >=0} → 200 {id, stock_quantity, is_available} | 400 negative | 404/400 not found
GET /plants?available=true|false → filter by is_available, combined with min_temp
POST /plants {category_id, name, frost_resistance} → includes stock_quantity=0, is_available=False
GET /categories/{id}/plants → each item includes stock_quantity, is_available
POST /plants/{id}/images → limit 5, main_image auto
GET /plants/{id}/images → gallery read + count
DELETE /plants/{id}/images/{image_id} → main promotion
POST /quotes {plant_id?, unit_price, quantity, discount_policy} → total, validates stock if plant_id present
Quote Stock Rules (C16.4/C16.5)
OUT_OF_STOCK when stock_quantity==0 → 400
INSUFFICIENT_STOCK when quantity > stock_quantity → 400
No plant_id → backward compat 200 (no stock check)
Success → decrement plant.stock_quantity -= quantity, update is_available = quantity>0
Second quote after zero → 400 OUT_OF_STOCK
Cafe / Lawyer (Phase 12, 15)
Cafe status DRAFT->ACTIVE->ARCHIVED
Lawyer submit_consultation_request M2M validation, list RBAC, status PENDING->APPROVED|REJECTED->COMPLETED RBAC
