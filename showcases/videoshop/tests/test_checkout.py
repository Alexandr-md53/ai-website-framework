"""Block 3c-2a: checkout and order creation (shop mode)."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.config import StoreConfig

SECRET = b"checkout-secret"
PASSWORD = "co-pass"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')
TOKEN_RE = re.compile(r'name="checkout_token" value="([^"]+)"')
TOTAL_RE = re.compile(r'name="expected_total" value="(\d+)"')
NUMBER_RE = re.compile(r"VS-\d{4}-\d{6}")


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
    return CSRF_RE.search(client.get("/cart").text).group(1)


def _add(client, csrf, qty="1") -> int:
    product_id = client.app.state.catalog.list_products()[0].id
    assert client.post("/cart/add", data={"csrf": csrf, "product_id": product_id, "qty": qty}).status_code == 303
    return product_id


def _checkout_form(client) -> dict:
    body = client.get("/checkout").text
    return {
        "csrf": CSRF_RE.search(body).group(1),
        "checkout_token": TOKEN_RE.search(body).group(1),
        "expected_total": TOTAL_RE.search(body).group(1),
    }


def _buyer(name="Анна", contact="+37360000000") -> dict:
    return {"name": name, "contact": contact, "address": "", "comment": ""}


def test_checkout_creates_order_with_snapshot_and_clears_cart(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    _add(client, csrf, "2")
    form = {**_checkout_form(client), **_buyer()}
    response = client.post("/checkout", data=form)
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/checkout/success?order=")
    number = parse_qs(urlparse(location).query)["order"][0]
    assert NUMBER_RE.fullmatch(number)

    with client.app.state.catalog._provider.read_transaction() as tx:
        order = dict(tx.fetchone("SELECT * FROM orders WHERE number = ?", (number,)))
        items = [dict(r) for r in tx.fetchall("SELECT * FROM order_items WHERE order_id = ?", (order["id"],))]
        assert order["status"] == "new" and order["total_minor"] == 2 * 129900
        assert len(items) == 1
        assert items[0]["product_name"] == "Камера X100"
        assert items[0]["price_minor"] == 129900 and items[0]["quantity"] == 2
        assert items[0]["line_total_minor"] == 2 * 129900
        assert tx.scalar("SELECT COUNT(*) FROM cart_items") == 0, "the cart must be cleared"


def test_empty_cart_is_rejected(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    response = client.post("/checkout", data={"csrf": csrf, "checkout_token": "x", "name": "A", "contact": "B"})
    assert response.status_code == 400
    assert "Корзина пуста" in response.text
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 0


def test_invalid_buyer_data_keeps_cart(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    _add(client, csrf)
    form = {**_checkout_form(client), **_buyer(name="   ")}
    response = client.post("/checkout", data=form)
    assert response.status_code == 400
    assert "Укажите имя" in response.text
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 0
        assert tx.scalar("SELECT COUNT(*) FROM cart_items") == 1


def test_unavailable_position_rejects_the_whole_order(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    product_id = _add(client, csrf)
    form = {**_checkout_form(client), **_buyer()}
    client.app.state.catalog.update_product(product_id, is_published=False)
    response = client.post("/checkout", data=form)
    assert response.status_code == 400
    assert "недоступны" in response.text
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 0
        assert tx.scalar("SELECT COUNT(*) FROM cart_items") == 1, "cart must not be cleared"


def test_stale_price_is_409_and_keeps_cart(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    product_id = _add(client, csrf)
    form = {**_checkout_form(client), **_buyer()}
    client.app.state.catalog.update_product(product_id, price="999.00")
    response = client.post("/checkout", data=form)
    assert response.status_code == 409
    assert "Цены изменились" in response.text
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 0
        assert tx.scalar("SELECT COUNT(*) FROM cart_items") == 1


def test_repeat_submit_does_not_duplicate(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    _add(client, csrf)
    form = {**_checkout_form(client), **_buyer()}
    first = client.post("/checkout", data=form)
    second = client.post("/checkout", data=form)
    assert first.status_code == second.status_code == 303
    first_number = parse_qs(urlparse(first.headers["location"]).query)["order"][0]
    second_number = parse_qs(urlparse(second.headers["location"]).query)["order"][0]
    assert first_number == second_number
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 1


def test_csrf_and_methods(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    _add(client, csrf)
    form = _checkout_form(client)
    no_csrf = dict(form, **_buyer())
    no_csrf.pop("csrf")
    assert client.post("/checkout", data=no_csrf).status_code == 403
    assert client.put("/checkout", data=form).status_code == 405


def test_checkout_is_shop_only(tmp_path):
    for mode in ("catalog", "visitka"):
        (tmp_path / mode).mkdir(parents=True, exist_ok=True)
        assert _client(tmp_path / mode, mode).get("/checkout").status_code == 404


def test_numbers_are_unique(tmp_path):
    client = _client(tmp_path)
    csrf = _csrf(client)
    _add(client, csrf)
    first = client.post("/checkout", data={**_checkout_form(client), **_buyer()})
    _add(client, csrf)
    second = client.post("/checkout", data={**_checkout_form(client), **_buyer()})
    assert first.status_code == second.status_code == 303
    first_number = parse_qs(urlparse(first.headers["location"]).query)["order"][0]
    second_number = parse_qs(urlparse(second.headers["location"]).query)["order"][0]
    assert first_number != second_number
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 2
        assert tx.scalar("SELECT COUNT(DISTINCT number) FROM orders") == 2
