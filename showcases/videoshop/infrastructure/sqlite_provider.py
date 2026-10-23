"""VideoShop SQLite provider - B-prime track, stage S1.

ai_framework/ is FROZEN: this module only SUBCLASSES the framework provider
(``ai_framework.crud.sqlite_persistence.SQLitePersistenceProvider``) and adds
new methods. Inherited behaviour (insert/fetch/fetch_all/update_record/
delete_record/is_unique) is intentionally NOT overridden, so the transaction
API cannot silently change existing interfaces.

Public contract of the transaction API (S1):

* ``provider.transaction()`` opens an explicit transaction on ONE dedicated
  sqlite3 connection and returns :class:`VideoShopTransaction`.
* All operations of the scope go through that single connection; the raw
  connection is never handed out, so callers cannot close or reuse it.
* ``commit()`` and ``rollback()`` are explicit and one-shot: a second call
  raises :class:`TransactionStateError`.
* Leaving the scope with an exception triggers ``rollback()``.
* Nested transactions are not supported: a second ``transaction()`` call for
  the same provider in the same thread raises :class:`NestedTransactionError`.
* If ``rollback()`` itself fails, the original error is still the one raised;
  the rollback error is attached to it (``exc.rollback_error``) and stored on
  the transaction object (``tx.rollback_error``).
* Using a closed/finished transaction raises :class:`TransactionClosedError`
  (or :class:`TransactionStateError` for one-shot violations).
* ``close()`` is idempotent; while the transaction is active it behaves as an
  implicit rollback.

S2 adds the CAS contract (limited scope, showcase level only):

* ``update_record_cas(entity, id, payload, expected_version)`` performs the
  version check, the data change and the version increment in ONE atomic SQL
  statement (``UPDATE ... WHERE id = ? AND version = ?``) - never
  "read the version, then update unconditionally";
* results are typed: :class:`CasResult` with status ``updated`` / ``conflict`` /
  ``not_found``; a conflict reports ``expected_version`` and ``actual_version``;
* a missing ``version`` column raises an explicit :class:`VersionColumnError`
  (never NOT_FOUND, never a silent fallback to the ordinary path);
* the version lives per record in the ``version`` column; a successful CAS
  increments it by exactly one, while a conflict or a missing row never changes it;
* the ordinary inherited ``update_record`` path is refused with
  :class:`VersionedEntityUpdateError` for entities that have a ``version``
  column, and keeps working unchanged for non-versioned tables;
* contract violations (``version`` inside the payload, non-int expected version)
  raise :class:`CasContractError`.

S2 corrective patch (closes findings F-1, F-2, F-3 of the S2 GREEN review, and
records the F-4 policy; showcase level only, no production schema involved):

* **F-1** - the version column is detected by normalisation (``strip`` +
  ``casefold``): ``version``, ``VERSION``, ``Version`` and ``"version "`` are all
  recognised as versioned. The *declared* name is used (quoted) in SQL, because
  SQLite is case-insensitive for identifiers but treats ``"version "`` as a
  distinct name. Two or more version-like columns raise an explicit
  :class:`VersionColumnError` (fail-closed).
* **F-2** - ``insert`` refuses a caller-provided version-like key for versioned
  entities (:class:`VersionedEntityInsertError`); the provider owns the version
  and the initial value is 0. For versioned entities ``insert`` returns the
  stored row, so the caller learns the initial version.
* **F-3** - the ordinary ``delete_record`` path is refused for versioned entities
  (:class:`VersionedEntityDeleteError`). A version-checked delete is a separate
  operation and is NOT implemented in S2.
* **Fail-closed** - a schema-detection error is never read as "not versioned":
  ordinary update/insert/delete then fail instead of proceeding.
* Non-versioned tables keep the inherited behaviour unchanged.
* **F-4 policy (architecture rule)** - this guard is NOT a security boundary
  against raw SQL: ``transaction().execute(...)``, ``executemany`` and private
  connection access stay *internal infrastructure mechanisms*. VideoShop services
  must not use them to write business entities; they are not a public way to
  update versioned data.

S6 adds the reliability contract (showcase level only):

* ONE timeout policy for BOTH connection factories: ``busy_timeout_ms`` is
  applied to the VideoShop ``_connect()`` AND to the overridden framework
  ``_get_connection()``, so inherited methods (insert/fetch/fetch_all/
  update_record/delete_record/is_unique) honour the same value;
* per-connection PRAGMAs applied on every connection: explicit
  ``busy_timeout``, ``foreign_keys = ON``, ``synchronous = FULL``; the journal
  mode stays ``delete`` (WAL is deliberately NOT enabled - decision D-S6-1);
* read and write scopes are separated: ``read_transaction()`` opens
  ``BEGIN DEFERRED`` (consistent snapshot, no write lock) and is used by the
  read paths, while ``transaction()`` keeps ``BEGIN IMMEDIATE`` for writes;
* bounded retry for ``SQLITE_BUSY`` only, around the WHOLE transactional
  operation (see ``infrastructure/retry.py``); ``SQLITE_LOCKED`` is never
  retried;
* deployment: the database file, its journal and (if ever enabled) WAL files
  must live on a LOCAL file system on a single node. Network file systems and
  multi-node access are NOT supported and are NOT auto-detected.

Out of scope: production DDL/migrations for the ``version`` column (separate
stage), CAS-delete, slug history retention, backup and HTTP handlers.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence

from ai_framework.crud.sqlite_persistence import SQLitePersistenceProvider

__all__ = [
    "TransactionError",
    "NestedTransactionError",
    "TransactionClosedError",
    "TransactionStateError",
    "CasError",
    "CasContractError",
    "VersionColumnError",
    "VersionedEntityUpdateError",
    "VersionedEntityInsertError",
    "VersionedEntityDeleteError",
    "CasResult",
    "VideoShopTransaction",
    "VideoShopSQLiteProvider",
]


class TransactionError(RuntimeError):
    """Base error for the VideoShop transaction API."""


class NestedTransactionError(TransactionError):
    """Nested transactions are not supported (S1 contract)."""


class TransactionClosedError(TransactionError):
    """The transaction is closed and cannot be used any more."""


class TransactionStateError(TransactionError):
    """The requested operation is invalid for the current transaction state."""


class CasError(TransactionError):
    """Base error for the CAS contract (S2)."""


class CasContractError(CasError):
    """The caller violated the CAS contract (bad argument or payload)."""


class VersionColumnError(CasError):
    """The entity table has no 'version' column, so CAS cannot be applied."""


class VersionedEntityUpdateError(CasError):
    """The ordinary update path must not be used for a versioned entity."""


class VersionedEntityInsertError(CasError):
    """A caller-provided version is not allowed on insert for a versioned entity."""


class VersionedEntityDeleteError(CasError):
    """The ordinary delete path must not be used for a versioned entity."""


class CasResult:
    """Typed outcome of :meth:`VideoShopSQLiteProvider.update_record_cas`.

    * ``status == UPDATED``   - the update was applied; ``record`` holds the new
      row (including the incremented version; keys use the *declared* column
      names, so read the version from ``actual_version`` when in doubt) and
      ``actual_version`` its version;
    * ``status == CONFLICT``  - the stored version differs; ``expected_version``
      and ``actual_version`` are both reported and the row is unchanged;
    * ``status == NOT_FOUND`` - there is no row with this id.
    """

    UPDATED = "updated"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"

    __slots__ = ("status", "record", "expected_version", "actual_version")

    def __init__(
        self,
        status: str,
        record: Optional[dict] = None,
        expected_version: Optional[int] = None,
        actual_version: Optional[int] = None,
    ) -> None:
        self.status = status
        self.record = record
        self.expected_version = expected_version
        self.actual_version = actual_version

    @property
    def is_updated(self) -> bool:
        return self.status == self.UPDATED

    @property
    def is_conflict(self) -> bool:
        return self.status == self.CONFLICT

    @property
    def is_not_found(self) -> bool:
        return self.status == self.NOT_FOUND

    def __repr__(self) -> str:
        return (
            f"CasResult(status={self.status!r}, "
            f"expected_version={self.expected_version!r}, "
            f"actual_version={self.actual_version!r}, record={self.record!r})"
        )


class VideoShopTransaction:
    """Explicit transaction scope bound to exactly one sqlite3 connection."""

    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    CLOSED = "closed"

    #: S6 transaction modes: writes lock immediately, reads use a snapshot
    MODE_WRITE = "write"
    MODE_READ = "read"

    def __init__(
        self,
        provider: "VideoShopSQLiteProvider",
        connection: sqlite3.Connection,
        mode: str = MODE_WRITE,
    ) -> None:
        if mode not in (self.MODE_WRITE, self.MODE_READ):
            raise TransactionStateError(f"unknown transaction mode: {mode!r}")
        self._provider = provider
        self._connection = connection
        self._mode = mode
        self._state = self.ACTIVE
        self._released = False
        #: rollback failure, kept for diagnostics (S1 requirement 6)
        self.rollback_error: Optional[BaseException] = None

    # --- state ----------------------------------------------------------

    @property
    def state(self) -> str:
        return self._state

    @property
    def mode(self) -> str:
        """``"write"`` (BEGIN IMMEDIATE) or ``"read"`` (BEGIN DEFERRED)."""
        return self._mode

    def _require_active(self, operation: str) -> None:
        if self._state == self.CLOSED:
            raise TransactionClosedError(f"{operation}: transaction is closed")
        if self._state != self.ACTIVE:
            raise TransactionStateError(
                f"{operation}: transaction is already {self._state}"
            )

    # --- operations (always the same connection) ------------------------

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        self._require_active("execute")
        return self._connection.execute(sql, tuple(params))

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]) -> sqlite3.Cursor:
        self._require_active("executemany")
        return self._connection.executemany(sql, seq_of_params)

    def fetchone(self, sql: str, params: Sequence[Any] = ()):
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: Sequence[Any] = ()):
        return self.execute(sql, params).fetchall()

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        row = self.fetchone(sql, params)
        return None if row is None else row[0]

    def update_record_cas(
        self,
        entity_name: str,
        entity_id: Any,
        payload: dict,
        expected_version: int,
    ) -> CasResult:
        """CAS inside THIS transaction (S4/D2): no extra connection, no commit.

        The version check, the data change and the version increment are one
        atomic statement on this transaction's connection; the enclosing scope
        decides whether the result is committed or rolled back.
        """
        self._require_active("update_record_cas")
        if self._mode != self.MODE_WRITE:
            raise TransactionStateError(
                "update_record_cas is not allowed in a read transaction"
            )
        return self._provider._apply_cas(
            self._connection, entity_name, entity_id, payload, expected_version
        )

    # --- completion -----------------------------------------------------

    def commit(self) -> None:
        self._require_active("commit")
        try:
            self._connection.commit()
            self._state = self.COMMITTED
        except BaseException:
            self._state = self.CLOSED
            raise
        finally:
            self._release()

    def rollback(self) -> None:
        self._require_active("rollback")
        try:
            self._connection.rollback()
            self._state = self.ROLLED_BACK
        except BaseException:
            self._state = self.CLOSED
            raise
        finally:
            self._release()

    def close(self) -> None:
        """Idempotent close; behaves as an implicit rollback while active."""
        if self._state == self.ACTIVE:
            try:
                self._connection.rollback()
            except BaseException as rollback_exc:
                self.rollback_error = rollback_exc
            finally:
                self._state = self.CLOSED
                self._release()
            return
        self._release()

    # --- context manager ------------------------------------------------

    def __enter__(self) -> "VideoShopTransaction":
        if self._state != self.ACTIVE:
            raise TransactionStateError(f"enter: transaction is already {self._state}")
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if exc_type is None:
            if self._state == self.ACTIVE:
                self.commit()
            else:
                self._release()
            return False

        # An exception happened inside the scope: roll back, but never hide
        # the original error (S1 requirement 6).
        if self._state == self.ACTIVE:
            try:
                self.rollback()
            except BaseException as rollback_exc:
                self.rollback_error = rollback_exc
                try:
                    setattr(exc, "rollback_error", rollback_exc)
                except BaseException:
                    pass
        else:
            self._release()
        return False

    # --- internals ------------------------------------------------------

    def _release(self) -> None:
        if self._released:
            return
        self._released = True
        self._provider._forget_transaction(self)
        try:
            self._connection.close()
        except BaseException:
            pass


class VideoShopSQLiteProvider(SQLitePersistenceProvider):
    """Framework SQLite provider plus the VideoShop transaction API (S1/S6)."""

    def __init__(self, db_path: str = ":memory:", *, busy_timeout_ms: int = 5000) -> None:
        self.busy_timeout_ms = int(busy_timeout_ms)
        #: one active transaction per provider and per thread (nested -> error)
        self._local = threading.local()
        super().__init__(db_path=db_path)

    # --- S6: per-connection settings -------------------------------------

    def _configure_connection(self, connection: sqlite3.Connection) -> None:
        """Apply the S6 per-connection policy to EVERY connection (D-S6-2/D-S6-4).

        ``busy_timeout`` is set explicitly (the Python ``timeout`` argument also
        installs a busy handler - both stay in sync), ``foreign_keys`` is
        switched ON and ``synchronous`` is pinned to FULL. The journal mode is
        deliberately NOT touched: it stays ``delete`` (WAL is not enabled,
        D-S6-1).
        """
        connection.execute(f"PRAGMA busy_timeout = {int(self.busy_timeout_ms)}")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")

    #: overridable seam: tests may substitute the connection
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=self.busy_timeout_ms / 1000.0,
            isolation_level=None,  # explicit transaction control only
        )
        connection.row_factory = sqlite3.Row
        self._configure_connection(connection)
        return connection

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Framework-path connection with the SAME timeout and PRAGMAs (D-S6-2).

        Equivalent to the framework implementation except that it uses
        ``busy_timeout_ms`` and applies the per-connection settings, so every
        inherited method (insert/fetch/fetch_all/update_record/delete_record/
        is_unique) honours the VideoShop timeout policy.
        """
        connection = sqlite3.connect(self.db_path, timeout=self.busy_timeout_ms / 1000.0)
        connection.row_factory = sqlite3.Row
        self._configure_connection(connection)
        try:
            yield connection
        finally:
            connection.close()

    @property
    def active_transaction(self) -> Optional[VideoShopTransaction]:
        return getattr(self._local, "transaction", None)

    # --- transactions: write (IMMEDIATE) and read (DEFERRED) --------------

    def transaction(self) -> VideoShopTransaction:
        """Open a WRITE transaction (single connection, ``BEGIN IMMEDIATE``)."""
        return self._open_transaction(VideoShopTransaction.MODE_WRITE)

    def read_transaction(self) -> VideoShopTransaction:
        """Open a READ transaction (``BEGIN DEFERRED``) for a consistent snapshot.

        It never takes the write lock: under the rollback journal it holds
        SHARED while reading, so writers are blocked only for the duration of the
        read statements, and readers do not fail merely because a writer holds
        RESERVED (D-S6-5).
        """
        return self._open_transaction(VideoShopTransaction.MODE_READ)

    def _open_transaction(self, mode: str) -> VideoShopTransaction:
        if self.active_transaction is not None:
            raise NestedTransactionError(
                "nested transactions are not supported: this provider already has an "
                "active transaction in the current thread"
            )

        connection = self._connect()
        transaction = VideoShopTransaction(self, connection, mode=mode)
        try:
            connection.execute(
                "BEGIN IMMEDIATE"
                if mode == VideoShopTransaction.MODE_WRITE
                else "BEGIN DEFERRED"
            )
        except BaseException:
            connection.close()
            raise

        self._local.transaction = transaction
        return transaction

    def _forget_transaction(self, transaction: VideoShopTransaction) -> None:
        if getattr(self._local, "transaction", None) is transaction:
            self._local.transaction = None

    # --- S2: CAS contract ------------------------------------------------

    #: name of the per-record version column (decision U-S2-6)
    VERSION_COLUMN = "version"

    def _table_info(self, connection: sqlite3.Connection, entity_name: str):
        return connection.execute(f"PRAGMA table_info({entity_name})").fetchall()

    def _version_column_name_on(
        self, connection: sqlite3.Connection, entity_name: str
    ) -> Optional[str]:
        """Return the declared version-like column name, or None (F-1 fix).

        Detection is normalisation based (``strip`` + ``casefold``) so ``version``,
        ``VERSION``, ``Version`` and ``"version "`` are all recognised. The
        *declared* name is returned because SQLite treats ``"version "`` as a
        distinct identifier. Detection errors propagate on purpose: they must
        never be read as "not versioned" (fail-closed).
        """
        matches = [
            row["name"]
            for row in self._table_info(connection, entity_name)
            if str(row["name"]).strip().casefold() == self.VERSION_COLUMN
        ]
        if not matches:
            return None
        if len(matches) > 1:
            raise VersionColumnError(
                f"entity '{entity_name}' has several version-like columns "
                f"{sorted(matches)}: exactly one '{self.VERSION_COLUMN}' column is required"
            )
        return matches[0]

    def _version_column_name(self, entity_name: str) -> Optional[str]:
        connection = self._connect()
        try:
            return self._version_column_name_on(connection, entity_name)
        finally:
            connection.close()

    def _table_has_version_column(self, entity_name: str) -> bool:
        """Compatibility shim keep for review tooling (F-1 fixed variant)."""
        return self._version_column_name(entity_name) is not None

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + str(identifier).replace('"', '""') + '"'

    @classmethod
    def _version_keys_in_payload(cls, payload: dict, declared: str) -> list:
        target = str(declared).strip().casefold()
        return [key for key in payload if str(key).strip().casefold() == target]

    async def update_record(self, entity_name: str, entity_id: Any, payload: dict):
        """S2 guard: refuse the non-versioned path for versioned entities.

        Scope (decision U-S2-4): only entities that actually have a version-like
        column are blocked; non-versioned tables keep the inherited behaviour.
        """
        version_column = self._version_column_name(entity_name)
        if version_column is not None:
            raise VersionedEntityUpdateError(
                f"ordinary update path is not allowed for versioned entity "
                f"'{entity_name}' (column '{version_column}'): use update_record_cas()"
            )
        return await super().update_record(entity_name, entity_id, payload)

    async def insert(self, entity_name: str, payload: dict):
        """S2 guard F-2: the provider owns the version, the caller must not set it."""
        version_column = self._version_column_name(entity_name)
        if version_column is None:
            return await super().insert(entity_name, payload)

        conflicting = self._version_keys_in_payload(payload, version_column)
        if conflicting:
            raise VersionedEntityInsertError(
                f"{conflicting[0]!r} must not be provided on insert for versioned entity "
                f"'{entity_name}': the provider manages the version (initial value 0)"
            )

        result = await super().insert(entity_name, payload)
        entity_id = result.get("id") if isinstance(result, dict) else None
        if entity_id is None:
            return result
        # return the stored row so the caller learns the provider-assigned version
        connection = self._connect()
        try:
            row = connection.execute(
                f"SELECT * FROM {entity_name} WHERE id = ?", (entity_id,)
            ).fetchone()
        finally:
            connection.close()
        return dict(row) if row is not None else result

    async def delete_record(self, entity_name: str, entity_id: Any):
        """S2 guard F-3: no ordinary delete for versioned entities."""
        version_column = self._version_column_name(entity_name)
        if version_column is not None:
            raise VersionedEntityDeleteError(
                f"ordinary delete is not allowed for versioned entity '{entity_name}' "
                f"(column '{version_column}'): a version-checked delete is a separate "
                f"operation and is not implemented yet"
            )
        return await super().delete_record(entity_name, entity_id)

    def version_column_name(self, entity_name: str) -> Optional[str]:
        """Public helper: declared name of the version column (or ``None``).

        Used by the showcase services (S4) to learn, *before* opening a
        transaction, whether an entity table is versioned.
        """
        return self._version_column_name(entity_name)

    def _apply_cas(
        self,
        connection: sqlite3.Connection,
        entity_name: str,
        entity_id: Any,
        payload: dict,
        expected_version: int,
    ) -> CasResult:
        """CAS core shared by the provider and the transaction scope (S4/D2).

        Takes a CALLER-OWNED connection: it never commits and never closes it,
        so the same logic runs standalone (own connection, autocommit) and
        inside a composite transaction where the caller decides the outcome.
        """
        if isinstance(expected_version, bool) or not isinstance(expected_version, int):
            raise CasContractError(
                "expected_version must be an int (the per-record version)"
            )
        version_column = self._version_column_name_on(connection, entity_name)
        if version_column is None:
            raise VersionColumnError(
                f"entity '{entity_name}' has no '{self.VERSION_COLUMN}' column: "
                f"CAS is not available for it"
            )
        conflicting = self._version_keys_in_payload(payload, version_column)
        if conflicting:
            raise CasContractError(
                f"{conflicting[0]!r} must not be part of the payload: "
                f"pass expected_version as a separate argument"
            )

        quoted_version = self._quote_identifier(version_column)
        set_clause = ", ".join(f"{key} = ?" for key in payload)
        assignments = f"{set_clause}, " if set_clause else ""
        sql = (
            f"UPDATE {entity_name} SET {assignments}"
            f"{quoted_version} = {quoted_version} + 1 "
            f"WHERE id = ? AND {quoted_version} = ?"
        )
        cursor = connection.execute(
            sql, list(payload.values()) + [entity_id, expected_version]
        )

        if cursor.rowcount == 1:
            row = connection.execute(
                f"SELECT * FROM {entity_name} WHERE id = ?", (entity_id,)
            ).fetchone()
            record = dict(row) if row is not None else None
            return CasResult(
                CasResult.UPDATED,
                record=record,
                expected_version=expected_version,
                actual_version=None if record is None else record[version_column],
            )

        # rowcount == 0: the row either exists with another version, or not
        row = connection.execute(
            f"SELECT {quoted_version} FROM {entity_name} WHERE id = ?",
            (entity_id,),
        ).fetchone()
        if row is None:
            return CasResult(CasResult.NOT_FOUND, expected_version=expected_version)
        return CasResult(
            CasResult.CONFLICT,
            expected_version=expected_version,
            actual_version=row[version_column],
        )

    def update_record_cas(
        self,
        entity_name: str,
        entity_id: Any,
        payload: dict,
        expected_version: int,
    ) -> CasResult:
        """Atomic compare-and-swap update (S2 contract) on its OWN connection.

        For composite operations (S4) use
        :meth:`VideoShopTransaction.update_record_cas` instead, so the CAS joins
        the caller's transaction.
        """
        connection = self._connect()
        try:
            result = self._apply_cas(
                connection, entity_name, entity_id, payload, expected_version
            )
            connection.commit()
            return result
        finally:
            connection.close()
