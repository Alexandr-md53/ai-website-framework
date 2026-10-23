"""S2 corrective patch tests: F-1 (schema detection), F-2 (insert), F-3 (delete).

Authorized policy under test (S2 corrective patch, showcase level only):

* **F-1** - the version column is detected by normalisation (``strip`` +
  ``casefold``): ``version``, ``VERSION``, ``Version`` and the whitespace
  variant ``"version "`` are all recognised. The *declared* column name is used
  (quoted) in SQL, because SQLite is case-insensitive for identifiers but treats
  ``"version "`` as a distinct name. Several version-like columns in one table
  are rejected with an explicit ``VersionColumnError`` (fail-closed).
* **F-2** - ``insert`` must not accept a caller-provided version for a versioned
  entity: the provider owns the version and the initial value is 0.
* **F-3** - the ordinary ``delete_record`` path is refused for versioned
  entities; a version-checked delete is a separate operation and is NOT
  implemented in S2.
* **Fail-closed** - a schema-detection error must never be read as "not
  versioned": ordinary update/insert/delete then fail instead of proceeding.
* **Non-versioned tables** keep the inherited behaviour.
* **F-4 rule (architecture policy)** - the guard is NOT a security boundary
  against raw SQL; ``transaction().execute(...)`` and private connection access
  stay internal infrastructure mechanisms and must not be used by VideoShop
  services to update business entities. This is recorded by a characterisation
  test, not enforced.

No production schema, migration or table is created or changed here: every table
used below lives in the pytest ``tmp_path``.
"""
from __future__ import annotations

import asyncio
import sqlite3

import pytest

from showcases.videoshop.infrastructure.sqlite_provider import (
    CasContractError,
    CasError,
    VersionColumnError,
    VersionedEntityDeleteError,
    VersionedEntityInsertError,
    VersionedEntityUpdateError,
    VideoShopSQLiteProvider,
)


# --- helpers -------------------------------------------------------------


def _make_versioned(db_path: str, declaration: str = "version INTEGER NOT NULL DEFAULT 0", seed: bool = True) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(f"CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, {declaration})")
    if seed:
        conn.execute("INSERT INTO items (id, name) VALUES (1, 'seed')")
    conn.commit()
    conn.close()


def _make_ambiguous(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        'CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, '
        'version INTEGER NOT NULL DEFAULT 0, "version " INTEGER)'
    )
    conn.execute("INSERT INTO items (id, name) VALUES (1, 'seed')")
    conn.commit()
    conn.close()


def _make_plain(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE plain_items (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO plain_items (id, name) VALUES (1, 'plain')")
    conn.commit()
    conn.close()


def _row(db_path: str, table: str = "items", entity_id: int = 1):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (entity_id,)).fetchone()
    conn.close()
    return None if row is None else dict(row)


def _count(db_path: str, table: str = "items") -> int:
    conn = sqlite3.connect(db_path)
    total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return int(total)


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "guards.db")


@pytest.fixture
def provider(db_path) -> VideoShopSQLiteProvider:
    return VideoShopSQLiteProvider(db_path=db_path)


# --- F-1: case-insensitive detection -------------------------------------


@pytest.mark.parametrize(
    "declaration, column",
    [
        ("VERSION INTEGER NOT NULL DEFAULT 0", "VERSION"),
        ("Version INTEGER NOT NULL DEFAULT 0", "Version"),
    ],
)
def test_version_column_is_detected_case_insensitively(declaration, column, db_path):
    """F-1: detection is case-insensitive; SQL uses the declared column name.

    ``sqlite3.Row``/``dict(row)`` keys use the *declared* spelling, so the
    returned record is addressed with ``column`` while ``actual_version`` always
    reports the version independently of spelling.
    """
    _make_versioned(db_path, declaration)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    with pytest.raises(VersionedEntityUpdateError):
        asyncio.run(provider.update_record("items", 1, {"name": "bypass"}))

    result = provider.update_record_cas("items", 1, {"name": "via-cas"}, 0)
    assert result.status == "updated"
    assert result.actual_version == 1
    assert result.record[column] == 1
    row = _row(db_path)
    assert row["name"] == "via-cas"
    assert row[column] == 1


def test_version_column_with_trailing_space_is_detected(db_path):
    """Whitespace variant: detection is normalised; SQL uses the declared name."""
    _make_versioned(db_path, '"version " INTEGER NOT NULL DEFAULT 0')
    provider = VideoShopSQLiteProvider(db_path=db_path)

    with pytest.raises(VersionedEntityUpdateError):
        asyncio.run(provider.update_record("items", 1, {"name": "bypass"}))

    result = provider.update_record_cas("items", 1, {"name": "via-cas"}, 0)
    assert result.status == "updated"
    row = _row(db_path)
    assert row["name"] == "via-cas"
    assert row["version "] == 1


def test_several_version_like_columns_are_rejected(db_path):
    _make_ambiguous(db_path)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    with pytest.raises(VersionColumnError):
        asyncio.run(provider.update_record("items", 1, {"name": "bypass"}))
    with pytest.raises(VersionColumnError):
        provider.update_record_cas("items", 1, {"name": "via-cas"}, 0)

    row = _row(db_path)
    assert row["name"] == "seed"
    assert row["version"] == 0


