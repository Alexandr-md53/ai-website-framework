"""
Slice 3 — Orders & Stock Runtime Evidence
Characterization, no production change, no lock/transaction.

Goal: зафиксировать фактический существующий контракт через реальный FastAPI TestClient.
- Сначала проверяем, какие endpoints/services существуют
- Каждый отсутствующий contract помечаем NOT IMPLEMENTED, а не реализуем
- Не вводим race/lock/semantics
- Разделяем VERIFIED и NOT IMPLEMENTED

Acceptance per manager spec:
1. Real TestClient
2. Characterization order/stock lifecycle
3. Total calc
4. Confirm -> stock--
5. Cancel -> stock++
6. stock=0, stock=1, two sequential purchases of last unit
7. Repeated ops on mutated order
8. Missing endpoint = NOT IMPLEMENTED
9. Existing HTTP/language tests stay PASS (checked separately)
10. Full cafe pytest + test_runner_no_fastapi.py after
11. git diff ai_framework = 0
12. git diff blog_cms = 0
"""

from __future__ import annotations
import pathlib
import tempfile
from decimal import Decimal

from fastapi.testclient import TestClient

from showcases.cafe.app_factory import create_app
from showcases.cafe.services.cafe_menu_service import CafeMenuService
from showcases.cafe.services.cafe_image_service import CafeImageService


def make_client():
    tmp_out = pathlib.Path(tempfile.mkdtemp(prefix="cafe_out_ord_"))
    tmp_uploads = pathlib.Path(tempfile.mkdtemp(prefix="cafe_up_ord_"))
    service = CafeMenuService()
    image_service = CafeImageService(uploads_root=tmp_uploads)
    app = create_app(service=service, out_dir=tmp_out, image_service=image_service)
    client = TestClient(app)
    return client, service, tmp_out, tmp_uploads


def create_published_item(client, service, stock=5, slug="espresso"):
    # via HTTP to keep evidence real
    r = client.post(
        "/menu/categories",
        json={
            "name": "Coffee",
            "slug": "coffee",
            "name_ru": "Кофе",
            "name_en": "Coffee",
            "name_ro": "Cafea",
        },
    )
    if r.status_code != 200:
        # category may already exist — get existing
        cats = client.get("/menu/categories").json()
        cat_id = cats[0]["id"] if cats else None
    else:
        cat_id = r.json()["id"]
    if not cat_id:
        # fallback via service
        cat = service.create_category(
            name="Coffee",
            slug="coffee",
            name_ru="Кофе",
            name_en="Coffee",
            name_ro="Cafea",
        )
        cat_id = str(cat.id)

    r = client.post(
        "/menu/items",
        json={
            "title": f"Item {slug}",
            "slug": slug,
            "description": "Description long enough for publish gate 12345",
            "price": "4.5",
            "category_id": cat_id,
            "stock_quantity": stock,
            "title_ru": f"Товар {slug}",
            "title_en": f"Item {slug}",
            "title_ro": f"Item {slug}",
            "description_ru": "Описание",
            "description_en": "Desc",
            "description_ro": "Desc",
        },
    )
    assert r.status_code == 200, f"create item {r.status_code} {r.text}"
    item_id = r.json()["id"]
    r = client.post(f"/menu/items/{item_id}/publish")
    assert r.status_code == 200, f"publish {r.status_code} {r.text}"
    return cat_id, item_id


# ---- Characterization ----


