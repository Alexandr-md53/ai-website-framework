"""Settings and informational pages: admin-managed, no code editing required.

Covered:

1. the owner edits shop name/tagline/description/contacts/social links and sees
   them on the public site;
2. the logo is uploaded through the browser (raw body) and rendered from the
   managed image directory, also after a restart;
3. site-wide SEO settings are injected by the framework ``SeoInjector``;
4. invalid social links are refused without side effects;
5. informational pages: create/edit/publish/unpublish/delete through the admin;
6. page texts are per language and follow the configured languages;
7. a renamed page slug redirects (301) from the historical URL;
8. settings and pages survive an application restart;
9. every mutating route requires authentication and a CSRF token;
10. demo seeding never overwrites owner settings or pages.

Only temporary databases/images under ``tmp_path`` are used.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app

try:
    from PIL import Image as PILImage

    HAS_PILLOW = True
except Exception:  # pragma: no cover
    PILImage = None
    HAS_PILLOW = False


def _png(width=24, height=24, colour=(20, 90, 160)) -> bytes:
    if not HAS_PILLOW:
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), colour).save(buffer, "PNG")
    return buffer.getvalue()


PASSWORD = "owner-password"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')


@pytest.fixture
def admin_config():
    return AdminConfig(
        username="owner",
        password_hash=hash_password(PASSWORD, iterations=1000),
        secret_key=b"settings-test-secret",
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


@pytest.fixture
def app(paths, admin_config):
    return create_app(**paths, admin_config=admin_config)


@pytest.fixture
def client(app):
    return TestClient(app, follow_redirects=False)


def _login(client, admin_config) -> str:
    response = client.post(
        "/admin/login", data={"username": admin_config.username, "password": PASSWORD}
    )
    assert response.status_code == 303
    return CSRF_RE.search(client.get("/admin").text).group(1)


SETTINGS = {
    "shop_name": "Nordic Photo",
    "tagline": "Cameras and light",
    "shop_description": "A small shop for photographers",
    "contact_email": "hello@nordic.example",
    "contact_phone": "+373 600 00 000",
    "contact_address": "Chisinau, Test street 1",
    "default_currency": "EUR",
    "social_facebook": "https://facebook.com/nordicphoto",
    "social_instagram": "https://instagram.com/nordicphoto",
    "social_telegram": "https://t.me/nordicphoto",
    "seo_title": "Nordic Photo — cameras",
    "seo_description": "Buy cameras and lenses in Chisinau",
}


# --- 1./3./4. settings ---------------------------------------------------


def test_settings_are_editable_and_visible_on_the_public_site(client, admin_config, app):
    csrf = _login(client, admin_config)
    saved = client.post("/admin/settings", data={"csrf": csrf, **SETTINGS})
    assert saved.status_code == 303

    settings = app.state.catalog.get_settings()
    assert settings.name == "Nordic Photo"
    assert settings.tagline == "Cameras and light"
    assert settings.default_currency == "EUR"
    assert settings.social_telegram == "https://t.me/nordicphoto"

    home = client.get("/")
    assert home.status_code == 200
    assert "Nordic Photo" in home.text
    assert "Cameras and light" in home.text
    assert "hello@nordic.example" in home.text
    assert "https://instagram.com/nordicphoto" in home.text
    assert 'meta name="description" content="Buy cameras and lenses in Chisinau"' in home.text
    assert 'property="og:title" content="Nordic Photo — cameras"' in home.text


def test_invalid_social_link_is_refused(client, admin_config, app):
    csrf = _login(client, admin_config)
    response = client.post(
        "/admin/settings",
        data={"csrf": csrf, "shop_name": "X", "social_facebook": "javascript:alert(1)"},
    )
    assert response.status_code == 400
    assert app.state.catalog.get_settings().social_facebook == ""
    assert app.state.catalog.get_settings().name == ""


def test_logo_upload_and_display_survives_restart(client, admin_config, app, paths):
    csrf = _login(client, admin_config)
    upload = client.post(
        "/admin/settings/logo",
        content=_png(),
        headers={"Content-Type": "image/png", "X-File-Name": "logo.png", "X-CSRF-Token": csrf},
    )
    assert upload.status_code == 303, upload.text
    logo = app.state.catalog.get_settings().logo
    assert re.match(r"^[0-9a-f]{32}\.png$", logo)
    assert (Path(paths["images_dir"]) / logo).is_file()
    assert f'<img class="logo" src="/media/{logo}"' in client.get("/").text
    assert client.get(f"/media/{logo}").status_code == 200

    restarted = TestClient(create_app(**paths, admin_config=admin_config), follow_redirects=False)
    assert f'<img class="logo" src="/media/{logo}"' in restarted.get("/").text
    assert restarted.get(f"/media/{logo}").status_code == 200


def test_settings_survive_restart(client, admin_config, app, paths):
    csrf = _login(client, admin_config)
    client.post("/admin/settings", data={"csrf": csrf, **SETTINGS})

    restarted = TestClient(create_app(**paths, admin_config=admin_config), follow_redirects=False)
    page = restarted.get("/")
    assert "Nordic Photo" in page.text and "Cameras and light" in page.text
    assert "hello@nordic.example" in page.text


# --- 5./6./7./8. informational pages -------------------------------------


def test_pages_crud_languages_and_public_visibility(client, admin_config, app):
    csrf = _login(client, admin_config)
    created = client.post(
        "/admin/pages/new",
        data={
            "csrf": csrf,
            "slug": "about",
            "title_ru": "О магазине",
            "body_ru": "Мы продаём камеры.",
            "title_en": "About us",
            "body_en": "We sell cameras.",
            "is_published": "1",
        },
    )
    assert created.status_code == 303, created.text
    page = app.state.catalog.list_pages()[0]
    assert page.slug == "about"

    assert "Мы продаём камеры." in client.get("/page/about?lang=ru").text
    assert "We sell cameras." in client.get("/page/about?lang=en").text
    # the page appears in the public footer navigation
    assert 'href="/page/about?lang=ru"' in client.get("/").text
    assert "О магазине" in client.get("/catalog?lang=ru").text

    edited = client.post(
        f"/admin/pages/{page.id}",
        data={
            "csrf": csrf,
            "slug": "about",
            "title_ru": "О нас",
            "body_ru": "Обновлённый текст.",
            "is_published": "1",
        },
    )
    assert edited.status_code == 303
    assert "Обновлённый текст." in client.get("/page/about?lang=ru").text


def test_unpublished_page_is_hidden_and_can_be_published(client, admin_config, app):
    csrf = _login(client, admin_config)
    client.post(
        "/admin/pages/new",
        data={"csrf": csrf, "slug": "delivery", "title_ru": "Доставка", "body_ru": "Доставка 2 дня", "is_published": "1"},
    )
    page = app.state.catalog.list_pages()[0]

    assert client.post(
        f"/admin/pages/{page.id}/publish", data={"csrf": csrf, "published": "0"}
    ).status_code == 303
    assert client.get("/page/delivery").status_code == 404
    assert 'href="/page/delivery' not in client.get("/").text

    assert client.post(
        f"/admin/pages/{page.id}/publish", data={"csrf": csrf, "published": "1"}
    ).status_code == 303
    assert client.get("/page/delivery").status_code == 200


def test_page_slug_history_redirects(client, admin_config, app):
    csrf = _login(client, admin_config)
    client.post(
        "/admin/pages/new",
        data={"csrf": csrf, "slug": "contacts", "title_ru": "Контакты", "is_published": "1"},
    )
    page = app.state.catalog.list_pages()[0]
    renamed = client.post(
        f"/admin/pages/{page.id}",
        data={"csrf": csrf, "slug": "contact-us", "title_ru": "Контакты", "is_published": "1"},
    )
    assert renamed.status_code == 303

    redirect = client.get("/page/contacts")
    assert redirect.status_code == 301
    assert redirect.headers["location"] == "/page/contact-us"
    assert client.get("/page/contact-us").status_code == 200


def test_page_delete_releases_the_slug(client, admin_config, app):
    csrf = _login(client, admin_config)
    client.post(
        "/admin/pages/new",
        data={"csrf": csrf, "slug": "terms", "title_ru": "Условия", "is_published": "1"},
    )
    page = app.state.catalog.list_pages()[0]
    deleted = client.post(f"/admin/pages/{page.id}/delete", data={"csrf": csrf})
    assert deleted.status_code == 303
    assert client.get("/page/terms").status_code == 404
    assert app.state.catalog.list_pages() == []
    row = app.state.catalog._registry.get("page", "terms")
    assert row is not None and row["state"] == "released"


def test_pages_and_settings_survive_restart(client, admin_config, app, paths):
    csrf = _login(client, admin_config)
    client.post("/admin/settings", data={"csrf": csrf, **SETTINGS})
    client.post(
        "/admin/pages/new",
        data={"csrf": csrf, "slug": "about", "title_ru": "О магазине", "body_ru": "Текст", "is_published": "1"},
    )

    restarted = TestClient(create_app(**paths, admin_config=admin_config), follow_redirects=False)
    assert restarted.get("/page/about").status_code == 200
    assert "О магазине" in restarted.get("/page/about").text
    assert "Nordic Photo" in restarted.get("/").text


# --- 9./10. protection and demo seeding ----------------------------------


def test_mutations_require_authentication_and_csrf(client, admin_config, app):
    for path, payload in (
        ("/admin/settings", {"csrf": "x", "shop_name": "Hacked"}),
        ("/admin/pages/new", {"csrf": "x", "slug": "hack", "title_ru": "Hack"}),
    ):
        assert client.post(path, data=payload).status_code == 401

    csrf = _login(client, admin_config)
    without_csrf = client.post("/admin/pages/new", data={"slug": "csrf-free", "title_ru": "X"})
    assert without_csrf.status_code == 403
    assert app.state.catalog.list_pages() == []
    assert client.post("/admin/settings", data={"shop_name": "No CSRF"}).status_code == 403
    assert app.state.catalog.get_settings().name == ""
    # the logo upload route also requires the CSRF header
    assert client.post(
        "/admin/settings/logo", content=_png(), headers={"Content-Type": "image/png"}
    ).status_code == 403


def test_invalid_page_input_is_refused(client, admin_config, app):
    csrf = _login(client, admin_config)
    empty_title = client.post(
        "/admin/pages/new", data={"csrf": csrf, "slug": "empty", "title_ru": "", "body_ru": "text"}
    )
    assert empty_title.status_code == 400
    # a slug that cannot be normalised to the strict slug grammar is refused
    # (a merely untidy slug such as "About Us" is normalised to "about-us",
    # exactly like product and category slugs)
    bad_slug = client.post(
        "/admin/pages/new",
        data={"csrf": csrf, "slug": "!!!", "title_ru": "Title", "is_published": "1"},
    )
    assert bad_slug.status_code == 400
    assert app.state.catalog.list_pages() == []


def test_demo_seed_does_not_overwrite_settings_or_pages(client, admin_config, app, paths):
    csrf = _login(client, admin_config)
    client.post("/admin/settings", data={"csrf": csrf, **SETTINGS})
    client.post(
        "/admin/pages/new",
        data={"csrf": csrf, "slug": "about", "title_ru": "Моя страница", "is_published": "1"},
    )

    assert app.state.catalog.seed_demo_catalog() == 0
    assert app.state.catalog.get_settings().name == "Nordic Photo"
    pages = app.state.catalog.list_pages()
    assert [page.text("ru").title for page in pages] == ["Моя страница"]
