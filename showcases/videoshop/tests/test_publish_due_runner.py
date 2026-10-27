"""Stage 4: scheduled publication runner (orchestration only, tmp_path)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest

from showcases.videoshop.domain.publications import (
    JOB_FAILED,
    JOB_QUEUED,
    JOB_SENDING,
    JOB_SENT,
    JOB_UNCERTAIN,
    PublishResult,
)
from showcases.videoshop.infrastructure.migrations.catalog import migrate_catalog
from showcases.videoshop.infrastructure.retry import BusyTimeoutError
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.services.publications import PublicationsService
from showcases.videoshop.tools import publish_due

START = "2026-01-01T10:00:00+00:00"
SILENT = lambda *args, **kwargs: None  # noqa: E731


class _Clock:
    def __init__(self, value: str = START) -> None:
        self.value = value

    def __call__(self) -> str:
        return self.value

    def advance(self, seconds: int) -> None:
        moment = datetime.fromisoformat(self.value) + timedelta(seconds=seconds)
        self.value = moment.isoformat()


class _FakeAdapter:
    def __init__(self, *, result=None, error=None, on_send=None) -> None:
        self.result = result
        self.error = error
        self.on_send = on_send
        self.calls = []

    def send(self, channel, text, media=None):
        self.calls.append((channel.channel_key, text))
        if self.on_send is not None:
            self.on_send(channel, text)
        if self.error is not None:
            raise self.error
        return self.result


def _setup(tmp_path, clock=None):
    clock = clock or _Clock()
    provider = VideoShopSQLiteProvider(db_path=str(tmp_path / "shop.sqlite"))
    migrate_catalog(provider)
    return provider, PublicationsService(provider, now=clock), clock


def _channel(service, *, key="main", name="Main"):
    return service.create_channel(
        channel_key=key,
        name=name,
        credentials_ref="MAIN",
        settings_json='{"chat_id": "123456789"}',
    )


def _jobs(service, *, channels=1, langs=("ru",)):
    publication = service.create_publication(
        texts={lang: (f"Title-{lang}", f"Body-{lang}") for lang in langs},
        created_by="owner",
    )
    rows = [_channel(service, key=f"ch{index}", name=f"C{index}") for index in range(channels)]
    jobs = service.schedule_jobs(
        publication.id,
        channel_ids=[row.id for row in rows],
        langs=list(langs),
        scheduled_for=START,
    )
    return publication, rows, jobs


def _patch_adapter(monkeypatch, adapter):
    monkeypatch.setattr(publish_due, "get_adapter", lambda platform: adapter)
    return adapter


class _SpyProvider:
    def __init__(self, provider) -> None:
        self._provider = provider
        self.depth = 0

    @contextmanager
    def transaction(self):
        self.depth += 1
        try:
            with self._provider.transaction() as tx:
                yield tx
        finally:
            self.depth -= 1

    @contextmanager
    def read_transaction(self):
        with self._provider.read_transaction() as tx:
            yield tx


def test_flag_off_runner_noop(tmp_path, monkeypatch):
    monkeypatch.delenv("VIDEOSHOP_PUBLICATIONS", raising=False)
    created = []

    class _ForbiddenProvider:
        def __init__(self, *args, **kwargs):
            created.append(1)
            raise AssertionError("provider must not be created when the flag is off")

    monkeypatch.setattr(publish_due, "VideoShopSQLiteProvider", _ForbiddenProvider)

    assert publish_due.main(["--db", str(tmp_path / "unused.sqlite")]) == 0
    assert created == []


def test_runner_no_http_inside_transaction(tmp_path, monkeypatch):
    provider, service, _ = _setup(tmp_path)
    _jobs(service)
    spy = _SpyProvider(provider)
    spy_service = PublicationsService(spy)
    violations = []
    adapter = _FakeAdapter(
        result=PublishResult(ok=True, external_id="1"),
        on_send=lambda channel, text: violations.append(spy.depth),
    )
    _patch_adapter(monkeypatch, adapter)

    publish_due.run_once(spy_service, log=SILENT)

    assert adapter.calls
    assert violations == [0]


def test_runner_respects_retry_after(tmp_path, monkeypatch):
    _, service, _ = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    _patch_adapter(
        monkeypatch,
        _FakeAdapter(
            result=PublishResult(False, None, "telegram 429", True, 120)
        ),
    )

    publish_due.run_once(service, log=SILENT)

    job = service.list_jobs(publication_id=publication.id)[0]
    assert job.status == JOB_QUEUED
    assert job.next_attempt_at == (
        datetime.fromisoformat(START) + timedelta(seconds=120)
    ).isoformat()


def test_runner_never_retries_ambiguous_timeout(tmp_path, monkeypatch):
    _, service, _ = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    adapter = _patch_adapter(
        monkeypatch,
        _FakeAdapter(result=PublishResult(False, None, "telegram timeout", True, None)),
    )

    publish_due.run_once(service, log=SILENT)
    job = service.list_jobs(publication_id=publication.id)[0]
    assert job.status == JOB_UNCERTAIN

    publish_due.run_once(service, log=SILENT)
    assert len(adapter.calls) == 1


def test_http_408_becomes_uncertain(tmp_path, monkeypatch):
    _, service, _ = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    adapter = _patch_adapter(
        monkeypatch,
        _FakeAdapter(
            result=PublishResult(
                False, None, "telegram 408 (outcome ambiguous)", True, None
            )
        ),
    )

    publish_due.run_once(service, log=SILENT)
    assert service.list_jobs(publication_id=publication.id)[0].status == JOB_UNCERTAIN

    publish_due.run_once(service, log=SILENT)
    assert len(adapter.calls) == 1


def test_invalid_json_response_becomes_uncertain(tmp_path, monkeypatch):
    _, service, _ = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    _patch_adapter(
        monkeypatch,
        _FakeAdapter(
            result=PublishResult(False, None, "telegram response invalid", False, None)
        ),
    )

    publish_due.run_once(service, log=SILENT)

    job = service.list_jobs(publication_id=publication.id)[0]
    assert job.status == JOB_UNCERTAIN
    assert job.status != JOB_FAILED


def test_stale_sending_becomes_uncertain(tmp_path, monkeypatch):
    _, service, clock = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    adapter = _patch_adapter(
        monkeypatch, _FakeAdapter(result=PublishResult(ok=True, external_id="1"))
    )

    service.claim_due(limit=1)
    clock.advance(601)
    counts = publish_due.run_once(service, ttl_seconds=600, log=SILENT)

    assert counts["expired"] == 1
    assert service.list_jobs(publication_id=publication.id)[0].status == JOB_UNCERTAIN
    assert adapter.calls == []


def test_runner_job_isolation(tmp_path, monkeypatch):
    _, service, _ = _setup(tmp_path)
    publication, channels, _ = _jobs(service, channels=2)
    adapter = _patch_adapter(
        monkeypatch,
        _FakeAdapter(result=PublishResult(ok=True, external_id="9")),
    )

    def fail_first(channel, text):
        if channel.channel_key == "ch0":
            raise RuntimeError("channel A is broken")

    adapter.on_send = fail_first

    counts = publish_due.run_once(service, log=SILENT)

    jobs = {job.channel_id: job for job in service.list_jobs(publication_id=publication.id)}
    assert jobs[channels[0].id].status == JOB_SENDING
    assert jobs[channels[1].id].status == JOB_SENT
    assert counts["errors"] == 1
    assert counts["sent"] == 1


def test_runner_claims_job_atomically(tmp_path, monkeypatch):
    provider, service, clock = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    _patch_adapter(
        monkeypatch, _FakeAdapter(result=PublishResult(ok=True, external_id="1"))
    )

    service.claim_due(limit=1)
    second = PublicationsService(provider, now=clock)

    counts = publish_due.run_once(second, log=SILENT)

    assert counts["claimed"] == 0
    assert service.list_jobs(publication_id=publication.id)[0].status == JOB_SENDING


def test_runner_does_not_resend_sent_job(tmp_path, monkeypatch):
    _, service, _ = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    adapter = _patch_adapter(
        monkeypatch, _FakeAdapter(result=PublishResult(ok=True, external_id="1"))
    )

    publish_due.run_once(service, log=SILENT)
    publish_due.run_once(service, log=SILENT)

    assert len(adapter.calls) == 1
    assert service.list_jobs(publication_id=publication.id)[0].status == JOB_SENT


def test_retry_limit_three_attempts(tmp_path, monkeypatch):
    _, service, clock = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    _patch_adapter(
        monkeypatch,
        _FakeAdapter(result=PublishResult(False, None, "telegram 429", True, 60)),
    )

    publish_due.run_once(service, log=SILENT)
    clock.advance(60)
    publish_due.run_once(service, log=SILENT)
    clock.advance(60)
    publish_due.run_once(service, log=SILENT)

    job = service.list_jobs(publication_id=publication.id)[0]
    assert job.status == JOB_FAILED
    assert job.attempts == 3


def test_sqlite_busy_handling(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEOSHOP_PUBLICATIONS", "on")

    class _StubService:
        def __init__(self, provider):
            pass

        def expire_stale_sends(self, ttl_seconds):
            raise BusyTimeoutError("busy")

    monkeypatch.setattr(publish_due, "PublicationsService", _StubService)
    monkeypatch.setattr(publish_due, "VideoShopSQLiteProvider", lambda **kwargs: object())

    assert publish_due.main(["--db", str(tmp_path / "shop.sqlite")]) == 2


def test_restart_after_claim_before_http(tmp_path, monkeypatch):
    _, service, clock = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    adapter = _patch_adapter(
        monkeypatch, _FakeAdapter(result=PublishResult(ok=True, external_id="1"))
    )

    service.claim_due(limit=1)
    clock.advance(601)
    counts = publish_due.run_once(service, log=SILENT)

    assert counts["expired"] == 1
    assert service.list_jobs(publication_id=publication.id)[0].status == JOB_UNCERTAIN
    assert adapter.calls == []


def test_restart_after_http_before_finish(tmp_path, monkeypatch):
    _, service, clock = _setup(tmp_path)
    publication, _, _ = _jobs(service)
    adapter = _patch_adapter(
        monkeypatch, _FakeAdapter(result=PublishResult(ok=True, external_id="1"))
    )

    claimed = service.claim_due(limit=1)
    assert claimed[0].status == JOB_SENDING
    clock.advance(601)
    publish_due.run_once(service, log=SILENT)

    job = service.list_jobs(publication_id=publication.id)[0]
    assert job.status == JOB_UNCERTAIN
    assert adapter.calls == []