# --- F-2: insert must not accept a caller-provided version ---------------


def test_insert_with_version_is_rejected_for_versioned_entity(db_path):
    _make_versioned(db_path, seed=False)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    with pytest.raises(VersionedEntityInsertError):
        asyncio.run(provider.insert("items", {"id": 5, "name": "v99", "version": 99}))

    assert _count(db_path) == 0, "the rejected insert must not create a row"
    conn = sqlite3.connect(db_path)
    stored = conn.execute("SELECT COUNT(*) FROM items WHERE version = 99").fetchone()[0]
    conn.close()
    assert stored == 0


def test_insert_rejects_version_key_case_insensitively(db_path):
    _make_versioned(db_path, seed=False)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    with pytest.raises(VersionedEntityInsertError):
        asyncio.run(provider.insert("items", {"id": 6, "name": "v7", "VERSION": 7}))

    assert _count(db_path) == 0


def test_insert_without_version_starts_at_zero(db_path):
    _make_versioned(db_path, seed=False)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    inserted = asyncio.run(provider.insert("items", {"id": 7, "name": "fresh"}))

    assert inserted["version"] == 0
    assert provider.update_record_cas("items", 7, {"name": "cas"}, 0).status == "updated"


# --- F-3: ordinary delete refused for versioned entities -----------------


def test_delete_is_rejected_for_versioned_entity(db_path):
    _make_versioned(db_path)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    with pytest.raises(VersionedEntityDeleteError):
        asyncio.run(provider.delete_record("items", 1))

    row = _row(db_path)
    assert row is not None, "the record must survive a refused delete"
    assert row["name"] == "seed"
    assert row["version"] == 0


# --- non-versioned tables keep normal behaviour --------------------------


def test_non_versioned_entity_keeps_normal_behaviour(db_path):
    _make_plain(db_path)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    inserted = asyncio.run(provider.insert("plain_items", {"id": 2, "name": "second"}))
    assert inserted["name"] == "second"

    updated = asyncio.run(provider.update_record("plain_items", 1, {"name": "renamed"}))
    assert updated["name"] == "renamed"

    assert asyncio.run(provider.delete_record("plain_items", 2)) is True
    assert _count(db_path, "plain_items") == 1


# --- fail-closed: schema-detection errors must not allow writes ----------


@pytest.mark.parametrize(
    "entity",
    ['items"; DROP TABLE items; --', "items name", "no_such_table", ""],
)
def test_schema_detection_failure_does_not_allow_writes(entity, db_path):
    _make_versioned(db_path)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    operations = (
        ("update", lambda: asyncio.run(provider.update_record(entity, 1, {"name": "pwned"}))),
        ("insert", lambda: asyncio.run(provider.insert(entity, {"name": "pwned"}))),
        ("delete", lambda: asyncio.run(provider.delete_record(entity, 1))),
        ("cas", lambda: provider.update_record_cas(entity, 1, {"name": "pwned"}, 0)),
    )
    for label, operation in operations:
        with pytest.raises((sqlite3.Error, CasError)) as excinfo:
            operation()
        assert excinfo.value is not None, f"{label} must fail, not write"

    row = _row(db_path)
    assert row is not None, "the real table must be untouched"
    assert row["name"] == "seed"
    assert row["version"] == 0
    assert _count(db_path) == 1


def test_unavailable_database_fails_closed(tmp_path):
    provider = VideoShopSQLiteProvider(db_path=str(tmp_path / "missing_dir" / "shop.db"))

    for operation in (
        lambda: asyncio.run(provider.update_record("items", 1, {"name": "x"})),
        lambda: asyncio.run(provider.insert("items", {"name": "x"})),
        lambda: asyncio.run(provider.delete_record("items", 1)),
        lambda: provider.update_record_cas("items", 1, {"name": "x"}, 0),
    ):
        with pytest.raises((sqlite3.Error, CasError)):
            operation()


# --- contract detail: version key in the CAS payload ---------------------


def test_cas_rejects_version_key_case_insensitively(provider, db_path):
    _make_versioned(db_path)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    with pytest.raises(CasContractError):
        provider.update_record_cas("items", 1, {"name": "x", "VERSION": 2}, 0)

    row = _row(db_path)
    assert row["name"] == "seed"
    assert row["version"] == 0


# --- F-4 rule (characterisation, not enforcement) ------------------------


def test_raw_transaction_path_is_an_internal_escape_hatch(db_path):
    """F-4 policy: the guard is not a boundary against raw SQL.

    ``transaction().execute(...)`` is an internal infrastructure mechanism: it
    can write without the version contract. This test records that behaviour so
    the rule stays explicit - VideoShop services must not use it to update
    business entities.
    """
    _make_versioned(db_path)
    provider = VideoShopSQLiteProvider(db_path=db_path)

    with provider.transaction() as tx:
        tx.execute("UPDATE items SET name = 'raw' WHERE id = 1")

    row = _row(db_path)
    assert row["name"] == "raw"
    assert row["version"] == 0, "the raw path does not bump the version (documented)"
