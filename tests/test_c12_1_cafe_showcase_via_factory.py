# coding: utf-8, ASCII only
"""
C12.1: Cafe Showcase via C10.1 Product Assembly Factory

Chain: ProductInfo -> build_app_from_product_info() -> C9.2 -> C6 -> FastAPI -> C8 -> C7 -> CafeService

0 changes in ai_framework/, new files only in showcases/cafe/
"""

from decimal import Decimal
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_framework.product_registry import ProductInfo

def test_c12_1_01_build_app_from_product_info_returns_fastapi():
    """C10.1 factory returns FastAPI for cafe showcase"""
    from showcases.cafe.api.app_factory import build_cafe_app

    app = build_cafe_app()

    assert isinstance(app, FastAPI)
    # C6 + C9.2 wiring present
    assert len(app.routes) >= 1

def test_c12_1_02_create_menu_item_endpoint_via_c10_factory():
    """POST /menu-items creates MenuItem via C10.1 -> C6 -> C8 -> C7 -> UseCase -> CafeService"""
    from showcases.cafe.api.app_factory import build_cafe_app

    app = build_cafe_app()
    client = TestClient(app)

    resp = client.post(
        "/menu-items",
        json={
            "name": "Cappuccino",
            "base_price": "4.50",
            "user_id": "barista-1",
            "user_role": "BARISTA",
        },
    )

    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["name"] == "Cappuccino"
    assert "id" in data
    assert data["status"] == "DRAFT"

def test_c12_1_03_rbac_manager_only_price_update():
    """RBAC via real endpoint path: non-manager rejected, manager succeeds"""
    from showcases.cafe.api.app_factory import build_cafe_app
    from showcases.cafe.services.cafe_service import PermissionDeniedError

    app = build_cafe_app()
    client = TestClient(app)

    # 1. Create item as BARISTA
    create_resp = client.post(
        "/menu-items",
        json={
            "name": "Latte",
            "base_price": "3.00",
            "user_id": "barista-1",
            "user_role": "BARISTA",
        },
    )
    assert create_resp.status_code in (200, 201)
    item_id = create_resp.json()["id"]

    # 2. BARISTA tries to update price -> must be rejected
    # Expect 403 or PermissionDenied mapped to error response
    barista_update = client.patch(
        f"/menu-items/{item_id}/price",
        json={
            "new_price": "5.00",
            "user_id": "barista-1",
            "user_role": "BARISTA",
        },
    )
    # Contract: non-manager rejected (403 or 400 with permission error)
    assert barista_update.status_code in (403, 400, 401)
    # Ensure it did NOT succeed
    assert barista_update.status_code != 200

    # 3. MANAGER updates price -> must succeed
    manager_update = client.patch(
        f"/menu-items/{item_id}/price",
        json={
            "new_price": "5.00",
            "user_id": "manager-1",
            "user_role": "MANAGER",
        },
    )
    assert manager_update.status_code == 200
    assert manager_update.json()["base_price"] == "5.00" or float(manager_update.json()["base_price"]) == 5.0