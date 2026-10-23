"""S3 tests: slug registry - uniqueness, normalization, stable SLUG_TAKEN.

Mandatory S3 coverage is mapped in the test names:
1. uniqueness inside one entity_type
2. the same slug for different entity types
3. an explicitly provided slug with an invalid format
4. concurrent registration through different connections
5. concurrent registration through separate processes
6. stable SLUG_TAKEN on conflict
7. rollback on a write error
8. normalization and strict case comparison
9. behaviour of repeated registration of the same slug
10. regression of the S1/S2 contracts (run separately, see the S3 report)

History lifecycle, slug change and HTTP behaviour belong to S4/S8 and are
intentionally NOT implemented or tested here.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from ai_framework.content.slug import Slug
from showcases.videoshop.infrastructure.slug_registry import (
    SLUG_PATTERN,
    STATE_LIVE,
    STATE_RELEASED,
    TABLE,
    InvalidSlug,
    SlugError,
    SlugRegistry,
    SlugTaken,
    normalize_slug,
    validate_slug,
)
from showcases.videoshop.infrastructure.migrations import S3_MIGRATIONS
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider

REPO_ROOT = Path(__file__).resolve().parents[3]

#: derived, so a later migration step cannot silently weaken these tests
EXPECTED_SCHEMA_VERSION = max(step.version for step in S3_MIGRATIONS)


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "s3_slug.db")


@pytest.fixture
def provider(db_path) -> VideoShopSQLiteProvider:
    return VideoShopSQLiteProvider(db_path=db_path)


@pytest.fixture
def registry(provider) -> SlugRegistry:
    registry = SlugRegistry(provider)
    assert registry.migrate() == EXPECTED_SCHEMA_VERSION
    return registry


def _rows(provider: VideoShopSQLiteProvider, entity_type: str | None = None) -> list[dict]:
    with provider.transaction() as tx:
        if entity_type is None:
            rows = tx.fetchall(f"SELECT * FROM {TABLE} ORDER BY entity_type, slug")
        else:
            rows = tx.fetchall(
                f"SELECT * FROM {TABLE} WHERE entity_type = ? ORDER BY slug", (entity_type,)
            )
    return [dict(row) for row in rows]


# --- 1. uniqueness inside one entity_type --------------------------------


def test_slug_is_unique_within_entity_type(registry, provider):
    first = registry.register("product", "oak-table", 1)
    assert first["state"] == STATE_LIVE
    assert first["entity_id"] == 1

    with pytest.raises(SlugTaken) as excinfo:
        registry.register("product", "oak-table", 2)

    assert excinfo.value.code == "SLUG_TAKEN"
    assert excinfo.value.held_by == 1
    assert len(_rows(provider, "product")) == 1


# --- 2. the same slug for different entity types -------------------------


def test_same_slug_is_allowed_for_different_entity_types(registry, provider):
    registry.register("product", "oak", 1)
    registry.register("category", "oak", 1)

    assert len(_rows(provider)) == 2
    assert registry.get("product", "oak")["entity_id"] == 1
    assert registry.get("category", "oak")["entity_id"] == 1


# --- 3. explicitly provided slug with an invalid format ------------------


@pytest.mark.parametrize(
    "candidate",
    [
        "UPPER",
        "with space",
        "under_score",
        "trailing-",
        "-leading",
        "double--dash",
        "юникод",
        "",
        "  padded  ",
        "a" * 256,
        "dot.name",
        "slash/name",
        "tab\there",
    ],
)
def test_invalid_slug_format_is_rejected(registry, candidate):
    with pytest.raises(InvalidSlug):
        validate_slug(candidate)
    with pytest.raises(InvalidSlug):
        registry.register("product", candidate, 1)


@pytest.mark.parametrize("candidate", ["a", "a-b", "a1-b2", "0", "a-0-b", "x" * 255])
def test_valid_slug_format_is_accepted(registry, candidate):
    validate_slug(candidate)
    record = registry.register("product", candidate, 1)
    assert record["slug"] == candidate


# --- 4. concurrent registration through different connections ------------


def test_concurrent_registration_two_connections(db_path):
    registry = SlugRegistry(VideoShopSQLiteProvider(db_path=db_path))
    registry.migrate()

    barrier = threading.Barrier(2)
    lock = threading.Lock()
    outcomes: list[str] = []

    def worker(entity_id: int) -> None:
        local = SlugRegistry(VideoShopSQLiteProvider(db_path=db_path))
        barrier.wait()
        try:
            local.register("product", "race-slug", entity_id)
            outcome = "OK"
        except SlugTaken:
            outcome = "SLUG_TAKEN"
        except Exception as exc:  # noqa: BLE001 - reported to the assertion below
            outcome = f"ERR:{type(exc).__name__}"
        with lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=worker, args=(index,)) for index in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["OK", "SLUG_TAKEN"], outcomes
    probe = VideoShopSQLiteProvider(db_path=db_path)
    rows = _rows(probe, "product")
    assert len(rows) == 1
    assert rows[0]["state"] == STATE_LIVE


# --- 5. concurrent registration through separate processes ---------------


WORKER_SOURCE = (
    "import sys\n"
    "from showcases.videoshop.infrastructure.slug_registry import SlugRegistry, SlugTaken\n"
    "from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider\n"
    "db_path, entity_id = sys.argv[1], int(sys.argv[2])\n"
    "registry = SlugRegistry(VideoShopSQLiteProvider(db_path=db_path))\n"
    "try:\n"
    "    registry.register('product', 'process-race', entity_id)\n"
    "    print('OK')\n"
    "except SlugTaken:\n"
    "    print('SLUG_TAKEN')\n"
    "except Exception as exc:\n"
    "    print('ERR:%s' % type(exc).__name__)\n"
)


def test_concurrent_registration_two_processes(tmp_path):
    db_path = str(tmp_path / "s3_process.db")
    registry = SlugRegistry(VideoShopSQLiteProvider(db_path=db_path))
    registry.migrate()

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONIOENCODING"] = "utf-8"

    processes = [
        subprocess.Popen(
            [sys.executable, "-B", "-c", WORKER_SOURCE, db_path, str(entity_id)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for entity_id in (1, 2)
    ]
    outcomes = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=120)
        outcomes.append((stdout.strip(), stderr.strip()))

    results = sorted(result for result, _ in outcomes)
    assert results == ["OK", "SLUG_TAKEN"], outcomes
    assert all(not err for _, err in outcomes), outcomes

    rows = _rows(VideoShopSQLiteProvider(db_path=db_path), "product")
    assert len(rows) == 1
    assert rows[0]["slug"] == "process-race"


# --- 6. stable SLUG_TAKEN on conflict ------------------------------------


def test_slug_taken_is_stable_and_typed(registry):
    registry.register("product", "taken-slug", 7)

    with pytest.raises(SlugTaken) as live_conflict:
        registry.register("product", "taken-slug", 8)
    error = live_conflict.value
    assert error.code == "SLUG_TAKEN"
    assert isinstance(error, SlugError)
    assert error.entity_type == "product"
    assert error.slug == "taken-slug"
    assert error.held_by == 7
    assert "SLUG_TAKEN" in str(error)

    assert registry.release("product", "taken-slug", 7) is True
    with pytest.raises(SlugTaken) as released_conflict:
        registry.register("product", "taken-slug", 8)
    assert released_conflict.value.code == "SLUG_TAKEN"
    assert released_conflict.value.held_by == 7


# --- 7. rollback on a write error ----------------------------------------


def test_rollback_leaves_no_partial_state(registry, provider):
    insert = (
        f"INSERT INTO {TABLE} (entity_type, slug, entity_id, state, created_at, released_at) "
        f"VALUES (?, ?, ?, 'live', '2026-01-01T00:00:00+00:00', NULL)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        with provider.transaction() as tx:
            tx.execute(insert, ("product", "rollback-slug", 1))
            tx.execute(insert, ("product", "rollback-slug", 2))  # PRIMARY KEY violation

    assert registry.get("product", "rollback-slug") is None, "the failed scope must not persist"

    # a refused registration must leave the existing row untouched
    registry.register("product", "kept-slug", 1)
    with pytest.raises(SlugTaken):
        registry.register("product", "kept-slug", 2)
    row = registry.get("product", "kept-slug")
    assert row["entity_id"] == 1
    assert row["state"] == STATE_LIVE
    assert len(_rows(provider, "product")) == 1


# --- 8. normalization and strict case comparison -------------------------


def test_normalization_and_strict_case_comparison(registry, provider):
    assert normalize_slug("  Some_Slug  ") == "some-slug"
    assert normalize_slug("a--b") == "a-b"
    assert normalize_slug("Hello World") == "hello-world"
    with pytest.raises(InvalidSlug):
        normalize_slug("Юникод")  # normalization does not transliterate

    # the S3 pattern is in parity with the framework value object
    assert SLUG_PATTERN.pattern == Slug("a").pattern

    registry.register("product", "abc", 1)

    # (a) the API boundary rejects a non-conforming spelling instead of repairing it
    with pytest.raises(InvalidSlug):
        registry.get("product", "ABC")
    with pytest.raises(InvalidSlug):
        registry.register("product", "ABC", 2)

    # (b) the stored comparison is strict at the database level (BINARY collation)
    with provider.transaction() as tx:
        exact = tx.fetchone(
            f"SELECT * FROM {TABLE} WHERE entity_type = ? AND slug = ?", ("product", "abc")
        )
        upper = tx.fetchone(
            f"SELECT * FROM {TABLE} WHERE entity_type = ? AND slug = ?", ("product", "ABC")
        )
    assert exact is not None
    assert upper is None, "SQLite must not treat 'abc' and 'ABC' as equal"

    normalized = normalize_slug("Some Slug")
    assert registry.register("product", normalized, 2)["slug"] == "some-slug"


# --- 9. repeated registration of the same slug ---------------------------


def test_repeated_registration_of_the_same_slug(registry, provider):
    first = registry.register("product", "dup-slug", 1)
    second = registry.register("product", "dup-slug", 1)
    assert first == second, "re-registering the same live slug is idempotent"
    assert len(_rows(provider, "product")) == 1

    assert registry.release("product", "dup-slug", 1) is True
    released = registry.get("product", "dup-slug")
    assert released["state"] == STATE_RELEASED
    assert released["released_at"] is not None

    with pytest.raises(SlugTaken):
        registry.register("product", "dup-slug", 1)  # even for the same entity (S3)
    with pytest.raises(SlugTaken):
        registry.register("product", "dup-slug", 2)
    assert len(_rows(provider, "product")) == 1


# --- supporting behaviour: release, schema requirement, value contract ---


def test_release_transitions_and_ownership(registry):
    registry.register("product", "owned-slug", 1)

    assert registry.release("product", "unknown-slug", 1) is False
    with pytest.raises(SlugTaken):
        registry.release("product", "owned-slug", 2)
    assert registry.release("product", "owned-slug", 1) is True
    assert registry.release("product", "owned-slug", 1) is False


def test_registry_requires_migration(db_path):
    provider = VideoShopSQLiteProvider(db_path=db_path)
    registry = SlugRegistry(provider)

    with pytest.raises(sqlite3.OperationalError):
        registry.register("product", "no-table", 1)
    with pytest.raises(sqlite3.OperationalError):
        registry.get("product", "no-table")


@pytest.mark.parametrize("entity_type", ["Product", "with space", "", "1bad", "x" * 65, "dash-type"])
def test_invalid_entity_type_is_rejected(registry, entity_type):
    with pytest.raises(InvalidSlug):
        registry.register(entity_type, "valid-slug", 1)


@pytest.mark.parametrize("entity_id", [0, -1, "1", True, None, 1.5])
def test_invalid_entity_id_is_rejected(registry, entity_id):
    with pytest.raises(InvalidSlug):
        registry.register("product", "valid-slug", entity_id)