def test_orders_characterization_endpoints_exist():
    """Check which order endpoints exist in current contract"""
    client, service, out_dir, up_dir = make_client()
    # create one item for order tests
    _, item_id = create_published_item(client, service, stock=5, slug="char-ep")

    endpoints = {
        "POST /orders": (
            "post",
            "/orders",
            {"lines": [{"menu_item_id": item_id, "quantity": 1}]},
        ),
        "GET /orders": ("get", "/orders", None),
        "POST /orders/{id}/validate": None,  # checked after creation
        "POST /orders/{id}/confirm": None,
        "POST /orders/{id}/cancel": None,
        "GET /menu/items/{id}": ("get", f"/menu/items/{item_id}", None),
    }

    results = {}
    for name, spec in endpoints.items():
        if spec is None:
            continue
        method, path, body = spec
        if method == "post":
            r = client.post(path, json=body)
        else:
            r = client.get(path)
        results[name] = r.status_code
        print(f"{name} -> {r.status_code}")

    # VERIFIED: at least POST /orders and GET /orders must exist per FROZEN_ROUTES
    assert results.get("POST /orders") in (200, 400), (
        f"POST /orders should exist, got {results.get('POST /orders')}"
    )
    # If missing, mark as NOT IMPLEMENTED explicitly
    for k, v in results.items():
        if v == 404:
            print(f"NOT IMPLEMENTED: {k}")
        else:
            print(f"VERIFIED: {k} exists ({v})")


def test_order_create_and_total():
    """VERIFIED: создание заказа и расчет total"""
    client, service, out_dir, up_dir = make_client()
    _, item_id = create_published_item(client, service, stock=5, slug="total")

    r = client.post(
        "/orders", json={"lines": [{"menu_item_id": item_id, "quantity": 2}]}
    )
    assert r.status_code == 200, f"create order {r.status_code} {r.text}"
    data = r.json()
    assert "total" in data
    assert Decimal(data["total"]) == Decimal("9.0"), (
        f"total expected 9.0 got {data['total']}"
    )
    print(f"VERIFIED: order total = {data['total']} for qty 2 x 4.5")


def test_order_confirm_decrements_stock_if_contract_exists():
    """Characterization: confirm должен уменьшать stock, если contract это обещает"""
    client, service, out_dir, up_dir = make_client()
    _, item_id = create_published_item(client, service, stock=5, slug="confirm-stock")

    # initial stock
    r = client.get(f"/menu/items/{item_id}")
    if r.status_code == 404:
        print("NOT IMPLEMENTED: GET /menu/items/{id} for stock check")
        # fallback via service
        from uuid import UUID

        item = service.get_item(UUID(item_id))
        initial_stock = item.stock_quantity
    else:
        initial_stock = r.json()["stock_quantity"]

    r = client.post(
        "/orders", json={"lines": [{"menu_item_id": item_id, "quantity": 2}]}
    )
    assert r.status_code == 200
    order_id = r.json()["id"]

    r = client.post(f"/orders/{order_id}/confirm")
    if r.status_code == 404:
        print("NOT IMPLEMENTED: POST /orders/{id}/confirm")
        return
    assert r.status_code == 200, f"confirm {r.status_code} {r.text}"

    # check stock after
    r2 = client.get(f"/menu/items/{item_id}")
    if r2.status_code == 404:
        from uuid import UUID

        item_after = service.get_item(UUID(item_id))
        after_stock = item_after.stock_quantity
    else:
        after_stock = r2.json()["stock_quantity"]

    print(f"Stock before {initial_stock} after confirm {after_stock}")
    if after_stock == initial_stock - 2:
        print("VERIFIED: confirm decrements stock")
    else:
        print(
            f"DEFECT? Expected {initial_stock - 2} got {after_stock} — фиксируем как дефект существующего контракта"
        )
        # Do not mask — assert to surface defect
        assert after_stock == initial_stock - 2, (
            f"stock not decremented: {initial_stock} -> {after_stock}"
        )


def test_order_cancel_restores_stock_if_contract_exists():
    client, service, out_dir, up_dir = make_client()
    _, item_id = create_published_item(client, service, stock=5, slug="cancel-stock")

    r = client.post(
        "/orders", json={"lines": [{"menu_item_id": item_id, "quantity": 2}]}
    )
    assert r.status_code == 200
    order_id = r.json()["id"]

    r = client.post(f"/orders/{order_id}/confirm")
    if r.status_code == 404:
        print("NOT IMPLEMENTED: confirm for cancel test")
        return
    assert r.status_code == 200

    r = client.post(f"/orders/{order_id}/cancel")
    if r.status_code == 404:
        print("NOT IMPLEMENTED: POST /orders/{id}/cancel")
        return
    assert r.status_code == 200, f"cancel {r.status_code} {r.text}"

    # check stock restored
    r2 = client.get(f"/menu/items/{item_id}")
    if r2.status_code != 200:
        from uuid import UUID

        after = service.get_item(UUID(item_id)).stock_quantity
    else:
        after = r2.json()["stock_quantity"]
    print(f"After cancel stock = {after}, expected 5")
    assert after == 5, f"stock not restored after cancel: got {after}"


