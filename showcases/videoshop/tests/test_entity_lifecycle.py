"""S4 tests: entity lifecycle integrated with the slug registry (TEST ENTITIES ONLY).

Covered contract scenarios (16):

1.  create + first slug
2.  create with a taken slug -> nothing is created
3.  create with a released slug -> rejected (no re-use)
4.  create with an invalid slug -> nothing is created
5.  rename of a versioned entity -> version + 1 and history kept
6.  rename of a non-versioned entity -> slug and fields replaced
7.  rename to a taken slug -> the CAS bump AND the slug stay untouched (rollback)
8.  rename to the same slug -> literal no-op
9.  history resolution a -> b -> c is a SINGLE hop
10. delete -> slug released, entity hard-deleted
11. unknown / deleted / other-type slugs -> not_found
12. CAS conflict -> the whole rename (and delete) is rolled back
13. concurrent rename through two processes -> one winner, no partial rename
14. concurrent create with the same slug -> one entity, one live slug
15. two entities renaming to the same slug -> one winner, no orphan live slug
16. database integrity after mixed lifecycles (<=1 live per entity, no orphans)

Test tables are created by the tests themselves in ``tmp_path``: no production
table, migration or HTTP route is created (D8).
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from showcases.videoshop.infrastructure.migrations import S3_MIGRATIONS
from showcases.videoshop.infrastructure.slug_registry import (
    TABLE,
    InvalidSlug,
    SlugRegistry,
    SlugTaken,
)
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.services.entity_lifecycle import (
    CasConflict,
    EntityLifecycleService,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPECTED_SCHEMA_VERSION = max(step.version for step in S3_MIGRATIONS)

#: explicit test entity types (D7) - test-only names, not a production list
ENTITY_TYPE_VERSIONED = "test_article"
ENTITY_TYPE_PLAIN = "test_page"
VERSIONED_TABLE = "test_articles"
PLAIN_TABLE = "test_pages"
ENTITY_TABLES = {
    ENTITY_TYPE_VERSIONED: VERSIONED_TABLE,
    ENTITY_TYPE_PLAIN: PLAIN_TABLE,
}


# --- fixtures ------------------------------------------------------------


def _create_test_tables(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS test_articles ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " title TEXT,"
        " version INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS test_pages ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " title TEXT)"
    )
    conn.commit()
    conn.close()


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "s4_lifecycle.db")


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
    _create_test_tables(db_path)
    return EntityLifecycleService(
        provider, registry, ENTITY_TYPE_VERSIONED, VERSIONED_TABLE, versioned=True
    )


@pytest.fixture
def pages(provider, registry, db_path) -> EntityLifecycleService:
    _create_test_tables(db_path)
    return EntityLifecycleService(
        provider, registry, ENTITY_TYPE_PLAIN, PLAIN_TABLE, versioned=False
    )


# --- database-state helpers ---------------------------------------------


def _registry_rows(provider, entity_type=None, state=None) -> list[tuple]:
    sql = f"SELECT slug, entity_id FROM {TABLE} WHERE 1 = 1"
    params: list = []
    if entity_type is not None:
        sql += " AND entity_type = ?"
        params.append(entity_type)
    if state is not None:
        sql += " AND state = ?"
        params.append(state)
    sql += " ORDER BY slug"
    with provider.transaction() as tx:
        return [(row["slug"], row["entity_id"]) for row in tx.fetchall(sql, tuple(params))]


def _live(provider, entity_type=None) -> list[tuple]:
    return _registry_rows(provider, entity_type, "live")


def _released(provider, entity_type=None) -> list[tuple]:
    return _registry_rows(provider, entity_type, "released")


def _entity(provider, table: str, entity_id: int):
    with provider.transaction() as tx:
        row = tx.fetchone(f"SELECT * FROM {table} WHERE id = ?", (entity_id,))
    return None if row is None else dict(row)


def _entity_count(provider, table: str) -> int:
    with provider.transaction() as tx:
        return int(tx.scalar(f"SELECT COUNT(*) FROM {table}"))


def _assert_integrity(provider, pairs: dict | None = None) -> None:
    """Whole-database invariants after any lifecycle sequence."""
    pairs = pairs or ENTITY_TABLES
    with provider.transaction() as tx:
        duplicated = tx.fetchall(
            f"SELECT entity_type, entity_id, COUNT(*) AS live_count FROM {TABLE} "
            f"WHERE state = 'live' GROUP BY entity_type, entity_id HAVING COUNT(*) > 1"
        )
        assert duplicated == [], [dict(row) for row in duplicated]
        live_rows = [dict(row) for row in tx.fetchall(f"SELECT * FROM {TABLE} WHERE state = 'live'")]
        for row in live_rows:
            table = pairs.get(row["entity_type"])
            assert table is not None, f"unknown entity_type in registry: {row['entity_type']}"
            present = tx.fetchone(f"SELECT 1 AS present FROM {table} WHERE id = ?", (row["entity_id"],))
            assert present is not None, (
                f"orphan live slug {row['slug']!r} for {row['entity_type']}#{row['entity_id']}"
            )


# --- 1. create + first slug ---------------------------------------------


def test_create_with_first_slug(articles, provider):
    created = articles.create("first-article", {"title": "First"})

    assert created["id"] == 1
    assert created["title"] == "First"
    assert created["version"] == 0
    assert _live(provider, ENTITY_TYPE_VERSIONED) == [("first-article", 1)]
    assert _released(provider, ENTITY_TYPE_VERSIONED) == []
    assert articles.resolve("first-article").is_current


# --- 2. create with a taken slug ----------------------------------------


def test_create_with_taken_slug_creates_nothing(articles, provider):
    articles.create("taken-slug", {"title": "One"})

    with pytest.raises(SlugTaken) as excinfo:
        articles.create("taken-slug", {"title": "Two"})

    assert excinfo.value.code == "SLUG_TAKEN"
    assert _entity_count(provider, VERSIONED_TABLE) == 1, "no entity row may survive"
    assert _live(provider, ENTITY_TYPE_VERSIONED) == [("taken-slug", 1)]


# --- 3. create with a released slug -------------------------------------


def test_create_with_released_slug_is_rejected(articles, provider):
    articles.create("old-slug", {"title": "One"})
    articles.rename(1, "new-slug", expected_version=0)

    with pytest.raises(SlugTaken):
        articles.create("old-slug", {"title": "Two"})

    assert _entity_count(provider, VERSIONED_TABLE) == 1
    assert _released(provider, ENTITY_TYPE_VERSIONED) == [("old-slug", 1)]


# --- 4. create with an invalid slug -------------------------------------


def test_create_with_invalid_slug_creates_nothing(articles, provider):
    with pytest.raises(InvalidSlug):
        articles.create("BAD SLUG", {"title": "X"})

    assert _entity_count(provider, VERSIONED_TABLE) == 0
    assert _live(provider) == [] and _released(provider) == []


# --- 5. rename of a versioned entity ------------------------------------


def test_rename_versioned_bumps_version_and_keeps_history(articles, provider):
    articles.create("old-slug", {"title": "T"})

    renamed = articles.rename(1, "new-slug", expected_version=0)

    assert renamed["version"] == 1
    assert _live(provider, ENTITY_TYPE_VERSIONED) == [("new-slug", 1)]
    assert _released(provider, ENTITY_TYPE_VERSIONED) == [("old-slug", 1)]


# --- 6. rename of a non-versioned entity --------------------------------


def test_rename_non_versioned_updates_slug_and_fields(pages, provider):
    pages.create("page-one", {"title": "Old"})

    renamed = pages.rename(1, "page-two", fields={"title": "New"})

    assert renamed["title"] == "New"
    assert _live(provider, ENTITY_TYPE_PLAIN) == [("page-two", 1)]
    assert _released(provider, ENTITY_TYPE_PLAIN) == [("page-one", 1)]


# --- 7. rename to a taken slug rolls everything back --------------------


def test_rename_to_taken_slug_rolls_back_cas_and_slug(articles, provider):
    articles.create("mine", {"title": "Mine"})
    articles.create("taken", {"title": "Taken"})

    with pytest.raises(SlugTaken):
        articles.rename(1, "taken", expected_version=0)

    row = _entity(provider, VERSIONED_TABLE, 1)
    assert row["version"] == 0, "the CAS version bump must be rolled back"
    assert row["title"] == "Mine"
    assert _live(provider, ENTITY_TYPE_VERSIONED) == [("mine", 1), ("taken", 2)]
    assert _released(provider, ENTITY_TYPE_VERSIONED) == [], "no partial rename"


# --- 8. rename to the same slug -----------------------------------------


def test_rename_to_same_slug_is_noop(articles, provider):
    articles.create("same-slug", {"title": "T"})

    result = articles.rename(1, "same-slug", expected_version=0)

    assert result["version"] == 0, "a literal no-op must not bump the version"
    assert _live(provider, ENTITY_TYPE_VERSIONED) == [("same-slug", 1)]
    assert _released(provider, ENTITY_TYPE_VERSIONED) == []


# --- 9. history resolution is a single hop ------------------------------


def test_history_redirects_are_single_hop(articles, provider):
    articles.create("a", {"title": "T"})
    articles.rename(1, "b", expected_version=0)
    articles.rename(1, "c", expected_version=1)

    first = articles.resolve("a")
    assert first.is_redirect
    assert first.current_slug == "c", "must point straight at the CURRENT slug"

    second = articles.resolve("b")
    assert second.is_redirect and second.current_slug == "c"

    current = articles.resolve("c")
    assert current.is_current and current.current_slug == "c"

    assert _released(provider, ENTITY_TYPE_VERSIONED) == [("a", 1), ("b", 1)]
    assert _live(provider, ENTITY_TYPE_VERSIONED) == [("c", 1)]


# --- 10. delete ---------------------------------------------------------


def test_delete_releases_slug_and_hard_deletes_entity(articles, provider, registry):
    articles.create("to-delete", {"title": "T"})

    result = articles.delete(1, expected_version=0)

    assert result["released_slug"] == "to-delete"
    assert _entity_count(provider, VERSIONED_TABLE) == 0, "hard delete"
    assert _live(provider, ENTITY_TYPE_VERSIONED) == []
    assert _released(provider, ENTITY_TYPE_VERSIONED) == [("to-delete", 1)]
    assert articles.resolve("to-delete").is_not_found

    with pytest.raises(SlugTaken):
        registry.register(ENTITY_TYPE_VERSIONED, "to-delete", 2)


# --- 11. unknown / deleted / other-type slugs ---------------------------


def test_unknown_and_deleted_slugs_are_not_found(articles, pages, provider):
    assert articles.resolve("never-existed").is_not_found

    pages.create("shared-name", {"title": "P"})
    assert articles.resolve("shared-name").is_not_found, "entity types are separate namespaces"

    articles.create("deleted-later", {"title": "T"})
    articles.delete(1, expected_version=0)
    assert articles.resolve("deleted-later").is_not_found
    assert pages.resolve("shared-name").is_current


# --- 12. CAS conflict rolls the operation back --------------------------


def test_cas_conflict_rolls_back_the_rename(articles, provider):
    articles.create("cas-slug", {"title": "T"})

    with pytest.raises(CasConflict) as excinfo:
        articles.rename(1, "cas-new", expected_version=99)

    assert excinfo.value.code == "CAS_CONFLICT"
    assert excinfo.value.actual_version == 0
    assert _entity(provider, VERSIONED_TABLE, 1)["version"] == 0
    assert _live(provider, ENTITY_TYPE_VERSIONED) == [("cas-slug", 1)]
    assert _released(provider, ENTITY_TYPE_VERSIONED) == []

    with pytest.raises(CasConflict):
        articles.delete(1, expected_version=99)
    assert _entity_count(provider, VERSIONED_TABLE) == 1
    assert _live(provider, ENTITY_TYPE_VERSIONED) == [("cas-slug", 1)]


# --- concurrency workers -------------------------------------------------


WORKER_SOURCE = (
    "import sys\n"
    "from showcases.videoshop.infrastructure.slug_registry import SlugRegistry, SlugTaken\n"
    "from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider\n"
    "from showcases.videoshop.services.entity_lifecycle import (\n"
    "    CasConflict, EntityLifecycleService)\n"
    "db, action, table, entity_type, entity_id, slug, expected = sys.argv[1:8]\n"
    "provider = VideoShopSQLiteProvider(db_path=db)\n"
    "service = EntityLifecycleService(\n"
    "    provider, SlugRegistry(provider), entity_type, table, versioned=True)\n"
    "try:\n"
    "    if action == 'rename':\n"
    "        service.rename(int(entity_id), slug, expected_version=int(expected))\n"
    "    else:\n"
    "        service.create(slug, {'title': 'worker'})\n"
    "    print('OK')\n"
    "except CasConflict:\n"
    "    print('CAS_CONFLICT')\n"
    "except SlugTaken:\n"
    "    print('SLUG_TAKEN')\n"
    "except Exception as exc:\n"
    "    print('ERR:%s' % type(exc).__name__)\n"
)


def _run_workers(db_path: str, jobs: list[tuple]) -> list[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-c",
                WORKER_SOURCE,
                db_path,
                action,
                table,
                entity_type,
                str(entity_id),
                slug,
                str(expected),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for (action, table, entity_type, entity_id, slug, expected) in jobs
    ]
    outputs = [process.communicate(timeout=180) for process in processes]
    assert all(not stderr for _, stderr in outputs), outputs
    return [stdout.strip() for stdout, _ in outputs]


# --- 13. concurrent rename ----------------------------------------------


def test_concurrent_rename_two_processes(articles, provider, db_path):
    articles.create("start-slug", {"title": "T"})

    results = _run_workers(
        db_path,
        [
            ("rename", VERSIONED_TABLE, ENTITY_TYPE_VERSIONED, 1, "race-a", 0),
            ("rename", VERSIONED_TABLE, ENTITY_TYPE_VERSIONED, 1, "race-b", 0),
        ],
    )

    assert sorted(results) == ["CAS_CONFLICT", "OK"], results
    assert _entity(provider, VERSIONED_TABLE, 1)["version"] == 1, "exactly one version bump"
    live = _live(provider, ENTITY_TYPE_VERSIONED)
    assert len(live) == 1 and live[0][1] == 1, live
    assert len(_released(provider, ENTITY_TYPE_VERSIONED)) == 1, "no partial rename"
    _assert_integrity(provider)


# --- 14. concurrent create with the same slug ---------------------------


def test_concurrent_create_same_slug_two_processes(provider, registry, db_path, articles):
    results = _run_workers(
        db_path,
        [
            ("create", VERSIONED_TABLE, ENTITY_TYPE_VERSIONED, 0, "dup-slug", 0),
            ("create", VERSIONED_TABLE, ENTITY_TYPE_VERSIONED, 0, "dup-slug", 0),
        ],
    )

    assert sorted(results) == ["OK", "SLUG_TAKEN"], results
    assert _entity_count(provider, VERSIONED_TABLE) == 1, "only the winner keeps an entity row"
    live = _live(provider, ENTITY_TYPE_VERSIONED)
    assert len(live) == 1 and live[0][0] == "dup-slug"
    _assert_integrity(provider)


# --- 15. two entities racing for the same new slug ----------------------


def test_concurrent_two_entities_rename_to_same_slug(articles, provider, db_path):
    articles.create("keep-one", {"title": "One"})
    articles.create("keep-two", {"title": "Two"})

    results = _run_workers(
        db_path,
        [
            ("rename", VERSIONED_TABLE, ENTITY_TYPE_VERSIONED, 1, "shared-slug", 0),
            ("rename", VERSIONED_TABLE, ENTITY_TYPE_VERSIONED, 2, "shared-slug", 0),
        ],
    )

    assert sorted(results) == ["OK", "SLUG_TAKEN"], results
    live = _live(provider, ENTITY_TYPE_VERSIONED)
    assert len(live) == 2, live
    assert sum(1 for slug, _ in live if slug == "shared-slug") == 1
    assert len(_released(provider, ENTITY_TYPE_VERSIONED)) == 1, "the loser keeps its slug live"
    _assert_integrity(provider)


# --- 16. integrity after mixed lifecycles -------------------------------


def test_database_integrity_after_mixed_lifecycles(articles, pages, provider):
    articles.create("one", {"title": "One"})
    articles.create("two", {"title": "Two"})
    articles.rename(1, "one-b", expected_version=0)

    with pytest.raises(CasConflict):
        articles.rename(2, "two-b", expected_version=7)  # stale version -> rolled back

    pages.create("page", {"title": "Page"})
    pages.rename(1, "page-b", fields={"title": "Page B"})

    articles.delete(2, expected_version=0)

    _assert_integrity(provider)

    assert articles.resolve("one").is_redirect
    assert articles.resolve("one").current_slug == "one-b"
    assert articles.resolve("one-b").is_current
    assert articles.resolve("two").is_not_found, "deleted entity"
    assert pages.resolve("page").is_redirect
    assert pages.resolve("page").current_slug == "page-b"
    assert _live(provider, ENTITY_TYPE_VERSIONED) == [("one-b", 1)]
    assert _live(provider, ENTITY_TYPE_PLAIN) == [("page-b", 1)]
    assert _released(provider, ENTITY_TYPE_VERSIONED) == [("one", 1), ("two", 2)]
