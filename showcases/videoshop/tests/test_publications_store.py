"""Stage 2: publications domain + store on the v9 schema (tmp_path only)."""
from __future__ import annotations

import sqlite3
from dataclasses import fields
from datetime import datetime, timedelta

import pytest

from showcases.videoshop.domain.catalog import ValidationError
from showcases.videoshop.domain.publications import (
    JOB_FAILED,
    JOB_QUEUED,
    JOB_SENDING,
    JOB_SENT,
    JOB_UNCERTAIN,
    Channel,
    Publication,
    PublicationJob,
    PublishResult,
    can_transition,
    credentials_env_name,
)
from showcases.videoshop.infrastructure.migrations.catalog import migrate_catalog
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.services.publications import PublicationsService

START = "2026-01-01T10:00:00+00:00"


class _Clock:
    """Deterministic clock: ISO-8601 UTC strings, advanceable by seconds."""

    def __init__(self, value: str = START) -> None:
        self.value = value

    def __call__(self) -> str:
        return self.value

    def advance(self, seconds: int) -> None:
        moment = datetime.fromisoformat(self.value) + timedelta(seconds=seconds)
        self.value = moment.isoformat()


def _service(tmp_path, clock=None):
    provider = VideoShopSQLiteProvider(db_path=str(tmp_path / "shop.sqlite"))
    migrate_catalog(provider)
    clock = clock or _Clock()
    return provider, PublicationsService(provider, now=clock), clock


def _channel(service, key="main", name="Main", ref="MAIN"):
    return service.create_channel(channel_key=key, name=name, credentials_ref=ref)


def _publication(service, langs=("ru", "ro", "en")):
    return service.create_publication(
        texts={lang: (f"Title-{lang}", f"Body-{lang}") for lang in langs},
        created_by="owner",
    )


def _jobs(service, *, channels=2, langs=("ru", "ro", "en"), scheduled=START):
    publication = _publication(service, langs)
    channel_rows = [
        _channel(service, key=f"ch{index}", name=f"Channel {index}")
        for index in range(channels)
    ]
    jobs = service.schedule_jobs(
        publication.id,
        channel_ids=[row.id for row in channel_rows],
        langs=list(langs),
        scheduled_for=scheduled,
    )
    return publication, channel_rows, jobs


def _columns(tx, table):
    return {
        row["name"]: (row["type"].upper(), int(row["notnull"]))
        for row in tx.fetchall(f"PRAGMA table_info({table})")
    }


def test_models_match_v9_schema(tmp_path):
    provider, _, _ = _service(tmp_path)
    with provider.read_transaction() as tx:
        channels = _columns(tx, "publish_channels")
        publications = _columns(tx, "publications")
        texts = _columns(tx, "publication_texts")
        jobs = _columns(tx, "publication_jobs")
        events = _columns(tx, "publication_events")
        dedup = _columns(tx, "publication_dedup")

    assert {field.name for field in fields(Channel)} == set(channels)
    assert {field.name for field in fields(Publication)} == set(publications)
    assert {"lang", "title", "body"} <= set(texts)
    assert {field.name for field in fields(PublicationJob)} == set(jobs)
    assert set(events) == {"id", "job_id", "at", "level", "message"}
    assert set(dedup) == {"idempotency_key", "created_at"}
    assert channels["is_active"][0] == "INTEGER"
    assert jobs["attempts"][0] == "INTEGER"
    assert channels["channel_key"][1] == 1
    assert jobs["idempotency_key"][1] == 1
    assert jobs["scheduled_for"][1] == 1


def test_channels_validation(tmp_path):
    _, service, _ = _service(tmp_path)
    with pytest.raises(ValidationError):
        service.create_channel(
            channel_key="BadKey", name="Main", credentials_ref="MAIN"
        )
    with pytest.raises(ValidationError):
        service.create_channel(channel_key="main", name="Main", credentials_ref="")
    with pytest.raises(ValidationError):
        service.create_channel(
            channel_key="main",
            name="Main",
            credentials_ref="MAIN",
            timezone="Mars/Base",
        )
    channel = _channel(service)
    assert channel.id == 1
    assert channel.is_active is True


