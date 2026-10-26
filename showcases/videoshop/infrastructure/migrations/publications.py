"""Publications schema: migration step 9 (``publications_core``).

Approved S1 decisions encoded here:

* channels are DATA (rows in ``publish_channels``); adapters are CODE (a
  per-platform registry) - one platform can have any number of configured
  channels without code changes;
* a job exists per ``(publication, channel, language, scheduled_for)`` and keeps
  an ``idempotency_key`` that must survive text anonymisation, therefore the
  unique key never lives only in a row that retention is allowed to rewrite;
* ``publication_jobs`` references its publication and its channel with
  ``ON DELETE RESTRICT``: deleting a publication or a channel can never destroy
  job history or dedup keys (a channel is retired with ``is_active = 0``);
* ``publication_dedup`` is a standalone key table without foreign keys - it is
  the long-term duplicate guard that outlives content anonymisation;
* the step is purely additive: no existing table is altered and WAL stays off.
"""
from __future__ import annotations

from typing import Any, Tuple

from .runner import Migration

#: version of the publications schema step
PUBLICATIONS_VERSION = 9


PUBLICATIONS_DDL: Tuple[str, ...] = (
    "CREATE TABLE IF NOT EXISTS publish_channels ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " platform TEXT NOT NULL,"
    " channel_key TEXT NOT NULL,"
    " name TEXT NOT NULL,"
    " credentials_ref TEXT NOT NULL DEFAULT '',"
    " settings_json TEXT NOT NULL DEFAULT '{}',"
    " default_language TEXT NOT NULL DEFAULT '',"
    " timezone TEXT NOT NULL DEFAULT 'Europe/Chisinau',"
    " is_active INTEGER NOT NULL DEFAULT 1,"
    " created_at TEXT NOT NULL,"
    " updated_at TEXT NOT NULL,"
    " UNIQUE(platform, channel_key),"
    " UNIQUE(platform, name))",
    "CREATE INDEX IF NOT EXISTS ix_publish_channels_active"
    " ON publish_channels (is_active)",
    "CREATE TABLE IF NOT EXISTS publications ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " kind TEXT NOT NULL DEFAULT 'manual',"
    " source_type TEXT NOT NULL DEFAULT '',"
    " source_slug TEXT NOT NULL DEFAULT '',"
    " status TEXT NOT NULL DEFAULT 'draft',"
    " created_by TEXT NOT NULL DEFAULT '',"
    " created_at TEXT NOT NULL,"
    " updated_at TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS ix_publications_status"
    " ON publications (status, updated_at)",
    "CREATE TABLE IF NOT EXISTS publication_texts ("
    " publication_id INTEGER NOT NULL REFERENCES publications(id) ON DELETE CASCADE,"
    " lang TEXT NOT NULL,"
    " title TEXT NOT NULL,"
    " body TEXT NOT NULL DEFAULT '',"
    " PRIMARY KEY (publication_id, lang))",
    "CREATE TABLE IF NOT EXISTS publication_jobs ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " publication_id INTEGER NOT NULL REFERENCES publications(id) ON DELETE RESTRICT,"
    " channel_id INTEGER NOT NULL REFERENCES publish_channels(id) ON DELETE RESTRICT,"
    " lang TEXT NOT NULL,"
    " scheduled_for TEXT NOT NULL,"
    " status TEXT NOT NULL DEFAULT 'queued',"
    " attempts INTEGER NOT NULL DEFAULT 0,"
    " next_attempt_at TEXT,"
    " last_error TEXT,"
    " external_id TEXT,"
    " idempotency_key TEXT NOT NULL,"
    " locked_at TEXT,"
    " send_started_at TEXT,"
    " created_at TEXT NOT NULL,"
    " updated_at TEXT NOT NULL,"
    " UNIQUE(idempotency_key),"
    " UNIQUE(publication_id, channel_id, lang, scheduled_for))",
    "CREATE INDEX IF NOT EXISTS ix_publication_jobs_due"
    " ON publication_jobs (status, next_attempt_at)",
    "CREATE INDEX IF NOT EXISTS ix_publication_jobs_channel"
    " ON publication_jobs (channel_id, scheduled_for)",
    "CREATE TABLE IF NOT EXISTS publication_events ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " job_id INTEGER NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,"
    " at TEXT NOT NULL,"
    " level TEXT NOT NULL DEFAULT 'info',"
    " message TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS ix_publication_events_job"
    " ON publication_events (job_id, at)",
    "CREATE TABLE IF NOT EXISTS publication_dedup ("
    " idempotency_key TEXT PRIMARY KEY,"
    " created_at TEXT NOT NULL)",
)


def _apply_publications(tx: Any) -> None:
    for statement in PUBLICATIONS_DDL:
        tx.execute(statement)


PUBLICATIONS_MIGRATIONS: Tuple[Migration, ...] = (
    Migration(
        version=PUBLICATIONS_VERSION,
        name="publications_core",
        apply=_apply_publications,
    ),
)
