"""Publication domain: states, models, validators and deterministic keys.

The schema lives in migration step 9
(``infrastructure/migrations/publications.py``); this module is the Python view of
it.  It contains no HTTP, no scheduling and no user interface.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .catalog import ValidationError, validate_language

JOB_QUEUED = "queued"
JOB_SENDING = "sending"
JOB_SENT = "sent"
JOB_FAILED = "failed"
JOB_SKIPPED = "skipped"
JOB_UNCERTAIN = "uncertain"
JOB_CANCELLED = "cancelled"

STATUSES: Tuple[str, ...] = (
    JOB_QUEUED,
    JOB_SENDING,
    JOB_SENT,
    JOB_FAILED,
    JOB_SKIPPED,
    JOB_UNCERTAIN,
    JOB_CANCELLED,
)
TERMINAL_STATUSES = frozenset({JOB_SENT, JOB_FAILED, JOB_SKIPPED, JOB_CANCELLED})

ALLOWED_TRANSITIONS = frozenset(
    {
        (JOB_QUEUED, JOB_SENDING),
        (JOB_SENDING, JOB_SENT),
        (JOB_SENDING, JOB_QUEUED),
        (JOB_SENDING, JOB_FAILED),
        (JOB_SENDING, JOB_UNCERTAIN),
        (JOB_UNCERTAIN, JOB_SENT),
        (JOB_UNCERTAIN, JOB_FAILED),
    }
)

#: hard cap of send attempts; stage 2 does not read any environment variable
MAX_ATTEMPTS = 3
RETRY_INTERVALS: Tuple[int, ...] = (60, 300)
DEFAULT_TIMEZONE = "Europe/Chisinau"
SUPPORTED_PLATFORMS = ("telegram",)

_CHANNEL_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
_CREDENTIALS_REF_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,31}$")


def can_transition(source: str, target: str) -> bool:
    """True when ``source -> target`` is one of the allowed job transitions."""
    return (source, target) in ALLOWED_TRANSITIONS


def validate_channel_key(value: Any) -> str:
    text = str(value or "").strip()
    if not _CHANNEL_KEY_RE.match(text):
        raise ValidationError(
            "channel_key must match ^[a-z][a-z0-9_]{1,31}$: a lowercase latin "
            "letter first, then lowercase letters, digits or underscore"
        )
    return text


def validate_credentials_ref(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        raise ValidationError(
            "credentials_ref is required: the token is resolved from "
            "VIDEOSHOP_TELEGRAM_<CREDENTIALS_REF>_BOT_TOKEN and is never "
            "substituted by channel_key"
        )
    if not _CREDENTIALS_REF_RE.match(text):
        raise ValidationError(
            "credentials_ref must match ^[A-Z][A-Z0-9_]{0,31}$ after upper-casing"
        )
    return text


def credentials_env_name(credentials_ref: Any) -> str:
    return "VIDEOSHOP_TELEGRAM_" + validate_credentials_ref(credentials_ref) + "_BOT_TOKEN"


def validate_timezone(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationError("timezone is required")
    try:
        ZoneInfo(text)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError(f"unknown timezone {text!r}") from exc
    return text


def idempotency_key(
    publication_id: int, channel_id: int, lang: str, scheduled_for: str
) -> str:
    raw = f"v1|{int(publication_id)}|{int(channel_id)}|{lang}|{scheduled_for}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def next_delay(attempts: int, intervals: Tuple[int, ...] = RETRY_INTERVALS) -> int:
    if not intervals:
        raise ValueError("intervals must not be empty")
    index = max(0, min(int(attempts) - 1, len(intervals) - 1))
    return int(intervals[index])


def retry_after_delay(
    retry_after: Optional[int],
    intervals: Tuple[int, ...] = RETRY_INTERVALS,
    attempts: int = 1,
) -> int:
    if retry_after is not None:
        return max(0, int(retry_after))
    return next_delay(attempts, intervals)


def _row_dict(row: Any) -> Mapping[str, Any]:
    if isinstance(row, Mapping):
        return row
    return dict(row)


@dataclass(frozen=True)
class Channel:
    id: Optional[int]
    platform: str
    channel_key: str
    name: str
    credentials_ref: str
    settings_json: str
    default_language: str
    timezone: str
    is_active: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Publication:
    id: Optional[int]
    kind: str
    source_type: str
    source_slug: str
    status: str
    created_by: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PublicationText:
    lang: str
    title: str
    body: str


@dataclass(frozen=True)
class PublicationJob:
    id: Optional[int]
    publication_id: int
    channel_id: int
    lang: str
    scheduled_for: str
    status: str
    attempts: int
    next_attempt_at: Optional[str]
    last_error: Optional[str]
    external_id: Optional[str]
    idempotency_key: str
    locked_at: Optional[str]
    send_started_at: Optional[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PublishResult:
    ok: bool
    external_id: Optional[str] = None
    error: Optional[str] = None
    retryable: bool = False
    retry_after: Optional[int] = None


def channel_from_row(row: Any) -> Channel:
    data = _row_dict(row)
    return Channel(
        id=data["id"],
        platform=data["platform"],
        channel_key=data["channel_key"],
        name=data["name"],
        credentials_ref=data["credentials_ref"],
        settings_json=data["settings_json"],
        default_language=data["default_language"],
        timezone=data["timezone"],
        is_active=bool(data["is_active"]),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def publication_from_row(row: Any) -> Publication:
    data = _row_dict(row)
    return Publication(
        id=data["id"],
        kind=data["kind"],
        source_type=data["source_type"],
        source_slug=data["source_slug"],
        status=data["status"],
        created_by=data["created_by"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def job_from_row(row: Any) -> PublicationJob:
    data = _row_dict(row)
    return PublicationJob(
        id=data["id"],
        publication_id=data["publication_id"],
        channel_id=data["channel_id"],
        lang=data["lang"],
        scheduled_for=data["scheduled_for"],
        status=data["status"],
        attempts=int(data["attempts"]),
        next_attempt_at=data["next_attempt_at"],
        last_error=data["last_error"],
        external_id=data["external_id"],
        idempotency_key=data["idempotency_key"],
        locked_at=data["locked_at"],
        send_started_at=data["send_started_at"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )
