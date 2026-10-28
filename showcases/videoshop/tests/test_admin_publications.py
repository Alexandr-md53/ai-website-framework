"""S5.3: admin publications UI (create + list, Telegram channels, UTC schedule)."""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.infrastructure.migrations.catalog import migrate_catalog
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.services.publications import PublicationsService
from showcases.videoshop.web.app import create_app

PASSWORD = "publications-pass"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')
START = "2026-01-01T10:00:00+00:00"
LANGS = ("ru", "ro", "en")


@pytest.fixture
def admin_config():
    return AdminConfig(
        username="owner",
        password_hash=hash_password(PASSWORD, iterations=1000),
        secret_key=b"publications-secret",
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


def _channel(paths, key="main", name="Main"):
    return _service(paths).create_channel(
        channel_key=key,
        name=name,
        credentials_ref="MAIN",
        settings_json='{"chat_id": "123456789"}',
    )


def _counts(paths):
    provider = VideoShopSQLiteProvider(db_path=paths["db_path"])
    with provider.read_transaction() as tx:
        return {
            "publications": tx.scalar("SELECT COUNT(*) FROM publications"),
            "texts": tx.scalar("SELECT COUNT(*) FROM publication_texts"),
            "jobs": tx.scalar("SELECT COUNT(*) FROM publication_jobs"),
        }


def _form(csrf, channel_id, *, scheduled="2026-06-15T12:00", **overrides):
    data = {"csrf": csrf, "scheduled_local": scheduled}
    data[f"channel_{channel_id}"] = "1"
    for code in LANGS:
        data[f"title_{code}"] = f"Title {code}"
        data[f"body_{code}"] = f"Body {code}"
    data.update(overrides)
    return data


def _post(client, csrf, channel_id, **overrides):
    return client.post(
        "/admin/publications/new",
        data=_form(csrf, channel_id, **overrides),
    )


def test_publications_requires_login(client):
    assert client.get("/admin/publications").status_code == 303
    assert client.get("/admin/publications/new").status_code == 303
    response = client.post(
        "/admin/publications/new",
        data={"title_ru": "T", "scheduled_local": "2026-06-15T12:00"},
    )
    assert response.status_code in (303, 401)


def test_publications_post_requires_csrf(client, admin_config, paths):
    _login(client, admin_config)
    channel = _channel(paths)
    response = client.post(
        "/admin/publications/new",
        data=_form("x", channel.id),
    )
    assert response.status_code == 403


def test_publications_list_renders(client, admin_config, paths):
    channel = _channel(paths)
    service = _service(paths)
    publication = service.create_publication(
        texts={code: (f"Title {code}", f"Body {code}") for code in LANGS},
        created_by="owner",
    )
    service.schedule_jobs(
        publication.id,
        channel_ids=[channel.id],
        langs=list(LANGS),
        scheduled_for=START,
    )
    _login(client, admin_config)

    response = client.get("/admin/publications")

    assert response.status_code == 200
    assert str(publication.id) in response.text
    assert "queued" in response.text
    assert "BOT_TOKEN" not in response.text


def test_publications_create_valid(client, admin_config, paths):
    csrf = _login(client, admin_config)
    channel = _channel(paths)

    response = _post(client, csrf, channel.id)

    assert response.status_code == 303
    counts = _counts(paths)
    assert counts == {"publications": 1, "texts": 3, "jobs": 3}
    jobs = _service(paths).list_jobs()
    assert {job.lang for job in jobs} == set(LANGS)
    assert {job.scheduled_for for job in jobs} == {"2026-06-15T09:00:00+00:00"}


def test_publications_missing_language_blocked(client, admin_config, paths):
    csrf = _login(client, admin_config)
    channel = _channel(paths)
    data = _form(csrf, channel.id)
    del data["title_ro"]

    response = client.post("/admin/publications/new", data=data)

    assert response.status_code == 400
    assert _counts(paths)["publications"] == 0


def test_publications_invalid_local_time_400(client, admin_config, paths):
    csrf = _login(client, admin_config)
    channel = _channel(paths)

    response = _post(client, csrf, channel.id, scheduled="not-a-date")

    assert response.status_code == 400
    assert _counts(paths)["publications"] == 0


def test_publications_dst_spring_shifts(client, admin_config, paths):
    csrf = _login(client, admin_config)
    channel = _channel(paths)

    response = _post(client, csrf, channel.id, scheduled="2026-03-29T03:30")

    assert response.status_code == 303
    assert "shifted=1" in response.headers.get("location", "")
    jobs = _service(paths).list_jobs()
    assert {job.scheduled_for for job in jobs} == {"2026-03-29T01:30:00+00:00"}


def test_publications_dst_fall_ambiguous_400(client, admin_config, paths):
    csrf = _login(client, admin_config)
    channel = _channel(paths)

    response = _post(client, csrf, channel.id, scheduled="2026-10-25T03:30")

    assert response.status_code == 400
    assert "ambiguous" in response.text
    assert _counts(paths)["publications"] == 0


def test_publications_schedule_idempotent(paths):
    channel = _channel(paths)
    service = _service(paths)
    publication = service.create_publication(
        texts={code: (f"Title {code}", f"Body {code}") for code in LANGS},
        created_by="owner",
    )
    first = service.schedule_jobs(
        publication.id,
        channel_ids=[channel.id],
        langs=list(LANGS),
        scheduled_for=START,
    )
    second = service.schedule_jobs(
        publication.id,
        channel_ids=[channel.id],
        langs=list(LANGS),
        scheduled_for=START,
    )

    assert len(first) == 3
    assert second == []
    assert _counts(paths)["jobs"] == 3


def test_publications_text_over_limit_rejected(client, admin_config, paths):
    csrf = _login(client, admin_config)
    channel = _channel(paths)

    response = _post(client, csrf, channel.id, body_ru="x" * 5000)

    assert response.status_code == 400
    assert "Telegram limit" in response.text
    assert _counts(paths)["publications"] == 0


def test_publications_text_escaping_limit(client, admin_config, paths):
    csrf = _login(client, admin_config)
    channel = _channel(paths)
    raw = "a" * 4090 + "<" + "b" * 5

    response = _post(client, csrf, channel.id, body_ru=raw)

    assert response.status_code == 400
    assert _counts(paths)["publications"] == 0


def test_publications_not_found_404(client, admin_config):
    _login(client, admin_config)
    assert client.get("/admin/publications/999").status_code == 404


def test_publications_hidden_when_flag_off(paths, admin_config):
    app = _make_app(paths, admin_config, "off")
    client = TestClient(app, follow_redirects=False)

    assert client.get("/admin/publications").status_code == 404
    assert client.get("/admin/publications/new").status_code == 404
    assert client.post(
        "/admin/publications/new", data={"scheduled_local": "2026-06-15T12:00"}
    ).status_code == 404


def test_publications_page_has_no_secret(client, admin_config, paths):
    csrf = _login(client, admin_config)
    channel = _channel(paths)
    assert _post(client, csrf, channel.id).status_code == 303

    list_body = client.get("/admin/publications").text
    form_body = client.get("/admin/publications/new").text
    ru_body = client.get("/admin/publications?lang=ru").text

    for body in (list_body, form_body, ru_body):
        assert "BOT_TOKEN" not in body
        assert "VIDEOSHOP_TELEGRAM_" not in body
    assert "Публикации" in ru_body


def test_publications_non_atomic_schedule_reports(client, admin_config, paths, monkeypatch):
    csrf = _login(client, admin_config)
    channel = _channel(paths)

    def boom(self, publication_id, *, channel_ids, langs, scheduled_for):
        raise RuntimeError("schedule failed")

    monkeypatch.setattr(PublicationsService, "schedule_jobs", boom)

    response = _post(client, csrf, channel.id)

    assert response.status_code == 400
    assert "jobs NOT scheduled" in response.text
    counts = _counts(paths)
    assert counts["publications"] == 1
    assert counts["jobs"] == 0
