"""S7 V1: restore is allowed ONLY into an isolated temporary directory.

Approved narrow scope (S7 V1):

* ``restore_backup`` writes a **new** file inside a caller-provided isolated
  temporary directory; it never touches the working database and never replaces
  a live database file;
* the target directory must live under the system temporary root, must not be
  the database directory, must not be the backup directory (nor contain either
  of them), and the target file must not exist yet;
* the copy is verified BEFORE the restore and the restored file is verified
  afterwards; a failed verification removes the file this module just created
  and raises a typed error;
* restore does NOT run migrations. Migrations stay an explicit, separate action
  owned by the caller (S7-11): the restored file is verified against the
  expected ``user_version`` instead.
"""
from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .backup import (
    DEFAULT_BUSY_TIMEOUT_MS,
    BackupResult,
    VerificationReport,
    create_backup,
    verify_database_file,
)
from .storage import StoragePaths


class RestoreError(RuntimeError):
    """Base error of the S7 restore contract."""

    code = "RESTORE_ERROR"


class RestoreSourceMissing(RestoreError):
    code = "RESTORE_SOURCE_MISSING"


class RestoreSourceNotVerified(RestoreError):
    code = "RESTORE_SOURCE_NOT_VERIFIED"

    def __init__(self, report: VerificationReport) -> None:
        self.report = report
        super().__init__(
            f"{self.code}: the backup did not pass verification "
            f"({', '.join(report.failed_checks) or 'unknown'})"
        )


class RestoreTargetRefused(RestoreError):
    code = "RESTORE_TARGET_REFUSED"


class RestoreFailed(RestoreError):
    code = "RESTORE_FAILED"


class RestoreVerificationFailed(RestoreError):
    code = "RESTORE_VERIFICATION_FAILED"

    def __init__(self, report: VerificationReport) -> None:
        self.report = report
        super().__init__(
            f"{self.code}: the restored file did not pass verification "
            f"({', '.join(report.failed_checks) or 'unknown'})"
        )


@dataclass(frozen=True)
class RestoreResult:
    source_path: str
    target_path: str
    work_dir: str
    restored_at: str
    source_report: VerificationReport
    target_report: VerificationReport


@dataclass(frozen=True)
class DrillResult:
    """Outcome of a backup + restore drill (no migration is performed)."""

    backup: BackupResult
    restore: RestoreResult


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _temp_root() -> Path:
    """System temporary root, read at call time so tests can substitute it."""
    return Path(tempfile.gettempdir()).resolve()


def _overlaps(first: Path, second: Path) -> bool:
    return (
        first == second
        or first.is_relative_to(second)
        or second.is_relative_to(first)
    )


def restore_backup(
    source_path,
    work_dir,
    *,
    name: Optional[str] = None,
    storage: Optional[StoragePaths] = None,
    expected_user_version: Optional[int] = None,
    clock: Callable[[], datetime] = _utc_now,
) -> RestoreResult:
    """Restore a verified backup into a NEW file in an isolated temp directory."""
    source = Path(source_path)
    if not source.exists() or not source.is_file():
        raise RestoreSourceMissing(f"backup file does not exist: {str(source)!r}")

    source_report = verify_database_file(
        source, expected_user_version=expected_user_version
    )
    if not source_report.ok:
        raise RestoreSourceNotVerified(source_report)

    if work_dir is None or str(work_dir).strip() == "":
        raise RestoreTargetRefused(
            "restore requires an explicit isolated temporary directory"
        )
    work = Path(work_dir).expanduser()
    if not work.exists() or not work.is_dir():
        raise RestoreTargetRefused(
            f"restore target directory does not exist: {str(work)!r}"
        )
    work = work.resolve()

    temp_root = _temp_root()
    if not work.is_relative_to(temp_root):
        raise RestoreTargetRefused(
            f"restore is allowed only inside the system temporary directory "
            f"({str(temp_root)!r}); got {str(work)!r}"
        )

    source_dir = source.resolve().parent
    if _overlaps(work, source_dir):
        raise RestoreTargetRefused(
            f"the restore directory must not be the backup directory "
            f"({str(source_dir)!r}) or contain it"
        )

    if storage is not None:
        if storage.db_path is not None:
            db_dir = storage.db_path.resolve().parent
            if _overlaps(work, db_dir):
                raise RestoreTargetRefused(
                    f"the restore directory must not touch the database "
                    f"directory ({str(db_dir)!r})"
                )
        if storage.backup_dir is not None:
            if _overlaps(work, storage.backup_dir.resolve()):
                raise RestoreTargetRefused(
                    f"the restore directory must not touch the backup "
                    f"directory ({str(storage.backup_dir)!r})"
                )

    target_name = name or f"{source.stem}.restored.sqlite"
    if Path(target_name).name != target_name or target_name in (".", ".."):
        raise RestoreTargetRefused(
            f"restore name must be a file name inside the target directory, got {target_name!r}"
        )
    target = work / target_name
    if target.exists():
        raise RestoreTargetRefused(
            f"the restore target already exists and is never overwritten: {str(target)!r}"
        )
    if storage is not None and storage.db_path is not None:
        if target.resolve() == storage.db_path.resolve():
            raise RestoreTargetRefused(
                "restore must never write to the working database file"
            )

    try:
        shutil.copyfile(str(source), str(target))
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise RestoreFailed(
            f"restore copy failed: {type(exc).__name__}: {exc}"
        ) from exc

    target_report = verify_database_file(
        target, expected_user_version=expected_user_version
    )
    if not target_report.ok:
        target.unlink(missing_ok=True)
        raise RestoreVerificationFailed(target_report)

    return RestoreResult(
        source_path=str(source),
        target_path=str(target),
        work_dir=str(work),
        restored_at=clock().isoformat(),
        source_report=source_report,
        target_report=target_report,
    )


def run_restore_drill(
    storage: StoragePaths,
    work_dir,
    *,
    backup_name: Optional[str] = None,
    name: Optional[str] = None,
    expected_user_version: Optional[int] = None,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    clock: Callable[[], datetime] = _utc_now,
) -> DrillResult:
    """Back up the configured database, then restore it into ``work_dir``.

    Migrations are deliberately NOT run here: the restored file is verified
    against ``expected_user_version`` and the caller applies ``migrate()``
    explicitly if the restored schema is older.
    """
    backup = create_backup(
        storage,
        name=backup_name,
        expected_user_version=expected_user_version,
        busy_timeout_ms=busy_timeout_ms,
        clock=clock,
    )
    restore = restore_backup(
        backup.backup_path,
        work_dir,
        name=name,
        storage=storage,
        expected_user_version=expected_user_version,
        clock=clock,
    )
    return DrillResult(backup=backup, restore=restore)
