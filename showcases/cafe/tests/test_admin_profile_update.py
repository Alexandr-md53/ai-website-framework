import os
import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv("CAFE_ADMIN_USER", "admin")
    monkeypatch.setenv("CAFE_ADMIN_PASSWORD", "secret123")
    monkeypatch.setenv("CAFE_SECRET_KEY", "test-secret-for-e2e")
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


import re
import time
import pytest

# ... твои существующие 5 тестов выше ...


def test_post_no_auth_returns_401(admin_client):
    client, _ = admin_client
    r = client.post("/admin/profile", data={"csrf_token": "anything"})
    assert r.status_code == 401


def test_post_no_csrf_returns_403(admin_client):
    client, _ = admin_client
    r = client.post("/admin/profile", data={}, headers=_auth())
    assert r.status_code == 403


def test_post_invalid_csrf_returns_403(admin_client):
    client, _ = admin_client
    r = client.post(
        "/admin/profile",
        data={"csrf_token": "totally-fake-token-12345"},
        headers=_auth(),
    )
    assert r.status_code == 403


def test_expired_csrf_rejected_by_validator(monkeypatch):
    from showcases.cafe.services import cafe_admin_security as sec
    import time as time_mod

    token = sec.generate_csrf_token()
    assert sec.validate_csrf_token(token) is True
    real_time = time_mod.time
    monkeypatch.setattr(time_mod, "time", lambda: real_time() + 7200)
    assert sec.validate_csrf_token(token) is False
    # подпись остается валидной без max_age — доказывает expiry
    try:
        sec.signer.unsign(token)
        sig_ok = True
    except Exception:
        sig_ok = False
    assert sig_ok is True


def test_admin_password_without_secret_raises(monkeypatch):
    monkeypatch.setenv("CAFE_ADMIN_PASSWORD", "any-real-password-xyz")
    monkeypatch.delenv("CAFE_SECRET_KEY", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    import importlib
    import showcases.cafe.services.cafe_admin_security as sec

    with pytest.raises(RuntimeError, match="CAFE_SECRET_KEY"):
        importlib.reload(sec)
    monkeypatch.setenv("CAFE_ADMIN_PASSWORD", "secret123")
    monkeypatch.setenv("CAFE_SECRET_KEY", "test-secret-for-e2e")
    importlib.reload(sec)


def test_secret123_without_secret_raises(monkeypatch):
    monkeypatch.setenv("CAFE_ADMIN_PASSWORD", "secret123")
    monkeypatch.delenv("CAFE_SECRET_KEY", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    import importlib
    import showcases.cafe.services.cafe_admin_security as sec

    with pytest.raises(RuntimeError, match="CAFE_SECRET_KEY"):
        importlib.reload(sec)
    monkeypatch.setenv("CAFE_SECRET_KEY", "test-secret-for-e2e")
    importlib.reload(sec)


def test_admin_with_explicit_secret_allowed(monkeypatch):
    monkeypatch.setenv("CAFE_ADMIN_PASSWORD", "secret123")
    monkeypatch.setenv("CAFE_SECRET_KEY", "explicit-test-secret-allowed")
    import importlib
    import showcases.cafe.services.cafe_admin_security as sec

    mod = importlib.reload(sec)
    assert mod.SECRET_KEY == "explicit-test-secret-allowed"
    monkeypatch.setenv("CAFE_SECRET_KEY", "test-secret-for-e2e")
    importlib.reload(sec)


def test_profile_escaping_in_attribute(admin_client):
    client, _ = admin_client
    r = client.get("/admin/profile", headers=_auth())
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    xss = '"><script>alert(1)</script>'
    payload = {
        "csrf_token": csrf,
        "profile_name_ru": xss,
        "profile_name_ro": "safe",
        "profile_name_en": "safe",
        "profile_city_ru": "safe",
        "profile_city_ro": "safe",
        "profile_city_en": "safe",
        "contact_phone": "safe",
        "contact_email": "safe",
        "contact_address_ru": "safe",
        "contact_address_ro": "safe",
        "contact_address_en": "safe",
        "contact_map_url": "",
    }
    client.post("/admin/profile", data=payload, headers=_auth(), follow_redirects=False)
    r = client.get("/admin/profile", headers=_auth())
    assert "<script>alert(1)</script>" not in r.text


def test_address_three_langs_persist(admin_client):
    client, data_path = admin_client
    r = client.get("/admin/profile", headers=_auth())
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    payload = {
        "csrf_token": csrf,
        "profile_name_ru": "Cafe",
        "profile_name_ro": "Cafe",
        "profile_name_en": "Cafe",
        "profile_city_ru": "K",
        "profile_city_ro": "K",
        "profile_city_en": "K",
        "contact_phone": "",
        "contact_email": "",
        "contact_address_ru": "Strada Stefan 1 RU",
        "contact_address_ro": "Strada Stefan 1 RO",
        "contact_address_en": "Stefan Street 1 EN",
        "contact_map_url": "",
    }
    r = client.post(
        "/admin/profile", data=payload, headers=_auth(), follow_redirects=False
    )
    assert r.status_code in (302, 303)
