# coding: utf-8, ASCII only
"""
C12.2: Status transition via C10.1 Product Assembly Factory

DRAFT -> ACTIVE with validation
* -> ARCHIVED with RBAC
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

def test_c12_2_01_draft_to_active_succeeds():
    from showcases.cafe.api.app_factory import build_cafe_app
    app = build_cafe_app()
    client = TestClient(app)

    create = client.post("/menu-items", json={"name": "Espresso", "base_price": "2.50", "user_id": "barista-1", "user_role": "BARISTA"})
    assert create.status_code in (200, 201)
    item_id = create.json()["id"]
    assert create.json()["status"] == "DRAFT"

    resp = client.patch(f"/menu-items/{item_id}/status", json={"new_status": "ACTIVE", "user_id": "barista-1", "user_role": "BARISTA"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == item_id
    assert data["status"] == "ACTIVE"

def test_c12_2_02_invalid_active_transition_validation_error():
    from showcases.cafe.api.app_factory import build_cafe_app
    app = build_cafe_app()
    client = TestClient(app)

    # Create with zero price -> activate must fail validation
    create = client.post("/menu-items", json={"name": "Invalid", "base_price": "0.00", "user_id": "barista-1", "user_role": "BARISTA"})
    assert create.status_code in (200, 201)
    item_id = create.json()["id"]

    resp = client.patch(f"/menu-items/{item_id}/status", json={"new_status": "ACTIVE", "user_id": "barista-1", "user_role": "BARISTA"})
    # Contract: validation error -> 400 or 422
    assert resp.status_code in (400, 422)

def test_c12_2_03_barista_archive_403_manager_archive_success():
    from showcases.cafe.api.app_factory import build_cafe_app
    app = build_cafe_app()
    client = TestClient(app)

    create = client.post("/menu-items", json={"name": "Mocha", "base_price": "3.50", "user_id": "barista-1", "user_role": "BARISTA"})
    assert create.status_code in (200, 201)
    item_id = create.json()["id"]

    # BARISTA tries ARCHIVE -> 403
    barista = client.patch(f"/menu-items/{item_id}/status", json={"new_status": "ARCHIVED", "user_id": "barista-1", "user_role": "BARISTA"})
    assert barista.status_code in (403, 400, 401)

    # MANAGER archives -> 200
    manager = client.patch(f"/menu-items/{item_id}/status", json={"new_status": "ARCHIVED", "user_id": "manager-1", "user_role": "MANAGER"})
    assert manager.status_code == 200
    assert manager.json()["status"] == "ARCHIVED"
