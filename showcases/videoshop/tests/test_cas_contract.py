"""S2 RED tests: CAS (compare-and-swap) contract of the VideoShop SQLite provider.

Contract under test (to be implemented in a separate, not-yet-authorized GREEN phase)::

    provider.update_record_cas(entity_name, entity_id, payload, expected_version) -> CasResult

    CasResult.status           in {"updated", "conflict", "not_found"}
    CasResult.record           dict with the updated row       (status == "updated")
    CasResult.expected_version int                             (status == "conflict")
    CasResult.actual_version   int                             (status == "conflict")

Rules encoded by these tests:
  1. the version is stored per record, in a ``version`` column of the entity table;
  2. the initial version is 0;
  3. check and update happen in ONE atomic SQL statement
     (``UPDATE ... SET ..., version = version + 1 WHERE id = ? AND version = ?``);
  4. ``rowcount == 0`` must be disambiguated: row exists -> conflict, row absent -> not_found;
  5. the inherited, non-versioned ``update_record`` path must NOT bypass the version
     guarantee for versioned entities - it must be refused with a defined error;
  6. CAS against an entity table without a ``version`` column must raise a defined error
     (``VersionColumnError``), never a silent success.

Scope notes (S2 RED phase only):
  * CAS is intentionally NOT implemented yet: the tests resolve the contract dynamically
    and fail with explicit "contract absent" messages, never with import errors;
  * the fixture creates a TEST-LOCAL table that contains a ``version`` column. No project
    schema, migration, table or field is created or changed here; the production DDL for
    ``version`` is a separate, not-yet-authorized change (planned for S3/S5).
"""
from __future__ import annotations

import asyncio
import importlib
import sqlite3
import threading
import time

import pytest

from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider

PROVIDER_MODULE = "showcases.videoshop.infrastructure.sqlite_provider"
CAS_ABSENT = "CAS contract absent: VideoShopSQLiteProvider.update_record_cas is not implemented"


# --- contract resolution helpers (never raise ImportError) ---------------


def _cas_fn(provider):
    fn = getattr(provider, "update_record_cas", None)
    if fn is None:
        pytest.fail(CAS_ABSENT)
    return fn


def _error_type(name: str):
    module = importlib.import_module(PROVIDER_MODULE)
    error_type = getattr(module, name, None)
    if error_type is None:
        pytest.fail(f"CAS contract absent: {name} is not defined in {PROVIDER_MODULE}")
    return error_type


# --- fixtures (test-local schema, not a project schema) ------------------


def _create_versioned_table(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE items ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name TEXT,"
        " version INTEGER NOT NULL DEFAULT 0)"
    )
    conn.commit()
    conn.close()


