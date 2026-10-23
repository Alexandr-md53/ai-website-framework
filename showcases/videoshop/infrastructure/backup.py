"""S7 V1: SQLite online backup with verification before publication.

Approved narrow scope (S7 V1):

* the copy is made with the SQLite **online backup API**
  (``sqlite3.Connection.backup``), so it is consistent while other processes
  keep writing (proven in the S6 audits: a copy taken under an active writer
  verifies);
* the backup NEVER runs migrations and never writes to the source database;
* the copy is first written to a uniquely named temporary file, then verified,
  and only a verified file is published under the final name;
* an existing final copy is never overwritten (the name is reserved atomically
  with ``O_CREAT|O_EXCL``);
* every failure is a typed error and leaves no file that could be mistaken for a
  finished backup.

File-system limits (documented, not hidden): atomic publication relies on
``os.replace`` within the same directory. On a local file system that rename is
atomic; on other file systems (network shares, exotic mounts) it may not be, and
a hard process kill between reserving the final name and the rename can leave a
zero-byte placeholder - verification rejects such a file (``file_empty``), so it
cannot pass as a valid backup. V1 is documented for a local file system on one
node (S6/D-S6-8).
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Tuple

from .slug_registry import STATE_LIVE, STATE_RELEASED, TABLE
from .storage import StoragePaths

#: consistent with the S6 connection policy
DEFAULT_BUSY_TIMEOUT_MS = 5000

#: every SQLite database file starts with this 16-byte string
SQLITE_HEADER = b"SQLite format 3\x00"

#: naming convention of a published copy (the exact convention is a V1 proposal)
BACKUP_SUFFIX = ".backup.sqlite"

#: prefix of the caller-facing names; tested for collisions
PARTIAL_SUFFIX = ".partial"

#: check identifiers reported in :class:`VerificationReport.failed_checks`
CHECK_FILE_MISSING = "file_missing"
CHECK_FILE_EMPTY = "file_empty"
CHECK_HEADER_INVALID = "header_invalid"
CHECK_INTEGRITY = "integrity_check"
CHECK_FOREIGN_KEYS = "foreign_key_check"
CHECK_USER_VERSION_MISMATCH = "user_version_mismatch"
CHECK_DUPLICATE_LIVE = "duplicate_live_slugs"
CHECK_LIVE_WITH_RELEASED_AT = "live_with_released_at"
CHECK_RELEASED_WITHOUT_RELEASED_AT = "released_without_released_at"
CHECK_INVALID_STATE = "invalid_state"
CHECK_UNREADABLE = "unreadable"
CHECK_QUERY_FAILED = "query_failed"


class BackupError(RuntimeError):
    """Base error of the S7 backup contract."""

    code = "BACKUP_ERROR"


class BackupSourceNotAFile(BackupError):
    """The configured source is not a file-backed database (e.g. ``:memory:``)."""

    code = "BACKUP_SOURCE_NOT_A_FILE"


class BackupSourceMissing(BackupError):
    code = "BACKUP_SOURCE_MISSING"


class BackupNameInvalid(BackupError):
    code = "BACKUP_NAME_INVALID"


class BackupAlreadyExists(BackupError):
    code = "BACKUP_ALREADY_EXISTS"


class BackupTargetUnavailable(BackupError):
    code = "BACKUP_TARGET_UNAVAILABLE"


class BackupCopyFailed(BackupError):
    code = "BACKUP_COPY_FAILED"


class BackupVerificationFailed(BackupError):
    code = "BACKUP_VERIFICATION_FAILED"

    def __init__(self, report: "VerificationReport") -> None:
        self.report = report
        super().__init__(
            f"{self.code}: the copy did not pass verification "
            f"({', '.join(report.failed_checks) or 'unknown'})"
        )


class BackupPublicationFailed(BackupError):
    code = "BACKUP_PUBLICATION_FAILED"


@dataclass(frozen=True)
class VerificationReport:
    """Result of verifying one database file (never raises for a bad file)."""

    path: str
    size_bytes: int = 0
    header_ok: bool = False
    integrity: Optional[str] = None
    foreign_key_violations: int = 0
    user_version: Optional[int] = None
    registry_present: bool = False
    indexes: Tuple[str, ...] = ()
    live_rows: int = 0
    released_rows: int = 0
    duplicate_live_slugs: int = 0
    live_with_released_at: int = 0
    released_without_released_at: int = 0
    invalid_state_rows: int = 0
    failed_checks: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.failed_checks

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "header_ok": self.header_ok,
            "integrity": self.integrity,
            "foreign_key_violations": self.foreign_key_violations,
            "user_version": self.user_version,
            "registry_present": self.registry_present,
            "indexes": list(self.indexes),
            "live_rows": self.live_rows,
            "released_rows": self.released_rows,
            "duplicate_live_slugs": self.duplicate_live_slugs,
            "failed_checks": list(self.failed_checks),
            "ok": self.ok,
        }


@dataclass(frozen=True)
class BackupResult:
    """A published, verified backup."""

    source_path: str
    backup_path: str
    size_bytes: int
    created_at: str
    report: VerificationReport
    pages: int


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _open_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro", uri=True, isolation_level=None
    )
    connection.row_factory = sqlite3.Row
    return connection


def _scalar_int(connection: sqlite3.Connection, sql: str) -> int:
    row = connection.execute(sql).fetchone()
    return int(row[0]) if row is not None else 0


def verify_database_file(
    path,
    *,
    expected_user_version: Optional[int] = None,
) -> VerificationReport:
    """Verify a database file: size, header, integrity, FKs, version, S3 invariants.

    The file is opened read-only, so verification never modifies the copy. A
    damaged or non-database file is reported through ``failed_checks`` instead of
    raising. Only the invariants that really exist in the current schema are
    checked (``slug_registry``); no entity tables are invented.
    """
    target = Path(path)
    failed: list[str] = []

    if not target.exists() or not target.is_file():
        return VerificationReport(path=str(target), failed_checks=(CHECK_FILE_MISSING,))

    size_bytes = target.stat().st_size
    header_ok = False
    if size_bytes <= 0:
        failed.append(CHECK_FILE_EMPTY)
    else:
        with open(target, "rb") as handle:
            header_ok = handle.read(len(SQLITE_HEADER)) == SQLITE_HEADER
        if not header_ok:
            failed.append(CHECK_HEADER_INVALID)

    if not header_ok:
        return VerificationReport(
            path=str(target),
            size_bytes=size_bytes,
            header_ok=False,
            failed_checks=tuple(failed),
        )

    integrity: Optional[str] = None
    foreign_key_violations = 0
    user_version: Optional[int] = None
    registry_present = False
    indexes: Tuple[str, ...] = ()
    live_rows = released_rows = 0
    duplicate_live = live_with_released_at = released_without_released_at = 0
    invalid_state = 0

    try:
        connection = _open_readonly(target)
    except sqlite3.Error:
        failed.append(CHECK_UNREADABLE)
        return VerificationReport(
            path=str(target),
            size_bytes=size_bytes,
            header_ok=True,
            failed_checks=tuple(failed),
        )

    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
        integrity = str(rows[0][0]) if rows else ""
        if integrity != "ok":
            failed.append(CHECK_INTEGRITY)

        foreign_key_violations = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        if foreign_key_violations:
            failed.append(CHECK_FOREIGN_KEYS)

        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if expected_user_version is not None and user_version != int(expected_user_version):
            failed.append(CHECK_USER_VERSION_MISMATCH)

        registry_present = (
            _scalar_int(
                connection,
                f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{TABLE}'",
            )
            > 0
        )
        if registry_present:
            indexes = tuple(
                sorted(str(row[1]) for row in connection.execute(f"PRAGMA index_list({TABLE})"))
            )
            live_rows = _scalar_int(
                connection, f"SELECT COUNT(*) FROM {TABLE} WHERE state='{STATE_LIVE}'"
            )
            released_rows = _scalar_int(
                connection, f"SELECT COUNT(*) FROM {TABLE} WHERE state='{STATE_RELEASED}'"
            )
            duplicate_live = _scalar_int(
                connection,
                f"SELECT COUNT(*) FROM (SELECT 1 FROM {TABLE} WHERE state='{STATE_LIVE}' "
                f"GROUP BY entity_type, entity_id HAVING COUNT(*) > 1)",
            )
            if duplicate_live:
                failed.append(CHECK_DUPLICATE_LIVE)
            live_with_released_at = _scalar_int(
                connection,
                f"SELECT COUNT(*) FROM {TABLE} WHERE state='{STATE_LIVE}' "
                f"AND released_at IS NOT NULL",
            )
            if live_with_released_at:
                failed.append(CHECK_LIVE_WITH_RELEASED_AT)
            released_without_released_at = _scalar_int(
                connection,
                f"SELECT COUNT(*) FROM {TABLE} WHERE state='{STATE_RELEASED}' "
                f"AND released_at IS NULL",
            )
            if released_without_released_at:
                failed.append(CHECK_RELEASED_WITHOUT_RELEASED_AT)
            invalid_state = _scalar_int(
                connection,
                f"SELECT COUNT(*) FROM {TABLE} "
                f"WHERE state NOT IN ('{STATE_LIVE}', '{STATE_RELEASED}')",
            )
            if invalid_state:
                failed.append(CHECK_INVALID_STATE)
    except sqlite3.Error:
        failed.append(CHECK_QUERY_FAILED)
    finally:
        connection.close()

    return VerificationReport(
        path=str(target),
        size_bytes=size_bytes,
        header_ok=True,
        integrity=integrity,
        foreign_key_violations=foreign_key_violations,
        user_version=user_version,
        registry_present=registry_present,
        indexes=indexes,
        live_rows=live_rows,
        released_rows=released_rows,
        duplicate_live_slugs=duplicate_live,
        live_with_released_at=live_with_released_at,
        released_without_released_at=released_without_released_at,
        invalid_state_rows=invalid_state,
        failed_checks=tuple(failed),
    )


def _copy_database(
    source_path: Path,
    target_path: Path,
    *,
    busy_timeout_ms: int,
    pages: int,
    sleep: float,
) -> None:
    """Copy ``source_path`` into a fresh ``target_path`` with the online backup API.

    The source is opened writable on purpose: a read-only connection cannot
    recover a hot rollback journal left by a killed process, while the backup API
    itself never writes to the source.
    """
    source = sqlite3.connect(
        str(source_path), timeout=busy_timeout_ms / 1000.0, isolation_level=None
    )
    try:
        source.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
        target = sqlite3.connect(str(target_path), isolation_level=None)
        try:
            source.backup(target, pages=pages, sleep=sleep)
        finally:
            target.close()
    finally:
        source.close()


def _remove_file(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def create_backup(
    storage: StoragePaths,
    *,
    name: Optional[str] = None,
    expected_user_version: Optional[int] = None,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    pages: int = -1,
    sleep: float = 0.0,
    clock: Callable[[], datetime] = _utc_now,
) -> BackupResult:
    """Create and publish a verified copy of the configured database file.

    ``name`` overrides the generated file name (an existing name is refused).
    ``expected_user_version``, when given, additionally fails verification if the
    copy's ``PRAGMA user_version`` differs.
    """
    db_path = storage.db_path
    if not storage.is_file or db_path is None:
        raise BackupSourceNotAFile(
            "backup requires file-backed storage: an in-memory database has no "
            "file to copy and is never protected by S7 V1"
        )
    backup_dir = storage.require_backup_dir()

    if not db_path.exists() or not db_path.is_file():
        raise BackupSourceMissing(f"database file does not exist: {str(db_path)!r}")
    if not backup_dir.exists() or not backup_dir.is_dir():
        raise BackupTargetUnavailable(f"backup directory is unavailable: {str(backup_dir)!r}")

    moment = clock()
    final_name = name or f"{db_path.stem}.{moment.strftime('%Y%m%dT%H%M%SZ')}{BACKUP_SUFFIX}"
    if Path(final_name).name != final_name or final_name in (".", ".."):
        raise BackupNameInvalid(
            f"backup name must be a file name inside the backup directory, got {final_name!r}"
        )

    final_path = backup_dir / final_name
    partial_path = backup_dir / f"{final_name}.{os.getpid()}.{uuid.uuid4().hex[:8]}{PARTIAL_SUFFIX}"

    # Reserve the final name atomically so it can never be overwritten.
    try:
        descriptor = os.open(str(final_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(descriptor)
    except FileExistsError as exc:
        raise BackupAlreadyExists(
            f"a backup with this name already exists: {str(final_path)!r}"
        ) from exc
    except OSError as exc:
        raise BackupTargetUnavailable(
            f"cannot reserve the backup name {str(final_path)!r}: {type(exc).__name__}: {exc}"
        ) from exc

    published = False
    try:
        try:
            _copy_database(
                db_path,
                partial_path,
                busy_timeout_ms=busy_timeout_ms,
                pages=pages,
                sleep=sleep,
            )
        except sqlite3.Error as exc:
            raise BackupCopyFailed(
                f"sqlite backup failed: {type(exc).__name__}: {exc}"
            ) from exc
        except OSError as exc:
            raise BackupTargetUnavailable(
                f"backup target is not writable: {type(exc).__name__}: {exc}"
            ) from exc

        report = verify_database_file(
            partial_path, expected_user_version=expected_user_version
        )
        if not report.ok:
            raise BackupVerificationFailed(report)

        try:
            os.replace(str(partial_path), str(final_path))
        except OSError as exc:
            raise BackupPublicationFailed(
                f"cannot publish the verified copy: {type(exc).__name__}: {exc}"
            ) from exc
        published = True

        # The verified content is now the published file (same bytes, renamed),
        # so the report points at what the operator can actually open.
        report = replace(report, path=str(final_path))
        return BackupResult(
            source_path=str(db_path),
            backup_path=str(final_path),
            size_bytes=report.size_bytes,
            created_at=moment.isoformat(),
            report=report,
            pages=pages,
        )
    finally:
        # Never leave a file that could be mistaken for a finished backup: the
        # temporary copy is always removed, and a reserved-but-unpublished
        # placeholder is removed as well.
        _remove_file(partial_path)
        if not published:
            _remove_file(final_path)