def test_credentials_ref_required_no_fallback(tmp_path):
    _, service, _ = _service(tmp_path)
    with pytest.raises(ValidationError):
        service.create_channel(channel_key="main", name="Main", credentials_ref="   ")
    channel = _channel(service, key="main", ref="main")
    assert channel.credentials_ref == "MAIN"
    assert credentials_env_name("MAIN") == "VIDEOSHOP_TELEGRAM_MAIN_BOT_TOKEN"


def test_channels_two_telegram_same_platform(tmp_path):
    _, service, _ = _service(tmp_path)
    first = _channel(service, key="main", name="Main")
    second = _channel(service, key="second", name="Second")
    assert first.platform == second.platform == "telegram"
    with pytest.raises(sqlite3.IntegrityError):
        _channel(service, key="third", name="Main")


def test_schedule_jobs_per_channel_language(tmp_path):
    _, service, _ = _service(tmp_path)
    _, _, jobs = _jobs(service)
    assert len(jobs) == 6
    assert len({job.idempotency_key for job in jobs}) == 6
    assert all(job.status == JOB_QUEUED for job in jobs)
    assert all(job.attempts == 0 for job in jobs)
    assert all(job.scheduled_for == START for job in jobs)


def test_schedule_jobs_idempotent(tmp_path):
    provider, service, _ = _service(tmp_path)
    publication, channel_rows, jobs = _jobs(service)
    assert len(jobs) == 6

    again = service.schedule_jobs(
        publication.id,
        channel_ids=[row.id for row in channel_rows],
        langs=["ru", "ro", "en"],
        scheduled_for=START,
    )
    assert again == []
    assert len(service.list_jobs(publication_id=publication.id)) == 6
    with provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM publication_dedup") == 6


def test_schedule_jobs_atomic_dedup_and_job(tmp_path, monkeypatch):
    provider, service, _ = _service(tmp_path)
    publication = _publication(service, ("ru", "ro", "en"))
    channel_rows = [
        _channel(service, key=f"ch{index}", name=f"Channel {index}")
        for index in range(2)
    ]
    store = service._store
    original = store._insert_job
    calls = {"count": 0}

    def boom(tx, **kwargs):
        calls["count"] += 1
        if calls["count"] == 3:
            raise RuntimeError("boom")
        return original(tx, **kwargs)

    monkeypatch.setattr(store, "_insert_job", boom)

    with pytest.raises(RuntimeError):
        service.schedule_jobs(
            publication.id,
            channel_ids=[row.id for row in channel_rows],
            langs=["ru", "ro", "en"],
            scheduled_for=START,
        )

    with provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM publication_jobs") == 0
        assert tx.scalar("SELECT COUNT(*) FROM publication_dedup") == 0


def test_claim_due_rowcount(tmp_path):
    _, service, _ = _service(tmp_path)
    _jobs(service, channels=1, langs=("ru", "ro", "en"))

    claimed = service.claim_due(limit=2)
    assert len(claimed) == 2
    assert all(job.status == JOB_SENDING for job in claimed)
    assert all(job.attempts == 1 for job in claimed)

    again = service.claim_due(limit=5)
    assert len(again) == 1
    assert {job.id for job in claimed}.isdisjoint({job.id for job in again})


def test_claim_due_two_providers_no_double_claim(tmp_path):
    provider, service, clock = _service(tmp_path)
    _jobs(service, channels=1, langs=("ru", "ro", "en"))
    other_provider = VideoShopSQLiteProvider(db_path=str(tmp_path / "shop.sqlite"))
    other_service = PublicationsService(other_provider, now=clock)

    first = service.claim_due(limit=2)
    second = other_service.claim_due(limit=3)
    assert len(first) == 2
    assert len(second) == 1
    assert {job.id for job in first}.isdisjoint({job.id for job in second})
    assert len(service.list_jobs(status=JOB_SENDING)) == 3


