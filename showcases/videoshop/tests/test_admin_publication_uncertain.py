"""S5.4: uncertain resolution UI and manual retry-as-new."""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.domain.publications import PublishResult
from showcases.videoshop.infrastructure.migrations.catalog import migrate_catalog
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.services.publications import PublicationsService
from showcases.videoshop.web.app import create_app

PASSWORD = "uncertain-pass"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')
START = "2026-01-01T10:00:00+00:00"
LANGS = ("ru", "ro", "en")


@pytest.fixture
def admin_config():
    return AdminConfig(
        username="owner",
        password_hash=hash_password(PASSWORD, iterations=1000),
        secret_key=b"uncertain-secret",
        session_ttl_seconds=3600,
    )


@pytest.fixture
def paths(tmp_path):
    (tmp_path / "db").mkdir()
    (tmp_path / "backups").mkdir()
    return {
        "db_path": str(tmp_path / "db" / "shop.sqlite"),
        "backup_dir": str(tmp_path / "backups"),
        "images_dir": str(tmp_path / "images"),
    }


def _make_app(paths, admin_config, flag="on"):
    return create_app(
        **paths,
        admin_config=admin_config,
        env={"VIDEOSHOP_PUBLICATIONS": flag},
    )


@pytest.fixture
def app(paths, admin_config):
    return _make_app(paths, admin_config, "on")


@pytest.fixture
def client(app):
    return TestClient(app, follow_redirects=False)


def _login(client, admin_config):
    response = client.post(
        "/admin/login",
        data={"username": admin_config.username, "password": PASSWORD},
    )
    assert response.status_code == 303
    return CSRF_RE.search(client.get("/admin").text).group(1)


def _service(paths):
    provider = VideoShopSQLiteProvider(db_path=paths["db_path"])
    migrate_catalog(provider)
    return PublicationsService(provider)


def _job(paths, *, uncertain=False):
    service = _service(paths)
    channel = service.create_channel(
        channel_key=f"main{len(service.list_channels())}",
        name=f"Main {len(service.list_channels())}",
        credentials_ref="MAIN",
        settings_json='{"chat_id": "123456789"}',
    )
    publication = service.create_publication(
        texts={code: (f"Title {code}", f"Body {code}") for code in LANGS},
        created_by="owner",
    )
    service.schedule_jobs(
        publication.id,
        channel_ids=[channel.id],
        langs=["ru"],
        scheduled_for=START,
    )
    job = service.claim_due(limit=1)[0]
    if uncertain:
        job = service.finish(
            job.id,
            PublishResult(ok=False, error="timeout", retryable=True),
            uncertain=True,
        )
    else:
        job = service.finish(
            job.id,
            PublishResult(ok=False, error="permanent", retryable=False),
        )
    return publication, channel, job


def _resolve(client, csrf, job, publication, outcome, **overrides):
    data = {
        "csrf": csrf,
        "publication_id": publication.id,
        "outcome": outcome,
    }
    data.update(overrides)
    return client.post(f"/admin/jobs/{job.id}/resolve", data=data)


def _retry(client, csrf, job, publication, **overrides):
    data = {"csrf": csrf, "publication_id": publication.id}
    data.update(overrides)
    return client.post(f"/admin/jobs/{job.id}/retry-as-new", data=data)


def test_jobs_requires_login(client):
    assert client.get("/admin/publications/1/jobs").status_code == 303
    assert client.post("/admin/jobs/1/resolve", data={"outcome": "sent"}).status_code in (303, 401)


def test_jobs_post_requires_csrf(client, admin_config, paths):
    _login(client, admin_config)
    publication, _, job = _job(paths, uncertain=True)
    response = client.post(
        f"/admin/jobs/{job.id}/resolve",
        data={"publication_id": publication.id, "outcome": "sent", "external_id": "1"},
    )
    assert response.status_code == 403


def test_jobs_page_renders(client, admin_config, paths):
    publication, _, uncertain_job = _job(paths, uncertain=True)
    _login(client, admin_config)
    _job(paths)  # separate publication with a failed job, not linked to this page

    response = client.get(f"/admin/publications/{publication.id}/jobs")

    assert response.status_code == 200
    assert str(uncertain_job.id) in response.text
    assert "uncertain" in response.text
    assert "BOT_TOKEN" not in response.text


def test_resolve_sent_ok(client, admin_config, paths):
    csrf = _login(client, admin_config)
    publication, _, job = _job(paths, uncertain=True)

    response = _resolve(client, csrf, job, publication, "sent", external_id="42", note="checked")

    assert response.status_code == 303
    stored = _service(paths).list_jobs(publication_id=publication.id)[0]
    assert stored.status == "sent"
    assert stored.external_id == "42"
    messages = [event["message"] for event in _service(paths).list_events(job.id)]
    assert "manual resolution: sent" in messages