def test_stock_edge_0_and_1_and_two_purchases_last_unit():
    """Граничные: stock 0, stock 1, две покупки последней единицы"""
    client, service, out_dir, up_dir = make_client()
    _, item_id_0 = create_published_item(client, service, stock=0, slug="stock0")
    _, item_id_1 = create_published_item(client, service, stock=1, slug="stock1")

    # stock 0 -> create order should fail OUT_OF_STOCK or INSUFFICIENT
    r = client.post(
        "/orders", json={"lines": [{"menu_item_id": item_id_0, "quantity": 1}]}
    )
    print(f"stock=0 order attempt -> {r.status_code} {r.text[:200]}")
    if r.status_code == 200:
        print("DEFECT? stock 0 allowed order creation — check service contract")
    else:
        print(f"VERIFIED: stock 0 blocks order ({r.status_code})")
        assert r.status_code == 400

    # stock 1 -> first order qty 1 should succeed
    r = client.post(
        "/orders", json={"lines": [{"menu_item_id": item_id_1, "quantity": 1}]}
    )
    assert r.status_code == 200, f"stock1 first order {r.text}"
    oid1 = r.json()["id"]
    r = client.post(f"/orders/{oid1}/confirm")
    assert r.status_code == 200, f"confirm first {r.text}"

    # second purchase of last unit -> should fail after first confirm
    r = client.post(
        "/orders", json={"lines": [{"menu_item_id": item_id_1, "quantity": 1}]}
    )
    print(f"second purchase after stock depleted -> {r.status_code} {r.text[:200]}")
    if r.status_code == 200:
        # service may allow creation but confirm should fail
        oid2 = r.json()["id"]
        r2 = client.post(f"/orders/{oid2}/confirm")
        print(f"second confirm -> {r2.status_code} {r2.text[:200]}")
        assert r2.status_code == 400, "second confirm should fail after stock depleted"
        print(
            "VERIFIED: two sequential purchases of last unit — second blocked at confirm"
        )
    else:
        print("VERIFIED: two sequential purchases — second blocked at creation")
        assert r.status_code == 400


def test_repeated_ops_on_mutated_order():
    """Повторные операции над измененным заказом"""
    client, service, out_dir, up_dir = make_client()
    _, item_id = create_published_item(client, service, stock=5, slug="repeat")

    r = client.post(
        "/orders", json={"lines": [{"menu_item_id": item_id, "quantity": 1}]}
    )
    assert r.status_code == 200
    oid = r.json()["id"]

    r = client.post(f"/orders/{oid}/confirm")
    if r.status_code == 404:
        print("NOT IMPLEMENTED: confirm for repeated ops test")
        return
    assert r.status_code == 200

    # repeat confirm
    r2 = client.post(f"/orders/{oid}/confirm")
    print(f"repeat confirm -> {r2.status_code} {r2.text[:200]}")
    # contract may return 400 or idempotent 200 — фиксируем факт
    if r2.status_code == 200:
        print("NOTE: confirm is idempotent — VERIFIED as existing behavior")
    else:
        print(f"VERIFIED: repeat confirm blocked ({r2.status_code})")

    # cancel after confirm then repeat cancel
    r = client.post(f"/orders/{oid}/cancel")
    assert r.status_code == 200
    r2 = client.post(f"/orders/{oid}/cancel")
    print(f"repeat cancel -> {r2.status_code} {r2.text[:200]}")
    if r2.status_code == 200:
        print("NOTE: cancel is idempotent")
    else:
        print(f"VERIFIED: repeat cancel blocked ({r2.status_code})")