def test_transitions_matrix(tmp_path):
    assert can_transition(JOB_QUEUED, JOB_SENDING)
    for target in (JOB_SENT, JOB_QUEUED, JOB_FAILED, JOB_UNCERTAIN):
        assert can_transition(JOB_SENDING, target)
    assert can_transition(JOB_UNCERTAIN, JOB_SENT)
    assert can_transition(JOB_UNCERTAIN, JOB_FAILED)
    assert not can_transition(JOB_UNCERTAIN, JOB_QUEUED)
    assert not can_transition(JOB_SENT, JOB_QUEUED)
    assert not can_transition(JOB_FAILED, JOB_QUEUED)

    _, service, _ = _service(tmp_path)
    _, _, jobs = _jobs(service, channels=1, langs=("ru",))
    with pytest.raises(ValidationError):
        service.finish(jobs[0].id, PublishResult(ok=True, external_id="1"))


def test_retry_schedule(tmp_path):
    _, service, clock = _service(tmp_path)
    _jobs(service, channels=1, langs=("ru",))

    job = service.claim_due(limit=1)[0]
    assert job.attempts == 1
    job = service.finish(
        job.id, PublishResult(ok=False, error="http 500", retryable=True)
    )
    assert job.status == JOB_QUEUED
    assert job.next_attempt_at == (
        datetime.fromisoformat(START) + timedelta(seconds=60)
    ).isoformat()

    clock.advance(60)
    job = service.claim_due(limit=1)[0]
    assert job.attempts == 2
    job = service.finish(
        job.id, PublishResult(ok=False, error="http 500", retryable=True)
    )
    assert job.next_attempt_at == (
        datetime.fromisoformat(START) + timedelta(seconds=360)
    ).isoformat()

    clock.advance(300)
    job = service.claim_due(limit=1)[0]
    assert job.attempts == 3
    job = service.finish(
        job.id, PublishResult(ok=False, error="http 500", retryable=True)
    )
    assert job.status == JOB_FAILED
    assert len(service.claim_due(limit=10)) == 0


def test_retry_after_overrides_intervals(tmp_path):
    _, service, _ = _service(tmp_path)
    _jobs(service, channels=1, langs=("ru",))
    job = service.claim_due(limit=1)[0]

    job = service.finish(
        job.id,
        PublishResult(ok=False, error="http 429", retryable=True, retry_after=120),
    )
    assert job.next_attempt_at == (
        datetime.fromisoformat(START) + timedelta(seconds=120)
    ).isoformat()


def test_stale_sending_to_uncertain(tmp_path):
    _, service, clock = _service(tmp_path)
    _jobs(service, channels=1, langs=("ru",))
    job = service.claim_due(limit=1)[0]
    assert job.status == JOB_SENDING

    assert service.expire_stale_sends(ttl_seconds=600) == 0
    clock.advance(601)
    assert service.expire_stale_sends(ttl_seconds=600) == 1

    stale = service.list_jobs(status=JOB_UNCERTAIN)
    assert len(stale) == 1
    assert stale[0].status == JOB_UNCERTAIN
    assert service.expire_stale_sends(ttl_seconds=600) == 0
    assert service.claim_due(limit=10) == []


def test_events_no_secrets(tmp_path):
    _, service, clock = _service(tmp_path)
    publication = service.create_publication(
        texts={"ru": ("Title-ABC", "Body-XYZ")}, created_by="owner"
    )
    channel = _channel(service, key="main", name="Main", ref="MAIN")
    service.schedule_jobs(
        publication.id,
        channel_ids=[channel.id],
        langs=["ru"],
        scheduled_for=START,
    )

    job = service.claim_due(limit=1)[0]
    service.finish(job.id, PublishResult(ok=False, error="network error", retryable=True))
    clock.advance(60)
    job = service.claim_due(limit=1)[0]
    service.finish(job.id, PublishResult(ok=False, error=""))

    events = service.list_events(job.id)
    assert events
    for event in events:
        for forbidden in ("Title-ABC", "Body-XYZ", "MAIN", "SECRET"):
            assert forbidden not in event["message"]


