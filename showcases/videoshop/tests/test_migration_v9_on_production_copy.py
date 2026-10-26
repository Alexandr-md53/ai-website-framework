"""Stage 1: migration v9 applied to a COPY of the production database only."""
from __future__ import annotations

import hashlib
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pytest

from showcases.videoshop.infrastructure.backup import verify_database_file
from showcases.videoshop.infrastructure.migrations.catalog import (
    CATALOG_VERSION,
    migrate_catalog,
)
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_DB = REPOSITORY_ROOT / "data" / "db" / "shop.sqlite"

EXPECTED_SHA256 = "F74BCAC7F59D25F22EFF95FFB4A47C82B20BE2CABA23C68BE660C1CD1E504167"
EXPECTED_SIZE = 204800
EXPECTED_MTIME = datetime.fromisoformat("2026-10-22T21:34:58.7109618+03:00").timestamp()

EXISTING_TABLES = ("products", "categories", "product_texts", "page_texts", "orders")


def _fingerprint(path: Path):
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    return digest, stat.st_size, stat.st_mtime


def _assert_consistent_source() -> None:
    if not PRODUCTION_DB.is_file():
        pytest.skip("production database is not present")

    for suffix in ("-wal", "-shm", "-journal"):
        side = Path(str(PRODUCTION_DB) + suffix)
        assert not side.exists(), f"STOP: unexpected SQLite side file {side.name}"

    first = PRODUCTION_DB.stat()
    time.sleep(1.1)
    second = PRODUCTION_DB.stat()
    assert (first.st_size, first.st_mtime_ns) == (second.st_size, second.st_mtime_ns), (
        "STOP: production database is being written right now"
    )

    connection = sqlite3.connect(
        f"{PRODUCTION_DB.resolve().as_uri()}?mode=ro", uri=True
    )
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 8
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    finally:
        connection.close()


def _copy_with_backup_api(target: Path) -> None:
    """Consistent copy through the online backup API; source stays read-only."""
    source = sqlite3.connect(
        f"{PRODUCTION_DB.resolve().as_uri()}?mode=ro", uri=True, isolation_level=None
    )
    destination = sqlite3.connect(str(target), isolation_level=None)
    try:
        source.backup(destination)
    except sqlite3.OperationalError as exc:
        pytest.fail(f"STOP: consistent copy is impossible: {exc}")
    finally:
        destination.close()
        source.close()


def _copy_fixture(tmp_path) -> Path:
    _assert_consistent_source()
    target = tmp_path / "copy" / "shop.sqlite"
    target.parent.mkdir()
    _copy_with_backup_api(target)
    assert target.stat().st_size > 0
    report = verify_database_file(target, expected_user_version=8)
    assert report.failed_checks == ()
    return target


def test_production_copy_migrates_8_to_9(tmp_path):
    copy_path = _copy_fixture(tmp_path)
    assert copy_path.resolve() != PRODUCTION_DB.resolve()

    provider = VideoShopSQLiteProvider(db_path=str(copy_path))
    assert migrate_catalog(provider) == CATALOG_VERSION == 9

    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA user_version") == 9
        names = {
            row["name"]
            for row in tx.fetchall("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert {
        "publish_channels",
        "publications",
        "publication_texts",
        "publication_jobs",
        "publication_events",
        "publication_dedup",
    } <= names
    assert verify_database_file(copy_path, expected_user_version=9).failed_checks == ()


def test_production_copy_keeps_row_counts(tmp_path):
    copy_path = _copy_fixture(tmp_path)

    def counts() -> dict[str, int]:
        connection = sqlite3.connect(str(copy_path))
        try:
            return {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in EXISTING_TABLES
            }
        finally:
            connection.close()

    before = counts()
    provider = VideoShopSQLiteProvider(db_path=str(copy_path))
    assert migrate_catalog(provider) == 9
    after = counts()
    assert after == before


def test_production_db_hash_and_mtime_unchanged(tmp_path):
    _assert_consistent_source()
    before = _fingerprint(PRODUCTION_DB)

    copy_path = tmp_path / "copy" / "shop.sqlite"
    copy_path.parent.mkdir()
    _copy_with_backup_api(copy_path)
    provider = VideoShopSQLiteProvider(db_path=str(copy_path))
    assert migrate_catalog(provider) == 9

    after = _fingerprint(PRODUCTION_DB)
    assert after == before
    assert before[0] == EXPECTED_SHA256
    assert before[1] == EXPECTED_SIZE
    assert abs(before[2] - EXPECTED_MTIME) < 0.001
    for suffix in ("-wal", "-shm", "-journal"):
        assert not Path(str(PRODUCTION_DB) + suffix).exists()
