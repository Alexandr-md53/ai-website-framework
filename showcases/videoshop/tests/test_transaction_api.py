"""S1 contract tests: minimal transaction API of the VideoShop SQLite provider.

Covered requirements (S1):
1. explicit commit and rollback;
2. an exception inside the scope triggers rollback;
3. every operation inside the scope uses ONE AND THE SAME connection;
4. nested transactions are rejected with an explicit, documented error;
5. someone else's connection cannot be closed or reused by accident;
6. a failing rollback never hides the original error (both remain diagnosable);
7. behaviour is defined and tested for: commit twice, rollback outside a
   transaction, use after close;
8. the transaction API does not silently change existing interfaces.
"""
from __future__ import annotations

import asyncio
import sqlite3
import threading

import pytest

from showcases.videoshop.infrastructure.sqlite_provider import (
    NestedTransactionError,
    TransactionClosedError,
    TransactionStateError,
    VideoShopSQLiteProvider,
)


def _create_schema(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
    conn.commit()
    conn.close()


def _count(db_path: str, name: str | None = None) -> int:
    conn = sqlite3.connect(db_path)
    if name is None:
        row = conn.execute("SELECT COUNT(*) FROM items").fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM items WHERE name = ?", (name,)).fetchone()
    conn.close()
    return int(row[0])


@pytest.fixture
def db_path(tmp_path) -> str:
    path = str(tmp_path / "shop.db")
    _create_schema(path)
    return path


@pytest.fixture
def provider(db_path) -> VideoShopSQLiteProvider:
    return VideoShopSQLiteProvider(db_path=db_path)


# --- 1. successful transaction commits -----------------------------------


def test_successful_transaction_commits_changes(provider, db_path):
    with provider.transaction() as tx:
        tx.execute("INSERT INTO items (name) VALUES (?)", ("alpha",))
        tx.execute("INSERT INTO items (name) VALUES (?)", ("beta",))

    assert _count(db_path) == 2


# --- 2. explicit rollback reverts changes --------------------------------


def test_rollback_reverts_changes(provider, db_path):
    tx = provider.transaction()
    tx.execute("INSERT INTO items (name) VALUES (?)", ("alpha",))
    tx.rollback()

    assert _count(db_path) == 0


# --- 3. exception inside the scope triggers rollback ---------------------


def test_exception_inside_transaction_rolls_back(provider, db_path):
    with pytest.raises(ValueError, match="boom"):
        with provider.transaction() as tx:
            tx.execute("INSERT INTO items (name) VALUES (?)", ("alpha",))
            raise ValueError("boom")

    assert _count(db_path) == 0


# --- 4. after rollback the connection is usable again --------------------


def test_connection_is_usable_after_rollback(provider, db_path):
    tx = provider.transaction()
    tx.execute("INSERT INTO items (name) VALUES (?)", ("discarded",))
    tx.rollback()

    with provider.transaction() as tx2:
        tx2.execute("INSERT INTO items (name) VALUES (?)", ("kept",))

    assert _count(db_path) == 1
    assert _count(db_path, "kept") == 1
    assert _count(db_path, "discarded") == 0


# --- 5. one connection per transaction, invisible outside until commit ---


def test_transaction_uses_one_connection_invisible_outside(provider, db_path):
    with provider.transaction() as tx:
        tx.execute("INSERT INTO items (name) VALUES (?)", ("inside",))
        # the same connection sees its own uncommitted write
        assert tx.scalar("SELECT COUNT(*) FROM items") == 1
        # any other connection must not see it yet
        assert _count(db_path) == 0

    assert _count(db_path) == 1


# --- 6. independent connections do not mix transaction state -------------


def test_two_independent_connections_do_not_mix_states(tmp_path):
    first_path = str(tmp_path / "first.db")
    second_path = str(tmp_path / "second.db")
    _create_schema(first_path)
    _create_schema(second_path)
    first = VideoShopSQLiteProvider(db_path=first_path)
    second = VideoShopSQLiteProvider(db_path=second_path)

    tx_first = first.transaction()
    tx_second = second.transaction()  # different connection: allowed
    tx_first.execute("INSERT INTO items (name) VALUES (?)", ("one",))
    tx_second.execute("INSERT INTO items (name) VALUES (?)", ("two",))
    tx_first.commit()
    tx_second.rollback()

    assert _count(first_path) == 1
    assert _count(first_path, "one") == 1
    assert _count(second_path) == 0
    assert first.active_transaction is None
    assert second.active_transaction is None


def test_transactions_in_two_threads_do_not_share_state(tmp_path):
    db_paths = [str(tmp_path / "t1.db"), str(tmp_path / "t2.db")]
    for path in db_paths:
        _create_schema(path)

    results: dict[int, str] = {}
    errors: list[BaseException] = []

    def worker(index: int) -> None:
        try:
            local_provider = VideoShopSQLiteProvider(db_path=db_paths[index])
            with local_provider.transaction() as tx:
                tx.execute("INSERT INTO items (name) VALUES (?)", (f"thread-{index}",))
                results[index] = tx.state
        except BaseException as exc:  # pragma: no cover - reported via errors
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert results == {0: "active", 1: "active"}
    assert _count(db_paths[0], "thread-0") == 1
    assert _count(db_paths[1], "thread-1") == 1


# --- 7. nested transactions rejected -------------------------------------


def test_nested_transaction_is_rejected(provider, db_path):
    with provider.transaction() as tx:
        with pytest.raises(NestedTransactionError):
            provider.transaction()
        tx.execute("INSERT INTO items (name) VALUES (?)", ("outer",))

    assert _count(db_path) == 1


def test_outer_transaction_survives_rejected_nesting(provider, db_path):
    tx = provider.transaction()
    with pytest.raises(NestedTransactionError):
        provider.transaction()
    tx.execute("INSERT INTO items (name) VALUES (?)", ("outer",))
    tx.commit()

    assert _count(db_path) == 1
    assert provider.active_transaction is None


# --- 8. defined behaviour: commit twice, rollback after commit, after close


def test_commit_called_twice_raises(provider):
    tx = provider.transaction()
    tx.execute("SELECT 1")
    tx.commit()

    with pytest.raises(TransactionStateError):
        tx.commit()


def test_rollback_after_commit_raises(provider):
    tx = provider.transaction()
    tx.commit()

    with pytest.raises(TransactionStateError):
        tx.rollback()


def test_rollback_after_rollback_raises(provider, db_path):
    tx = provider.transaction()
    tx.rollback()
    with pytest.raises(TransactionStateError):
        tx.rollback()
    # the provider is still usable afterwards
    with provider.transaction() as tx2:
        tx2.execute("INSERT INTO items (name) VALUES (?)", ("after",))
    assert _count(db_path) == 1


def test_use_after_close_raises_and_close_is_idempotent(provider, db_path):
    tx = provider.transaction()
    tx.execute("INSERT INTO items (name) VALUES (?)", ("discarded",))
    tx.close()
    tx.close()  # idempotent

    with pytest.raises(TransactionClosedError):
        tx.execute("SELECT 1")
    with pytest.raises(TransactionClosedError):
        tx.commit()
    with pytest.raises(TransactionClosedError):
        tx.rollback()

    # close() while active behaves as an implicit rollback
    assert _count(db_path) == 0
    assert provider.active_transaction is None


# --- 9. the raw connection is not handed out -----------------------------


def test_raw_connection_is_not_exposed(provider):
    tx = provider.transaction()
    try:
        assert not hasattr(tx, "connection")
    finally:
        tx.rollback()


# --- 10. a failing rollback does not hide the original error -------------


class _FailingRollbackConnection:
    """Proxy connection whose rollback always fails (test-only seam)."""

    def __init__(self, inner: sqlite3.Connection) -> None:
        self._inner = inner
        self.row_factory = inner.row_factory

    def execute(self, *args, **kwargs):
        return self._inner.execute(*args, **kwargs)

    def commit(self) -> None:
        self._inner.commit()

    def rollback(self) -> None:
        raise RuntimeError("rollback failed on purpose")

    def close(self) -> None:
        self._inner.close()


class _FailingRollbackProvider(VideoShopSQLiteProvider):
    def _connect(self):  # type: ignore[override]
        return _FailingRollbackConnection(super()._connect())


def test_rollback_failure_does_not_hide_original_error(tmp_path, db_path):
    provider = _FailingRollbackProvider(db_path=db_path)
    captured: dict[str, object] = {}

    with pytest.raises(ValueError, match="original failure") as excinfo:
        with provider.transaction() as tx:
            captured["tx"] = tx
            tx.execute("INSERT INTO items (name) VALUES (?)", ("discarded",))
            raise ValueError("original failure")

    transaction = captured["tx"]
    attached = getattr(excinfo.value, "rollback_error", None)
    stored = getattr(transaction, "rollback_error", None)
    assert isinstance(attached or stored, RuntimeError), "rollback error must stay diagnosable"
    assert isinstance(stored, RuntimeError), "rollback error must be stored on the transaction"


# --- 11. existing provider interfaces unchanged --------------------------


def test_existing_provider_interfaces_unchanged(provider, db_path):
    inserted = asyncio.run(provider.insert("items", {"name": "plain"}))
    assert inserted["name"] == "plain"

    fetched = asyncio.run(provider.fetch("items", inserted["id"]))
    assert fetched["name"] == "plain"

    updated = asyncio.run(provider.update_record("items", inserted["id"], {"name": "updated"}))
    assert updated["name"] == "updated"

    assert asyncio.run(provider.is_unique("items", "name", "updated")) is False
    assert asyncio.run(provider.is_unique("items", "name", "other")) is True

    assert asyncio.run(provider.delete_record("items", inserted["id"])) is True
    assert asyncio.run(provider.fetch("items", inserted["id"])) is None

    # no transaction state leaks from the plain (non-transactional) interfaces
    assert provider.active_transaction is None
    with provider.transaction() as tx:
        tx.execute("INSERT INTO items (name) VALUES (?)", ("after-plain",))
    assert _count(db_path) == 1
