"""Block 3c-1: cart token TTL — 30 days, no auto-renewal (decision 3)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.services.cart import CART_TTL_SECONDS
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.config import StoreConfig

SECRET = b"ttl-secret"


def _client(tmp_path):
    (tmp_path / "db").mkdir(parents=True, exist_ok=True)
    (tmp_path / "backups").mkdir(parents=True, exist_ok=True)
    app = create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner", password_hash=hash_password("x", iterations=1000), secret_key=SECRET
        ),
        store_config=StoreConfig(mode="shop"),
        env={"VIDEOSHOP_SECRET_KEY": SECRET.decode()},
    )
    return TestClient(app, follow_redirects=False)


def _token(cart_id: int, issued_at: int) -> str:
    payload = f"{cart_id}:{issued_at}".encode("ascii")
    body = base64.urlsafe_b64encode(payload).decode("ascii")
    mac = hmac.new(SECRET, body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{mac}"


def _issued(cookie: str) -> int:
    body = cookie.split(".", 1)[0]
    return int(base64.urlsafe_b64decode(body.encode("ascii")).decode("ascii").split(":", 1)[1])


def test_cookie_is_not_renewed_on_a_normal_read(tmp_path):
    client = _client(tmp_path)
    first = client.get("/cart")
    cookie = first.cookies.get("videoshop_cart")
    assert cookie, "a new cart must issue a cookie"
    issued = _issued(cookie)

    second = client.get("/cart")
    assert "videoshop_cart" not in second.cookies, "a valid token must not be re-issued"
    assert client.cookies.get("videoshop_cart") == cookie
    assert _issued(client.cookies.get("videoshop_cart")) == issued


def test_token_is_still_valid_one_day_before_expiry(tmp_path):
    client = _client(tmp_path)
    client.get("/cart")  # creates cart #1
    issued = int(time.time()) - CART_TTL_SECONDS + 86400
    client.cookies.set("videoshop_cart", _token(1, issued))
    response = client.get("/cart")
    assert response.status_code == 200
    assert "Срок корзины истёк" not in response.text
    assert "videoshop_cart" not in response.cookies


def test_token_expires_after_thirty_days(tmp_path):
    client = _client(tmp_path)
    client.get("/cart")
    issued = int(time.time()) - CART_TTL_SECONDS - 86400
    client.cookies.set("videoshop_cart", _token(1, issued))
    response = client.get("/cart")
    assert response.status_code == 200
    assert "Срок корзины истёк" in response.text
    assert "videoshop_cart" in response.cookies, "an expired cart must issue a new cookie"
    assert _issued(response.cookies["videoshop_cart"]) > issued
