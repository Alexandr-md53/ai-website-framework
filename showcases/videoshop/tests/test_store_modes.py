"""Block 3a: store modes (visitka / catalog / shop) and the request form.

The contract keeps ``catalog`` as the default, so every pre-existing test must
keep passing unchanged; this module only adds coverage for the new mode layer.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.services.catalog import CatalogService
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.config import (
    StoreConfig,
    StoreConfigConflict,
    UnknownStoreMode,
)
from showcases.videoshop.web.i18n import UI

PASSWORD = "store-modes-pass"
TOKEN_RE = re.compile(r'name="csrf" value="([^"]+)"')


def _app(tmp_path, mode=None, seed=True):
    (tmp_path / "db").mkdir(exist_ok=True)
    (tmp_path / "backups").mkdir(exist_ok=True)
    return create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner", password_hash=hash_password(PASSWORD, iterations=1000), secret_key=b"3a"
        ),
        store_config=StoreConfig(mode=mode) if mode else None,
        seed_demo=seed,
    )


def _client(tmp_path, mode=None):
    return TestClient(_app(tmp_path, mode), follow_redirects=False)


def _token(html: str) -> str:
    match = TOKEN_RE.search(html)
    return match.group(1) if match else ""


def _login(client) -> None:
    assert client.post("/admin/login", data={"username": "owner", "password": PASSWORD}).status_code == 303


# --- configuration -------------------------------------------------------


def test_default_mode_is_catalog_and_preserves_behaviour(tmp_path):
    config = StoreConfig()
    assert config.mode == "catalog"
    assert config.public_catalog is True and config.request_form is False

    client = _client(tmp_path)
    assert client.get("/catalog").status_code == 200
    assert client.get("/product/demo-camera-x100").status_code == 200
    # the request form is not part of a catalogue shop
    assert client.post("/request", data={}).status_code == 404


def test_unknown_mode_and_conflicting_overrides_are_typed_errors():
    with pytest.raises(UnknownStoreMode):
        StoreConfig(mode="foo")
    with pytest.raises(StoreConfigConflict):
        StoreConfig(mode="visitka", enable_public_catalog=True)
    with pytest.raises(StoreConfigConflict):
        StoreConfig(mode="visitka", enable_cart=True)


def test_mode_feature_matrix():
    visitka = StoreConfig(mode="visitka").to_flags()
    catalog = StoreConfig(mode="catalog").to_flags()
    shop = StoreConfig(mode="shop").to_flags()
    assert visitka["public_catalog"] is False and visitka["request_form"] is True
    assert catalog["public_catalog"] is True and catalog["cart"] is False
    assert shop["cart"] is True and shop["public_catalog"] is True
    assert visitka["admin_products"] is True and visitka["admin_pages"] is True


# --- visitka -------------------------------------------------------------


def test_visitka_hides_public_catalogue_but_keeps_the_admin(tmp_path):
    client = _client(tmp_path, "visitka")
    assert client.get("/catalog").status_code == 404
    assert client.get("/product/demo-camera-x100").status_code == 404
    home = client.get("/").text
    assert 'href="/catalog' not in home
    assert 'id="request"' in home

    _login(client)
    assert client.get("/admin/products").status_code == 200
    assert client.get("/admin/categories").status_code == 200
    assert client.get("/admin/requests").status_code == 200


def test_request_is_stored_from_home_and_from_contacts(tmp_path):
    client = _client(tmp_path, "visitka")
    home = client.get("/").text
    response = client.post(
        "/request?lang=ru",
        data={"csrf": _token(home), "name": "Анна", "contact": "+37360000000", "message": "Нужна камера"},
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/?sent=1"

    contacts = client.get("/page/contacts")
    assert contacts.status_code == 200
    assert 'id="request"' in contacts.text
    second = client.post(
        "/request?lang=ro",
        data={"csrf": _token(contacts.text), "name": "Ion", "contact": "ion@example.com"},
    )
    assert second.status_code == 303
    assert second.headers["location"] == "/?sent=1"

    _login(client)
    listing = client.get("/admin/requests").text
    assert "Анна" in listing and "Ion" in listing


def test_prg_confirmation_and_no_duplicate_on_repeat(tmp_path):
    client = _client(tmp_path, "visitka")
    home = client.get("/").text
    client.post("/request", data={"csrf": _token(home), "name": "PRG", "contact": "x"})
    _login(client)
    before = client.get("/admin/requests").text.count("PRG")
    for _ in range(3):
        page = client.get("/?sent=1")
        assert page.status_code == 200
        assert UI["ru"]["request_ok"] in page.text
    client.post("/admin/logout")
    after = _client(tmp_path, "visitka").get("/admin/requests")
    assert after.status_code == 303  # admin link still protected
    _login(client)
    assert client.get("/admin/requests").text.count("PRG") == before


def test_request_validation_csrf_honeypot_and_rate_limit(tmp_path):
    client = _client(tmp_path, "visitka")
    home = client.get("/").text
    token = _token(home)

    # no CSRF token -> 403
    assert client.post("/request", data={"name": "x", "contact": "y"}).status_code == 403
    # honeypot filled -> 400, nothing stored
    assert client.post(
        "/request", data={"csrf": token, "name": "x", "contact": "y", "company": "bot"}
    ).status_code == 400
    # too many submissions within the window -> 429
    codes = [client.post("/request", data={"csrf": token, "name": "x", "contact": "y"}).status_code for _ in range(5)]
    assert 429 in codes


def test_storage_failure_returns_500_without_success(tmp_path, monkeypatch):
    client = _client(tmp_path, "visitka")
    token = _token(client.get("/").text)

    def boom(self, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(CatalogService, "add_request", boom)
    response = client.post(
        "/request", data={"csrf": token, "name": "z", "contact": "w"}, follow_redirects=False
    )
    assert response.status_code == 500
    assert "sent=1" not in response.headers.get("location", "")
    assert UI["ru"]["request_error"] in response.text


# --- catalogue / i18n ----------------------------------------------------


def test_subscription_is_disabled_in_visitka(tmp_path):
    client = _client(tmp_path, "visitka")
    assert client.post("/subscribe", data={"email": "a@b.co"}).status_code == 404


def test_i18n_key_sets_match_in_all_languages():
    def keys(lang):
        return {key for key, value in UI[lang].items() if isinstance(value, str)}

    def admin_keys(lang):
        return set(UI[lang]["admin"])

    assert keys("ru") == keys("ro") == keys("en")
    assert admin_keys("ru") == admin_keys("ro") == admin_keys("en")
    for lang in ("ru", "ro", "en"):
        for key in ("request_title", "request_hint", "request_name", "request_contact",
                    "request_message", "request_send", "request_ok", "request_error"):
            assert UI[lang][key], (lang, key)
