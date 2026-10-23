"""S3-owned schema: the slug registry table (migration step 1).

Only S3-owned objects are created here. No catalogue or business entity table is
created, and no versioned-entity DDL is touched.
"""
from __future__ import annotations

from typing import Any

from ..slug_registry import ENTITY_TYPE_MAX_LENGTH, SLUG_MAX_LENGTH, TABLE
from .runner import Migration

#: identifiers are module constants (never user input); values are bound elsewhere
SLUG_REGISTRY_DDL = (
    f"CREATE TABLE IF NOT EXISTS {TABLE} ("
    " entity_type TEXT NOT NULL,"
    " slug        TEXT NOT NULL,"
    " entity_id   INTEGER NOT NULL,"
    " state       TEXT NOT NULL DEFAULT 'live',"
    " created_at  TEXT NOT NULL,"
    " released_at TEXT,"
    " PRIMARY KEY (entity_type, slug),"
    " CHECK (state IN ('live', 'released')),"
    f" CHECK (length(slug) BETWEEN 1 AND {SLUG_MAX_LENGTH}),"
    f" CHECK (length(entity_type) BETWEEN 1 AND {ENTITY_TYPE_MAX_LENGTH}),"
    " CHECK (entity_id > 0),"
    " CHECK ((state = 'live' AND released_at IS NULL)"
    "     OR (state = 'released' AND released_at IS NOT NULL))"
    ")"
)

SLUG_REGISTRY_INDEX = (
    f"CREATE INDEX IF NOT EXISTS ix_slug_registry_entity "
    f"ON {TABLE} (entity_type, entity_id, state)"
)


def _apply_s3_1(tx: Any) -> None:
    tx.execute(SLUG_REGISTRY_DDL)
    tx.execute(SLUG_REGISTRY_INDEX)


#: step 2: at most one LIVE slug per entity - enforced by the database itself
LIVE_ENTITY_UNIQUE_INDEX = (
    f"CREATE UNIQUE INDEX IF NOT EXISTS ux_slug_registry_live_entity "
    f"ON {TABLE} (entity_type, entity_id) WHERE state = 'live'"
)


class LiveSlugDuplicatesError(RuntimeError):
    """Existing rows already violate the live-slug invariant.

    Raised by step 2 *inside* its transaction: the migration never deletes or
    rewrites rows, so the operator has to resolve the listed duplicates and run
    the migration again. The runner rolls the step back, therefore neither the
    index nor ``user_version`` change.
    """

    def __init__(self, duplicates: Any) -> None:
        self.duplicates = [
            (row["entity_type"], row["entity_id"], row["live_count"]) for row in duplicates
        ]
        detail = ", ".join(
            f"{entity_type}#{entity_id} x{count}"
            for entity_type, entity_id, count in self.duplicates
        )
        super().__init__(
            "existing live slug duplicates for (entity_type, entity_id): "
            f"{detail}; resolve them manually before migrating - the migration "
            "never deletes or rewrites rows"
        )


def _apply_s3_2(tx: Any) -> None:
    duplicates = tx.fetchall(
        f"SELECT entity_type, entity_id, COUNT(*) AS live_count FROM {TABLE} "
        f"WHERE state = 'live' GROUP BY entity_type, entity_id HAVING COUNT(*) > 1"
    )
    if duplicates:
        raise LiveSlugDuplicatesError(duplicates)
    tx.execute(LIVE_ENTITY_UNIQUE_INDEX)


S3_MIGRATIONS = (
    Migration(version=1, name="s3_slug_registry", apply=_apply_s3_1),
    Migration(version=2, name="s3_live_slug_invariant", apply=_apply_s3_2),
)
