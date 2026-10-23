"""S3: slug registry with database-enforced uniqueness (showcase level only).

Authorized S3 scope implemented here:

* slug syntax ``^[a-z0-9]+(?:-[a-z0-9]+)*$`` with length 1..255 - parity with
  ``ai_framework.content.slug.Slug`` (the framework value object stays the
  normalization authority; ``ai_framework/`` is not modified);
* uniqueness scope is ``(entity_type, slug)`` - one namespace per entity type;
* normalization is EXPLICIT (:func:`normalize_slug`); validation is STRICT
  (:func:`validate_slug` never trims, lower-cases or otherwise repairs input);
* the database PRIMARY KEY of ``slug_registry`` is the final guarantee; a
  conflict is never resolved by an application-level re-check;
* every conflict raises :class:`SlugTaken` carrying the stable code
  ``"SLUG_TAKEN"`` plus ``entity_type`` / ``slug`` / ``held_by``;
* released slugs stay in the registry (state ``released``) and can never be
  registered again in S3 - the "an old slug must not be re-assigned" invariant
  is guaranteed structurally by the same primary key (no cross-table check and
  no trigger needed);
* every SQL identifier is a module constant; ``entity_type``, ``slug`` and
  ``entity_id`` are always bound parameters - user input is never concatenated
  into SQL.

Storage note (S3 decision for review): the approved history semantics
(``entity_type``, ``old_slug``, ``entity_id``) are realised by the
``released``-state rows of the single ``slug_registry`` table instead of a
separate ``slug_history`` table. A separate table would put live uniqueness and
the "no reuse" rule into two tables, which SQLite cannot protect with one
constraint (it needs triggers); the single table makes both invariants
structural.

Live-slug invariant (step 2 of the S3 migration): the partial unique index
``ux_slug_registry_live_entity`` on ``(entity_type, entity_id) WHERE state =
'live'`` guarantees that one entity never holds two live slugs. Because the
index is the final authority, a slug is replaced through
``release(old) -> register(new)`` inside ONE transaction
(:meth:`SlugRegistry.replace_slug`); if registering the new slug fails, the
release is rolled back with it.

Out of scope (S4/S8): the slug-change service, the full history lifecycle,
HTTP redirects and 404 handling, ``tx.update_record_cas``, versioned entities
and their DDL.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from ai_framework.content.slug import Slug

from .retry import run_transaction_with_retry

#: slug syntax - kept in parity with ``ai_framework.content.slug.Slug``
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX_LENGTH = 255

#: entity_type is a code-owned namespace token (never user input), validated anyway
ENTITY_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
ENTITY_TYPE_MAX_LENGTH = 64

#: S3-owned table (identifier is a constant, never interpolated user input)
TABLE = "slug_registry"

STATE_LIVE = "live"
STATE_RELEASED = "released"

#: stable machine-readable conflict code (requirement: стабильный SLUG_TAKEN)
SLUG_TAKEN_CODE = "SLUG_TAKEN"


class SlugError(Exception):
    """Base error of the slug registry."""


class InvalidSlug(SlugError, ValueError):
    """The value violates the S3 slug / entity contract."""


class SlugTaken(SlugError):
    """The slug is already registered for this entity type (stable code)."""

    code = SLUG_TAKEN_CODE

    def __init__(
        self,
        entity_type: str,
        slug: str,
        held_by: Optional[int] = None,
        reason: str = "",
    ) -> None:
        self.entity_type = entity_type
        self.slug = slug
        self.held_by = held_by
        self.reason = reason
        message = (
            f"{SLUG_TAKEN_CODE}: slug '{slug}' is not available "
            f"for entity type '{entity_type}'"
        )
        if reason:
            message += f" ({reason})"
        super().__init__(message)


class SlugNotLive(SlugError):
    """The slug is not the live slug of the given entity (stable code)."""

    code = "SLUG_NOT_LIVE"

    def __init__(
        self,
        entity_type: str,
        slug: str,
        entity_id: Optional[int] = None,
        reason: str = "",
    ) -> None:
        self.entity_type = entity_type
        self.slug = slug
        self.entity_id = entity_id
        self.reason = reason
        message = (
            f"{self.code}: slug '{slug}' is not a live slug of "
            f"'{entity_type}#{entity_id}'"
        )
        if reason:
            message += f" ({reason})"
        super().__init__(message)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_slug(raw: str) -> str:
    """Explicit normalization, delegated to the framework ``Slug`` value object.

    ``"Some_Slug"`` -> ``"some-slug"``. No transliteration is performed: a
    Cyrillic or otherwise non-latin input cannot be normalized and raises
    :class:`InvalidSlug` (transliteration belongs to the framework slug
    generator, outside S3).
    """
    if not isinstance(raw, str):
        raise InvalidSlug(f"slug must be str, got {type(raw).__name__}")
    try:
        return str(Slug.try_normalize(raw))
    except ValueError as exc:
        raise InvalidSlug(f"cannot normalize slug {raw!r}: {exc}") from exc


def validate_slug(raw: str) -> str:
    """Strict validation - the value is accepted exactly as provided.

    Surrounding whitespace is rejected (that would be normalization and must be
    requested explicitly through :func:`normalize_slug`), as are upper-case
    letters, underscores, spaces, unicode and any other non-conforming input.
    """
    if not isinstance(raw, str):
        raise InvalidSlug(f"slug must be str, got {type(raw).__name__}")
    if raw != raw.strip():
        raise InvalidSlug(
            f"slug {raw!r} has surrounding whitespace: "
            f"call normalize_slug() explicitly instead of relying on implicit trimming"
        )
    if not 1 <= len(raw) <= SLUG_MAX_LENGTH:
        raise InvalidSlug(f"slug length must be 1..{SLUG_MAX_LENGTH}, got {len(raw)}")
    if not SLUG_PATTERN.match(raw):
        raise InvalidSlug(
            f"slug {raw!r} does not match {SLUG_PATTERN.pattern}"
        )
    return raw


def validate_entity_type(value: Any) -> str:
    if not isinstance(value, str):
        raise InvalidSlug(f"entity_type must be str, got {type(value).__name__}")
    if not 1 <= len(value) <= ENTITY_TYPE_MAX_LENGTH:
        raise InvalidSlug(
            f"entity_type length must be 1..{ENTITY_TYPE_MAX_LENGTH}, got {len(value)}"
        )
    if not ENTITY_TYPE_PATTERN.match(value):
        raise InvalidSlug(
            f"entity_type {value!r} does not match {ENTITY_TYPE_PATTERN.pattern}"
        )
    return value


def validate_entity_id(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidSlug(f"entity_id must be int, got {type(value).__name__}")
    if value <= 0:
        raise InvalidSlug(f"entity_id must be positive, got {value}")
    return value


class SlugRegistry:
    """Registry of slugs with database-enforced uniqueness per entity type.

    The registry is synchronous on purpose: it uses the S1 transaction API
    (``provider.transaction()``), which is synchronous, and every write happens
    inside a single ``BEGIN IMMEDIATE`` scope on one connection.
    """

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    # --- schema ---------------------------------------------------------

    def migrate(self, migrations: Any = None) -> int:
        """Apply the S3-owned migrations (idempotent; see migrations.runner)."""
        from .migrations.runner import migrate

        return migrate(self._provider, migrations)

    # --- read -----------------------------------------------------------

    def get(self, entity_type: str, slug: str) -> Optional[dict]:
        """Return the registry row for ``(entity_type, slug)`` or ``None``.

        Comparison is strict (SQLite BINARY): ``"abc"`` and ``"ABC"`` are
        different values, and ``"ABC"`` can never be a registered slug because
        validation rejects it.
        """
        entity_type = validate_entity_type(entity_type)
        slug = validate_slug(slug)
        with self._provider.read_transaction() as tx:
            row = tx.fetchone(
                f"SELECT * FROM {TABLE} WHERE entity_type = ? AND slug = ?",
                (entity_type, slug),
            )
        return None if row is None else dict(row)

    # --- transaction-scoped primitives ----------------------------------

    def _register_in(self, tx: Any, entity_type: str, slug: str, entity_id: int) -> dict:
        """Register inside an existing transaction (no nested scope)."""
        existing = tx.fetchone(
            f"SELECT * FROM {TABLE} WHERE entity_type = ? AND slug = ?",
            (entity_type, slug),
        )
        if existing is not None:
            if existing["state"] == STATE_LIVE and existing["entity_id"] == entity_id:
                return dict(existing)
            if existing["state"] == STATE_LIVE:
                raise SlugTaken(
                    entity_type,
                    slug,
                    held_by=existing["entity_id"],
                    reason="already registered for another entity",
                )
            raise SlugTaken(
                entity_type,
                slug,
                held_by=existing["entity_id"],
                reason="released slugs are never re-assigned in S3",
            )

        try:
            tx.execute(
                f"INSERT INTO {TABLE} "
                f"(entity_type, slug, entity_id, state, created_at, released_at) "
                f"VALUES (?, ?, ?, ?, ?, NULL)",
                (entity_type, slug, entity_id, STATE_LIVE, _utc_now()),
            )
        except sqlite3.IntegrityError as exc:
            live = tx.fetchone(
                f"SELECT slug, entity_id FROM {TABLE} "
                f"WHERE entity_type = ? AND entity_id = ? AND state = ?",
                (entity_type, entity_id, STATE_LIVE),
            )
            if live is not None:
                raise SlugTaken(
                    entity_type,
                    slug,
                    held_by=live["entity_id"],
                    reason=f"entity already holds the live slug '{live['slug']}'",
                ) from exc
            raise SlugTaken(
                entity_type,
                slug,
                reason=f"database constraint rejected the registration: {exc}",
            ) from exc

        row = tx.fetchone(
            f"SELECT * FROM {TABLE} WHERE entity_type = ? AND slug = ?",
            (entity_type, slug),
        )
        return dict(row)

    def _release_in(self, tx: Any, entity_type: str, slug: str, entity_id: int) -> bool:
        """Release inside an existing transaction (no nested scope)."""
        row = tx.fetchone(
            f"SELECT * FROM {TABLE} WHERE entity_type = ? AND slug = ?",
            (entity_type, slug),
        )
        if row is None or row["state"] != STATE_LIVE:
            return False
        if row["entity_id"] != entity_id:
            raise SlugTaken(
                entity_type,
                slug,
                held_by=row["entity_id"],
                reason="held by another entity",
            )
        cursor = tx.execute(
            f"UPDATE {TABLE} SET state = ?, released_at = ? "
            f"WHERE entity_type = ? AND slug = ? AND state = ?",
            (STATE_RELEASED, _utc_now(), entity_type, slug, STATE_LIVE),
        )
        return cursor.rowcount == 1

    # --- write ----------------------------------------------------------

    def register(self, entity_type: str, slug: str, entity_id: int) -> dict:
        """Register ``slug`` for ``entity_id`` inside one transaction.

        * returns the stored row for a new registration;
        * returns the existing row unchanged when the same entity re-registers
          its own live slug (idempotent);
        * raises :class:`SlugTaken` when the slug is live for another entity,
          when it is already released (S3 never re-uses an old slug) or when the
          entity already holds another live slug (step-2 partial unique index).

        The database constraints are the final guarantee: the insert runs inside
        the same transaction as the lookup, and a constraint violation is
        translated into the same stable :class:`SlugTaken` result.
        """
        entity_type = validate_entity_type(entity_type)
        slug = validate_slug(slug)
        entity_id = validate_entity_id(entity_id)

        return run_transaction_with_retry(
            self._provider,
            lambda tx: self._register_in(tx, entity_type, slug, entity_id),
        )

    def release(self, entity_type: str, slug: str, entity_id: int) -> bool:
        """Mark a live slug as released (kept forever as the history record).

        Returns ``True`` when the row transitioned ``live -> released`` and
        ``False`` when the slug is unknown or already released. Raises
        :class:`SlugTaken` when the slug belongs to a different entity.

        S3 provides this primitive only; wiring it to an entity update is S4.
        """
        entity_type = validate_entity_type(entity_type)
        slug = validate_slug(slug)
        entity_id = validate_entity_id(entity_id)

        return run_transaction_with_retry(
            self._provider,
            lambda tx: self._release_in(tx, entity_type, slug, entity_id),
        )

    def _replace_in(
        self, tx: Any, entity_type: str, entity_id: int, old_slug: str, new_slug: str
    ) -> dict:
        """Replace inside an existing transaction (no nested scope, S4)."""
        if old_slug == new_slug:
            row = tx.fetchone(
                f"SELECT * FROM {TABLE} WHERE entity_type = ? AND slug = ?",
                (entity_type, old_slug),
            )
            if (
                row is None
                or row["state"] != STATE_LIVE
                or row["entity_id"] != entity_id
            ):
                raise SlugNotLive(
                    entity_type,
                    old_slug,
                    entity_id=entity_id,
                    reason="not the live slug of this entity",
                )
            return dict(row)

        released = self._release_in(tx, entity_type, old_slug, entity_id)
        if not released:
            raise SlugNotLive(
                entity_type,
                old_slug,
                entity_id=entity_id,
                reason="not the live slug of this entity",
            )
        return self._register_in(tx, entity_type, new_slug, entity_id)

    def replace_slug(
        self, entity_type: str, entity_id: int, old_slug: str, new_slug: str
    ) -> dict:
        """Atomically replace ``old_slug`` with ``new_slug`` for one entity.

        Both steps run in ONE transaction: ``release(old_slug)`` followed by
        ``register(new_slug)``. If the registration fails (slug taken, invalid,
        database constraint) the whole transaction rolls back and the old slug
        stays live - there is no state in which the entity lost its slug without
        gaining a new one.

        ``old_slug == new_slug`` is an explicit no-op returning the current live
        row (re-registering a released slug is forbidden in S3).
        """
        entity_type = validate_entity_type(entity_type)
        entity_id = validate_entity_id(entity_id)
        old_slug = validate_slug(old_slug)
        new_slug = validate_slug(new_slug)

        return run_transaction_with_retry(
            self._provider,
            lambda tx: self._replace_in(tx, entity_type, entity_id, old_slug, new_slug),
        )

    def within(self, tx: Any) -> "RegistrySession":
        """Bind registry operations to a CALLER-OWNED transaction (S4).

        Used inside ``provider.transaction()`` so slug operations join the same
        transaction as the entity change instead of opening their own - the
        requirement behind the S4 single-transaction contract.
        """
        return RegistrySession(self, tx)


class RegistrySession:
    """Slug-registry operations bound to a caller-owned transaction (S4).

    Every method validates its arguments exactly like the standalone registry
    API, but performs NO commit and opens NO connection of its own: the caller's
    transaction decides the outcome, so any failure rolls the whole composite
    operation back.
    """

    def __init__(self, registry: SlugRegistry, tx: Any) -> None:
        self._registry = registry
        self._tx = tx

    def get(self, entity_type: str, slug: str) -> Optional[dict]:
        entity_type = validate_entity_type(entity_type)
        slug = validate_slug(slug)
        row = self._tx.fetchone(
            f"SELECT * FROM {TABLE} WHERE entity_type = ? AND slug = ?",
            (entity_type, slug),
        )
        return None if row is None else dict(row)

    def live_slug(self, entity_type: str, entity_id: int) -> Optional[str]:
        """Current live slug of an entity, or ``None``."""
        entity_type = validate_entity_type(entity_type)
        entity_id = validate_entity_id(entity_id)
        row = self._tx.fetchone(
            f"SELECT slug FROM {TABLE} WHERE entity_type = ? AND entity_id = ? "
            f"AND state = ?",
            (entity_type, entity_id, STATE_LIVE),
        )
        return None if row is None else row["slug"]

    def register(self, entity_type: str, slug: str, entity_id: int) -> dict:
        return self._registry._register_in(
            self._tx,
            validate_entity_type(entity_type),
            validate_slug(slug),
            validate_entity_id(entity_id),
        )

    def release(self, entity_type: str, slug: str, entity_id: int) -> bool:
        return self._registry._release_in(
            self._tx,
            validate_entity_type(entity_type),
            validate_slug(slug),
            validate_entity_id(entity_id),
        )

    def replace_slug(
        self, entity_type: str, entity_id: int, old_slug: str, new_slug: str
    ) -> dict:
        return self._registry._replace_in(
            self._tx,
            validate_entity_type(entity_type),
            validate_entity_id(entity_id),
            validate_slug(old_slug),
            validate_slug(new_slug),
        )
