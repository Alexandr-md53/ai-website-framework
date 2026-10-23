"""S3 tests: the migration runner (S3-owned tables only).

Covers: creation of the S3 schema (step 1 + step 2), idempotency, atomic failure
(rollback keeps schema and ``user_version`` unchanged) and rejection of a newer
schema version. Version expectations are derived from ``S3_MIGRATIONS`` so that a
later step cannot silently weaken these tests.
"""
from __future__ import annotations

import sqlite3

import pytest

from showcases.videoshop.infrastructure.migrations import (
    Migration,
    MigrationError,
    S3_MIGRATIONS,
    UnsupportedSchemaVersion,
    migrate,
    read_schema_version,
)
from showcases.videoshop.infrastructure.slug_registry import TABLE, SlugRegistry
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider

EXPECTED_SCHEMA_VERSION = max(step.version for step in S3_MIGRATIONS)


@pytest.fixture
def provider(tmp_path) -> VideoShopSQLiteProvider:
    return VideoShopSQLiteProvider(db_path=str(tmp_path / "s3_migrations.db"))


def _objects(provider: VideoShopSQLiteProvider) -> set[str]:
    with provider.transaction() as tx:
        rows = tx.fetchall("SELECT name FROM sqlite_master WHERE type IN ('table','index')")
    return {row["name"] for row in rows}


def test_migration_creates_registry_and_sets_version(provider):
    assert read_schema_version(provider) == 0
    assert TABLE not in _objects(provider)

    version = migrate(provider)

    assert version == EXPECTED_SCHEMA_VERSION
    assert read_schema_version(provider) == EXPECTED_SCHEMA_VERSION
    objects = _objects(provider)
    assert TABLE in objects
    assert "ix_slug_registry_entity" in objects
    assert "ux_slug_registry_live_entity" in objects, "step 2 index must exist"


def test_migration_is_idempotent(provider):
    migrate(provider)
    registry = SlugRegistry(provider)
    registry.register("product", "kept", 1)

    assert migrate(provider) == EXPECTED_SCHEMA_VERSION
    assert migrate(provider) == EXPECTED_SCHEMA_VERSION
    assert read_schema_version(provider) == EXPECTED_SCHEMA_VERSION
    assert registry.get("product", "kept")["entity_id"] == 1


def test_failing_migration_rolls_back_and_keeps_version(provider):
    def _good(tx):
        tx.execute("CREATE TABLE probe_one (id INTEGER PRIMARY KEY)")

    def _bad(tx):
        tx.execute("CREATE TABLE probe_two (id INTEGER PRIMARY KEY)")
        raise RuntimeError("boom")

    with pytest.raises(MigrationError) as excinfo:
        migrate(provider, (Migration(1, "good", _good), Migration(2, "bad", _bad)))

    assert "bad" in str(excinfo.value) and "2" in str(excinfo.value)
    assert read_schema_version(provider) == 1, "the version must stay at the last good step"
    objects = _objects(provider)
    assert "probe_one" in objects
    assert "probe_two" not in objects, "the failed step must leave nothing behind"


def test_newer_schema_version_is_rejected(provider):
    with provider.transaction() as tx:
        tx.execute("PRAGMA user_version = 999")

    with pytest.raises(UnsupportedSchemaVersion):
        migrate(provider)

    assert read_schema_version(provider) == 999
    assert TABLE not in _objects(provider), "no change may be attempted"


def test_registry_write_fails_closed_without_migration(provider):
    registry = SlugRegistry(provider)
    with pytest.raises(sqlite3.OperationalError):
        registry.register("product", "no-schema", 1)
    assert read_schema_version(provider) == 0