def test_resolve_sent_requires_external_id(client, admin_config, paths):
    csrf = _login(client, admin_config)
    publication, _, job = _job(paths, uncertain=True)

    response = _resolve(client, csrf, job, publication, "sent")

    assert response.status_code == 400
    assert "external_id is required" in response.text
    assert _service(paths).list_jobs(publication_id=publication.id)[0].status == "uncertain"


def test_resolve_failed_ok(client, admin_config, paths):
    csrf = _login(client, admin_config)
    publication, _, job = _job(paths, uncertain=True)

    response = _resolve(
        client, csrf, job, publication, "failed", confirmed_not_sent="1", note="not delivered"
    )

    assert response.status_code == 303
    stored = _service(paths).list_jobs(publication_id=publication.id)[0]
    assert stored.status == "failed"
    assert stored.last_error == "not delivered"
    messages = [event["message"] for event in _service(paths).list_events(job.id)]
    assert "manual resolution: failed" in messages


def test_resolve_failed_requires_confirmation(client, admin_config, paths):
    csrf = _login(client, admin_config)
    publication, _, job = _job(paths, uncertain=True)

    response = _resolve(client, csrf, job, publication, "failed")

    assert response.status_code == 400
    assert "confirmation" in response.text
    assert _service(paths).list_jobs(publication_id=publication.id)[0].status == "uncertain"


def test_leave_unknown_noop(client, admin_config, paths):
    publication, _, job = _job(paths, uncertain=True)
    _login(client, admin_config)
    before_events = _service(paths).list_events(job.id)

    response = client.get(f"/admin/publications/{publication.id}/jobs?kept=1")

    assert response.status_code == 200
    stored = _service(paths).list_jobs(publication_id=publication.id)[0]
    assert stored.status == "uncertain"
    assert _service(paths).list_events(job.id) == before_events


def test_retry_from_failed(client, admin_config, paths):
    csrf = _login(client, admin_config)
    publication, _, job = _job(paths)

    response = _retry(client, csrf, job, publication)

    assert response.status_code == 303
    jobs = _service(paths).list_jobs(publication_id=publication.id)
    assert len(jobs) == 2
    original = [item for item in jobs if item.id == job.id][0]
    created = [item for item in jobs if item.id != job.id][0]
    assert original.status == "failed"
    assert created.status == "queued"
    assert created.attempts == 0
    assert created.idempotency_key != original.idempotency_key


def test_retry_from_uncertain_rejected(client, admin_config, paths):
    csrf = _login(client, admin_config)
    publication, _, job = _job(paths, uncertain=True)

    response = _retry(client, csrf, job, publication)

    assert response.status_code == 400
    assert len(_service(paths).list_jobs(publication_id=publication.id)) == 1


def test_second_resolve_rejected(client, admin_config, paths):
    csrf = _login(client, admin_config)
    publication, _, job = _job(paths, uncertain=True)
    assert _resolve(client, csrf, job, publication, "sent", external_id="1").status_code == 303

    response = _resolve(client, csrf, job, publication, "failed", confirmed_not_sent="1")

    assert response.status_code == 400
    assert "resolve requires" in response.text


def test_second_retry_creates_second_job(client, admin_config, paths):
    csrf = _login(client, admin_config)
    publication, _, job = _job(paths)

    assert _retry(client, csrf, job, publication).status_code == 303
    assert _retry(client, csrf, job, publication).status_code == 303

    assert len(_service(paths).list_jobs(publication_id=publication.id)) == 3


def test_jobs_not_found_404(client, admin_config):
    _login(client, admin_config)
    assert client.get("/admin/publications/999/jobs").status_code == 404


def test_jobs_hidden_when_flag_off(paths, admin_config):
    app = _make_app(paths, admin_config, "off")
    client = TestClient(app, follow_redirects=False)

    assert client.get("/admin/publications/1/jobs").status_code == 404
    assert client.post("/admin/jobs/1/resolve", data={"outcome": "sent"}).status_code == 404
    assert client.post("/admin/jobs/1/retry-as-new", data={}).status_code == 404


def test_jobs_no_secret_and_i18n(client, admin_config, paths):
    publication, _, job = _job(paths, uncertain=True)
    _login(client, admin_config)

    body = client.get(f"/admin/publications/{publication.id}/jobs?lang=ru").text

    assert "Задания" in body
    assert "BOT_TOKEN" not in body
    assert "VIDEOSHOP_TELEGRAM_" not in body


def test_retry_optional_scheduled_local(client, admin_config, paths):
    csrf = _login(client, admin_config)
    publication, _, job = _job(paths)

    response = _retry(client, csrf, job, publication, scheduled_local="2026-06-15T12:00")

    assert response.status_code == 303
    jobs = _service(paths).list_jobs(publication_id=publication.id)
    created = [item for item in jobs if item.id != job.id][0]
    assert created.scheduled_for == "2026-06-15T09:00:00+00:00"
