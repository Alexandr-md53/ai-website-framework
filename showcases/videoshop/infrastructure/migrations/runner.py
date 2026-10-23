"""VideoShop migration runner (S3 scope: S3-owned tables only).

Contract:

* schema version is stored in ``PRAGMA user_version`` (the only interpolated
  value is a code-owned integer - never user input);
* migrations are applied in ascending version order, each one inside a single
  transaction that also bumps ``user_version`` - the step and its version are
  therefore atomic (a failure leaves both the schema and the version
  unchanged);
* re-running is a no-op for already applied versions (idempotent);
* a database whose ``user_version`` is newer than the highest known migration is
  rejected with :class:`UnsupportedSchemaVersion` and no changes are made.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Sequence


class MigrationError(RuntimeError):
    """A migration step failed (nothing from that step was applied)."""


class UnsupportedSchemaVersion(MigrationError):
    """The database schema version is newer than this code supports."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[Any], None]  # receives the transaction handle


def _validated_steps(migrations: Optional[Iterable[Migration]]) -> Sequence[Migration]:
    if migrations is None:
        from .s3 import S3_MIGRATIONS

        migrations = S3_MIGRATIONS
    steps = sorted(list(migrations), key=lambda step: step.version)
    for step in steps:
        if isinstance(step.version, bool) or not isinstance(step.version, int):
            raise MigrationError(f"migration version must be int: {step!r}")
        if step.version < 1:
            raise MigrationError(f"migration version must be >= 1: {step!r}")
        if not callable(step.apply):
            raise MigrationError(f"migration {step.version} has no callable apply()")
    return steps


def read_schema_version(provider: Any) -> int:
    """Read ``PRAGMA user_version`` through the S1 transaction API."""
    with provider.transaction() as tx:
        return int(tx.scalar("PRAGMA user_version"))


def migrate(provider: Any, migrations: Optional[Iterable[Migration]] = None) -> int:
    """Apply pending migrations; returns the resulting schema version."""
    steps = _validated_steps(migrations)
    target = steps[-1].version if steps else 0

    current = read_schema_version(provider)
    if current > target:
        raise UnsupportedSchemaVersion(
            f"database schema version {current} is newer than the highest "
            f"supported version {target}: refusing to touch the database"
        )

    for step in steps:
        if step.version <= current:
            continue
        try:
            with provider.transaction() as tx:
                step.apply(tx)
                tx.execute(f"PRAGMA user_version = {step.version}")
        except Exception as exc:
            raise MigrationError(
                f"migration {step.version} ({step.name}) failed and was rolled "
                f"back: {type(exc).__name__}: {exc}"
            ) from exc
        current = step.version

    return current
