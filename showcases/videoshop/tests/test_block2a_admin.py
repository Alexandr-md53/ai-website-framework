"""Block 2a: category photos, admin search/filter and create_app hardening.

Covers:

1. the category form shows the current photo and an upload control; uploading
   stores a managed image and redirects back to the form;
2. the category list shows a thumbnail column and falls back to the packaged
   photo for a category without an upload;
3. the home page category grid resolves: uploaded → packaged guess → placeholder;
4. ``/admin/categories?q=`` filters by name/slug (LIKE) and keeps the term;
5. ``/admin/products?q=&category_id=`` filters by name and category together;
6. ``create_app()`` without a file database raises ``StoragePathMissing``.
"""
from __future__ import annotations

import io
import re

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.infrastructure.storage import StoragePathMissing
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app, category_photo

try:
    from PIL import Image as PILImage

    HAS_PILLOW = True
except Exception:  # pragma: no cover
    PILImage = None
    HAS_PILLOW = False

PASSWORD = "block2a-pass"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')


def _jpeg(width=640, height=480) -> bytes:
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), (30, 60, 140)).save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.fixture
def admin_config():
    return AdminConfig(
        username="owner",
        password_hash=hash_password(PASSWORD, iterations=1000),
        secret_key=b"block2a-secret",
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


def _make_category(client, csrf, slug, name, image=None) -> int:
    data = {"csrf": csrf, "slug": slug, "name_ru": name, "is_published": "1"}
    if image:
        data["image"] = image
    assert client.post("/admin/categories/new", data=data).status_code == 303
    return 1


# --- 1. category photo in the admin form ---------------------------------


def test_category_form_shows_photo_block_and_preview(client, admin_config, app):
    csrf = _login(client, admin_config)
    _make_category(client, csrf, "cameras", "Камеры")

    form = client.get("/admin/categories/1").text
    assert 'id="category-photo-form"' in form
    assert 'id="category-photo"' in form and 'type="file"' in form
    assert "/admin/categories/1/image?name=" in form
    # no upload yet: preview falls back to the placeholder
    assert "/media/placeholder.jpg" in form


def test_uploaded_category_photo_is_stored_and_shown(client, admin_config, app):
    csrf = _login(client, admin_config)
    _make_category(client, csrf, "cameras", "Камеры")
    if not HAS_PILLOW:
        pytest.skip("Pillow is required for a real upload")

    response = client.post(
        "/admin/categories/1/image?name=%D0%BA%D0%B0%D0%BC%D0%B5%D1%80%D1%8B.jpg",
        content=_jpeg(),
        headers={"Content-Type": "image/jpeg", "X-CSRF-Token": csrf},
    )
    assert response.status_code == 303
    stored = app.state.catalog.get_category(1).image
    assert stored.endswith(".jpg") and stored != "category-camera.jpg"
    assert client.get(f"/media/{stored}").status_code == 200
    # the form now previews the managed file
    assert f'/media/{stored}' in client.get("/admin/categories/1").text


# --- 2. thumbnail column in the list ------------------------------------


def test_category_list_has_preview_column_with_packaged_fallback(client, admin_config):
    csrf = _login(client, admin_config)
    _make_category(client, csrf, "cameras", "Камеры")
    listing = client.get("/admin/categories").text
    assert "thumb-cell" in listing
    # no upload: the packaged camera photo is used as the fallback
    assert "/media/category-camera.jpg" in listing
    assert 'width:60px' in listing or "thumb-cell" in listing


# --- 3. photo resolution order -----------------------------------------


def test_category_photo_resolution_order():
    from showcases.videoshop.domain.catalog import Category, CategoryText

    def make(slug, names, image=""):
        return Category(
            id=1,
            slug=slug,
            is_published=True,
            position=0,
            texts={lang: CategoryText(lang=lang, name=name) for lang, name in names.items()},
            image=image,
        )

    assert category_photo(make("anything", {"ru": "X"}, image="abc.jpg")) == "abc.jpg"
    assert category_photo(make("cameras", {"ru": "Камеры"})) == "category-camera.jpg"
    assert category_photo(make("objektivy", {"ru": "Объективы"})) == "category-lens.jpg"
    assert category_photo(make("svet", {"ru": "Свет"})) == "category-light.jpg"
    assert category_photo(make("zvuk", {"ru": "Звук"})) == "category-mic.png"
    assert category_photo(make("shtativy", {"ru": "Штативы"})) == "category-tripod.jpg"
    assert category_photo(make("stabilizatory", {"ru": "Стабилизаторы"})) == "category-gimbal.jpg"
    assert category_photo(make("unknown", {"ru": "Прочее"})) == "placeholder.jpg"


def test_home_page_uses_category_photo_fallback(client, admin_config):
    csrf = _login(client, admin_config)
    _make_category(client, csrf, "cameras", "Камеры")
    client.post("/admin/logout")
    home = client.get("/").text
    assert "/media/category-camera.jpg" in home
    assert "/media/placeholder.jpg" in home  # product cards still have no photo


# --- 4. category search -------------------------------------------------


def test_category_search_filters_by_name_and_keeps_the_term(client, admin_config):
    csrf = _login(client, admin_config)
    _make_category(client, csrf, "cameras", "Камеры")
    client.post("/admin/categories/new", data={"csrf": csrf, "slug": "svet", "name_ru": "Свет", "is_published": "1"})

    found = client.get("/admin/categories?q=камер").text
    assert "Камеры" in found and "Свет" not in found
    assert 'value="камер"' in found  # the term is echoed back

    by_slug = client.get("/admin/categories?q=svet").text
    assert "Свет" in by_slug and "Камеры" not in by_slug

    assert "Камеры" in client.get("/admin/categories").text  # no filter → all


# --- 5. product search + category filter --------------------------------


def test_product_search_and_category_filter_combine(client, admin_config, app):
    csrf = _login(client, admin_config)
    _make_category(client, csrf, "cameras", "Камеры")
    client.post("/admin/categories/new", data={"csrf": csrf, "slug": "svet", "name_ru": "Свет", "is_published": "1"})
    client.post(
        "/admin/products/new",
        data={"csrf": csrf, "slug": "cam-1", "name_ru": "Камера X", "price": "10.00", "currency": "MDL",
              "category_id": "1", "is_published": "1"},
    )
    client.post(
        "/admin/products/new",
        data={"csrf": csrf, "slug": "light-1", "name_ru": "Панель Y", "price": "20.00", "currency": "MDL",
              "category_id": "2", "is_published": "1"},
    )

    everything = client.get("/admin/products").text
    assert "Камера X" in everything and "Панель Y" in everything

    searched = client.get("/admin/products?q=камера").text
    assert "Камера X" in searched and "Панель Y" not in searched

    filtered = client.get("/admin/products?category_id=2").text
    assert "Панель Y" in filtered and "Камера X" not in filtered

    combined = client.get("/admin/products?q=камера&category_id=2").text
    assert "Камера X" not in combined and "Панель Y" not in combined

    # the select and the search field keep their state
    assert 'value="камера"' in combined
    assert 'value="2" selected' in client.get("/admin/products?category_id=2").text


# --- 6. create_app hardening -------------------------------------------


def test_create_app_without_db_path_raises_storage_path_missing():
    with pytest.raises(StoragePathMissing):
        create_app()
    with pytest.raises(StoragePathMissing):
        create_app(db_path=":memory:")


def test_create_app_still_works_with_a_file_path(paths, admin_config):
    app = create_app(**paths, admin_config=admin_config)
    assert TestClient(app).get("/").status_code == 200
