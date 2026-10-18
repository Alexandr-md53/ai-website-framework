import os
import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv("CAFE_ADMIN_USER", "admin")
    monkeypatch.setenv("CAFE_ADMIN_PASSWORD", "secret123")
    import importlib
    import showcases.cafe.services.cafe_admin_security as sec

    importlib.reload(sec)
    import showcases.cafe.services.cafe_profile_service as prof

    importlib.reload(prof)
    from showcases.cafe.app_factory import create_app

    data_path = Path("showcases/cafe/data/profile.json")
    if data_path.exists():
        data_path.unlink()
    app = create_app()
    client = TestClient(app)
    return client, data_path


def _auth():
    token = base64.b64encode(b"admin:secret123").decode()
    return {"Authorization": f"Basic {token}"}


def test_admin_closed_without_env(monkeypatch):
    monkeypatch.delenv("CAFE_ADMIN_USER", raising=False)
    monkeypatch.delenv("CAFE_ADMIN_PASSWORD", raising=False)

    from showcases.cafe.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)
    r = client.get("/admin")
    assert r.status_code == 403


def test_admin_profile_requires_auth(admin_client):
    client, _ = admin_client
    r = client.get("/admin/profile")
    assert r.status_code == 401


def test_admin_profile_get_ok(admin_client):
    client, _ = admin_client
    r = client.get("/admin/profile", headers=_auth())
    assert r.status_code == 200
    assert "Profile Settings" in r.text
    assert "csrf_token" in r.text


def test_admin_profile_update_and_persist(admin_client):
    client, data_path = admin_client
    r = client.get("/admin/profile", headers=_auth())
    import re

    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert m
    csrf = m.group(1)
    payload = {
        "csrf_token": csrf,
        "profile_name_ru": "Кофейня Тест",
        "profile_name_ro": "Cafenea Test",
        "profile_name_en": "Test Cafe",
        "profile_city_ru": "Кишинев",
        "profile_city_ro": "Chisinau",
        "profile_city_en": "Chisinau",
        "contact_phone": "+373 22 123456",
        "contact_email": "test@example.md",
        "contact_address_ru": "Stefan cel Mare 1",
        "contact_map_url": "https://maps.example.com/test",
    }
    r = client.post(
        "/admin/profile", data=payload, headers=_auth(), follow_redirects=False
    )
    assert r.status_code in (302, 303)
    assert data_path.exists()
    from showcases.cafe.product_app import _make_contact_for_lang
    import importlib
    import showcases.cafe.services.cafe_profile_service as prof_mod

    importlib.reload(prof_mod)
    import showcases.cafe.product_app as pa

    importlib.reload(pa)
    ctx = pa._make_contact_for_lang("ru")
    assert ctx is not None
    assert "Stefan cel Mare" in ctx["address"] or "+373" in (ctx.get("phone") or "")


def test_contact_optional_no_fake_tel():
    from showcases.cafe.product_app import _make_contact_for_lang

    ctx = _make_contact_for_lang("ru")
    if ctx and ctx.get("phone"):
        assert "123 456" not in ctx.get("phone", "")
        assert "example" not in ctx.get("phone", "").lower()
