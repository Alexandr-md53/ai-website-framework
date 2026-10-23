"""S7 V1 tests: explicit storage paths, verified backup, temp-only restore drill.

Covered scenarios (approved narrow scope):

1. missing storage path / ``:memory:`` in storage mode (typed refusals);
2. memory mode still works for tests and cannot be backed up;
3. successful verified backup (integrity, FKs, user_version, S3 invariants);
4. consistency while another process/thread keeps writing;
5. copy-creation failure leaves no file that could pass for a backup;
6. verification failure before publication;
7. an existing final copy is never overwritten;
8. dangerous path overlaps are refused;
9. a corrupted copy is rejected by verification and by restore;
10. an incompatible ``user_version`` is detected and ``migrate()`` stays fail-closed;
11. a foreign-key violation is detected and the restore is refused;
12. a simulated write failure leaves no published copy (a real ENOSPC was NOT
    reproduced - the failure is injected at the copy boundary);
13. restore is allowed only inside the system temporary directory;
14. the restore drill succeeds into a new temp file (data, indexes, version,
    explicit idempotent ``migrate()`` on the restored copy);
15. explicit ``migrate()`` forward-migrates an older restored copy;
16. a failed restore removes the target file it created.

No production table, no live database and no HTTP route is involved: every
database lives under pytest's ``tmp_path``.
"""
from __future__ import annotations

import dataclasses
import hashlib
import sqlite3
import threading
from pathlib import Path

import pytest

from showcases.videoshop.infrastructure import backup as backup_module
from showcases.videoshop.infrastructure import restore as restore_module
from showcases.videoshop.infrastructure.backup import (
    CHECK_FOREIGN_KEYS,
    CHECK_HEADER_INVALID,
    CHECK_USER_VERSION_MISMATCH,
    BackupAlreadyExists,
    BackupCopyFailed,
    BackupSourceNotAFile,
    BackupVerificationFailed,
    create_backup,
    verify_database_file,
)
from showcases.videoshop.infrastructure.migrations import (
    S3_MIGRATIONS,
    UnsupportedSchemaVersion,
    migrate,
    read_schema_version,
)
from showcases.videoshop.infrastructure.restore import (
    RestoreFailed,
    RestoreSourceNotVerified,
    RestoreTargetRefused,
    RestoreVerificationFailed,
    restore_backup,
    run_restore_drill,
)
from showcases.videoshop.infrastructure.slug_registry import SlugRegistry
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.infrastructure.storage import (
    MODE_MEMORY,
    StorageBackupDirectoryConflict,
    StorageMemoryForbidden,
    StorageModeConflict,
    StoragePathMissing,
    resolve_storage,
)

EXPECTED_SCHEMA_VERSION = max(step.version for step in S3_MIGRATIONS)
ENTITY_TYPE = "test_article"
LIVE_INDEX = "ux_slug_registry_live_entity"
ENTITY_INDEX = "ix_slug_registry_entity"


# --- fixtures and helpers ------------------------------------------------


@pytest.fixture
def storage(tmp_path):
    # sibling trees on purpose: the contract refuses a backup directory that
    # lives inside the database directory
    (tmp_path / "db").mkdir()
    (tmp_path / "backups").mkdir()
    return resolve_storage(
        db_path=tmp_path / "db" / "shop.db", backup_dir=tmp_path / "backups"
    )


@pytest.fixture
def work_dir(tmp_path):
    directory = tmp_path / "work"
    directory.mkdir()
    return directory


def _seed(storage, *, slugs=(("alpha", 1), ("beta", 2)), release=("beta",)):
    """Create the current schema and a live + released slug history."""
    provider = VideoShopSQLiteProvider(db_path=str(storage.db_path))
    registry = SlugRegistry(provider)
    assert registry.migrate() == EXPECTED_SCHEMA_VERSION
    owners = dict(slugs)
    for slug, entity_id in slugs:
        registry.register(ENTITY_TYPE, slug, entity_id)
    for slug in release:
        registry.release(ENTITY_TYPE, slug, owners[slug])
    return provider, registry