def test_resolve_uncertain_manual_only(tmp_path):
    _, service, _ = _service(tmp_path)
    _, _, jobs = _jobs(service, channels=1, langs=("ru", "ro"))

    with pytest.raises(ValidationError):
        service.resolve_uncertain(jobs[0].id, outcome="sent", external_id="1")

    claimed = service.claim_due(limit=1)[0]
    with pytest.raises(ValidationError):
        service.resolve_uncertain(claimed.id, outcome="sent", external_id=None)

    service.finish(
        claimed.id,
        PublishResult(ok=False, error="timeout", retryable=False),
        uncertain=True,
    )
    with pytest.raises(ValidationError):
        service.resolve_uncertain(claimed.id, outcome="sent", external_id=None)

    resolved = service.resolve_uncertain(claimed.id, outcome="sent", external_id="42")
    assert resolved.status == JOB_SENT
    assert resolved.external_id == "42"


def test_retry_as_new_new_key_and_source_unchanged(tmp_path):
    provider, service, _ = _service(tmp_path)
    _jobs(service, channels=1, langs=("ru",))

    job = service.claim_due(limit=1)[0]
    job = service.finish(job.id, PublishResult(ok=True, external_id="777"))
    assert job.status == JOB_SENT

    new_job = service.retry_as_new(job.id)
    assert new_job.id != job.id
    assert new_job.status == JOB_QUEUED
    assert new_job.attempts == 0
    assert new_job.idempotency_key != job.idempotency_key
    assert new_job.scheduled_for != job.scheduled_for

    with provider.read_transaction() as tx:
        row = tx.fetchone("SELECT * FROM publication_jobs WHERE id = ?", (job.id,))
    assert row["status"] == JOB_SENT
    assert row["external_id"] == "777"
    assert row["attempts"] == job.attempts


def test_retry_as_new_repeated_keys_unique(tmp_path):
    _, service, _ = _service(tmp_path)
    _jobs(service, channels=1, langs=("ru",))

    job = service.claim_due(limit=1)[0]
    job = service.finish(job.id, PublishResult(ok=True, external_id="1"))

    first = service.retry_as_new(job.id)
    second = service.retry_as_new(job.id)
    assert first.scheduled_for != second.scheduled_for
    assert first.idempotency_key != second.idempotency_key
    assert first.id != second.id


def test_retention_sweep_not_implemented(tmp_path):
    _, service, _ = _service(tmp_path)
    with pytest.raises(NotImplementedError):
        service.retention_sweep()


class _SpyProvider:
    def __init__(self, provider) -> None:
        self._provider = provider
        self.calls = []

    def transaction(self):
        self.calls.append("transaction")
        return self._provider.transaction()

    def read_transaction(self):
        self.calls.append("read_transaction")
        return self._provider.read_transaction()

    @property
    def db_path(self):
        return self._provider.db_path


def test_read_only_operations_use_read_transaction(tmp_path):
    provider, _, _ = _service(tmp_path)
    spy = _SpyProvider(provider)
    service = PublicationsService(spy)

    service.list_channels()
    assert spy.calls == ["read_transaction"]

    spy.calls.clear()
    service.create_channel(channel_key="main", name="Main", credentials_ref="MAIN")
    assert spy.calls == ["transaction"]


def test_publications_enabled_default_off(tmp_path, monkeypatch):
    _, service, _ = _service(tmp_path)
    monkeypatch.delenv("VIDEOSHOP_PUBLICATIONS", raising=False)
    assert service.publications_enabled() is False
    monkeypatch.setenv("VIDEOSHOP_PUBLICATIONS", "on")
    assert service.publications_enabled() is True
    monkeypatch.setenv("VIDEOSHOP_PUBLICATIONS", "ON")
    assert service.publications_enabled() is True
    monkeypatch.setenv("VIDEOSHOP_PUBLICATIONS", "yes")
    assert service.publications_enabled() is False
    monkeypatch.setenv("VIDEOSHOP_PUBLICATIONS", "")
    assert service.publications_enabled() is False
