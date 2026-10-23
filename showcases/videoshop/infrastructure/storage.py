"""S7 V1: explicit storage paths for the VideoShop SQLite database.

Approved narrow scope (S7 V1):

* permanent storage requires an **explicit file path**: there is no default path
  and no hidden fallback to ``:memory:``;
* ``:memory:`` is legal only in the explicitly declared memory mode (tests); in
  the file/storage mode it is a typed error;
* the backup directory must be a **separate directory tree** from the working
  database directory (equal, nested or containing paths are refused);
* the configuration arrives from the caller as an argument. Environment
  variables, CLI flags, schedulers and retention are deliberately NOT part of
  V1 (they are owner decisions, see the S7 design register).

This module never invents a path: it only validates and normalises what the
caller supplies, and refuses unsafe combinations before any file is touched.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

#: the SQLite in-memory sentinel
MEMORY_PATH = ":memory:"

#: explicit modes; there is no third "guess it" mode on purpose
MODE_MEMORY = "memory"
MODE_FILE = "file"

PathLike = Union[str, "os.PathLike[str]"]


class StorageError(RuntimeError):
    """Base error of the S7 storage contract."""

    code = "STORAGE_ERROR"


class StorageModeInvalid(StorageError):
    code = "STORAGE_MODE_INVALID"


class StorageModeConflict(StorageError):
    """The mode and the supplied paths disagree (e.g. file mode + :memory:)."""

    code = "STORAGE_MODE_CONFLICT"


class StoragePathMissing(StorageError):
    code = "STORAGE_PATH_MISSING"


class StorageMemoryForbidden(StorageError):
    code = "STORAGE_MEMORY_FORBIDDEN"


class StoragePathNotAbsolute(StorageError):
    code = "STORAGE_PATH_NOT_ABSOLUTE"


class StorageDirectoryMissing(StorageError):
    code = "STORAGE_DIRECTORY_MISSING"


class StorageNotADirectory(StorageError):
    code = "STORAGE_NOT_A_DIRECTORY"


class StorageNotAFilePath(StorageError):
    code = "STORAGE_NOT_A_FILE_PATH"


class StorageDirectoryNotWritable(StorageError):
    code = "STORAGE_DIRECTORY_NOT_WRITABLE"


class StorageBackupDirectoryConflict(StorageError):
    code = "STORAGE_BACKUP_DIRECTORY_CONFLICT"


@dataclass(frozen=True)
class StoragePaths:
    """Validated storage configuration.

    ``db_path`` / ``backup_dir`` are ``None`` in memory mode: an in-memory
    database has no file to copy, and V1 refuses to back it up.
    """

    mode: str
    db_path: Optional[Path] = None
    backup_dir: Optional[Path] = None

    @property
    def is_file(self) -> bool:
        return self.mode == MODE_FILE

    def require_file_path(self) -> Path:
        """Return the database file path or refuse with a typed error."""
        if not self.is_file or self.db_path is None:
            raise StorageMemoryForbidden(
                "this operation requires file-backed storage; an in-memory "
                "database has no file to copy"
            )
        return self.db_path

    def require_backup_dir(self) -> Path:
        """Return the validated backup directory or refuse with a typed error."""
        if self.backup_dir is None:
            raise StoragePathMissing("no backup directory is configured")
        return self.backup_dir


def _probe_writable(directory: Path) -> bool:
    """Return True when a file can be created in ``directory`` right now."""
    try:
        with tempfile.NamedTemporaryFile(dir=str(directory), prefix=".s7-probe-"):
            return True
    except OSError:
        return False


def _resolve_directory(raw: PathLike, label: str, *, create_directory: bool) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise StoragePathNotAbsolute(f"{label} must be an absolute path, got {str(path)!r}")
    if path.exists() and not path.is_dir():
        raise StorageNotADirectory(f"{label} is not a directory: {str(path)!r}")
    if not path.exists():
        if not create_directory:
            raise StorageDirectoryMissing(
                f"{label} does not exist: {str(path)!r} "
                f"(creating directories is an explicit opt-in)"
            )
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageDirectoryMissing(
                f"{label} could not be created: {str(path)!r}: {exc}"
            ) from exc
    if not _probe_writable(path):
        raise StorageDirectoryNotWritable(f"{label} is not writable: {str(path)!r}")
    return path


def resolve_storage(
    db_path: Optional[PathLike] = None,
    backup_dir: Optional[PathLike] = None,
    *,
    mode: str = MODE_FILE,
    create_directory: bool = False,
) -> StoragePaths:
    """Validate and normalise the storage configuration.

    File mode is the default: it fails closed when the path is missing, empty or
    ``:memory:``. Memory mode must be requested explicitly and rejects file
    paths. Nothing is created unless ``create_directory=True`` is passed
    explicitly.
    """
    if mode not in (MODE_MEMORY, MODE_FILE):
        raise StorageModeInvalid(f"unknown storage mode {mode!r}")

    if mode == MODE_MEMORY:
        if db_path is not None and str(db_path) != MEMORY_PATH:
            raise StorageModeConflict(
                f"memory mode cannot use the file path {str(db_path)!r}; "
                f"pass {MEMORY_PATH!r} or use mode={MODE_FILE!r}"
            )
        if backup_dir is not None:
            raise StorageModeConflict(
                "memory mode has no backup directory: an in-memory database "
                "cannot be protected by file backup in S7 V1"
            )
        return StoragePaths(mode=MODE_MEMORY)

    if db_path is None or str(db_path).strip() == "":
        raise StoragePathMissing(
            "file storage requires an explicit database path "
            "(no default path and no fallback to :memory:)"
        )
    if str(db_path) == MEMORY_PATH:
        raise StorageMemoryForbidden(
            ":memory: is not a storage path; pass a real file path in file mode "
            "or request mode='memory' explicitly"
        )
    if backup_dir is None or str(backup_dir).strip() == "":
        raise StoragePathMissing(
            "file storage requires an explicit backup directory"
        )

    db_file = Path(db_path).expanduser()
    if not db_file.is_absolute():
        raise StoragePathNotAbsolute(
            f"database path must be absolute, got {str(db_file)!r}"
        )
    if db_file.exists() and db_file.is_dir():
        raise StorageNotAFilePath(f"database path is a directory: {str(db_file)!r}")

    db_dir = _resolve_directory(db_file.parent, "database directory", create_directory=create_directory)
    backup_dir_path = _resolve_directory(
        Path(backup_dir), "backup directory", create_directory=create_directory
    )

    db_dir_real = db_dir.resolve()
    backup_real = backup_dir_path.resolve()
    if backup_real == db_dir_real:
        raise StorageBackupDirectoryConflict(
            f"the backup directory must differ from the database directory: {str(backup_real)!r}"
        )
    if backup_real.is_relative_to(db_dir_real):
        raise StorageBackupDirectoryConflict(
            f"the backup directory {str(backup_real)!r} is inside the database "
            f"directory {str(db_dir_real)!r}"
        )
    if db_dir_real.is_relative_to(backup_real):
        raise StorageBackupDirectoryConflict(
            f"the database directory {str(db_dir_real)!r} is inside the backup "
            f"directory {str(backup_real)!r}"
        )

    return StoragePaths(
        mode=MODE_FILE,
        db_path=(db_dir / db_file.name).resolve(),
        backup_dir=backup_real,
    )
