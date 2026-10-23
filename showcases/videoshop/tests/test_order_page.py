"""Block 3c-2b: public order page /order/{number}?token=... (shop only)."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.config import StoreConfig

SECRET = b"order-page-secret"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')
TOKEN_RE = re.compile(r'name="checkout_token" value="([^"]+)"')
TOTAL_RE = re.compile(r'name="expected_total" value="(\d+)"')
TOKEN_SHAPE = re.compile(r"^[A-Za-z0-9_-]{43}$")


def _app(tmp_path, mode="shop"):
    (tmp_path / "db").mkdir(parents=True, exist_ok=True)
    (tmp_path / "backups").mkdir(parents=True, exist_ok=True)
    return create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner", password_hash=hash_password("x", iterations=1000), secret_key=SECRET
        ),
        store_config=StoreConfig(mode=mode),
        env={"VIDEOSHOP_SECRET_KEY": SECRET.decode()},
        seed_demo=True,
    )


def _client(tmp_path, mode="shop"):
    return TestClient(_app(tmp_path, mode), follow_redirects=False)


def _place_order(client, name="Анна"):
    csrf = CSRF_RE.search(client.get("/cart").text).group(1)
    product = client.app.state.catalog.list_products()[0]
    assert client.post("/cart/add", data={"csrf": csrf, "product_id": product.id, "qty": "1"}).status_code == 303
    body = client.get("/checkout").text
    form = {
        "csrf": CSRF_RE.search(body).group(1),
        "checkout_token": TOKEN_RE.search(body).group(1),
        "expected_total": TOTAL_RE.search(body).group(1),
        "name": name, "contact": "+373", "address": "", "comment": "",
    }
    response = client.post("/checkout", data=form)
    assert response.status_code == 303
    query = parse_qs(urlparse(response.headers["location"]).query)
    return query["order"][0], query.get("token", [""])[0], product


def _order_url(number, token):
    return f"/order/{number}?token={token}" if token else f"/order/{number}"


def test_valid_token_shows_that_order(tmp_path):
    client = _client(tmp_path)
    number, token, product = _place_order(client)
    page = client.get(_order_url(number, token))
    assert page.status_code == 200
    assert number in page.text
    assert product.text("ru").name in page.text
    assert str(product.price.minor) in page.text


def test_wrong_missing_and_foreign_tokens_are_404(tmp_path):
    first = _client(tmp_path)
    number_a, token_a, _ = _place_order(first, "Анна")
    # a second order in the same shop (new cart session)
    second = TestClient(first.app, follow_redirects=False)
    number_b, token_b, _ = _place_order(second, "Ion")

    # 2. wrong token
    assert first.get(_order_url(number_a, token_a + "x")).status_code == 404
    # 3. no token
    assert first.get(_order_url(number_a, "")).status_code == 404
    # 4. unknown number
    assert first.get(_order_url("VS-1999-000001", token_a)).status_code == 404
    # 5. known number, no token
    assert first.get(_order_url(number_a, "")).status_code == 404
    # 6. token A on order B
    assert first.get(_order_url(number_b, token_a)).status_code == 404


def test_all_failures_return_the_same_404_body(tmp_path):
    client = _client(tmp_path)
    number, token, _ = _place_order(client)
    variants = [
        _order_url(number, ""),
        _order_url(number, "bogus"),
        _order_url("VS-1999-000001", token),
    ]
    bodies = [client.get(url) for url in variants]
    assert all(response.status_code == 404 for response in bodies)
    assert len({response.text for response in bodies}) == 1, "404 responses must be identical"


def test_order_page_is_shop_only(tmp_path):
    for mode in ("catalog", "visitka"):
        (tmp_path / mode).mkdir(parents=True, exist_ok=True)
        assert _client(tmp_path / mode, mode).get("/order/VS-2026-000001?token=x").status_code == 404


def test_only_the_hash_is_stored_and_the_token_is_random(tmp_path):
    client = _client(tmp_path)
    number, token, _ = _place_order(client)
    assert TOKEN_SHAPE.fullmatch(token), token
    with client.app.state.catalog._provider.read_transaction() as tx:
        stored = tx.scalar("SELECT access_token_hash FROM orders WHERE number = ?", (number,))
    assert stored != token
    assert stored == hashlib.sha256(token.encode("utf-8")).hexdigest()

    second_number, second_token, _ = _place_order(TestClient(client.app, follow_redirects=False), "Ion")
    assert second_token != token


def test_repeat_checkout_keeps_the_first_token_valid(tmp_path):
    client = _client(tmp_path)
    csrf = CSRF_RE.search(client.get("/cart").text).group(1)
    product = client.app.state.catalog.list_products()[0]
    client.post("/cart/add", data={"csrf": csrf, "product_id": product.id, "qty": "1"})
    body = client.get("/checkout").text
    form = {"csrf": CSRF_RE.search(body).group(1), "checkout_token": TOKEN_RE.search(body).group(1),
            "expected_total": TOTAL_RE.search(body).group(1), "name": "Анна", "contact": "+373",
            "address": "", "comment": ""}
    first = client.post("/checkout", data=form)
    second = client.post("/checkout", data=form)
    first_query = parse_qs(urlparse(first.headers["location"]).query)
    second_query = parse_qs(urlparse(second.headers["location"]).query)
    assert first_query["order"] == second_query["order"]
    assert "token" in first_query and "token" not in second_query
    assert client.get(_order_url(first_query["order"][0], first_query["token"][0])).status_code == 200
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 1


def test_order_page_uses_the_snapshot_after_catalog_changes(tmp_path):
    client = _client(tmp_path)
    number, token, product = _place_order(client)
    client.app.state.catalog.update_product(product.id, price="999.00")
    page = client.get(_order_url(number, token))
    assert page.status_code == 200
    assert "999.00" not in page.text.replace("99900", "")
    assert product.text("ru").name in page.text


def test_order_page_is_localized(tmp_path):
    client = _client(tmp_path)
    number, token, _ = _place_order(client)
    for lang, word in (("ru", "Заказ"), ("ro", "Comandă"), ("en", "Order")):
        page = client.get(_order_url(number, token) + f"&lang={lang}")
        assert page.status_code == 200
        assert word in page.text
