"""Block 3c-2a-fix: two genuinely concurrent checkouts.

Two independent clients (own cart cookies, own checkout tokens) add a product
and submit ``POST /checkout`` simultaneously behind a ``threading.Barrier``,
so the assertions describe concurrent behaviour, not sequential calls.
"""
from __future__ import annotations

import re
import threading
from urllib.parse import parse_qs, urlparse
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.config import StoreConfig

SECRET = b"concurrency-secret"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')
TOKEN_RE = re.compile(r'name="checkout_token" value="([^"]+)"')
TOTAL_RE = re.compile(r'name="expected_total" value="(\d+)"')
NUMBER_RE = re.compile(r"VS-\d{4}-\d{6}")


def _app(tmp_path):
    (tmp_path / "db").mkdir(parents=True, exist_ok=True)
    (tmp_path / "backups").mkdir(parents=True, exist_ok=True)
    return create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner", password_hash=hash_password("x", iterations=1000), secret_key=SECRET
        ),
        store_config=StoreConfig(mode="shop"),
        env={"VIDEOSHOP_SECRET_KEY": SECRET.decode()},
        seed_demo=True,
    )


def _client(app, **kwargs):
    return TestClient(app, follow_redirects=False, **kwargs)


def _csrf(client) -> str:
    return CSRF_RE.search(client.get("/cart").text).group(1)


def _add(client, product_id, qty="1") -> None:
    csrf = _csrf(client)
    assert client.post("/cart/add", data={"csrf": csrf, "product_id": product_id, "qty": qty}).status_code == 303


def _form(client, name, contact) -> dict:
    body = client.get("/checkout").text
    return {
        "csrf": CSRF_RE.search(body).group(1),
        "checkout_token": TOKEN_RE.search(body).group(1),
        "expected_total": TOTAL_RE.search(body).group(1),
        "name": name,
        "contact": contact,
        "address": "",
        "comment": "",
    }


def test_two_concurrent_checkouts_create_two_distinct_orders(tmp_path):
    app = _app(tmp_path)
    first_client = _client(app)
    second_client = _client(app)
    product = app.state.catalog.list_products()[0]
    _add(first_client, product.id)
    _add(second_client, product.id)

    first_form = _form(first_client, "Анна", "+37360000001")
    second_form = _form(second_client, "Ion", "+37360000002")
    assert first_form["checkout_token"] != second_form["checkout_token"], "tokens must be per session"
    assert first_client.cookies.get("videoshop_cart") != second_client.cookies.get("videoshop_cart")

    barrier = threading.Barrier(2, timeout=15)
    reached = []
    lock = threading.Lock()

    def worker(client, form):
        barrier.wait()
        with lock:
            reached.append(threading.get_ident())
        return client.post("/checkout", data=form)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, first_client, first_form), pool.submit(worker, second_client, second_form)]
        results = [future.result(timeout=60) for future in futures]

    # 1. both requests were in flight simultaneously (both passed the barrier)
    assert len(reached) == 2 and len(set(reached)) == 2

    # 2. two different, well-formed order numbers
    assert [r.status_code for r in results] == [303, 303]
    numbers = [parse_qs(urlparse(r.headers["location"]).query)["order"][0] for r in results]
    assert numbers[0] != numbers[1]
    assert all(NUMBER_RE.fullmatch(number) for number in numbers)

    with app.state.catalog._provider.read_transaction() as tx:
        for number in numbers:
            # 3. the order exists in the database, not only in the response
            order = tx.fetchone("SELECT * FROM orders WHERE number = ?", (number,))
            assert order is not None, number
            # 4. the full snapshot is stored for that order
            items = [dict(row) for row in tx.fetchall(
                "SELECT * FROM order_items WHERE order_id = ?", (order["id"],))]
            assert len(items) == 1
            item = items[0]
            assert item["product_name"] == product.text("ru").name
            assert item["product_slug"] == product.slug
            assert item["price_minor"] == product.price.minor
            assert item["currency"] == product.price.currency
            assert item["quantity"] == 1
            assert item["line_total_minor"] == product.price.minor
            assert order["total_minor"] == product.price.minor
            assert order["status"] == "new"
        # 5. no orphaned items and both carts were cleared
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 2
        assert tx.scalar("SELECT COUNT(DISTINCT number) FROM orders") == 2
        assert tx.scalar(
            "SELECT COUNT(*) FROM order_items WHERE order_id NOT IN (SELECT id FROM orders)"
        ) == 0
        assert tx.scalar("SELECT COUNT(*) FROM cart_items") == 0


def test_failed_checkout_does_not_leave_partial_rows(tmp_path):
    """A failure inside the transaction rolls back the order and its items."""
    app = _app(tmp_path)
    good_client = _client(app, raise_server_exceptions=False)
    fail_client = _client(app, raise_server_exceptions=False)
    product = app.state.catalog.list_products()[0]
    _add(good_client, product.id)
    _add(fail_client, product.id)

    good_form = _form(good_client, "Анна", "+37360000001")
    fail_form = _form(fail_client, "Пётр", "+37360000002")

    original_write = app.state.order_service._write

    def failing_write(tx, *args):
        # args: cart_id, name_text, contact_text, address_text, comment_text,
        #       source_lang, token_hash, access_hash, currency, total_minor, lines
        cart_id, name_text, contact_text = args[0], args[1], args[2]
        token_hash, access_hash = args[6], args[7]
        currency, total_minor = args[8], args[9]
        if name_text == "Пётр":
            # write a row *inside* the transaction and then fail: the transaction
            # must roll back, leaving neither the order nor its items behind
            tx.execute(
                "INSERT INTO orders (number, name, contact, address, comment, source_lang, "
                "currency, total_minor, status, checkout_token_hash, access_token_hash, "
                "created_at, updated_at) VALUES "
                "('VS-1900-999999', ?, ?, '', '', '', ?, ?, 'new', ?, ?, ?, ?)",
                (name_text, contact_text, currency, total_minor, token_hash, access_hash,
                 "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
            )
            raise RuntimeError("simulated failure after the order insert")
        return original_write(tx, *args)

    app.state.order_service._write = failing_write

    barrier = threading.Barrier(2, timeout=15)

    def worker(client, form):
        barrier.wait()
        return client.post("/checkout", data=form)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, good_client, good_form), pool.submit(worker, fail_client, fail_form)]
        results = [future.result(timeout=60) for future in futures]

    statuses = sorted(r.status_code for r in results)
    assert statuses == [303, 500], statuses

    with app.state.catalog._provider.read_transaction() as tx:
        # the rolled-back transaction left no rows at all
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 1
        assert tx.scalar("SELECT COUNT(*) FROM order_items") == 1
        assert tx.scalar("SELECT COUNT(*) FROM orders WHERE number = 'VS-1900-999999'") == 0
        assert tx.scalar(
            "SELECT COUNT(*) FROM order_items WHERE order_id NOT IN (SELECT id FROM orders)"
        ) == 0
        # the successful order belongs to the client that did not fail
        order = tx.fetchone("SELECT * FROM orders")
        assert order["name"] == "Анна"
        # the failed client still has its cart (nothing was cleared)
        assert tx.scalar("SELECT COUNT(*) FROM cart_items") == 1
