"""Block 3a-fix: localized request errors, admin date header, migration 5->6, shop mode."""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.infrastructure.image_store import ImageStore
from showcases.videoshop.infrastructure.migrations.catalog import (
    CATALOG_MIGRATIONS,
    CATALOG_VERSION,
    migrate_catalog,
)
from showcases.videoshop.infrastructure.migrations.runner import migrate
from showcases.videoshop.infrastructure.retry import run_transaction_with_retry
from showcases.videoshop.infrastructure.slug_registry import SlugRegistry
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.services.catalog import CatalogService
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.config import StoreConfig
from showcases.videoshop.web.i18n import UI

PASSWORD = "fix-pass"
TOKEN_RE = re.compile(r'name="csrf" value="([^"]+)"')


def _app(tmp_path, mode=None):
    (tmp_path / "db").mkdir(exist_ok=True)
    (tmp_path / "backups").mkdir(exist_ok=True)
    return create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(username="owner", password_hash=hash_password(PASSWORD, iterations=1000), secret_key=b"fix"),
        store_config=StoreConfig(mode=mode) if mode else None,
    )


def _token(html: str) -> str:
    match = TOKEN_RE.search(html)
    return match.group(1) if match else ""


def test_empty_name_shows_localized_error(tmp_path):
    client = TestClient(_app(tmp_path, "visitka"), follow_redirects=False)
    token = _token(client.get("/").text)
    response = client.post("/request", data={"csrf": token, "name": "   ", "contact": "+373"})
    assert response.status_code == 400
    assert UI["ru"]["request_err_name_required"] in response.text


def test_long_contact_shows_localized_error(tmp_path):
    client = TestClient(_app(tmp_path, "visitka"), follow_redirects=False)
    token = _token(client.get("/").text)
    response = client.post(
        "/request", data={"csrf": token, "name": "Анна", "contact": "x" * 201}
    )
    assert response.status_code == 400
    assert UI["ru"]["request_err_contact_long"] in response.text


def test_admin_requests_has_localized_date_header(tmp_path):
    client = TestClient(_app(tmp_path, "visitka"), follow_redirects=False)
    client.post("/admin/login", data={"username": "owner", "password": PASSWORD})
    listing = client.get("/admin/requests").text
    assert UI["ru"]["admin"]["requests_created_at"] in listing
    assert UI["en"]["admin"]["requests_created_at"] == "Date"


def test_migration_5_to_6_keeps_data_and_is_idempotent(tmp_path):
    """Block 3b-1: a v5 database migrates to the current version without loss."""
    db = tmp_path / "db"
    db.mkdir()
    provider = VideoShopSQLiteProvider(db_path=str(db / "shop.sqlite"))
    steps_to_five = tuple(m for m in CATALOG_MIGRATIONS if m.version <= 5)
    assert migrate(provider, steps_to_five) == 5

    stamp = "2026-01-01T00:00:00+00:00"

    def seed(tx):
        tx.execute(
            "INSERT INTO categories (is_published, position, image, created_at, updated_at) "
            "VALUES (1, 0, '', ?, ?)",
            (stamp, stamp),
        )
        tx.execute(
            "INSERT INTO category_texts (category_id, lang, name, description) "
            "VALUES (1, 'ru', 'Старая категория', '')"
        )
        tx.execute(
            "INSERT INTO products (category_id, price_minor, currency, is_published, position, "
            "created_at, updated_at) VALUES (1, 1000, 'MDL', 1, 0, ?, ?)",
            (stamp, stamp),
        )
        tx.execute(
            "INSERT INTO product_texts (product_id, lang, name, description) "
            "VALUES (1, 'ru', 'Старый товар', '')"
        )
        tx.execute(
            "INSERT INTO product_attributes (product_id, position, name, value) "
            "VALUES (1, 0, 'Сенсор', 'APS-C')"
        )

    run_transaction_with_retry(provider, seed)

    assert migrate_catalog(provider) == CATALOG_VERSION
    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA user_version") == CATALOG_VERSION
        assert tx.scalar("SELECT COUNT(*) FROM requests") == 0
        assert tx.scalar("SELECT lang FROM product_attributes") == ""
        assert tx.scalar("SELECT name FROM category_texts") == "Старая категория"
        assert tx.scalar("SELECT name FROM product_texts") == "Старый товар"

    # idempotent: a second run changes nothing
    assert migrate_catalog(provider) == CATALOG_VERSION
    with provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM product_attributes") == 1


def test_shop_mode_has_catalogue_and_cart_flag(tmp_path):
    config = StoreConfig(mode="shop")
    assert config.cart is True
    assert config.public_catalog is True
    assert config.product_page is True
    assert config.request_form is False

    client = TestClient(_app(tmp_path, "shop"), follow_redirects=False)
    assert client.get("/catalog").status_code == 200
    assert client.get("/request", follow_redirects=False) is not None
    assert client.post("/request", data={}).status_code == 404
