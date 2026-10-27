"""Scheduled publication runner (stage 4).

One pass: expire stale ``sending`` jobs, claim due jobs atomically, send each
through the platform adapter and record the result.  HTTP never runs inside a
SQLite transaction, and every ambiguous outcome (408 / timeout / transport error
/ unreadable response) is finished as ``uncertain`` - never retried
automatically.

Exit codes: ``0`` - ok or no-op; ``2`` - infrastructure error (database cannot
be opened, BUSY/LOCKED retry budget exhausted).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

from ..domain.catalog import ValidationError
from ..domain.publications import (
    JOB_FAILED,
    JOB_QUEUED,
    JOB_SENT,
    JOB_UNCERTAIN,
    PublishResult,
)
from ..infrastructure.retry import BusyTimeoutError, LockedError
from ..infrastructure.sqlite_provider import VideoShopSQLiteProvider
from ..publishers.registry import get_adapter
from ..services.publications import PublicationsService

SENT = "sent"
RETRY = "retry"
FAILED = "failed"
UNCERTAIN = "uncertain"

#: adapter messages produced before any HTTP request (safe to treat as failed)
PRE_HTTP_FAILURES = frozenset(
    {
        "media not supported in S1",
        "credentials_ref invalid",
        "settings_json invalid",
        "chat_id missing/invalid",
        "text is required",
        "message too long for single-part send in S1",
    }
)

AMBIGUOUS_MESSAGES = frozenset(
    {
        "telegram timeout",
        "telegram transport error",
        "telegram response invalid",
    }
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DB_PATH = _REPOSITORY_ROOT / "data" / "db" / "shop.sqlite"


def classify(result: PublishResult) -> str:
    """Map an adapter result to SENT / RETRY / FAILED / UNCERTAIN."""
    if result.ok:
        return SENT
    error = (result.error or "").strip()
    if error == "telegram 429" or error.startswith("telegram 5"):
        return RETRY
    if error.startswith("telegram 408") or error in AMBIGUOUS_MESSAGES:
        return UNCERTAIN
    if error.startswith("telegram 4"):
        return FAILED
    if error in PRE_HTTP_FAILURES or error.startswith("credentials env missing:"):
        return FAILED
    if result.retryable:
        return UNCERTAIN
    return FAILED


def _log(message: str) -> None:
    print(message, flush=True)


def _finish(
    service: PublicationsService,
    job_id: int,
    result: PublishResult,
    action: str,
    counts: Dict[str, int],
) -> None:
    if action == UNCERTAIN:
        final = service.finish(job_id, result, uncertain=True)
        counts["uncertain"] += 1
    elif action == SENT:
        final = service.finish(job_id, result)
        counts["sent"] += 1
    else:
        final = service.finish(job_id, result)
        if final.status == JOB_FAILED:
            counts["failed"] += 1
        elif final.status == JOB_QUEUED:
            counts["retried"] += 1
        elif final.status == JOB_UNCERTAIN:
            counts["uncertain"] += 1
        else:
            counts["sent"] += 1
    _log(
        "job={job} status={status} action={action}".format(
            job=job_id, status=final.status, action=action
        )
    )


def _process_job(
    service: PublicationsService,
    job: Any,
    counts: Dict[str, int],
) -> None:
    channel = service.get_channel(job.channel_id)
    if not channel.is_active:
        counts["inactive"] += 1
        _finish(
            service,
            job.id,
            PublishResult(False, None, "channel inactive", False, None),
            FAILED,
            counts,
        )
        return

    texts = service.get_texts(job.publication_id)
    text = texts.get(job.lang)
    if text is None:
        _finish(
            service,
            job.id,
            PublishResult(False, None, "text missing for language", False, None),
            FAILED,
            counts,
        )
        return

    try:
        adapter = get_adapter(channel.platform)
    except ValidationError:
        _finish(
            service,
            job.id,
            PublishResult(False, None, "platform unsupported", False, None),
            FAILED,
            counts,
        )
        return

    content = text.body if str(text.body or "").strip() else text.title
    result = adapter.send(channel, content, media=None)
    _finish(service, job.id, result, classify(result), counts)


def run_once(
    service: PublicationsService,
    *,
    limit: int = 20,
    ttl_seconds: int = 600,
    log=_log,
) -> Dict[str, int]:
    """Run one scheduling pass; returns counters (no exceptions per job)."""
    counts: Dict[str, int] = {
        "expired": 0,
        "claimed": 0,
        "sent": 0,
        "retried": 0,
        "failed": 0,
        "uncertain": 0,
        "inactive": 0,
        "errors": 0,
    }
    counts["expired"] = int(service.expire_stale_sends(ttl_seconds))
    jobs = list(service.claim_due(limit))
    counts["claimed"] = len(jobs)
    for job in jobs:
        try:
            _process_job(service, job, counts)
        except Exception as exc:  # noqa: BLE001 - job isolation is deliberate
            counts["errors"] += 1
            log(f"job={job.id} error={type(exc).__name__}")
    return counts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="publish_due.py",
        description="Send one batch of due publications (stage 4).",
    )
    parser.add_argument("--once", action="store_true", default=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--ttl-seconds", type=int, default=600)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--db", default=None)
    return parser


def _resolve_db_path(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    from_env = os.environ.get("VIDEOSHOP_DB_PATH")
    if from_env:
        return from_env
    return str(_DEFAULT_DB_PATH)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    if os.environ.get("VIDEOSHOP_PUBLICATIONS", "off").strip().lower() != "on":
        print("publications disabled (VIDEOSHOP_PUBLICATIONS != on): exit 0")
        return 0

    db_path = _resolve_db_path(args.db)
    try:
        provider = VideoShopSQLiteProvider(db_path=db_path)
        service = PublicationsService(provider)
        if args.dry_run:
            channels = service.list_channels()
            print(f"dry-run: channels={len(channels)}")
            return 0
        counts = run_once(
            service, limit=max(0, args.limit), ttl_seconds=max(0, args.ttl_seconds)
        )
        print("pass: " + " ".join(f"{key}={value}" for key, value in counts.items()))
        return 0
    except (BusyTimeoutError, LockedError) as exc:
        print(f"infra error: {type(exc).__name__}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"infra error: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
