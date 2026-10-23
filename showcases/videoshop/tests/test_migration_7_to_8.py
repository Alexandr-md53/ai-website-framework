"""Block 3c-1: migration 7 -> 8 (cart/order tables) keeps data and is idempotent."""
from __future__ import annotations

from showcases.videoshop.infrastructure.migrations.catalog import (
    CATALOG_MIGRATIONS,
    CATALOG_VERSION,
    migrate_catalog,
)
from showcases.videoshop.infrastructure.migrations.runner import migrate
from showcases.videoshop.infrastructure.retry import run_transaction_with_retry
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider

STAMP = "2026-01-01T00:00:00+00:00"


def _seed_v7(tx):
    tx.execute(
        "INSERT INTO categories (is_published, position, image, created_at, updated_at) "
        "VALUES (1, 0, '', ?, ?)",
        (STAMP, STAMP),
    )
    tx.execute(
        "INSERT INTO category_texts (category_id, lang, name, description) "
        "VALUES (1, 'ru', 'Категория', '')"
    )
    tx.execute(
        "INSERT INTO products (category_id, price_minor, currency, is_published, position, "
        "created_at, updated_at) VALUES (1, 1000, 'MDL', 1, 0, ?, ?)",
        (STAMP, STAMP),
    )
    tx.execute(
        "INSERT INTO product_texts (product_id, lang, name, description) "
        "VALUES (1, 'ru', 'Товар', '')"
    )
    tx.execute(
        "INSERT INTO product_attributes (product_id, position, lang, name, value) "
        "VALUES (1, 0, 'ru', 'Сенсор', 'APS-C')"
    )
    tx.execute(
        "INSERT INTO requests (name, contact, message, source_lang, state, created_at, updated_at) "
        "VALUES ('Анна', '+373', 'Текст', 'ru', 'new', ?, ?)",
        (STAMP, STAMP),
    )


def test_migration_7_to_8_keeps_data_and_is_idempotent(tmp_path):
    db = tmp_path / "db"
    db.mkdir()
    provider = VideoShopSQLiteProvider(db_path=str(db / "shop.sqlite"))
    steps_to_seven = tuple(m for m in CATALOG_MIGRATIONS if m.version <= 7)
    assert migrate(provider, steps_to_seven) == 7

    run_transaction_with_retry(provider, _seed_v7)

    assert migrate_catalog(provider) == CATALOG_VERSION == 8
    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA user_version") == 8
        names = {
            row["name"]
            for row in tx.fetchall("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert {"carts", "cart_items", "orders", "order_items"} <= names
        # old data survived
        assert tx.scalar("SELECT name FROM category_texts") == "Категория"
        assert tx.scalar("SELECT name FROM product_texts") == "Товар"
        assert tx.scalar("SELECT value FROM product_attributes") == "APS-C"
        assert tx.scalar("SELECT lang FROM product_attributes") == "ru"
        assert tx.scalar("SELECT name FROM requests") == "Анна"
        # new tables are empty
        assert tx.scalar("SELECT COUNT(*) FROM carts") == 0
        assert tx.scalar("SELECT COUNT(*) FROM orders") == 0
        assert tx.scalar("SELECT COUNT(*) FROM order_items") == 0

    # idempotent: a second run changes nothing and duplicates no rows
    assert migrate_catalog(provider) == 8
    with provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM product_attributes") == 1
        assert tx.scalar("SELECT COUNT(*) FROM requests") == 1
        assert tx.scalar("SELECT COUNT(*) FROM carts") == 0


def test_fresh_database_reaches_version_8(tmp_path):
    db = tmp_path / "db"
    db.mkdir()
    provider = VideoShopSQLiteProvider(db_path=str(db / "shop.sqlite"))
    assert migrate_catalog(provider) == 8
    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA user_version") == 8
