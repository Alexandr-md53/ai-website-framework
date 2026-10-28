"""SQL layer for the publications tables (migration step 9).

Writes go through ``run_transaction_with_retry`` (one write transaction per
operation, BUSY retried); reads go through ``provider.read_transaction()``.
No sending happens here: stage 4 calls ``claim_due`` and then sends outside any
transaction, and reports back through ``finish``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from ..domain.catalog import NotFoundError, ValidationError
from ..domain.publications import (
    JOB_FAILED,
    JOB_QUEUED,
    JOB_SENDING,
    JOB_SENT,
    JOB_UNCERTAIN,
    MAX_ATTEMPTS,
    TERMINAL_STATUSES,
    Channel,
    Publication,
    PublicationJob,
    PublicationText,
    PublishResult,
    channel_from_row,
    idempotency_key,
    job_from_row,
    publication_from_row,
    retry_after_delay,
)
from .retry import run_transaction_with_retry

EDITABLE_CHANNEL_FIELDS = (
    "platform",
    "channel_key",
    "name",
    "credentials_ref",
    "settings_json",
    "default_language",
    "timezone",
    "is_active",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


class PublicationsStore:
    """All SQL for the six publications tables; no policy beyond job states."""

    def __init__(self, provider: Any, *, now: Optional[Callable[[], str]] = None) -> None:
        self._provider = provider
        self._now = now or _now_iso

    # ------------------------------------------------------------------ reads
    def _channel_tx(self, tx: Any, channel_id: int) -> Channel:
        row = tx.fetchone("SELECT * FROM publish_channels WHERE id = ?", (channel_id,))
        if row is None:
            raise NotFoundError(f"publish channel {channel_id} not found")
        return channel_from_row(row)

    def get_channel(self, channel_id: int) -> Channel:
        with self._provider.read_transaction() as tx:
            return self._channel_tx(tx, channel_id)

    def list_channels(self, *, active_only: bool = False) -> List[Channel]:
        sql = "SELECT * FROM publish_channels"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY platform, channel_key, id"
        with self._provider.read_transaction() as tx:
            return [channel_from_row(row) for row in tx.fetchall(sql)]

    def _publication_tx(self, tx: Any, publication_id: int) -> Publication:
        row = tx.fetchone("SELECT * FROM publications WHERE id = ?", (publication_id,))
        if row is None:
            raise NotFoundError(f"publication {publication_id} not found")
        return publication_from_row(row)

    def get_publication(self, publication_id: int) -> Publication:
        with self._provider.read_transaction() as tx:
            return self._publication_tx(tx, publication_id)

    def get_texts(self, publication_id: int) -> Dict[str, PublicationText]:
        with self._provider.read_transaction() as tx:
            self._publication_tx(tx, publication_id)
            rows = tx.fetchall(
                "SELECT lang, title, body FROM publication_texts"
                " WHERE publication_id = ? ORDER BY lang",
                (publication_id,),
            )
        return {
            row["lang"]: PublicationText(
                lang=row["lang"], title=row["title"], body=row["body"]
            )
            for row in rows
        }

    def _job_tx(self, tx: Any, job_id: int) -> PublicationJob:
        row = tx.fetchone("SELECT * FROM publication_jobs WHERE id = ?", (job_id,))
        if row is None:
            raise NotFoundError(f"publication job {job_id} not found")
        return job_from_row(row)

    def get_job(self, job_id: int) -> PublicationJob:
        with self._provider.read_transaction() as tx:
            return self._job_tx(tx, job_id)

    def list_jobs(
        self,
        publication_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[PublicationJob]:
        clauses: List[str] = []
        params: List[Any] = []
        if publication_id is not None:
            clauses.append("publication_id = ?")
            params.append(int(publication_id))
        if channel_id is not None:
            clauses.append("channel_id = ?")
            params.append(int(channel_id))
        if status is not None:
            clauses.append("status = ?")
            params.append(str(status))
        sql = "SELECT * FROM publication_jobs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id LIMIT ?"
        params.append(max(0, int(limit)))
        with self._provider.read_transaction() as tx:
            return [job_from_row(row) for row in tx.fetchall(sql, tuple(params))]

    def list_events(self, job_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        with self._provider.read_transaction() as tx:
            rows = tx.fetchall(
                "SELECT id, job_id, at, level, message FROM publication_events"
                " WHERE job_id = ? ORDER BY id LIMIT ?",
                (int(job_id), max(0, int(limit))),
            )
        return [
            {
                "id": row["id"],
                "job_id": row["job_id"],
                "at": row["at"],
                "level": row["level"],
                "message": row["message"],
            }
            for row in rows
        ]

    # ----------------------------------------------------------------- writes
    def insert_channel(
        self,
        *,
        platform: str,
        channel_key: str,
        name: str,
        credentials_ref: str,
        settings_json: str = "{}",
        default_language: str = "",
        timezone: str = "Europe/Chisinau",
        is_active: bool = True,
    ) -> Channel:
        def op(tx: Any) -> Channel:
            now = self._now()
            cursor = tx.execute(
                "INSERT INTO publish_channels (platform, channel_key, name,"
                " credentials_ref, settings_json, default_language, timezone,"
                " is_active, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    platform,
                    channel_key,
                    name,
                    credentials_ref,
                    settings_json,
                    default_language,
                    timezone,
                    1 if is_active else 0,
                    now,
                    now,
                ),
            )
            return self._channel_tx(tx, int(cursor.lastrowid))

        return run_transaction_with_retry(self._provider, op)

    def update_channel(self, channel_id: int, **fields: Any) -> Channel:
        unknown = [key for key in fields if key not in EDITABLE_CHANNEL_FIELDS]
        if unknown:
            raise ValidationError(f"unknown channel fields: {sorted(unknown)}")

        def op(tx: Any) -> Channel:
            current = self._channel_tx(tx, channel_id)
            if not fields:
                return current
            assignments: List[str] = []
            params: List[Any] = []
            for key in EDITABLE_CHANNEL_FIELDS:
                if key not in fields:
                    continue
                assignments.append(f"{key} = ?")
                value = fields[key]
                if key == "is_active":
                    value = 1 if value else 0
                params.append(value)
            assignments.append("updated_at = ?")
            params.append(self._now())
            params.append(channel_id)
            tx.execute(
                "UPDATE publish_channels SET " + ", ".join(assignments) + " WHERE id = ?",
                tuple(params),
            )
            return self._channel_tx(tx, channel_id)

        return run_transaction_with_retry(self._provider, op)

    def set_channel_active(self, channel_id: int, active: bool) -> Channel:
        return self.update_channel(channel_id, is_active=bool(active))

    def create_publication(
        self,
        *,
        kind: str,
        source_type: str,
        source_slug: str,
        texts: Mapping[str, Tuple[str, str]],
        created_by: str,
    ) -> Publication:
        def op(tx: Any) -> Publication:
            now = self._now()
            cursor = tx.execute(
                "INSERT INTO publications (kind, source_type, source_slug, status,"
                " created_by, created_at, updated_at)"
                " VALUES (?, ?, ?, 'draft', ?, ?, ?)",
                (kind, source_type, source_slug, created_by, now, now),
            )
            publication_id = int(cursor.lastrowid)
            for lang, (title, body) in texts.items():
                tx.execute(
                    "INSERT INTO publication_texts (publication_id, lang, title, body)"
                    " VALUES (?, ?, ?, ?)",
                    (publication_id, lang, title, body),
                )
            return self._publication_tx(tx, publication_id)

        return run_transaction_with_retry(self._provider, op)

    def _insert_job(
        self,
        tx: Any,
        *,
        publication_id: int,
        channel_id: int,
        lang: str,
        scheduled_for: str,
        key: str,
        now: str,
    ) -> int:
        cursor = tx.execute(
            "INSERT INTO publication_jobs (publication_id, channel_id, lang,"
            " scheduled_for, status, attempts, idempotency_key, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)",
            (publication_id, channel_id, lang, scheduled_for, JOB_QUEUED, key, now, now),
        )
        return int(cursor.lastrowid)

    def schedule_jobs(
        self,
        publication_id: int,
        *,
        channel_ids: Sequence[int],
        langs: Sequence[str],
        scheduled_for: str,
    ) -> List[PublicationJob]:
        """Create jobs + dedup keys in ONE transaction (no partial state possible)."""

        def op(tx: Any) -> List[PublicationJob]:
            self._publication_tx(tx, publication_id)
            now = self._now()
            created: List[PublicationJob] = []
            for channel_id in channel_ids:
                for lang in langs:
                    key = idempotency_key(publication_id, channel_id, lang, scheduled_for)
                    cursor = tx.execute(
                        "INSERT OR IGNORE INTO publication_dedup"
                        " (idempotency_key, created_at) VALUES (?, ?)",
                        (key, now),
                    )
                    if cursor.rowcount != 1:
                        continue
                    job_id = self._insert_job(
                        tx,
                        publication_id=publication_id,
                        channel_id=int(channel_id),
                        lang=lang,
                        scheduled_for=scheduled_for,
                        key=key,
                        now=now,
                    )
                    created.append(self._job_tx(tx, job_id))
            return created

        return run_transaction_with_retry(self._provider, op)

    def claim_due(self, limit: int = 20) -> List[PublicationJob]:
        """Atomically move due ``queued`` jobs to ``sending`` (rowcount == 1)."""

        def op(tx: Any) -> List[PublicationJob]:
            now = self._now()
            rows = tx.fetchall(
                "SELECT id FROM publication_jobs WHERE status = 'queued'"
                " AND COALESCE(next_attempt_at, scheduled_for) <= ?"
                " ORDER BY COALESCE(next_attempt_at, scheduled_for), id LIMIT ?",
                (now, max(0, int(limit))),
            )
            claimed: List[PublicationJob] = []
            for row in rows:
                cursor = tx.execute(
                    "UPDATE publication_jobs SET status = ?, locked_at = ?,"
                    " send_started_at = ?, attempts = attempts + 1, updated_at = ?"
                    " WHERE id = ? AND status = ?",
                    (JOB_SENDING, now, now, now, row["id"], JOB_QUEUED),
                )
                if cursor.rowcount == 1:
                    claimed.append(self._job_tx(tx, row["id"]))
            return claimed

        return run_transaction_with_retry(self._provider, op)

    def _add_event(self, tx: Any, job_id: int, level: str, message: str) -> None:
        tx.execute(
            "INSERT INTO publication_events (job_id, at, level, message)"
            " VALUES (?, ?, ?, ?)",
            (job_id, self._now(), level, message),
        )

    def _set_job_state(
        self,
        tx: Any,
        job: PublicationJob,
        status: str,
        *,
        next_attempt_at: Optional[str],
        last_error: Optional[str],
        external_id: Optional[str],
    ) -> None:
        now = self._now()
        tx.execute(
            "UPDATE publication_jobs SET status = ?, next_attempt_at = ?,"
            " last_error = ?, external_id = ?, locked_at = NULL, updated_at = ?"
            " WHERE id = ?",
            (status, next_attempt_at, last_error, external_id, now, job.id),
        )

    def finish(
        self, job_id: int, result: PublishResult, *, uncertain: bool = False
    ) -> PublicationJob:
        def op(tx: Any) -> PublicationJob:
            job = self._job_tx(tx, job_id)
            if job.status != JOB_SENDING:
                raise ValidationError(
                    f"finish requires a sending job, got {job.status!r}"
                )
            now = self._now()
            if uncertain:
                self._set_job_state(
                    tx,
                    job,
                    JOB_UNCERTAIN,
                    next_attempt_at=None,
                    last_error=(result.error or "send outcome unknown"),
                    external_id=None,
                )
                self._add_event(
                    tx,
                    job_id,
                    "warn",
                    "send outcome uncertain: manual resolution required",
                )
            elif result.ok:
                if not result.external_id:
                    raise ValidationError("a successful send needs an external_id")
                self._set_job_state(
                    tx,
                    job,
                    JOB_SENT,
                    next_attempt_at=None,
                    last_error=None,
                    external_id=str(result.external_id),
                )
                self._add_event(tx, job_id, "info", "sent")
            elif result.retryable and job.attempts < MAX_ATTEMPTS:
                delay = retry_after_delay(result.retry_after, attempts=job.attempts)
                next_at = (_parse_iso(now) + timedelta(seconds=delay)).isoformat()
                self._set_job_state(
                    tx,
                    job,
                    JOB_QUEUED,
                    next_attempt_at=next_at,
                    last_error=(result.error or "retryable failure"),
                    external_id=None,
                )
                self._add_event(
                    tx, job_id, "warn", "retry scheduled after retryable failure"
                )
            else:
                error = result.error or "permanent failure"
                if result.retryable:
                    error = "retry budget exhausted"
                self._set_job_state(
                    tx,
                    job,
                    JOB_FAILED,
                    next_attempt_at=None,
                    last_error=str(error)[:500],
                    external_id=None,
                )
                self._add_event(tx, job_id, "error", "send failed")
            return self._job_tx(tx, job_id)

        return run_transaction_with_retry(self._provider, op)

    def expire_stale_sends(self, ttl_seconds: int = 600) -> int:
        def op(tx: Any) -> int:
            now = self._now()
            cutoff = (_parse_iso(now) - timedelta(seconds=int(ttl_seconds))).isoformat()
            rows = tx.fetchall(
                "SELECT id FROM publication_jobs WHERE status = 'sending'"
                " AND locked_at IS NOT NULL AND locked_at < ?",
                (cutoff,),
            )
            for row in rows:
                tx.execute(
                    "UPDATE publication_jobs SET status = ?, last_error = ?,"
                    " locked_at = NULL, updated_at = ? WHERE id = ?",
                    (
                        JOB_UNCERTAIN,
                        "stale sending lock (possible duplicate)",
                        now,
                        row["id"],
                    ),
                )
                self._add_event(
                    tx,
                    row["id"],
                    "warn",
                    "stale sending lock (possible duplicate)",
                )
            return len(rows)

        return run_transaction_with_retry(self._provider, op)

    def resolve_uncertain(
        self,
        job_id: int,
        *,
        outcome: str,
        external_id: Optional[str],
        note: str = "",
    ) -> PublicationJob:
        def op(tx: Any) -> PublicationJob:
            job = self._job_tx(tx, job_id)
            if job.status != JOB_UNCERTAIN:
                raise ValidationError(
                    f"resolve requires an uncertain job, got {job.status!r}"
                )
            if outcome == "sent":
                if not external_id:
                    raise ValidationError("outcome 'sent' requires an external_id")
                self._set_job_state(
                    tx,
                    job,
                    JOB_SENT,
                    next_attempt_at=None,
                    last_error=None,
                    external_id=str(external_id),
                )
            elif outcome == "failed":
                self._set_job_state(
                    tx,
                    job,
                    JOB_FAILED,
                    next_attempt_at=None,
                    last_error=(note or "resolved as failed")[:500],
                    external_id=None,
                )
            else:
                raise ValidationError("outcome must be 'sent' or 'failed'")
            self._add_event(tx, job_id, "info", f"manual resolution: {outcome}"[:500])
            return self._job_tx(tx, job_id)

        return run_transaction_with_retry(self._provider, op)

    def _next_free_slot(self, tx: Any, job: PublicationJob) -> str:
        base = _parse_iso(self._now()).replace(microsecond=0)
        for step in range(1, 3601):
            candidate = (base + timedelta(seconds=step)).isoformat()
            row = tx.fetchone(
                "SELECT 1 FROM publication_jobs WHERE publication_id = ?"
                " AND channel_id = ? AND lang = ? AND scheduled_for = ?",
                (job.publication_id, job.channel_id, job.lang, candidate),
            )
            if row is None:
                return candidate
        raise ValidationError("no free schedule slot for retry_as_new")

    def retry_as_new(
        self, job_id: int, *, scheduled_for: Optional[str] = None
    ) -> PublicationJob:
        def op(tx: Any) -> PublicationJob:
            source = self._job_tx(tx, job_id)
            if source.status not in TERMINAL_STATUSES:
                raise ValidationError(
                    f"retry_as_new requires a terminal job, got {source.status!r}"
                )
            candidate = scheduled_for or self._next_free_slot(tx, source)
            key = idempotency_key(
                source.publication_id, source.channel_id, source.lang, candidate
            )
            now = self._now()
            tx.execute(
                "INSERT OR IGNORE INTO publication_dedup (idempotency_key, created_at)"
                " VALUES (?, ?)",
                (key, now),
            )
            new_id = self._insert_job(
                tx,
                publication_id=source.publication_id,
                channel_id=source.channel_id,
                lang=source.lang,
                scheduled_for=candidate,
                key=key,
                now=now,
            )
            self._add_event(tx, job_id, "info", "retry as new job")
            return self._job_tx(tx, new_id)

        return run_transaction_with_retry(self._provider, op)

    def retention_sweep(self) -> int:
        raise NotImplementedError(
            "retention is implemented in stage 6 (G9): events older than 90 days "
            "are deleted, texts are anonymised, jobs and dedup keys are kept"
        )