def _create_table_without_version(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE plain_items (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()


def _insert_row(db_path: str, name: str, entity_id: int = 1) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO items (id, name) VALUES (?, ?)", (entity_id, name))
    conn.commit()
    conn.close()


def _insert_plain_row(db_path: str, name: str, entity_id: int = 1) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO plain_items (id, name) VALUES (?, ?)", (entity_id, name))
    conn.commit()
    conn.close()


def _read_row(db_path: str, entity_id: int = 1):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM items WHERE id = ?", (entity_id,)).fetchone()
    conn.close()
    return None if row is None else dict(row)


def _read_unique_row(db_path: str, entity_id: int):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM unique_items WHERE id = ?", (entity_id,)).fetchone()
    conn.close()
    return None if row is None else dict(row)


@pytest.fixture
def db_path(tmp_path) -> str:
    path = str(tmp_path / "cas.db")
    _create_versioned_table(path)
    return path


@pytest.fixture
def provider(db_path) -> VideoShopSQLiteProvider:
    return VideoShopSQLiteProvider(db_path=db_path)


# --- 1. successful CAS ---------------------------------------------------


def test_cas_updates_record_with_expected_version(provider, db_path):
    cas = _cas_fn(provider)
    _insert_row(db_path, "seed")

    result = cas("items", 1, {"name": "renamed"}, 0)

    assert result.status == "updated"
    assert result.record["name"] == "renamed"
    row = _read_row(db_path)
    assert row["name"] == "renamed"
    assert row["version"] == 1


# --- 2. a successful CAS increments the version --------------------------


def test_successful_cas_increments_version_by_one(provider, db_path):
    cas = _cas_fn(provider)
    _insert_row(db_path, "seed")

    first = cas("items", 1, {"name": "first"}, 0)
    assert first.status == "updated"
    assert first.record["version"] == 1

    second = cas("items", 1, {"name": "second"}, 1)
    assert second.status == "updated"
    assert second.record["version"] == 2
    assert _read_row(db_path)["version"] == 2


# --- 3./4. stale version: no change, conflict reported with versions -----


def test_stale_version_does_not_change_record(provider, db_path):
    cas = _cas_fn(provider)
    _insert_row(db_path, "seed")
    assert cas("items", 1, {"name": "first"}, 0).status == "updated"

    stale = cas("items", 1, {"name": "second"}, 0)

    assert stale.status == "conflict"
    row = _read_row(db_path)
    assert row["name"] == "first", "a losing CAS must not modify the record"
    assert row["version"] == 1, "a losing CAS must not change the version"


def test_conflict_reports_expected_and_actual_version(provider, db_path):
    cas = _cas_fn(provider)
    _insert_row(db_path, "seed")
    cas("items", 1, {"name": "first"}, 0)

    stale = cas("items", 1, {"name": "second"}, 0)

    assert stale.status == "conflict"
    assert stale.expected_version == 0
    assert stale.actual_version == 1


# --- 5. missing record is not a version conflict -------------------------


def test_missing_record_is_reported_as_not_found_not_conflict(provider):
    cas = _cas_fn(provider)

    result = cas("items", 999, {"name": "ghost"}, 0)

    assert result.status == "not_found"
    assert result.status != "conflict"


# --- 6. two connections cannot apply incompatible updates to one version -


def test_two_connections_cannot_apply_the_same_version(db_path):
    first = VideoShopSQLiteProvider(db_path=db_path)
    second = VideoShopSQLiteProvider(db_path=db_path)
    cas_first = _cas_fn(first)
    cas_second = _cas_fn(second)
    _insert_row(db_path, "seed")

    first_result = cas_first("items", 1, {"name": "from-first"}, 0)
    second_result = cas_second("items", 1, {"name": "from-second"}, 0)

    assert sorted([first_result.status, second_result.status]) == ["conflict", "updated"]
    row = _read_row(db_path)
    assert row["version"] == 1, "exactly one version bump must have been applied"
    assert row["name"] == "from-first", "only the winning payload may be stored"


# --- 7. competing CAS does not lose updates ------------------------------


def test_competing_cas_does_not_lose_updates(db_path):
    probe = VideoShopSQLiteProvider(db_path=db_path)
    _cas_fn(probe)  # contract must exist before the concurrent scenario
    _insert_row(db_path, "seed")

    attempts_per_thread = 10
    barrier = threading.Barrier(2)
    lock = threading.Lock()
    succeeded_versions: list[int] = []
    problems: list[str] = []

    def worker(tag: str) -> None:
        local_provider = VideoShopSQLiteProvider(db_path=db_path)
        local_cas = getattr(local_provider, "update_record_cas", None)
        if local_cas is None:
            with lock:
                problems.append(f"{tag}: CAS API absent")
            barrier.wait()
            return
        barrier.wait()
        completed = 0
        deadline = time.time() + 30
        while completed < attempts_per_thread and time.time() < deadline:
            row = _read_row(db_path)
            if row is None:
                with lock:
                    problems.append(f"{tag}: row disappeared")
                return
            try:
                result = local_cas("items", 1, {"name": f"{tag}-{completed}"}, row["version"])
            except Exception as exc:  # retry on lock contention
                with lock:
                    problems.append(f"{tag}: {type(exc).__name__}")
                time.sleep(0.01)
                continue
            status = getattr(result, "status", None)
            if status == "updated":
                with lock:
                    succeeded_versions.append(row["version"])
                completed += 1
            elif status == "conflict":
                time.sleep(0.005)
            else:
                with lock:
                    problems.append(f"{tag}: unexpected status {status!r}")
                return

    threads = [threading.Thread(target=worker, args=(tag,)) for tag in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert problems == [], f"no errors expected during CAS contention, got {problems}"
    assert len(succeeded_versions) == 2 * attempts_per_thread
    assert sorted(succeeded_versions) == list(range(2 * attempts_per_thread)), (
        "every successful CAS must consume exactly one distinct version "
        "(no lost update)"
    )
    assert _read_row(db_path)["version"] == 2 * attempts_per_thread


# --- 8. the ordinary update path must not bypass version guarantees ------


def test_ordinary_update_path_is_refused_for_versioned_entities(provider, db_path):
    error_type = _error_type("VersionedEntityUpdateError")
    _insert_row(db_path, "seed")

    with pytest.raises(error_type):
        asyncio.run(provider.update_record("items", 1, {"name": "bypass"}))

    row = _read_row(db_path)
    assert row["name"] == "seed"
    assert row["version"] == 0


# --- 9. the provider stays usable after a conflict -----------------------


def test_connection_usable_after_conflict(provider, db_path):
    cas = _cas_fn(provider)
    _insert_row(db_path, "seed")
    assert cas("items", 1, {"name": "first"}, 0).status == "updated"

    conflict = cas("items", 1, {"name": "stale"}, 0)
    assert conflict.status == "conflict"

    retry = cas("items", 1, {"name": "second"}, conflict.actual_version)
    assert retry.status == "updated"
    assert retry.record["version"] == 2
    assert _read_row(db_path)["name"] == "second"

    # the S1 transaction API keeps working after a CAS conflict
    with provider.transaction() as tx:
        tx.execute("UPDATE items SET name = ? WHERE id = ?", ("via-transaction", 1))
    assert _read_row(db_path)["name"] == "via-transaction"
    assert provider.active_transaction is None


# --- 10. CAS on an entity table without a version column -----------------


def test_cas_on_table_without_version_column_raises_defined_error(db_path):
    provider = VideoShopSQLiteProvider(db_path=db_path)
    cas = _cas_fn(provider)
    error_type = _error_type("VersionColumnError")
    _create_table_without_version(db_path)
    _insert_plain_row(db_path, "plain")

    with pytest.raises(error_type):
        cas("plain_items", 1, {"name": "renamed"}, 0)

    conn = sqlite3.connect(db_path)
    stored = conn.execute("SELECT name FROM plain_items WHERE id = 1").fetchone()[0]
    conn.close()
    assert stored == "plain", "a failed CAS must not modify the record"


# --- 11. rollback / error behaviour matches the contract -----------------


def test_cas_rollback_behaviour_matches_contract(db_path):
    """Mandatory item: rollback behaviour must match the contract.

    ``tx.update_record_cas`` is NOT part of S2, so this test covers the contract
    of the CAS statement itself: when the atomic UPDATE fails (constraint
    violation), no partial change is committed, the provider keeps no open
    transaction, and both the CAS path and the S1 transaction API stay usable.
    """
    provider = VideoShopSQLiteProvider(db_path=db_path)
    cas = _cas_fn(provider)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE unique_items ("
        " id INTEGER PRIMARY KEY,"
        " name TEXT UNIQUE,"
        " version INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute("INSERT INTO unique_items (id, name) VALUES (1, 'taken')")
    conn.execute("INSERT INTO unique_items (id, name) VALUES (2, 'free')")
    conn.commit()
    conn.close()

    with pytest.raises(sqlite3.IntegrityError):
        cas("unique_items", 2, {"name": "taken"}, 0)

    row = _read_unique_row(db_path, 2)
    assert row["name"] == "free", "a failed CAS must not leave a partial change"
    assert row["version"] == 0, "a failed CAS must not bump the version"
    assert provider.active_transaction is None

    ok = cas("unique_items", 2, {"name": "renamed"}, 0)
    assert ok.status == "updated"
    assert ok.record["version"] == 1

    with provider.transaction() as tx:
        tx.execute("UPDATE unique_items SET name = ? WHERE id = ?", ("via-transaction", 2))
    assert _read_unique_row(db_path, 2)["name"] == "via-transaction"
    assert provider.active_transaction is None


# --- 12. contract violation: 'version' inside the payload ----------------


def test_payload_must_not_contain_version(provider, db_path):
    cas = _cas_fn(provider)
    error_type = _error_type("CasContractError")
    _insert_row(db_path, "seed")

    with pytest.raises(error_type):
        cas("items", 1, {"name": "attempt", "version": 0}, 0)

    row = _read_row(db_path)
    assert row["name"] == "seed"
    assert row["version"] == 0


# --- 13. the guard must not block non-versioned entities -----------------


def test_ordinary_update_still_works_for_non_versioned_entities(provider, db_path):
    _create_table_without_version(db_path)
    _insert_plain_row(db_path, "plain")

    updated = asyncio.run(provider.update_record("plain_items", 1, {"name": "renamed"}))

    assert updated["name"] == "renamed"
    conn = sqlite3.connect(db_path)
    stored = conn.execute("SELECT name FROM plain_items WHERE id = 1").fetchone()[0]
    conn.close()
    assert stored == "renamed"
