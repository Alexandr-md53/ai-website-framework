"""Block 3c-1: server-side cart (shop mode)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.services.cart import CART_TTL_SECONDS
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.config import StoreConfig

PASSWORD = "cart-pass"
SECRET = b"cart-test-secret"
TOKEN_RE = re.compile(r'name="csrf" value="([^"]+)"')


def _app(tmp_path, mode="shop"):
    (tmp_path / "db").mkdir(parents=True, exist_ok=True)
    (tmp_path / "backups").mkdir(parents=True, exist_ok=True)
    return create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner", password_hash=hash_password(PASSWORD, iterations=1000), secret_key=SECRET
        ),
        store_config=StoreConfig(mode=mode),
        env={"VIDEOSHOP_SECRET_KEY": SECRET.decode()},
        seed_demo=True,
    )


def _client(tmp_path, mode="shop"):
    return TestClient(_app(tmp_path, mode), follow_redirects=False)


def _csrf(client) -> str:
    body = client.get("/cart").text
    match = TOKEN_RE.search(body)
    return match.group(1) if match else ""


def _product_id(client) -> int:
    return client.app.state.catalog.list_products()[0].id


def _token(cart_id: int, issued_at: int) -> str:
    payload = f"{cart_id}:{issued_at}".encode("ascii")
    body = base64.urlsafe_b64encode(payload).decode("ascii")
    mac = hmac.new(SECRET, body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{mac}"


def test_cart_is_created_and_empty(tmp_path):
    client = _client(tmp_path)
    response = client.get("/cart")
    assert response.status_code == 200
    assert "videoshop_cart" in response.cookies
    assert "Корзина пуста" in response.text


def test_add_update_remove_clear(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    product_id = _product_id(client)
    added = client.post("/cart/add", data={"csrf": csrf, "product_id": product_id, "qty": "2"})
    assert added.status_code == 303
    body = client.get("/cart").text
    assert "Камера X100" in body and "2" in body

    item = client.app.state.cart_service.read(
        client.app.state.cart_service.load(1), "ru"
    ).lines[0]
    updated = client.post("/cart/update", data={"csrf": csrf, "item_id": item.item_id, "qty": "5"})
    assert updated.status_code == 303
    assert client.app.state.cart_service.read(
        client.app.state.cart_service.load(1), "ru"
    ).lines[0].quantity == 5

    assert client.post("/cart/remove", data={"csrf": csrf, "item_id": item.item_id}).status_code == 303
    assert "Корзина пуста" in client.get("/cart").text


def test_quantity_and_position_limits(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    product_id = _product_id(client)
    assert client.post("/cart/add", data={"csrf": csrf, "product_id": product_id, "qty": "100"}).status_code == 400

    catalog = client.app.state.catalog
    category = catalog.list_categories()[0]
    for index in range(51):
        catalog.create_product(slug=f"extra-{index}", category_id=category.id, price="1.00",
                               currency="MDL", texts={"ru": {"name": f"Товар {index}"}}, is_published=True)
    catalog.update_product(product_id, is_published=False)
    filled = 0
    for product in catalog.list_products(published_only=True):
        if filled >= 50:
            break
        if client.post("/cart/add", data={"csrf": csrf, "product_id": product.id, "qty": "1"}).status_code == 303:
            filled += 1
    assert filled == 50
    extra = catalog.create_product(slug="extra-overflow", category_id=category.id, price="1.00",
                                   currency="MDL", texts={"ru": {"name": "Переполнение"}}, is_published=True)
    assert client.post("/cart/add", data={"csrf": csrf, "product_id": extra.id, "qty": "1"}).status_code == 400


def test_bad_signature_is_403(tmp_path):
    client = _client(tmp_path)
    client.cookies.set("videoshop_cart", "bm90LWEtY2FydA.deadbeef")
    assert client.get("/cart").status_code == 403


def test_expired_token_creates_a_new_empty_cart(tmp_path):
    client = _client(tmp_path)
    old = int(time.time()) - CART_TTL_SECONDS - 3600
    client.cookies.set("videoshop_cart", _token(1, old))
    response = client.get("/cart")
    assert response.status_code == 200
    assert "Срок корзины истёк" in response.text
    assert "videoshop_cart" in response.cookies


def test_unavailable_product_is_marked(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    product_id = _product_id(client)
    client.post("/cart/add", data={"csrf": csrf, "product_id": product_id, "qty": "1"})
    client.app.state.catalog.update_product(product_id, is_published=False)
    body = client.get("/cart").text
    assert "Товар недоступен" in body


def test_csrf_and_methods(tmp_path):
    client = _client(tmp_path)
    product_id = _product_id(client)
    assert client.post("/cart/add", data={"product_id": product_id, "qty": "1"}).status_code == 403
    assert client.get("/cart/add").status_code == 405


def test_cart_is_shop_only(tmp_path):
    for mode in ("catalog", "visitka"):
        client = _client(tmp_path / mode, mode)
        (tmp_path / mode).mkdir(exist_ok=True)
        assert client.get("/cart").status_code == 404


def test_counter_only_in_shop(tmp_path):
    shop = _client(tmp_path / "shop")
    (tmp_path / "shop").mkdir(exist_ok=True)
    csrf = _csrf(shop)
    shop.post("/cart/add", data={"csrf": csrf, "product_id": _product_id(shop), "qty": "1"})
    home = shop.get("/").text
    assert 'class="cart"' in home and "<b>1</b>" in home
    catalog_client = _client(tmp_path / "cat", "catalog")
    (tmp_path / "cat").mkdir(exist_ok=True)
    assert 'class="cart"' not in catalog_client.get("/").text
