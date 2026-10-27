"""S5.2: admin channels UI (Telegram only, flag-gated)."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.services.publications import PublicationsService
from showcases.videoshop.web.app import create_app

PASSWORD = "channels-pass"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')
START = "2026-01-01T10:00:00+00:00"


@pytest.fixture
def admin_config():
    return AdminConfig(
        username="owner",
        password_hash=hash_password(PASSWORD, iterations=1000),
        secret_key=b"channels-secret",
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
    return PublicationsService(VideoShopSQLiteProvider(db_path=paths["db_path"]))


def _form(csrf, **overrides):
    data = {
        "csrf": csrf,
        "platform": "telegram",
        "channel_key": "main",
        "name": "Main",
        "credentials_ref": "MAIN",
        "chat_id": "-1001234567890",
        "timezone": "Europe/Chisinau",
        "default_language": "",
        "is_active": "1",
    }
    data.update(overrides)
    return data


def _create(client, csrf, **overrides):
    return client.post("/admin/channels/new", data=_form(csrf, **overrides))


def test_channels_requires_login(client):
    assert client.get("/admin/channels").status_code == 303
    response = client.post(
        "/admin/channels/new",
        data={"channel_key": "x", "name": "X", "credentials_ref": "X", "chat_id": "1"},
    )
    assert response.status_code in (303, 401)


def test_channels_post_requires_csrf(client, admin_config):
    _login(client, admin_config)
    response = client.post(
        "/admin/channels/new",
        data={
            "channel_key": "main",
            "name": "Main",
            "credentials_ref": "MAIN",
            "chat_id": "1",
        },
    )
    assert response.status_code == 403


def test_channels_list_renders(client, admin_config, paths):
    csrf = _login(client, admin_config)
    assert _create(client, csrf).status_code == 303

    response = client.get("/admin/channels")

    assert response.status_code == 200
    body = response.text
    assert "main" in body and "Main" in body
    assert "BOT_TOKEN" not in body
    assert "channels" in body.lower()


def test_channel_create_valid(client, admin_config, paths):
    csrf = _login(client, admin_config)

    response = _create(client, csrf)

    assert response.status_code == 303
    channels = _service(paths).list_channels()
    assert len(channels) == 1
    channel = channels[0]
    assert channel.channel_key == "main"
    assert channel.credentials_ref == "MAIN"
    assert channel.platform == "telegram"
    assert channel.is_active is True
    assert json.loads(channel.settings_json)["chat_id"] == "-1001234567890"


def test_channel_create_duplicate_key(client, admin_config, paths):
    csrf = _login(client, admin_config)
    assert _create(client, csrf).status_code == 303

    response = _create(client, csrf, name="Other")

    assert response.status_code == 400
    assert "already used" in response.text
    assert len(_service(paths).list_channels()) == 1


def test_channel_create_duplicate_name(client, admin_config, paths):
    csrf = _login(client, admin_config)
    assert _create(client, csrf).status_code == 303

    response = _create(client, csrf, channel_key="second")

    assert response.status_code == 400
    assert "already used" in response.text
    assert len(_service(paths).list_channels()) == 1


def test_channel_invalid_channel_key(client, admin_config, paths):
    csrf = _login(client, admin_config)

    response = _create(client, csrf, channel_key="BadKey")

    assert response.status_code == 400
    assert _service(paths).list_channels() == []


def test_channel_invalid_credentials_ref(client, admin_config, paths):
    csrf = _login(client, admin_config)

    response = _create(client, csrf, credentials_ref="")

    assert response.status_code == 400
    assert _service(paths).list_channels() == []


def test_channel_invalid_chat_id(client, admin_config, paths):
    csrf = _login(client, admin_config)

    response = _create(client, csrf, chat_id="")

    assert response.status_code == 400
    assert "chat_id" in response.text
    assert _service(paths).list_channels() == []


def test_channel_update_and_deactivate(client, admin_config, paths):
    csrf = _login(client, admin_config)
    assert _create(client, csrf).status_code == 303
    channel = _service(paths).list_channels()[0]

    publications = _service(paths)
    publication = publications.create_publication(
        texts={"ru": ("Title", "Body")}, created_by="owner"
    )
    job = publications.schedule_jobs(
        publication.id,
        channel_ids=[channel.id],
        langs=["ru"],
        scheduled_for=START,
    )[0]

    response = client.post(
        f"/admin/channels/{channel.id}",
        data=_form(csrf, name="Renamed", is_active=None),
    )

    assert response.status_code == 303
    updated = _service(paths).get_channel(channel.id)
    assert updated.name == "Renamed"
    assert updated.is_active is False
    stored_job = _service(paths).list_jobs(publication_id=publication.id)[0]
    assert stored_job.scheduled_for == job.scheduled_for
    assert stored_job.status == job.status
    assert len(_service(paths).list_jobs(publication_id=publication.id)) == 1


def test_channel_not_found(client, admin_config):
    csrf = _login(client, admin_config)

    assert client.get("/admin/channels/999").status_code == 404
    assert client.post("/admin/channels/999", data=_form(csrf)).status_code == 404


def test_channels_hidden_when_flag_off(paths, admin_config):
    app = _make_app(paths, admin_config, "off")
    client = TestClient(app, follow_redirects=False)

    assert client.get("/admin/channels").status_code == 404
    assert client.get("/admin/channels/new").status_code == 404
    assert client.get("/admin/channels/1").status_code == 404
    assert client.post("/admin/channels/new", data={"channel_key": "x"}).status_code == 404
    assert client.post("/admin/channels/1", data={"channel_key": "x"}).status_code == 404


def test_channel_page_has_no_secret(client, admin_config, paths):
    csrf = _login(client, admin_config)
    assert _create(client, csrf).status_code == 303
    channel = _service(paths).list_channels()[0]

    list_body = client.get("/admin/channels").text
    form_body = client.get(f"/admin/channels/{channel.id}").text

    for body in (list_body, form_body):
        assert "BOT_TOKEN" not in body
        assert "VIDEOSHOP_TELEGRAM_" not in body
    assert "MAIN" in form_body


def test_channel_update_preserves_extra_settings_keys(client, admin_config, paths):
    csrf = _login(client, admin_config)
    assert _create(client, csrf).status_code == 303
    channel = _service(paths).list_channels()[0]
    store = _service(paths)
    store.update_channel(channel.id, settings_json='{"chat_id": "1", "note": "keep"}')

    response = client.post(
        f"/admin/channels/{channel.id}",
        data=_form(csrf, chat_id="2"),
    )

    assert response.status_code == 303
    stored = json.loads(_service(paths).get_channel(channel.id).settings_json)
    assert stored["chat_id"] == "2"
    assert stored["note"] == "keep"


def test_channel_invalid_existing_settings_json_is_refused(client, admin_config, paths):
    csrf = _login(client, admin_config)
    assert _create(client, csrf).status_code == 303
    channel = _service(paths).list_channels()[0]
    _service(paths).update_channel(channel.id, settings_json="not-json")

    response = client.post(
        f"/admin/channels/{channel.id}",
        data=_form(csrf, chat_id="2"),
    )

    assert response.status_code == 400
    assert "settings_json invalid" in response.text
    assert _service(paths).get_channel(channel.id).settings_json == "not-json"


def test_channel_timezone_validated(client, admin_config, paths):
    csrf = _login(client, admin_config)

    response = _create(client, csrf, timezone="Mars/Base")

    assert response.status_code == 400
    assert _service(paths).list_channels() == []


def test_channel_empty_default_language_allowed(client, admin_config, paths):
    csrf = _login(client, admin_config)

    response = _create(client, csrf, default_language="")

    assert response.status_code == 303
    assert _service(paths).list_channels()[0].default_language == ""
