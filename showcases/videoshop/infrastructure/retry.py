"""S6: bounded retry for SQLITE_BUSY around a WHOLE transactional operation.

Approved policy (D-S6-3 / D-S6-9):

* retry happens ONLY for ``SQLITE_BUSY`` (primary result code 5, extended codes
  included);
* the retry wraps the WHOLE operation - ``operation(tx)`` is re-executed inside a
  fresh write transaction, because a BUSY error aborts and rolls back the
  previous scope, so no partial state can be replayed;
* ``SQLITE_LOCKED`` (primary code 6) is NEVER retried;
* every other SQLite error propagates unchanged;
* ``operation`` must be free of external side effects, because a retry replays
  it. This is verified for the current callers in the S6 report: the lifecycle
  and registry operations perform database work only.

The attempt/backoff numbers below are the mechanism defaults and are flagged for
ratification in the S6 report - they are policy parameters, not measurements.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any, Callable, Optional

SQLITE_BUSY_CODE = int(sqlite3.SQLITE_BUSY)
SQLITE_LOCKED_CODE = int(sqlite3.SQLITE_LOCKED)

#: mechanism defaults (pending ratification by the manager)
DEFAULT_ATTEMPTS = 3
DEFAULT_BASE_DELAY_MS = 50
DEFAULT_MAX_DELAY_MS = 400
DEFAULT_BUDGET_MS = 2000


class BusyTimeoutError(RuntimeError):
    """SQLITE_BUSY persisted through the whole retry budget."""

    code = "SQLITE_BUSY"


class LockedError(RuntimeError):
    """SQLITE_LOCKED (table-level lock): never retried."""

    code = "SQLITE_LOCKED"


def primary_error_code(exc: BaseException) -> Optional[int]:
    """Primary SQLite result code (extended codes masked), or ``None``."""
    code = getattr(exc, "sqlite_errorcode", None)
    if code is None:
        return None
    try:
        return int(code) & 0xFF
    except (TypeError, ValueError):
        return None


def is_busy_error(exc: BaseException) -> bool:
    """True only for ``SQLITE_BUSY`` (wrapper BUSY codes included)."""
    if not isinstance(exc, sqlite3.Error):
        return False
    code = primary_error_code(exc)
    if code:  # a real result code; 0/None falls back to the message
        return code == SQLITE_BUSY_CODE
    return "database is locked" in str(exc).lower()


def is_locked_error(exc: BaseException) -> bool:
    """True only for ``SQLITE_LOCKED`` (separate from BUSY, never retried)."""
    if not isinstance(exc, sqlite3.Error):
        return False
    code = primary_error_code(exc)
    if code:  # a real result code; 0/None falls back to the message
        return code == SQLITE_LOCKED_CODE
    return "database table is locked" in str(exc).lower()


def run_transaction_with_retry(
    provider: Any,
    operation: Callable[[Any], Any],
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay_ms: int = DEFAULT_BASE_DELAY_MS,
    max_delay_ms: int = DEFAULT_MAX_DELAY_MS,
    budget_ms: int = DEFAULT_BUDGET_MS,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Any:
    """Run ``operation(tx)`` in ONE write transaction, retrying it on BUSY only.

    Returns whatever ``operation`` returns. Raises :class:`BusyTimeoutError` when
    BUSY persists through the attempts/budget, :class:`LockedError` for
    SQLITE_LOCKED, and re-raises every other error unchanged.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    deadline = clock() + max(0, budget_ms) / 1000.0
    attempt = 0

    while True:
        attempt += 1
        try:
            with provider.transaction() as tx:
                return operation(tx)
        except sqlite3.Error as exc:
            if is_locked_error(exc):
                raise LockedError(
                    f"SQLITE_LOCKED is not retried (attempt {attempt}): {exc}"
                ) from exc
            if not is_busy_error(exc):
                raise
            if attempt >= attempts or clock() >= deadline:
                raise BusyTimeoutError(
                    f"SQLITE_BUSY persisted after {attempt} attempt(s) "
                    f"(budget {budget_ms} ms): {exc}"
                ) from exc
            delay_ms = min(base_delay_ms * (2 ** (attempt - 1)), max_delay_ms)
            sleep(max(0, delay_ms) / 1000.0)
