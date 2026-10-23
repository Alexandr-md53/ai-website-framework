"""Admin UI: localization (RU/RO/EN), admin-link visibility, password toggle,
image-upload behaviour and logo placement.

Covered:

1. admin pages are localized and the language switcher drives the admin UI;
2. the admin UI language works even when the shop itself has a single language;
3. the "Admin" link is rendered for a signed-in administrator only;
4. the login form has a working password show/hide control;
5. the logo upload form exists on the settings page only;
6. the new-product page explains that images are uploaded after saving;
7. image uploads use a URL-encoded query parameter for the original name, so
   non-ASCII names (e.g. Cyrillic) no longer break the request;
8. PNG and JPEG uploads both work through the pipeline.
"""
from __future__ import annotations

import io
import re

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.i18n import ADMIN_LANGUAGES, UI

try:
    from PIL import Image as PILImage

    HAS_PILLOW = True
except Exception:  # pragma: no cover
    PILImage = None
    HAS_PILLOW = False

PASSWORD = "admin-ui-pass"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')

ADMIN_PAGES = (
    "/admin",
    "/admin/categories",
    "/admin/categories/new",
    "/admin/products",
    "/admin/products/new",
    "/admin/pages",
    "/admin/pages/new",
    "/admin/settings",
)


def _png(width=8, height=8, colour=(10, 90, 40)) -> bytes:
    if not HAS_PILLOW:
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), colour).save(buffer, "PNG")
    return buffer.getvalue()


