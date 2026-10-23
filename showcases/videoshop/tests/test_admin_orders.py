"""Block 3c-3: admin orders (list, detail, status transitions, dashboard counter)."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.config import StoreConfig

SECRET = b"admin-orders-secret"
PASSWORD = "orders-pass"
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


def _place_order(client, name="Анна"):
    csrf = CSRF_RE.search(client.get("/cart").text).group(1)
    product = client.app.state.catalog.list_products()[0]
    client.post("/cart/add", data={"csrf": csrf, "product_id": product.id, "qty": "1"})
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
    return query["order"][0], query["token"][0], product


def _admin(client) -> str:
    assert client.post("/admin/login", data={"username": "owner", "password": PASSWORD}).status_code == 303
    return CSRF_RE.search(client.get("/admin").text).group(1)


def test_list_orders_newest_first_and_filter(tmp_path):
    client = _client(tmp_path)
    first, _, _ = _place_order(client, "Первый")
    second, _, _ = _place_order(client, "Второй")
    csrf = _admin(client)

    listing = client.get("/admin/orders").text
    assert first in listing and second in listing
    assert listing.index(second) < listing.index(first), "newest first"

    assert client.post(f"/admin/orders/{first}/status", data={"csrf": csrf, "status": "confirmed"}).status_code == 303
    confirmed = client.get("/admin/orders?status=confirmed").text
    assert first in confirmed and second not in confirmed
    new_only = client.get("/admin/orders?status=new").text
    assert second in new_only and first not in new_only
    assert client.get("/admin/orders?status=bogus").status_code == 200


def test_detail_uses_the_snapshot(tmp_path):
    client = _client(tmp_path)
    number, _, product = _place_order(client)
    _admin(client)
    old_price = str(product.price.minor)
    client.app.state.catalog.update_product(product.id, price="999.00")
    page = client.get(f"/admin/orders/{number}").text
    assert number in page and old_price in page
    assert "99900" not in page


def test_allowed_transitions_are_applied(tmp_path):
    client = _client(tmp_path)
    number, _, _ = _place_order(client)
    csrf = _admin(client)
    for target in ("confirmed", "done"):
        response = client.post(f"/admin/orders/{number}/status", data={"csrf": csrf, "status": target})
        assert response.status_code == 303, target
        with client.app.state.catalog._provider.read_transaction() as tx:
            assert tx.scalar("SELECT status FROM orders WHERE number = ?", (number,)) == target


def test_forbidden_transitions_are_400_and_change_nothing(tmp_path):
    client = _client(tmp_path)
    number, _, _ = _place_order(client)
    csrf = _admin(client)
    assert client.post(f"/admin/orders/{number}/status", data={"csrf": csrf, "status": "done"}).status_code == 400
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT status FROM orders WHERE number = ?", (number,)) == "new"
    assert client.post(f"/admin/orders/{number}/status", data={"csrf": csrf, "status": "cancelled"}).status_code == 303
    assert client.post(f"/admin/orders/{number}/status", data={"csrf": csrf, "status": "confirmed"}).status_code == 400
    detail = client.get(f"/admin/orders/{number}").text
    assert "Отменён" in detail


def test_session_and_csrf_are_required(tmp_path):
    client = _client(tmp_path)
    number, _, _ = _place_order(client)
    # no session: pages redirect to the login form, mutating calls are 401
    assert client.get("/admin/orders").status_code in (303, 401)
    assert client.post(f"/admin/orders/{number}/status", data={"status": "confirmed"}).status_code in (401, 403)

    csrf = _admin(client)
    assert client.post(f"/admin/orders/{number}/status", data={"status": "confirmed"}).status_code == 403
    assert client.post(
        f"/admin/orders/{number}/status", data={"csrf": "bad", "status": "confirmed"}
    ).status_code == 403


def test_dashboard_counter(tmp_path):
    client = _client(tmp_path)
    _place_order(client, "A")
    _place_order(client, "B")
    _admin(client)
    page = client.get("/admin").text
    assert "Новых заказов" in page and "2" in page
    assert 'href="/admin/orders?status=new"' in page


def test_orders_admin_is_shop_only(tmp_path):
    for mode in ("catalog", "visitka"):
        (tmp_path / mode).mkdir(parents=True, exist_ok=True)
        client = _client(tmp_path / mode, mode)
        assert client.get("/admin/orders").status_code == 404


def test_unknown_number_is_404_and_get_does_not_change(tmp_path):
    client = _client(tmp_path)
    number, _, _ = _place_order(client)
    csrf = _admin(client)
    assert client.get("/admin/orders/VS-1999-000001").status_code == 404
    assert client.post("/admin/orders/VS-1999-000001/status", data={"csrf": csrf, "status": "confirmed"}).status_code == 404
    before = client.get(f"/admin/orders/{number}").text
    after = client.get(f"/admin/orders/{number}").text
    assert before == after
    assert "Новый" in after


def test_new_to_cancelled(tmp_path):
    """new -> cancelled is allowed; the page shows it and GET never mutates."""
    client = _client(tmp_path)
    number, _, _ = _place_order(client, "Отмена")
    csrf = _admin(client)

    response = client.post(f"/admin/orders/{number}/status", data={"csrf": csrf, "status": "cancelled"})
    assert response.status_code == 303
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT status FROM orders WHERE number = ?", (number,)) == "cancelled"

    detail = client.get(f"/admin/orders/{number}").text
    assert "Отменён" in detail
    # GET is not a mutation: two more reads keep the status unchanged
    again = client.get(f"/admin/orders/{number}").text
    assert again == detail
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT status FROM orders WHERE number = ?", (number,)) == "cancelled"


def test_confirmed_to_cancelled(tmp_path):
    """confirmed -> cancelled is allowed."""
    client = _client(tmp_path)
    number, _, _ = _place_order(client, "Отмена после подтверждения")
    csrf = _admin(client)

    assert client.post(
        f"/admin/orders/{number}/status", data={"csrf": csrf, "status": "confirmed"}
    ).status_code == 303
    response = client.post(f"/admin/orders/{number}/status", data={"csrf": csrf, "status": "cancelled"})
    assert response.status_code == 303
    with client.app.state.catalog._provider.read_transaction() as tx:
        assert tx.scalar("SELECT status FROM orders WHERE number = ?", (number,)) == "cancelled"
    assert "Отменён" in client.get(f"/admin/orders/{number}").text
