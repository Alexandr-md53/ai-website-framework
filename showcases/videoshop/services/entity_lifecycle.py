"""S4: entity lifecycle integration with the slug registry (TEST ENTITIES ONLY).

Authorized scope: test tables and a test lifecycle. No production business
model, no production migration, no HTTP routes.

Accepted decisions implemented here:

* **D1** - the slug lives ONLY in ``slug_registry``; entity tables have no slug
  column (no dual write, no divergence);
* **D2** - CAS participates in the caller's transaction through
  ``tx.update_record_cas`` (no ``ai_framework`` change);
* **D3** - test entities use INTEGER ids > 0 (the production id type is UNKNOWN);
* **D4** - both versioned and non-versioned test entities are supported;
* **D5** - delete = release the live slug + HARD DELETE the entity, in ONE
  transaction (the production deletion policy is not decided);
* **D6** - resolution returns ``current`` / ``redirect`` (target = the entity's
  current live slug) / ``not_found``; no HTTP status is fixed here;
* **D7** - ``entity_type`` is explicit; type tokens are supplied by the caller;
* **D9** - released slugs are kept forever and are never re-assigned;
* **D10** - no tenant/language dimension in the key.

Single-transaction guarantee: every lifecycle operation runs in ONE
``provider.transaction()`` and uses only transaction-bound operations
(``tx.execute``, ``tx.update_record_cas``, ``registry.within(tx)``). No method
that opens its own connection is called inside a lifecycle scope, therefore a
CAS conflict, a slug conflict or a delete error rolls the whole operation back.

Test-only: the concrete tables used by the tests are created by the tests
themselves; this module never creates tables and never runs entity migrations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from ..infrastructure.slug_registry import (
    STATE_LIVE,
    STATE_RELEASED,
    SlugRegistry,
    validate_entity_id,
    validate_entity_type,
    validate_slug,
)
from ..infrastructure.retry import run_transaction_with_retry
from ..infrastructure.sqlite_provider import CasResult

#: code-owned identifiers only - user input is never interpolated as an identifier
IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

RESOLUTION_CURRENT = "current"
RESOLUTION_REDIRECT = "redirect"
RESOLUTION_NOT_FOUND = "not_found"


class LifecycleError(RuntimeError):
    """Base error of the S4 entity lifecycle."""


class InvalidEntityTable(LifecycleError):
    """The entity table / column name is not a safe code-owned identifier."""


class EntityNotFound(LifecycleError):
    """The entity row does not exist."""


class CasConflict(LifecycleError):
    """Stored version differs from the expected one; the whole operation rolls back."""

    code = "CAS_CONFLICT"

    def __init__(
        self,
        entity_type: str,
        entity_id: int,
        expected_version: int,
        actual_version: Optional[int],
    ) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"CAS_CONFLICT: entity '{entity_type}#{entity_id}' has version "
            f"{actual_version}, expected {expected_version}"
        )


@dataclass(frozen=True)
class SlugResolution:
    """Outcome of resolving a requested slug (no HTTP status is decided here)."""

    kind: str
    requested_slug: str
    entity_id: Optional[int] = None
    current_slug: Optional[str] = None

    @property
    def is_current(self) -> bool:
        return self.kind == RESOLUTION_CURRENT

    @property
    def is_redirect(self) -> bool:
        return self.kind == RESOLUTION_REDIRECT

    @property
    def is_not_found(self) -> bool:
        return self.kind == RESOLUTION_NOT_FOUND


class EntityLifecycleService:
    """Test-entity lifecycle bound to one explicit entity type and table."""

    def __init__(
        self,
        provider: Any,
        registry: SlugRegistry,
        entity_type: str,
        table: str,
        *,
        versioned: bool = False,
    ) -> None:
        if not IDENTIFIER_PATTERN.match(str(table)):
            raise InvalidEntityTable(f"unsafe entity table identifier: {table!r}")
        self._provider = provider
        self._registry = registry
        self._entity_type = validate_entity_type(entity_type)
        self._table = str(table)
        self._versioned = bool(versioned)
        # learned before any transaction is opened (public provider helper, D2)
        self._version_column = provider.version_column_name(self._table) if self._versioned else None
        if self._versioned and self._version_column is None:
            raise LifecycleError(
                f"entity table '{self._table}' is declared versioned but has no version column"
            )

    # --- properties ------------------------------------------------------

    @property
    def entity_type(self) -> str:
        return self._entity_type

    @property
    def table(self) -> str:
        return self._table

    @property
    def versioned(self) -> bool:
        return self._versioned

    # --- internals -------------------------------------------------------

    def _validated_fields(self, fields: Optional[dict]) -> dict:
        cleaned: dict = {}
        for key, value in (fields or {}).items():
            name = str(key)
            if not IDENTIFIER_PATTERN.match(name):
                raise LifecycleError(f"unsafe column identifier: {key!r}")
            if name == "id" or name.strip().casefold() == "version":
                raise LifecycleError(
                    f"column {name!r} is owned by the provider and cannot be set directly"
                )
            cleaned[name] = value
        return cleaned

    def _fetch_entity(self, tx: Any, entity_id: int) -> Optional[dict]:
        row = tx.fetchone(f"SELECT * FROM {self._table} WHERE id = ?", (entity_id,))
        return None if row is None else dict(row)

    # --- reads -----------------------------------------------------------

    def get_entity(self, entity_id: int) -> Optional[dict]:
        entity_id = validate_entity_id(entity_id)
        with self._provider.read_transaction() as tx:
            return self._fetch_entity(tx, entity_id)

    def live_slug(self, entity_id: int) -> Optional[str]:
        entity_id = validate_entity_id(entity_id)
        with self._provider.read_transaction() as tx:
            return self._registry.within(tx).live_slug(self._entity_type, entity_id)

    def resolve(self, slug: str) -> SlugResolution:
        """Resolve a requested slug (D6): current / redirect / not_found."""
        requested = validate_slug(slug)
        with self._provider.read_transaction() as tx:
            session = self._registry.within(tx)
            row = session.get(self._entity_type, requested)
            if row is None:
                return SlugResolution(RESOLUTION_NOT_FOUND, requested_slug=requested)

            entity_exists = self._fetch_entity(tx, row["entity_id"]) is not None

            if row["state"] == STATE_LIVE:
                if entity_exists:
                    return SlugResolution(
                        RESOLUTION_CURRENT,
                        requested_slug=requested,
                        entity_id=row["entity_id"],
                        current_slug=requested,
                    )
                # orphan live row (should be impossible through this service)
                return SlugResolution(RESOLUTION_NOT_FOUND, requested_slug=requested)

            if row["state"] != STATE_RELEASED:  # defensive: schema allows live/released only
                return SlugResolution(RESOLUTION_NOT_FOUND, requested_slug=requested)

            # released history -> exactly ONE hop to the entity's CURRENT live slug
            if not entity_exists:
                return SlugResolution(RESOLUTION_NOT_FOUND, requested_slug=requested)
            current = session.live_slug(self._entity_type, row["entity_id"])
            if current is None or current == requested:
                return SlugResolution(RESOLUTION_NOT_FOUND, requested_slug=requested)
            return SlugResolution(
                RESOLUTION_REDIRECT,
                requested_slug=requested,
                entity_id=row["entity_id"],
                current_slug=current,
            )

    # --- writes ----------------------------------------------------------

    def create(self, slug: str, fields: dict) -> dict:
        """Insert the entity and register its first slug in ONE transaction (S6 retry)."""
        slug = validate_slug(slug)
        return run_transaction_with_retry(
            self._provider, lambda tx: self._create_in(tx, slug, fields)
        )

    def _create_in(self, tx: Any, slug: str, fields: dict) -> dict:
        columns = self._validated_fields(fields)
        if not columns:
            raise LifecycleError("create() requires at least one entity field")
        placeholders = ", ".join("?" for _ in columns)
        cursor = tx.execute(
            f"INSERT INTO {self._table} ({', '.join(columns)}) VALUES ({placeholders})",
            list(columns.values()),
        )
        entity_id = int(cursor.lastrowid)
        self._registry.within(tx).register(self._entity_type, slug, entity_id)
        return self._fetch_entity(tx, entity_id)

    def rename(
        self,
        entity_id: int,
        new_slug: str,
        *,
        expected_version: Optional[int] = None,
        fields: Optional[dict] = None,
    ) -> dict:
        """Replace the entity's live slug in ONE transaction (D2/D6) with S6 retry.

        For versioned entities the version bump and the slug replacement share
        the transaction: if the slug is taken, the CAS is rolled back too.
        ``new_slug`` equal to the current slug without other ``fields`` is a
        literal no-op (no version bump, no history row).

        The WHOLE operation is retried on SQLITE_BUSY (S6/D-S6-3); it performs
        database work only, so a retry cannot replay external side effects.
        """
        entity_id = validate_entity_id(entity_id)
        new_slug = validate_slug(new_slug)

        return run_transaction_with_retry(
            self._provider,
            lambda tx: self._rename_in(tx, entity_id, new_slug, expected_version, fields),
        )

    def _rename_in(
        self,
        tx: Any,
        entity_id: int,
        new_slug: str,
        expected_version: Optional[int],
        fields: Optional[dict],
    ) -> dict:
        session = self._registry.within(tx)
        entity = self._fetch_entity(tx, entity_id)
        if entity is None:
            raise EntityNotFound(f"entity '{self._entity_type}#{entity_id}' does not exist")

        old_slug = session.live_slug(self._entity_type, entity_id)
        if old_slug is None:
            raise LifecycleError(
                f"entity '{self._entity_type}#{entity_id}' has no live slug to replace"
            )

        if old_slug == new_slug and not fields:
            return entity  # literal no-op

        if self._versioned:
            if expected_version is None:
                raise LifecycleError("expected_version is required for versioned entities")
            result = tx.update_record_cas(
                self._table, entity_id, self._validated_fields(fields), expected_version
            )
            if result.status == CasResult.CONFLICT:
                raise CasConflict(
                    self._entity_type, entity_id, expected_version, result.actual_version
                )
            if result.status == CasResult.NOT_FOUND:
                raise EntityNotFound(
                    f"entity '{self._entity_type}#{entity_id}' does not exist"
                )
        else:
            columns = self._validated_fields(fields)
            if columns:
                assignments = ", ".join(f"{key} = ?" for key in columns)
                tx.execute(
                    f"UPDATE {self._table} SET {assignments} WHERE id = ?",
                    list(columns.values()) + [entity_id],
                )

        session.replace_slug(self._entity_type, entity_id, old_slug, new_slug)
        return self._fetch_entity(tx, entity_id)

    def delete(self, entity_id: int, *, expected_version: Optional[int] = None) -> dict:
        """Release the live slug and HARD DELETE the entity in ONE transaction (D5, S6 retry)."""
        entity_id = validate_entity_id(entity_id)
        return run_transaction_with_retry(
            self._provider, lambda tx: self._delete_in(tx, entity_id, expected_version)
        )

    def _delete_in(
        self, tx: Any, entity_id: int, expected_version: Optional[int]
    ) -> dict:
        session = self._registry.within(tx)
        entity = self._fetch_entity(tx, entity_id)
        if entity is None:
            raise EntityNotFound(f"entity '{self._entity_type}#{entity_id}' does not exist")

        if self._versioned:
            if expected_version is None:
                raise LifecycleError("expected_version is required for versioned entities")
            actual = entity[self._version_column]
            if actual != expected_version:
                raise CasConflict(self._entity_type, entity_id, expected_version, actual)

        old_slug = session.live_slug(self._entity_type, entity_id)
        if old_slug is not None:
            session.release(self._entity_type, old_slug, entity_id)
        tx.execute(f"DELETE FROM {self._table} WHERE id = ?", (entity_id,))

        return {"entity_id": entity_id, "released_slug": old_slug}
