"""S6 tests: SQLite reliability contract (timeouts, retry, read/write scopes).

Covered areas (authorized S6 scope):

1. per-connection settings of BOTH connection factories;
2. ``busy_timeout`` expiry, including inherited framework methods;
3. SQLITE_BUSY vs SQLITE_LOCKED distinction (LOCKED is never retried);
4. bounded retry around the WHOLE transactional operation (no duplicated effect);
5. read paths do not take the write lock (L-12 fix);
6. ``resolve`` reads ONE consistent snapshot under a concurrent rename;
7. rollback and crash recovery (process killed mid-transaction);
8. concurrent migrations and more than two writers.

Test tables are created by the tests themselves in ``tmp_path``; no production
table, migration or HTTP route is involved. ``journal_mode`` must stay ``delete``
(WAL is deliberately not enabled).
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from showcases.videoshop.infrastructure.migrations import (
    S3_MIGRATIONS,
    migrate,
    read_schema_version,
)
from showcases.videoshop.infrastructure.retry import (
    BusyTimeoutError,
    LockedError,
    is_busy_error,
    is_locked_error,
    primary_error_code,
    run_transaction_with_retry,
)
from showcases.videoshop.infrastructure.slug_registry import TABLE, SlugRegistry
from showcases.videoshop.infrastructure.sqlite_provider import (
    TransactionStateError,
    VideoShopSQLiteProvider,
)
from showcases.videoshop.services.entity_lifecycle import EntityLifecycleService

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPECTED_SCHEMA_VERSION = max(step.version for step in S3_MIGRATIONS)

ENTITY_TYPE = "test_article"
VERSIONED_TABLE = "test_articles"


# --- fixtures ------------------------------------------------------------


def _create_tables(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS test_articles ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " title TEXT,"
        " version INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute("INSERT OR IGNORE INTO items (id, name) VALUES (1, 'seed')")
    conn.commit()
    conn.close()


@pytest.fixture
def db_path(tmp_path) -> str:
    path = str(tmp_path / "s6.db")
    _create_tables(path)
    return path


@pytest.fixture
def provider(db_path) -> VideoShopSQLiteProvider:
    return VideoShopSQLiteProvider(db_path=db_path)


@pytest.fixture
def registry(provider) -> SlugRegistry:
    registry = SlugRegistry(provider)
    assert registry.migrate() == EXPECTED_SCHEMA_VERSION
    return registry


@pytest.fixture
def articles(provider, registry, db_path) -> EntityLifecycleService:
    _create_tables(db_path)
    return EntityLifecycleService(
        provider, registry, ENTITY_TYPE, VERSIONED_TABLE, versioned=True
    )


# --- process helpers -----------------------------------------------------


def _spawn(source: str, *args: str) -> subprocess.Popen:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.Popen(
        [sys.executable, "-B", "-c", source, *args],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _handshake(process: subprocess.Popen) -> str:
    """Wait until the child confirms it holds the lock."""
    line = process.stdout.readline().strip()
    assert line == "holding", f"unexpected handshake: {line!r}"
    return line


HOLDER_SOURCE = (
    "import sys, time\n"
    "from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider\n"
    "provider = VideoShopSQLiteProvider(db_path=sys.argv[1], busy_timeout_ms=5000)\n"
    "with provider.transaction() as tx:\n"
    "    tx.execute(\"UPDATE items SET name = 'held' WHERE id = 1\")\n"
    "    print('holding', flush=True)\n"
    "    time.sleep(float(sys.argv[2]))\n"
    "print('released', flush=True)\n"
)

CRASH_SOURCE = (
    "import sys, time\n"
    "from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider\n"
    "provider = VideoShopSQLiteProvider(db_path=sys.argv[1], busy_timeout_ms=5000)\n"
    "tx = provider.transaction()\n"
    "tx.execute(\"INSERT INTO items (id, name) VALUES (99, 'uncommitted')\")\n"
    "print('holding', flush=True)\n"
    "time.sleep(60)\n"
)

MIGRATE_SOURCE = (
    "import sys\n"
    "from showcases.videoshop.infrastructure.migrations import migrate, read_schema_version\n"
    "from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider\n"
    "provider = VideoShopSQLiteProvider(db_path=sys.argv[1], busy_timeout_ms=5000)\n"
    "migrate(provider)\n"
    "print('MIGRATED:%d' % read_schema_version(provider), flush=True)\n"
)

RENAME_SOURCE = (
    "import sys\n"
    "from showcases.videoshop.infrastructure.slug_registry import SlugRegistry\n"
    "from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider\n"
    "from showcases.videoshop.services.entity_lifecycle import EntityLifecycleService\n"
    "provider = VideoShopSQLiteProvider(db_path=sys.argv[1], busy_timeout_ms=5000)\n"
    "service = EntityLifecycleService(provider, SlugRegistry(provider), 'test_article',\n"
    "                                 'test_articles', versioned=True)\n"
    "service.rename(int(sys.argv[2]), sys.argv[3], expected_version=int(sys.argv[4]))\n"
    "print('OK', flush=True)\n"
)

CREATE_SOURCE = (
    "import sys\n"
    "from showcases.videoshop.infrastructure.slug_registry import SlugRegistry, SlugTaken\n"
    "from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider\n"
    "from showcases.videoshop.services.entity_lifecycle import EntityLifecycleService\n"
    "provider = VideoShopSQLiteProvider(db_path=sys.argv[1], busy_timeout_ms=5000)\n"
    "service = EntityLifecycleService(provider, SlugRegistry(provider), 'test_article',\n"
    "                                 'test_articles', versioned=True)\n"
    "try:\n"
    "    service.create(sys.argv[2], {'title': sys.argv[3]})\n"
    "    print('OK', flush=True)\n"
    "except SlugTaken:\n"
    "    print('SLUG_TAKEN', flush=True)\n"
)

CAS_LOOP_SOURCE = (
    "import sys\n"
    "from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider\n"
    "provider = VideoShopSQLiteProvider(db_path=sys.argv[1], busy_timeout_ms=5000)\n"
    "target = int(sys.argv[2])\n"
    "done = 0\n"
    "while done < target:\n"
    "    with provider.transaction() as tx:\n"
    "        version = tx.scalar('SELECT version FROM test_articles WHERE id = 1')\n"
    "        result = tx.update_record_cas('test_articles', 1, {}, version)\n"
    "        if result.status == 'updated':\n"
    "            done += 1\n"
    "        else:\n"
    "            import time as _t; _t.sleep(0.005)\n"
    "print('DONE:%d' % done, flush=True)\n"
)


# --- 1. both factories share the settings --------------------------------


def test_both_connection_factories_apply_the_same_settings(db_path):
    """D-S6-2: busy_timeout, foreign_keys and synchronous on BOTH factories."""
    provider = VideoShopSQLiteProvider(db_path=db_path, busy_timeout_ms=250)

    connection = provider._connect()  # VideoShop factory
    try:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 250
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    finally:
        connection.close()

    with provider._get_connection() as framework_connection:  # framework factory
        assert framework_connection.execute("PRAGMA busy_timeout").fetchone()[0] == 250
        assert framework_connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert framework_connection.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert framework_connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


# --- 2. timeout expiry on the framework path -----------------------------


def test_inherited_methods_honour_busy_timeout(db_path):
    """Before S6 the framework path used the 5 s default; now it uses the setting."""
    holder = _spawn(HOLDER_SOURCE, db_path, "2.0")
    _handshake(holder)

    provider = VideoShopSQLiteProvider(db_path=db_path, busy_timeout_ms=0)
    started = time.time()
    with pytest.raises(sqlite3.OperationalError) as excinfo:
        asyncio.run(provider.insert("items", {"id": 2, "name": "blocked"}))
    elapsed = time.time() - started

    assert elapsed < 0.6, f"the configured timeout must apply to insert() (took {elapsed:.2f}s)"
    assert is_busy_error(excinfo.value), "the error must be SQLITE_BUSY"
    assert primary_error_code(excinfo.value) == sqlite3.SQLITE_BUSY
    holder.communicate(timeout=60)


# --- 3. BUSY vs LOCKED ---------------------------------------------------


class _LockedLike(sqlite3.OperationalError):
    sqlite_errorcode = sqlite3.SQLITE_LOCKED


def test_busy_and_locked_are_distinguished(db_path):
    holder = _spawn(HOLDER_SOURCE, db_path, "1.5")
    _handshake(holder)
    provider = VideoShopSQLiteProvider(db_path=db_path, busy_timeout_ms=0)
    with pytest.raises(sqlite3.OperationalError) as excinfo:
        provider.transaction()
    holder.communicate(timeout=60)

    busy = excinfo.value
    assert is_busy_error(busy) and not is_locked_error(busy)
    assert primary_error_code(busy) == sqlite3.SQLITE_BUSY

    locked = _LockedLike("database table is locked")
    assert is_locked_error(locked) and not is_busy_error(locked)
    assert primary_error_code(locked) == sqlite3.SQLITE_LOCKED

    # message-based fallback when no result code is available
    class _NoCode(sqlite3.OperationalError):
        sqlite_errorcode = None

    assert is_locked_error(_NoCode("database table is locked"))
    assert is_busy_error(_NoCode("database is locked"))


# --- 4. bounded retry ----------------------------------------------------


def test_busy_retry_succeeds_and_does_not_duplicate_effects(db_path):
    holder = _spawn(HOLDER_SOURCE, db_path, "0.6")
    _handshake(holder)

    provider = VideoShopSQLiteProvider(db_path=db_path, busy_timeout_ms=0)
    body_runs: list[int] = []
    retry_delays: list[float] = []

    def fake_sleep(seconds: float) -> None:
        retry_delays.append(seconds)  # the wrapper sleeps ONLY between retries
        time.sleep(seconds)

    def operation(tx):
        body_runs.append(1)
        tx.execute("INSERT INTO items (id, name) VALUES (42, 'retried')")
        return "ok"

    result = run_transaction_with_retry(
        provider,
        operation,
        attempts=10,
        base_delay_ms=50,
        max_delay_ms=200,
        budget_ms=3000,
        sleep=fake_sleep,
    )
    holder.communicate(timeout=60)

    assert result == "ok"
    assert retry_delays, "at least one retry delay proves the BUSY retry happened"
    assert body_runs == [1], "the body must run exactly once (the BUSY hit BEGIN)"
    with provider.read_transaction() as tx:
        rows = tx.fetchall("SELECT id FROM items WHERE id = 42")
        assert len(rows) == 1, "a retried operation must not duplicate its effect"


def test_busy_retry_exhaustion_is_typed_and_leaves_no_state(db_path):
    holder = _spawn(HOLDER_SOURCE, db_path, "3.0")
    _handshake(holder)

    provider = VideoShopSQLiteProvider(db_path=db_path, busy_timeout_ms=0)
    attempts: list[int] = []

    def operation(tx):
        attempts.append(1)
        tx.execute("INSERT INTO items (id, name) VALUES (43, 'never')")
        return "ok"

    with pytest.raises(BusyTimeoutError):
        run_transaction_with_retry(
            provider, operation, attempts=2, base_delay_ms=10, max_delay_ms=20, budget_ms=100
        )
    holder.communicate(timeout=60)

    assert attempts == [], "BEGIN failed, so the operation body must never run"
    with provider.read_transaction() as tx:
        assert tx.fetchall("SELECT id FROM items WHERE id = 43") == []


def test_locked_error_is_never_retried(db_path):
    provider = VideoShopSQLiteProvider(db_path=db_path, busy_timeout_ms=0)
    attempts: list[int] = []

    def operation(tx):
        attempts.append(1)
        raise _LockedLike("database table is locked")

    with pytest.raises(LockedError) as excinfo:
        run_transaction_with_retry(provider, operation, attempts=5, budget_ms=1000)

    assert excinfo.value.code == "SQLITE_LOCKED"
    assert len(attempts) == 1, "SQLITE_LOCKED must not be retried"


def test_other_sqlite_errors_propagate_unchanged(db_path):
    provider = VideoShopSQLiteProvider(db_path=db_path, busy_timeout_ms=0)
    attempts: list[int] = []

    def operation(tx):
        attempts.append(1)
        raise sqlite3.OperationalError("no such table: nope")

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        run_transaction_with_retry(provider, operation, attempts=5, budget_ms=1000)
    assert len(attempts) == 1


# --- 5. read paths do not take the write lock ----------------------------


def test_read_paths_do_not_take_the_write_lock(articles, provider, registry, db_path):
    """L-12 fix: reads use BEGIN DEFERRED and succeed while a writer holds IMMEDIATE."""
    articles.create("snap-one", {"title": "Snap"})

    holder = _spawn(HOLDER_SOURCE, db_path, "3.0")
    _handshake(holder)

    assert articles.get_entity(1)["title"] == "Snap"
    assert articles.live_slug(1) == "snap-one"
    assert articles.resolve("snap-one").is_current
    assert registry.get(ENTITY_TYPE, "snap-one")["entity_id"] == 1

    holder.communicate(timeout=60)


def test_read_transaction_is_deferred_and_refuses_cas(provider):
    with provider.read_transaction() as tx:
        assert tx.mode == "read"
        assert tx.scalar("SELECT 1") == 1
        with pytest.raises(TransactionStateError):
            tx.update_record_cas("items", 1, {}, 0)

    with provider.transaction() as tx:
        assert tx.mode == "write"


# --- 6. resolve uses ONE snapshot ----------------------------------------


def test_resolve_uses_one_snapshot_under_concurrent_rename(articles, provider, db_path):
    articles.create("snap-a", {"title": "Snap"})

    with provider.read_transaction() as tx:
        first = tx.scalar(
            f"SELECT slug FROM {TABLE} WHERE entity_type = ? AND entity_id = 1 AND state = 'live'",
            (ENTITY_TYPE,),
        )
        assert first == "snap-a"

        writer = _spawn(RENAME_SOURCE, db_path, "1", "snap-b", "0")
        time.sleep(0.6)

        assert writer.poll() is None, "the writer must be blocked by the reader's snapshot"
        second = tx.scalar(
            f"SELECT slug FROM {TABLE} WHERE entity_type = ? AND entity_id = 1 AND state = 'live'",
            (ENTITY_TYPE,),
        )
        released = tx.fetchall(
            f"SELECT slug FROM {TABLE} WHERE entity_type = ? AND entity_id = 1 AND state = 'released'",
            (ENTITY_TYPE,),
        )
        assert second == first, "the snapshot must not change mid-transaction"
        assert released == [], "no partially visible history inside the snapshot"

    stdout, stderr = writer.communicate(timeout=60)
    assert stdout.strip() == "OK" and not stderr

    # after the snapshot is released the new state is visible and resolution is direct
    resolution = articles.resolve("snap-a")
    assert resolution.is_redirect and resolution.current_slug == "snap-b"


# --- 7. rollback and crash recovery --------------------------------------


def test_rollback_leaves_no_state(provider):
    def operation(tx):
        tx.execute("INSERT INTO items (id, name) VALUES (77, 'transient')")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_transaction_with_retry(provider, operation, attempts=3, budget_ms=1000)

    with provider.read_transaction() as tx:
        assert tx.fetchall("SELECT id FROM items WHERE id = 77") == []


def test_crash_recovery_leaves_no_partial_state(provider, registry, db_path):
    crash = _spawn(CRASH_SOURCE, db_path)
    _handshake(crash)
    crash.kill()
    crash.communicate(timeout=60)

    with provider.read_transaction() as tx:
        rows = tx.fetchall("SELECT id FROM items WHERE id = 99")
        assert rows == [], "an uncommitted insert must not survive a kill"
        integrity = tx.scalar("PRAGMA integrity_check")
        assert integrity == "ok"
        objects = {
            row["name"] for row in tx.fetchall("SELECT name FROM sqlite_master")
        }
    assert "items" in objects and TABLE in objects, objects

    # the database is still writable afterwards
    with provider.transaction() as tx:
        tx.execute("INSERT INTO items (id, name) VALUES (100, 'after-crash')")
    with provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM items WHERE id = 100") == 1


# --- 8. concurrent migrations and >2 writers -----------------------------


def test_concurrent_migrations_two_processes(tmp_path):
    db_path = str(tmp_path / "s6_migrations.db")

    first = _spawn(MIGRATE_SOURCE, db_path)
    second = _spawn(MIGRATE_SOURCE, db_path)
    outputs = []
    for process in (first, second):
        stdout, stderr = process.communicate(timeout=120)
        assert not stderr, stderr
        assert process.returncode == 0
        outputs.append(stdout.strip())

    assert sorted(outputs) == [f"MIGRATED:{EXPECTED_SCHEMA_VERSION}"] * 2, outputs

    provider = VideoShopSQLiteProvider(db_path=db_path)
    assert read_schema_version(provider) == EXPECTED_SCHEMA_VERSION
    with provider.read_transaction() as tx:
        indexes = {
            row["name"]
            for row in tx.fetchall(f"PRAGMA index_list({TABLE})")
        }
    assert "ux_slug_registry_live_entity" in indexes


def test_more_than_two_writers_keep_the_state_correct(articles, provider, db_path):
    articles.create("shared-start", {"title": "Shared"})

    writers = [_spawn(CAS_LOOP_SOURCE, db_path, "5") for _ in range(4)]
    outputs = []
    for process in writers:
        stdout, stderr = process.communicate(timeout=180)
        assert process.returncode == 0, stderr
        outputs.append(stdout.strip())

    assert sorted(outputs) == ["DONE:5"] * 4, outputs

    with provider.read_transaction() as tx:
        version = tx.scalar("SELECT version FROM test_articles WHERE id = 1")
        live = tx.fetchall(
            f"SELECT slug FROM {TABLE} WHERE entity_type = ? AND entity_id = 1 AND state = 'live'",
            (ENTITY_TYPE,),
        )
        released = tx.fetchall(
            f"SELECT slug FROM {TABLE} WHERE entity_type = ? AND entity_id = 1 AND state = 'released'",
            (ENTITY_TYPE,),
        )
    assert version == 20, "every successful CAS must have incremented exactly once"
    assert [row["slug"] for row in live] == ["shared-start"]
    assert released == [], "no partial rename may be recorded by the CAS writers"


def test_four_concurrent_creates_keep_the_registry_consistent(articles, provider, db_path):
    creators = [
        _spawn(CREATE_SOURCE, db_path, f"slug-{index}", f"title-{index}")
        for index in range(1, 5)
    ]
    outputs = []
    for process in creators:
        stdout, stderr = process.communicate(timeout=180)
        assert process.returncode == 0, stderr
        outputs.append(stdout.strip())

    assert sorted(outputs) == ["OK"] * 4, outputs

    with provider.read_transaction() as tx:
        entities = tx.scalar("SELECT COUNT(*) FROM test_articles")
        live = tx.fetchall(
            f"SELECT slug, entity_id FROM {TABLE} WHERE entity_type = ? AND state = 'live' "
            f"ORDER BY slug",
            (ENTITY_TYPE,),
        )
        duplicated = tx.fetchall(
            f"SELECT entity_id FROM {TABLE} WHERE entity_type = ? AND state = 'live' "
            f"GROUP BY entity_id HAVING COUNT(*) > 1",
            (ENTITY_TYPE,),
        )
    assert entities == 4
    assert [row["slug"] for row in live] == ["slug-1", "slug-2", "slug-3", "slug-4"]
    assert duplicated == []
