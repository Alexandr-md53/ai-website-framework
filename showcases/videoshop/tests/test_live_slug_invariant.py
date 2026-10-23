"""S3 step 2 tests: the live-slug invariant (at most one live slug per entity).

Mandatory checks from the S3 step-2 report:

1. two live rows for one entity are forbidden;
2. ``release(old) + register(new)`` in one transaction replaces the slug;
3. ``register(new)`` without ``release(old)`` is rejected;
4. concurrent registration through two connections cannot create two live slugs;
5. concurrent registration through two processes cannot create two live slugs;
6. step 2 creates the partial unique index and bumps the schema version;
7. the migration is fail-closed on existing duplicates (rows and version intact).

Plus two extra checks of the replacement contract: a failed replacement rolls the
release back, and ``replace_slug`` has a defined behaviour for a non-live old slug.

Every test verifies the ACTUAL DATABASE STATE, not only API results.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from showcases.videoshop.infrastructure.migrations import (
    LIVE_ENTITY_UNIQUE_INDEX,
    MigrationError,
    S3_MIGRATIONS,
    migrate,
    read_schema_version,
)
from showcases.videoshop.infrastructure.slug_registry import (
    STATE_LIVE,
    STATE_RELEASED,
    TABLE,
    InvalidSlug,
    SlugNotLive,
    SlugRegistry,
    SlugTaken,
)
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider

REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_INDEX_NAME = "ux_slug_registry_live_entity"
EXPECTED_SCHEMA_VERSION = max(step.version for step in S3_MIGRATIONS)


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "s3_live.db")


@pytest.fixture
def provider(db_path) -> VideoShopSQLiteProvider:
    return VideoShopSQLiteProvider(db_path=db_path)


@pytest.fixture
def registry(provider) -> SlugRegistry:
    registry = SlugRegistry(provider)
    assert registry.migrate() == EXPECTED_SCHEMA_VERSION
    return registry


# --- database-state helpers ---------------------------------------------


def _live_rows(provider: VideoShopSQLiteProvider, entity_id: int | None = None) -> list[dict]:
    with provider.transaction() as tx:
        if entity_id is None:
            rows = tx.fetchall(
                f"SELECT * FROM {TABLE} WHERE entity_type = ? AND state = ? ORDER BY slug",
                ("product", STATE_LIVE),
            )
        else:
            rows = tx.fetchall(
                f"SELECT * FROM {TABLE} WHERE entity_type = ? AND entity_id = ? "
                f"AND state = ? ORDER BY slug",
                ("product", entity_id, STATE_LIVE),
            )
    return [dict(row) for row in rows]


def _all_rows(provider: VideoShopSQLiteProvider) -> list[dict]:
    with provider.transaction() as tx:
        rows = tx.fetchall(
            f"SELECT * FROM {TABLE} WHERE entity_type = ? ORDER BY state, slug", ("product",)
        )
    return [dict(row) for row in rows]


def _indexes(provider: VideoShopSQLiteProvider) -> list[tuple]:
    with provider.transaction() as tx:
        return [tuple(row) for row in tx.fetchall(f"PRAGMA index_list({TABLE})")]


# --- 1. two live slugs for one entity are forbidden ----------------------


def test_two_live_slugs_for_one_entity_are_forbidden(registry, provider):
    registry.register("product", "live-one", 1)

    with pytest.raises(SlugTaken) as excinfo:
        registry.register("product", "live-two", 1)

    assert excinfo.value.code == "SLUG_TAKEN"
    assert excinfo.value.held_by == 1
    assert [row["slug"] for row in _live_rows(provider, entity_id=1)] == ["live-one"]
    assert len(_all_rows(provider)) == 1, "the refused row must not exist"


# --- 2. release + register in one transaction replaces the slug ----------


def test_replace_slug_is_atomic_and_keeps_history(registry, provider):
    registry.register("product", "old-slug", 1)

    record = registry.replace_slug("product", 1, "old-slug", "new-slug")

    assert record["slug"] == "new-slug"
    assert record["state"] == STATE_LIVE
    assert [row["slug"] for row in _live_rows(provider, entity_id=1)] == ["new-slug"]

    rows = _all_rows(provider)
    assert len(rows) == 2, "old slug must stay as the released history record"
    released = [row for row in rows if row["state"] == STATE_RELEASED]
    assert [row["slug"] for row in released] == ["old-slug"]
    assert released[0]["entity_id"] == 1
    assert released[0]["released_at"] is not None

    with pytest.raises(SlugTaken):
        registry.register("product", "old-slug", 2)  # (entity_type, slug) still protected


# --- 3. register without release is rejected -----------------------------


def test_register_without_release_is_rejected(registry, provider):
    registry.register("product", "keep-me", 1)

    with pytest.raises(SlugTaken):
        registry.register("product", "brand-new", 1)

    assert [row["slug"] for row in _live_rows(provider, entity_id=1)] == ["keep-me"]
    assert registry.get("product", "brand-new") is None
    assert len(_all_rows(provider)) == 1


# --- 4. a failed replacement rolls the release back ----------------------


def test_failed_replacement_rolls_back_the_release(registry, provider):
    registry.register("product", "mine", 1)
    registry.register("product", "taken", 2)

    with pytest.raises(SlugTaken):
        registry.replace_slug("product", 1, "mine", "taken")

    assert [row["slug"] for row in _live_rows(provider, entity_id=1)] == ["mine"]
    assert [row for row in _all_rows(provider) if row["state"] == STATE_RELEASED] == [], (
        "the release must be rolled back together with the failed registration"
    )

    with pytest.raises(InvalidSlug):
        registry.replace_slug("product", 1, "mine", "NOT-VALID")
    assert [row["slug"] for row in _live_rows(provider, entity_id=1)] == ["mine"]


# --- 5. concurrency through two connections ------------------------------


def test_concurrent_two_connections_cannot_create_two_live_slugs(db_path):
    SlugRegistry(VideoShopSQLiteProvider(db_path=db_path)).migrate()

    barrier = threading.Barrier(2)
    lock = threading.Lock()
    outcomes: list[str] = []

    def worker(slug: str) -> None:
        local = SlugRegistry(VideoShopSQLiteProvider(db_path=db_path))
        barrier.wait()
        try:
            local.register("product", slug, 1)
            outcome = "OK"
        except SlugTaken:
            outcome = "SLUG_TAKEN"
        except Exception as exc:  # noqa: BLE001 - reported through the assertion
            outcome = f"ERR:{type(exc).__name__}"
        with lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=worker, args=(slug,)) for slug in ("conn-a", "conn-b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["OK", "SLUG_TAKEN"], outcomes
    live = _live_rows(VideoShopSQLiteProvider(db_path=db_path), entity_id=1)
    assert len(live) == 1, live


# --- 6. concurrency through two processes --------------------------------


WORKER_SOURCE = (
    "import sys\n"
    "from showcases.videoshop.infrastructure.slug_registry import SlugRegistry, SlugTaken\n"
    "from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider\n"
    "db_path, slug = sys.argv[1], sys.argv[2]\n"
    "registry = SlugRegistry(VideoShopSQLiteProvider(db_path=db_path))\n"
    "try:\n"
    "    registry.register('product', slug, 1)\n"
    "    print('OK')\n"
    "except SlugTaken:\n"
    "    print('SLUG_TAKEN')\n"
    "except Exception as exc:\n"
    "    print('ERR:%s' % type(exc).__name__)\n"
)


def test_concurrent_two_processes_cannot_create_two_live_slugs(tmp_path):
    db_path = str(tmp_path / "s3_live_proc.db")
    SlugRegistry(VideoShopSQLiteProvider(db_path=db_path)).migrate()

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONIOENCODING"] = "utf-8"

    processes = [
        subprocess.Popen(
            [sys.executable, "-B", "-c", WORKER_SOURCE, db_path, slug],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for slug in ("proc-a", "proc-b")
    ]
    outcomes = [(p.communicate(timeout=120)) for p in processes]

    results = sorted(stdout.strip() for stdout, _ in outcomes)
    assert results == ["OK", "SLUG_TAKEN"], outcomes
    assert all(not stderr for _, stderr in outcomes), outcomes

    live = _live_rows(VideoShopSQLiteProvider(db_path=db_path), entity_id=1)
    assert len(live) == 1, live


# --- 7. step 2 creates the partial unique index and bumps the version ----


def test_step_two_creates_partial_unique_index_and_bumps_version(db_path):
    provider = VideoShopSQLiteProvider(db_path=db_path)
    assert read_schema_version(provider) == 0

    assert migrate(provider) == EXPECTED_SCHEMA_VERSION
    assert EXPECTED_SCHEMA_VERSION == 2, "step 2 must be the second migration step"

    indexes = {row[1]: row for row in _indexes(provider)}
    assert LIVE_INDEX_NAME in indexes
    _, name, unique, origin, partial = indexes[LIVE_INDEX_NAME]
    assert name == LIVE_INDEX_NAME
    assert unique == 1, "the live-slug index must be UNIQUE"
    assert partial == 1, "the index must be partial (WHERE state = 'live')"

    with provider.transaction() as tx:
        columns = [row["name"] for row in tx.fetchall(f"PRAGMA index_info({LIVE_INDEX_NAME})")]
        sql = tx.scalar(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
            (LIVE_INDEX_NAME,),
        )
    assert columns == ["entity_type", "entity_id"]
    assert "WHERE state = 'live'" in sql
    assert read_schema_version(provider) == EXPECTED_SCHEMA_VERSION


# --- 8. fail-closed on existing duplicates -------------------------------


def test_migration_fails_closed_on_existing_duplicates(db_path):
    provider = VideoShopSQLiteProvider(db_path=db_path)
    first_step = min(S3_MIGRATIONS, key=lambda step: step.version)
    assert migrate(provider, (first_step,)) == 1, "seed data needs the pre-step-2 schema"

    insert = (
        f"INSERT INTO {TABLE} (entity_type, slug, entity_id, state, created_at, released_at) "
        f"VALUES ('product', ?, 1, 'live', '2026-01-01T00:00:00+00:00', NULL)"
    )
    with provider.transaction() as tx:
        tx.execute(insert, ("dup-a",))
        tx.execute(insert, ("dup-b",))

    with pytest.raises(MigrationError) as excinfo:
        migrate(provider)
    assert "duplicate" in str(excinfo.value).lower()

    # fail-closed: version unchanged, index absent, seeded rows untouched
    assert read_schema_version(provider) == 1
    assert LIVE_INDEX_NAME not in {row[1] for row in _indexes(provider)}
    rows = _all_rows(provider)
    assert sorted(row["slug"] for row in rows) == ["dup-a", "dup-b"]
    assert all(row["state"] == STATE_LIVE and row["entity_id"] == 1 for row in rows)

    # the migration never repairs data: after a manual fix it can succeed
    with provider.transaction() as tx:
        tx.execute(f"DELETE FROM {TABLE} WHERE entity_type = 'product' AND slug = ?", ("dup-b",))
    assert migrate(provider) == EXPECTED_SCHEMA_VERSION
    assert LIVE_INDEX_NAME in {row[1] for row in _indexes(provider)}


# --- 9. replace_slug contract for a non-live old slug --------------------


def test_replace_slug_requires_the_current_live_slug(registry, provider):
    registry.register("product", "current", 1)

    with pytest.raises(SlugNotLive):
        registry.replace_slug("product", 1, "unknown-slug", "brand-new")

    same = registry.replace_slug("product", 1, "current", "current")
    assert same["slug"] == "current"
    assert [row["slug"] for row in _live_rows(provider, entity_id=1)] == ["current"]
    assert len(_all_rows(provider)) == 1
