"""Stage 1: migration v9 (publications_core) on a synthetic v8 database."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from showcases.videoshop.infrastructure.migrations.catalog import (
    CATALOG_MIGRATIONS,
    CATALOG_VERSION,
    migrate_catalog,
)
from showcases.videoshop.infrastructure.migrations.runner import (
    UnsupportedSchemaVersion,
    migrate,
)
from showcases.videoshop.infrastructure.retry import run_transaction_with_retry
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider

STAMP = "2026-01-01T00:00:00+00:00"

PUBLICATION_TABLES = {
    "publish_channels",
    "publications",
    "publication_texts",
    "publication_jobs",
    "publication_events",
    "publication_dedup",
}
PUBLICATION_INDEXES = {
    "ix_publish_channels_active",
    "ix_publications_status",
    "ix_publication_jobs_due",
    "ix_publication_jobs_channel",
    "ix_publication_events_job",
}


def _provider(tmp_path) -> VideoShopSQLiteProvider:
    db = tmp_path / "db"
    db.mkdir()
    return VideoShopSQLiteProvider(db_path=str(db / "shop.sqlite"))


def _to_v8(provider) -> int:
    steps = tuple(step for step in CATALOG_MIGRATIONS if step.version <= 8)
    return migrate(provider, steps)


def _seed(tx) -> None:
    tx.execute(
        "INSERT INTO categories (is_published, position, image, created_at, updated_at)"
        " VALUES (1, 0, '', ?, ?)",
        (STAMP, STAMP),
    )
    tx.execute(
        "INSERT INTO category_texts (category_id, lang, name, description)"
        " VALUES (1, 'ru', 'Категория', '')"
    )
    tx.execute(
        "INSERT INTO products (category_id, price_minor, currency, is_published,"
        " position, created_at, updated_at) VALUES (1, 1000, 'MDL', 1, 0, ?, ?)",
        (STAMP, STAMP),
    )
    tx.execute(
        "INSERT INTO product_texts (product_id, lang, name, description)"
        " VALUES (1, 'ru', 'Товар', '')"
    )
    tx.execute(
        "INSERT INTO product_attributes (product_id, position, lang, name, value)"
        " VALUES (1, 0, 'ru', 'Сенсор', 'APS-C')"
    )
    tx.execute(
        "INSERT INTO pages (is_published, position, created_at, updated_at)"
        " VALUES (1, 0, ?, ?)",
        (STAMP, STAMP),
    )
    tx.execute(
        "INSERT INTO page_texts (page_id, lang, title, body) VALUES (1, 'ru', 'О нас', '')"
    )
    tx.execute(
        "INSERT INTO requests (name, contact, message, source_lang, state,"
        " created_at, updated_at) VALUES ('Анна', '+373', 'Текст', 'ru', 'new', ?, ?)",
        (STAMP, STAMP),
    )


def _objects(provider) -> set[str]:
    with provider.read_transaction() as tx:
        rows = tx.fetchall(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index')"
        )
    return {row["name"] for row in rows}


def test_v9_creates_publication_tables(tmp_path):
    provider = _provider(tmp_path)
    assert _to_v8(provider) == 8

    assert migrate_catalog(provider) == CATALOG_VERSION == 9

    objects = _objects(provider)
    assert PUBLICATION_TABLES <= objects
    assert PUBLICATION_INDEXES <= objects


def test_v9_sets_user_version_9(tmp_path):
    provider = _provider(tmp_path)
    _to_v8(provider)

    assert migrate_catalog(provider) == 9

    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA user_version") == 9
        assert CATALOG_VERSION == 9


def test_v9_keeps_existing_data(tmp_path):
    provider = _provider(tmp_path)
    assert _to_v8(provider) == 8
    run_transaction_with_retry(provider, _seed)

    assert migrate_catalog(provider) == 9

    with provider.read_transaction() as tx:
        assert tx.scalar("SELECT name FROM category_texts") == "Категория"
        assert tx.scalar("SELECT name FROM product_texts") == "Товар"
        assert tx.scalar("SELECT value FROM product_attributes") == "APS-C"
        assert tx.scalar("SELECT lang FROM product_attributes") == "ru"
        assert tx.scalar("SELECT title FROM page_texts") == "О нас"
        assert tx.scalar("SELECT name FROM requests") == "Анна"
        assert tx.scalar("SELECT COUNT(*) FROM products") == 1
        assert tx.scalar("SELECT COUNT(*) FROM categories") == 1


def test_v9_rerun_is_noop(tmp_path):
    provider = _provider(tmp_path)
    assert _to_v8(provider) == 8
    run_transaction_with_retry(provider, _seed)
    assert migrate_catalog(provider) == 9
    before_objects = _objects(provider)

    assert migrate_catalog(provider) == 9

    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA user_version") == 9
        assert tx.scalar("SELECT COUNT(*) FROM products") == 1
        assert tx.scalar("SELECT COUNT(*) FROM publish_channels") == 0
    assert _objects(provider) == before_objects


def test_v9_rejects_v10_with_unsupported_schema_version(tmp_path):
    provider = _provider(tmp_path)
    assert _to_v8(provider) == 8
    with provider.transaction() as tx:
        tx.execute("PRAGMA user_version = 10")

    with pytest.raises(UnsupportedSchemaVersion):
        migrate_catalog(provider)

    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA user_version") == 10
    assert not (PUBLICATION_TABLES & _objects(provider))


def test_v9_jobs_fk_restrict_blocks_publication_delete(tmp_path):
    provider = _provider(tmp_path)
    _to_v8(provider)
    assert migrate_catalog(provider) == 9

    with provider.transaction() as tx:
        tx.execute(
            "INSERT INTO publish_channels (platform, channel_key, name,"
            " credentials_ref, settings_json, default_language, timezone,"
            " is_active, created_at, updated_at)"
            " VALUES ('telegram', 'main', 'Main', 'MAIN', '{}', 'ru',"
            " 'Europe/Chisinau', 1, ?, ?)",
            (STAMP, STAMP),
        )
        tx.execute(
            "INSERT INTO publications (kind, source_type, source_slug, status,"
            " created_by, created_at, updated_at)"
            " VALUES ('manual', '', '', 'scheduled', 'owner', ?, ?)",
            (STAMP, STAMP),
        )
        tx.execute(
            "INSERT INTO publication_texts (publication_id, lang, title, body)"
            " VALUES (1, 'ru', 'Заголовок', 'Текст')"
        )
        tx.execute(
            "INSERT INTO publication_jobs (publication_id, channel_id, lang,"
            " scheduled_for, status, attempts, idempotency_key, created_at, updated_at)"
            " VALUES (1, 1, 'ru', ?, 'queued', 0, 'key-1', ?, ?)",
            (STAMP, STAMP, STAMP),
        )

    with pytest.raises(sqlite3.IntegrityError):
        with provider.transaction() as tx:
            tx.execute("DELETE FROM publications WHERE id = 1")

    with pytest.raises(sqlite3.IntegrityError):
        with provider.transaction() as tx:
            tx.execute("DELETE FROM publish_channels WHERE id = 1")

    with provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM publication_jobs") == 1


def test_v9_journal_mode_stays_delete(tmp_path):
    provider = _provider(tmp_path)
    db_path = tmp_path / "db" / "shop.sqlite"
    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA journal_mode") == "delete"
    _to_v8(provider)
    assert migrate_catalog(provider) == 9
    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA journal_mode") == "delete"
    assert not Path(str(db_path) + "-wal").exists()
    assert not Path(str(db_path) + "-shm").exists()