def _digest(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _backup_dir_entries(storage):
    return sorted(entry.name for entry in storage.backup_dir.iterdir())


# --- 1. storage path contract -------------------------------------------


def test_file_mode_requires_an_explicit_path(tmp_path):
    with pytest.raises(StoragePathMissing):
        resolve_storage(None, tmp_path / "backups")
    with pytest.raises(StoragePathMissing):
        resolve_storage("", tmp_path / "backups")
    with pytest.raises(StoragePathMissing):
        resolve_storage(tmp_path / "shop.db", None)
    with pytest.raises(StorageMemoryForbidden):
        resolve_storage(":memory:", tmp_path / "backups")


def test_memory_mode_is_explicit_and_not_backupable(tmp_path):
    memory = resolve_storage(mode=MODE_MEMORY)
    assert memory.is_file is False
    assert memory.db_path is None and memory.backup_dir is None

    # the in-memory database itself keeps working (tests only)
    provider = VideoShopSQLiteProvider(db_path=":memory:")
    with provider.transaction() as tx:
        tx.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")

    with pytest.raises(StorageMemoryForbidden):
        memory.require_file_path()
    with pytest.raises(BackupSourceNotAFile):
        create_backup(memory)
    with pytest.raises(StorageModeConflict):
        resolve_storage(tmp_path / "shop.db", mode=MODE_MEMORY)


# --- 2./3. successful verified backup -----------------------------------


def test_backup_publishes_a_verified_copy(storage):
    _seed(storage)

    result = create_backup(storage, expected_user_version=EXPECTED_SCHEMA_VERSION)

    backup_path = Path(result.backup_path)
    assert backup_path.exists() and backup_path.parent == storage.backup_dir
    assert result.report.ok, result.report.as_dict()
    assert result.report.path == str(backup_path), "the report must name the published file"
    assert result.report.integrity == "ok"
    assert result.report.foreign_key_violations == 0
    assert result.report.user_version == EXPECTED_SCHEMA_VERSION
    assert result.report.registry_present is True
    assert result.report.live_rows == 1
    assert result.report.released_rows == 1
    assert LIVE_INDEX in result.report.indexes
    assert ENTITY_INDEX in result.report.indexes
    assert _backup_dir_entries(storage) == [backup_path.name], "no temporary files may remain"

    # the copy is a usable database with the same registry content
    copy_registry = SlugRegistry(VideoShopSQLiteProvider(db_path=str(backup_path)))
    assert copy_registry.get(ENTITY_TYPE, "alpha")["state"] == "live"
    assert copy_registry.get(ENTITY_TYPE, "beta")["state"] == "released"


def test_backup_is_consistent_while_a_writer_commits(storage):
    _seed(storage)
    errors: list[str] = []
    stop = threading.Event()

    def writer() -> None:
        try:
            provider = VideoShopSQLiteProvider(db_path=str(storage.db_path))
            registry = SlugRegistry(provider)
            for index in range(1, 26):
                if stop.is_set():
                    break
                registry.register(ENTITY_TYPE, f"race-{index}", 100 + index)
        except Exception as exc:  # noqa: BLE001 - reported through the assertion
            errors.append(f"{type(exc).__name__}: {exc}")

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()
    try:
        result = create_backup(storage, expected_user_version=EXPECTED_SCHEMA_VERSION)
    finally:
        stop.set()
        thread.join(timeout=120)

    assert errors == [], errors
    assert result.report.ok, result.report.as_dict()
    assert 1 <= result.report.live_rows <= 26, result.report.live_rows
    assert result.report.released_rows == 1
    # the working database is intact and still verifies
    assert verify_database_file(storage.db_path).ok


# --- 4./5./6. failures never publish ------------------------------------


def test_copy_failure_is_typed_and_leaves_nothing(storage):
    _seed(storage)
    storage.db_path.write_bytes(b"this file is not a sqlite database")

    with pytest.raises(BackupCopyFailed):
        create_backup(storage)

    assert _backup_dir_entries(storage) == [], "a failed copy must not leave any file"


def test_verification_failure_does_not_publish(storage):
    _seed(storage)

    with pytest.raises(BackupVerificationFailed) as excinfo:
        create_backup(storage, expected_user_version=EXPECTED_SCHEMA_VERSION + 1)

    assert CHECK_USER_VERSION_MISMATCH in excinfo.value.report.failed_checks
    assert _backup_dir_entries(storage) == []


def test_existing_final_copy_is_never_overwritten(storage):
    _seed(storage)
    first = create_backup(storage, name="fixed.backup.sqlite")
    before = _digest(first.backup_path)

    with pytest.raises(BackupAlreadyExists):
        create_backup(storage, name="fixed.backup.sqlite")

    assert _digest(first.backup_path) == before, "the existing copy must stay untouched"
    assert _backup_dir_entries(storage) == ["fixed.backup.sqlite"]


def test_dangerous_path_overlaps_are_refused(tmp_path):
    with pytest.raises(StorageBackupDirectoryConflict):
        resolve_storage(db_path=tmp_path / "shop.db", backup_dir=tmp_path)

    db_dir = tmp_path / "db"
    (db_dir / "backups").mkdir(parents=True)
    with pytest.raises(StorageBackupDirectoryConflict):
        resolve_storage(db_path=db_dir / "shop.db", backup_dir=db_dir / "backups")

    (tmp_path / "tree" / "db").mkdir(parents=True)
    with pytest.raises(StorageBackupDirectoryConflict):
        resolve_storage(
            db_path=tmp_path / "tree" / "db" / "shop.db",
            backup_dir=tmp_path / "tree",
        )


# --- 7. corrupted copy / wrong version / FK violation -------------------


def test_corrupted_copy_is_rejected(storage, work_dir):
    _seed(storage)
    result = create_backup(storage)
    copy_path = Path(result.backup_path)

    original = copy_path.read_bytes()
    copy_path.write_bytes(b"X" * len(original))  # header destroyed (test-only)
    report = verify_database_file(copy_path, expected_user_version=EXPECTED_SCHEMA_VERSION)
    assert not report.ok
    assert CHECK_HEADER_INVALID in report.failed_checks

    copy_path.write_bytes(original[: max(1, len(original) // 2)])  # truncated copy
    report = verify_database_file(copy_path, expected_user_version=EXPECTED_SCHEMA_VERSION)
    assert not report.ok, "a truncated copy must never verify"

    with pytest.raises(RestoreSourceNotVerified):
        restore_backup(copy_path, work_dir, storage=storage)
    assert list(work_dir.iterdir()) == [], "a refused restore creates nothing"


def test_incompatible_user_version_is_detected(storage, work_dir):
    provider, _ = _seed(storage)
    with provider.transaction() as tx:
        tx.execute("PRAGMA user_version = 999")

    report = verify_database_file(storage.db_path, expected_user_version=EXPECTED_SCHEMA_VERSION)
    assert CHECK_USER_VERSION_MISMATCH in report.failed_checks
    with pytest.raises(UnsupportedSchemaVersion):
        migrate(provider)

    result = create_backup(storage)  # publication only records the version
    assert result.report.user_version == 999
    with pytest.raises(RestoreSourceNotVerified):
        restore_backup(
            result.backup_path,
            work_dir,
            storage=storage,
            expected_user_version=EXPECTED_SCHEMA_VERSION,
        )
    assert list(work_dir.iterdir()) == []


def test_foreign_key_violation_is_detected(storage, work_dir):
    connection = sqlite3.connect(str(storage.db_path))
    try:
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE child (id INTEGER PRIMARY KEY, pid INTEGER REFERENCES parent(id))"
        )
        # foreign_keys is OFF on this raw connection, so the orphan row is stored
        connection.execute("INSERT INTO child (id, pid) VALUES (1, 42)")
        connection.commit()
    finally:
        connection.close()

    report = verify_database_file(storage.db_path)
    assert report.foreign_key_violations == 1
    assert CHECK_FOREIGN_KEYS in report.failed_checks

    with pytest.raises(RestoreSourceNotVerified):
        restore_backup(storage.db_path, work_dir, storage=storage)
    assert list(work_dir.iterdir()) == []


def test_simulated_write_failure_leaves_no_published_copy(storage, monkeypatch):
    """A real 'disk full' was NOT reproduced: the failure is injected."""
    _seed(storage)

    def failing_copy(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error (simulated, not a real ENOSPC)")

    monkeypatch.setattr(backup_module, "_copy_database", failing_copy)

    with pytest.raises(BackupCopyFailed):
        create_backup(storage)
    assert _backup_dir_entries(storage) == []


# --- 8. restore is temp-only -------------------------------------------


def test_restore_is_allowed_only_in_the_temporary_directory(storage, work_dir, monkeypatch):
    _seed(storage)
    result = create_backup(storage)
    db_dir_before = sorted(entry.name for entry in storage.db_path.parent.iterdir())

    monkeypatch.setattr(restore_module, "_temp_root", lambda: work_dir.parent / "fake-root")
    with pytest.raises(RestoreTargetRefused):
        restore_backup(result.backup_path, work_dir, storage=storage)
    monkeypatch.undo()

    with pytest.raises(RestoreTargetRefused):
        restore_backup(result.backup_path, storage.backup_dir, storage=storage)
    with pytest.raises(RestoreTargetRefused):
        restore_backup(result.backup_path, storage.db_path.parent, storage=storage)

    assert list(work_dir.iterdir()) == []
    assert sorted(entry.name for entry in storage.db_path.parent.iterdir()) == db_dir_before, (
        "nothing may be written next to the working database"
    )


# --- 9. the drill -------------------------------------------------------


def test_restore_drill_into_a_new_temp_file(storage, work_dir):
    _seed(storage)
    working_digest = _digest(storage.db_path)

    drill = run_restore_drill(
        storage, work_dir, expected_user_version=EXPECTED_SCHEMA_VERSION
    )

    restore = drill.restore
    target = Path(restore.target_path)
    assert target.exists() and target.parent == work_dir.resolve()
    assert target.name != storage.db_path.name

    for report in (drill.backup.report, restore.source_report, restore.target_report):
        assert report.ok, report.as_dict()
    target_report = restore.target_report
    assert target_report.user_version == EXPECTED_SCHEMA_VERSION
    assert LIVE_INDEX in target_report.indexes and ENTITY_INDEX in target_report.indexes
    assert target_report.live_rows == 1 and target_report.released_rows == 1

    restored_provider = VideoShopSQLiteProvider(db_path=str(target))
    restored_registry = SlugRegistry(restored_provider)
    assert restored_registry.get(ENTITY_TYPE, "alpha")["state"] == "live"
    assert restored_registry.get(ENTITY_TYPE, "beta")["state"] == "released"

    # migrations are an explicit, separate step and stay idempotent here
    assert migrate(restored_provider) == EXPECTED_SCHEMA_VERSION
    assert read_schema_version(restored_provider) == EXPECTED_SCHEMA_VERSION

    # the working database was neither replaced nor modified
    assert _digest(storage.db_path) == working_digest
    assert verify_database_file(storage.db_path).ok


def test_drill_forward_migrates_an_older_copy(storage, work_dir):
    provider = VideoShopSQLiteProvider(db_path=str(storage.db_path))
    registry = SlugRegistry(provider)
    assert registry.migrate((S3_MIGRATIONS[0],)) == 1, "only the step-1 schema"
    registry.register(ENTITY_TYPE, "legacy", 7)

    backup = create_backup(storage)
    assert backup.report.user_version == 1

    restore = restore_backup(
        backup.backup_path,
        work_dir,
        storage=storage,
        expected_user_version=1,
    )
    restored_provider = VideoShopSQLiteProvider(db_path=restore.target_path)
    assert read_schema_version(restored_provider) == 1

    assert migrate(restored_provider) == EXPECTED_SCHEMA_VERSION
    assert read_schema_version(restored_provider) == EXPECTED_SCHEMA_VERSION
    assert SlugRegistry(restored_provider).get(ENTITY_TYPE, "legacy")["entity_id"] == 7
    assert verify_database_file(
        restore.target_path, expected_user_version=EXPECTED_SCHEMA_VERSION
    ).ok


# --- 10. failed restore ------------------------------------------------


def test_failed_restore_copy_removes_its_own_target(storage, work_dir, monkeypatch):
    _seed(storage)
    result = create_backup(storage)

    def failing_copy(source, target):
        Path(target).write_bytes(b"half written")
        raise OSError("simulated copy failure")

    monkeypatch.setattr(restore_module.shutil, "copyfile", failing_copy)

    with pytest.raises(RestoreFailed):
        restore_backup(result.backup_path, work_dir, storage=storage)
    assert list(work_dir.iterdir()) == [], "the partial target must be removed"


def test_failed_restore_verification_removes_the_restored_file(storage, work_dir, monkeypatch):
    _seed(storage)
    result = create_backup(storage)
    real_verify = restore_module.verify_database_file

    def failing_verification(path, *, expected_user_version=None):
        report = real_verify(path, expected_user_version=expected_user_version)
        if Path(path).name.endswith(".restored.sqlite"):
            return dataclasses.replace(report, failed_checks=("integrity_check",))
        return report

    monkeypatch.setattr(restore_module, "verify_database_file", failing_verification)

    with pytest.raises(RestoreVerificationFailed):
        restore_backup(result.backup_path, work_dir, storage=storage)
    assert list(work_dir.iterdir()) == [], "an unverified restore must be removed"