def _jpeg(width=8, height=8) -> bytes:
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), (120, 30, 30)).save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.fixture
def admin_config():
    return AdminConfig(
        username="owner",
        password_hash=hash_password(PASSWORD, iterations=1000),
        secret_key=b"admin-ui-secret",
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
    assert client.post(
        "/admin/login", data={"username": admin_config.username, "password": PASSWORD}
    ).status_code == 303
    return CSRF_RE.search(client.get("/admin").text).group(1)


# --- 1./2. localization ---------------------------------------------------


@pytest.mark.parametrize("lang", ADMIN_LANGUAGES)
def test_every_admin_page_renders_in_every_admin_language(client, admin_config, lang):
    _login(client, admin_config)
    admin_ui = UI[lang]["admin"]
    labels = [value for value in admin_ui.values() if value]
    for path in ADMIN_PAGES:
        response = client.get(f"{path}?lang={lang}")
        assert response.status_code == 200, (path, lang, response.status_code)
        # at least one label of this language must appear on every admin page
        assert any(label in response.text for label in labels), (path, lang)
    if lang == "ru":
        # and no English admin label leaks into the Russian panel
        for english_only in ("Create category", "Delete product", "Save settings", "New page"):
            assert english_only not in client.get("/admin?lang=ru").text


def test_admin_language_switch_changes_labels(client, admin_config):
    _login(client, admin_config)
    for lang, marker in (("ru", "Товары"), ("ro", "Produse"), ("en", "Products")):
        body = client.get(f"/admin/products?lang={lang}").text
        assert marker in body, (lang, marker)
    # no mixed languages: the English label is absent from the Russian page
    assert "Products" not in client.get("/admin/products?lang=ru").text


def test_admin_ui_language_is_independent_of_shop_languages(client, admin_config, app):
    csrf = _login(client, admin_config)
    # the shop keeps a single content language
    saved = client.post(
        "/admin/settings",
        data={
            "csrf": csrf,
            "shop_name": "Один язык",
            "language_code_0": "ru",
            "language_title_0": "Русский",
            "default_language": "ru",
        },
    )
    assert saved.status_code == 303
    assert app.state.catalog.get_settings().language_codes == ("ru",)

    # ... but the admin panel can still be switched to English
    assert "Products" in client.get("/admin/products?lang=en").text
    assert "Produse" in client.get("/admin/products?lang=ro").text


def test_public_site_ui_is_untouched(client):
    assert "Все категории" in client.get("/catalog?lang=ru").text
    assert "Toate categoriile" in client.get("/catalog?lang=ro").text
    assert "All categories" in client.get("/catalog?lang=en").text


# --- 3. admin link visibility --------------------------------------------


def test_admin_link_is_hidden_for_visitors_and_shown_for_admin(client, admin_config):
    anonymous = client.get("/").text
    assert 'href="/admin"' not in anonymous
    assert 'href="/admin/login"' not in anonymous
    assert 'href="/catalog?' in anonymous

    _login(client, admin_config)
    authenticated = client.get("/").text
    assert 'href="/admin"' in authenticated


# --- 4. password toggle --------------------------------------------------


def test_login_page_has_password_toggle(client):
    body = client.get("/admin/login").text
    assert 'id="password-toggle"' in body
    assert 'id="password"' in body and 'type="password"' in body
    assert "password-toggle" in body and "addEventListener" in body


# --- 5. logo only on settings -------------------------------------------


def test_logo_form_is_only_on_the_settings_page(client, admin_config):
    _login(client, admin_config)
    assert 'id="logo-form"' in client.get("/admin/settings").text
    for path in ("/admin", "/admin/categories", "/admin/products", "/admin/products/new", "/admin/pages"):
        assert 'id="logo-form"' not in client.get(path).text, path


# --- 6./7. product image upload -----------------------------------------


def test_new_product_page_explains_that_images_come_after_saving(client, admin_config, app):
    csrf = _login(client, admin_config)
    new_page = client.get("/admin/products/new?lang=en").text
    assert 'id="upload-form"' not in new_page
    assert UI["en"]["admin"]["images_after_save"] in new_page

    client.post("/admin/categories/new", data={"csrf": csrf, "slug": "c1", "name_ru": "К1", "is_published": "1"})
    assert client.post(
        "/admin/products/new",
        data={"csrf": csrf, "slug": "p1", "name_ru": "Т1", "price": "1.00", "currency": "MDL", "is_published": "1"},
    ).status_code == 303
    edit_page = client.get("/admin/products/1").text
    assert 'id="upload-form"' in edit_page
    # the original name travels URL-encoded in the query string
    assert "?name=' + encodeURIComponent(file.name)" in edit_page


def test_image_upload_accepts_png_jpeg_and_unicode_names(client, admin_config, app, paths):
    csrf = _login(client, admin_config)
    client.post("/admin/categories/new", data={"csrf": csrf, "slug": "c1", "name_ru": "К1", "is_published": "1"})
    client.post(
        "/admin/products/new",
        data={"csrf": csrf, "slug": "p1", "name_ru": "Т1", "price": "1.00", "currency": "MDL", "is_published": "1"},
    )

    if HAS_PILLOW:
        unicode_name = "фото товара.png"
        encoded = "%D1%84%D0%BE%D1%82%D0%BE%20%D1%82%D0%BE%D0%B2%D0%B0%D1%80%D0%B0.png"
        response = client.post(
            f"/admin/products/1/images?name={encoded}",
            content=_png(1600, 1200),
            headers={"Content-Type": "image/png", "X-CSRF-Token": csrf},
        )
        assert response.status_code == 303, response.text
        image = app.state.catalog.get_product(1).images[-1]
        assert image.original_name == unicode_name
        assert image.catalog_name.endswith("_catalog.png") and image.detail_name.endswith("_detail.png")
        assert (paths and image.file_name.endswith(".png"))

        jpeg = client.post(
            "/admin/products/1/images?name=photo.jpg",
            content=_jpeg(1600, 1200),
            headers={"Content-Type": "image/jpeg", "X-CSRF-Token": csrf},
        )
        assert jpeg.status_code == 303, jpeg.text
        assert app.state.catalog.get_product(1).images[-1].file_name.endswith(".jpg")

    # limits and type checks stay intact
    assert client.post(
        "/admin/products/1/images",
        content=b"#!/bin/sh\n",
        headers={"Content-Type": "image/png", "X-CSRF-Token": csrf},
    ).status_code == 400
