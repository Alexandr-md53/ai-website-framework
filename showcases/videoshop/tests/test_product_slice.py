"""Product-slice tests: admin panel, catalog, images, persistence, safety.

Covered (approved product-slice scope):

1. unauthenticated and CSRF-less mutations are refused;
2. a missing configuration disables the admin area (no default password);
3. login rejects wrong credentials and issues a signed session cookie;
4. the full admin flow: category -> product (name/description/price/currency/
   category/attributes) -> image upload -> public catalog and product page;
5. editing price/description and managing images is visible on the public site;
6. data (and uploaded files) survive an application restart;
7. unpublished products are hidden and can be published again;
8. deleting a product releases its slug and keeps other products intact;
9. deleting a category that still holds products is refused; with an explicit
   reassignment the products survive and keep valid links;
10. upload validation: wrong content type and oversize files are refused;
11. safe names/paths: stored names are generated, traversal names are rejected;
12. demo data never overwrites a user catalog;
13. exact money semantics (integer minor units, no float);
14. multilingual content per configured language, with a configurable default;
15. historical slugs redirect (301) to the current one;
16. languages are configurable data, not code.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.domain.catalog import Money, ValidationError
from showcases.videoshop.infrastructure.image_store import (
    IMAGE_PRESETS,
    ImageStore,
    InvalidImageName,
    UnsupportedImageType,
)
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app
from showcases.videoshop.services.catalog import slugify

try:
    from PIL import Image as PILImage

    HAS_PILLOW = True
except Exception:  # pragma: no cover - only without Pillow
    PILImage = None
    HAS_PILLOW = False


def _image_bytes(width=8, height=8, colour=(200, 30, 30), fmt="PNG") -> bytes:
    """A real image when Pillow is present, otherwise the magic-byte minimum."""
    if not HAS_PILLOW:
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), colour).save(buffer, fmt)
    return buffer.getvalue()


PNG = _image_bytes()
PNG_SECOND = _image_bytes(10, 10, (10, 120, 200))
PASSWORD = "correct-horse-battery"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')


@pytest.fixture
def admin_config():
    # a low iteration count keeps the tests fast; production uses the default
    return AdminConfig(
        username="owner",
        password_hash=hash_password(PASSWORD, iterations=1000),
        secret_key=b"unit-test-secret-key",
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


def _login(client, admin_config):
    response = client.post(
        "/admin/login",
        data={"username": admin_config.username, "password": PASSWORD},
    )
    assert response.status_code == 303, response.text
    page = client.get("/admin")
    assert page.status_code == 200
    return CSRF_RE.search(page.text).group(1)


def _open_app(paths, admin_config):
    """A second application instance on the same files (a process restart)."""
    return TestClient(create_app(**paths, admin_config=admin_config), follow_redirects=False)


def _create_category(client, csrf, name="Cameras", slug="cameras", lang="ru"):
    return client.post(
        "/admin/categories/new",
        data={
            "csrf": csrf,
            "slug": slug,
            f"name_{lang}": name,
            f"description_{lang}": "Photo gear",
            "is_published": "1",
        },
    )


def _create_product(client, csrf, *, slug, name, price, category_id, attributes=None, lang="ru"):
    data = {
        "csrf": csrf,
        "slug": slug,
        f"name_{lang}": name,
        f"description_{lang}": f"{name} description",
        "price": price,
        "currency": "MDL",
        "category_id": "" if category_id is None else str(category_id),
        "is_published": "1",
    }
    for index, (attr_name, attr_value) in enumerate(attributes or ()):
        # block 3b-1-fix-TABLE: the table stores the English (master) column
        # first, so a flat list of pairs fills group 0..n of the master column
        slot = index * 3
        data[f"attribute_lang_{slot}"] = "en"
        data[f"attribute_name_{slot}"] = attr_name
        data[f"attribute_value_{slot}"] = attr_value
    return client.post("/admin/products/new", data=data)


# --- 1./2./3. authentication ----------------------------------------------


def test_unauthenticated_mutations_are_refused_and_change_nothing(client, app):
    assert client.get("/admin").status_code == 303  # redirected to the login page

    for path, payload in (
        ("/admin/categories/new", {"csrf": "x", "slug": "nope", "name_ru": "Nope"}),
        ("/admin/products/new", {"csrf": "x", "slug": "nope", "price": "1"}),
        ("/admin/settings", {"csrf": "x", "shop_name": "Hacked"}),
    ):
        response = client.post(path, data=payload)
        assert response.status_code == 401, (path, response.status_code)

    catalog = app.state.catalog
    assert catalog.list_products() == []
    assert catalog.list_categories() == []
    assert catalog.get_settings().name == ""


def test_admin_is_disabled_without_configuration(paths):
    disabled = TestClient(
        create_app(**paths, admin_config=None, env={}), follow_redirects=False
    )
    assert disabled.get("/admin/login").status_code == 503
    assert disabled.post("/admin/login", data={"username": "a", "password": "b"}).status_code == 503
    assert disabled.get("/admin").status_code == 503
    assert disabled.post("/admin/categories/new", data={"csrf": "x"}).status_code == 503


def test_login_rejects_wrong_credentials(client, admin_config):
    bad = client.post("/admin/login", data={"username": admin_config.username, "password": "wrong"})
    assert bad.status_code == 401
    bad_user = client.post("/admin/login", data={"username": "someone", "password": PASSWORD})
    assert bad_user.status_code == 401
    assert client.get("/admin").status_code == 303


def test_csrf_is_required_for_mutations(client, admin_config, app):
    _login(client, admin_config)
    response = client.post("/admin/categories/new", data={"slug": "no-csrf", "name_ru": "X"})
    assert response.status_code == 403
    assert app.state.catalog.list_categories() == []


# --- 4./5./6. the full flow ----------------------------------------------


def test_full_admin_flow_creates_catalog_with_image(client, admin_config, app, paths):
    csrf = _login(client, admin_config)

    assert _create_category(client, csrf).status_code == 303
    category = app.state.catalog.list_categories()[0]
    assert category.slug == "cameras"

    created = _create_product(
        client,
        csrf,
        slug="camera-x100",
        name="Camera X100",
        price="1299.90",
        category_id=category.id,
        attributes=[("Sensor", "APS-C"), ("Video", "4K")],
    )
    assert created.status_code == 303
    product = app.state.catalog.list_products()[0]
    assert product.price == Money(minor=129990, currency="MDL")
    assert product.attributes == (("Sensor", "APS-C"), ("Video", "4K"))

    upload = client.post(
        f"/admin/products/{product.id}/images",
        content=PNG,
        headers={
            "Content-Type": "image/png",
            "X-File-Name": "photo.png",
            "X-CSRF-Token": csrf,
        },
    )
    assert upload.status_code == 303, upload.text
    stored = app.state.catalog.get_product(product.id).images
    assert len(stored) == 1 and stored[0].content_type == "image/png"

    public = client.get("/product/camera-x100")
    assert public.status_code == 200
    assert "Camera X100" in public.text
    assert "1299.90 MDL" in public.text
    assert "APS-C" in public.text
    assert f"/media/{stored[0].detail_name or stored[0].file_name}" in public.text

    media = client.get(f"/media/{stored[0].file_name}")
    assert media.status_code == 200
    assert media.content.startswith(b"\x89PNG"), "the stored file is a normalised image"

    # products are listed on the catalogue page (the home page shows no
    # product showcase since block 2b-FIX)
    catalog_page = client.get("/catalog")
    assert "Camera X100" in catalog_page.text


def test_editing_price_description_and_images_is_visible(client, admin_config, app, paths):
    csrf = _login(client, admin_config)
    _create_category(client, csrf)
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="edit-me", name="Edit Me", price="10.00", category_id=category.id)
    product = app.state.catalog.list_products()[0]

    client.post(
        f"/admin/products/{product.id}/images",
        content=PNG,
        headers={"Content-Type": "image/png", "X-File-Name": "first.png", "X-CSRF-Token": csrf},
    )
    first_image = app.state.catalog.get_product(product.id).images[0]

    updated = client.post(
        f"/admin/products/{product.id}",
        data={
            "csrf": csrf,
            "slug": "edit-me",
            "name_ru": "Edited Name",
            "description_ru": "Edited description",
            "price": "42.50",
            "currency": "MDL",
            "category_id": str(category.id),
            "is_published": "1",
            "attribute_name_0": "Colour",
            "attribute_value_0": "Black",
        },
    )
    assert updated.status_code == 303
    assert "42.50 MDL" in client.get("/product/edit-me").text
    assert "Edited description" in client.get("/product/edit-me").text
    assert "Black" in client.get("/product/edit-me").text

    client.post(
        f"/admin/products/{product.id}/images",
        content=PNG_SECOND,
        headers={"Content-Type": "image/png", "X-File-Name": "second.png", "X-CSRF-Token": csrf},
    )
    assert len(app.state.catalog.get_product(product.id).images) == 2

    removed = client.post(
        f"/admin/products/{product.id}/images/{first_image.id}/delete",
        data={"csrf": csrf},
    )
    assert removed.status_code == 303
    remaining = app.state.catalog.get_product(product.id).images
    assert [image.original_name for image in remaining] == ["second.png"]
    assert client.get(f"/media/{first_image.file_name}").status_code == 404
    assert Path(paths["images_dir"], first_image.file_name).exists() is False


def test_changes_survive_application_restart(client, admin_config, app, paths):
    csrf = _login(client, admin_config)
    _create_category(client, csrf, name="Cameras", slug="cameras")
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="persistent", name="Persistent", price="7.77", category_id=category.id)
    product = app.state.catalog.list_products()[0]
    client.post(
        f"/admin/products/{product.id}/images",
        content=PNG,
        headers={"Content-Type": "image/png", "X-File-Name": "keep.png", "X-CSRF-Token": csrf},
    )
    image = app.state.catalog.get_product(product.id).images[0]
    image_name = image.file_name

    restarted = _open_app(paths, admin_config)
    page = restarted.get("/product/persistent")
    assert page.status_code == 200
    assert "Persistent" in page.text and "7.77 MDL" in page.text
    assert f"/media/{image.detail_name or image_name}" in page.text
    assert restarted.get(f"/media/{image_name}").status_code == 200
    assert restarted.get("/catalog").status_code == 200
    assert "Persistent" in restarted.get("/catalog").text


# --- 7./8. publication and deletion --------------------------------------


def test_unpublished_product_is_hidden_and_can_be_published_again(client, admin_config, app):
    csrf = _login(client, admin_config)
    _create_category(client, csrf)
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="draft-item", name="Draft", price="5.00", category_id=category.id)
    product = app.state.catalog.list_products()[0]

    assert client.post(
        f"/admin/products/{product.id}/publish", data={"csrf": csrf, "published": "0"}
    ).status_code == 303
    assert client.get("/product/draft-item").status_code == 404
    assert "Draft" not in client.get("/catalog").text

    assert client.post(
        f"/admin/products/{product.id}/publish", data={"csrf": csrf, "published": "1"}
    ).status_code == 303
    assert client.get("/product/draft-item").status_code == 200


def test_product_delete_is_safe(client, admin_config, app):
    csrf = _login(client, admin_config)
    _create_category(client, csrf)
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="keep-me", name="Keep", price="1.00", category_id=category.id)
    _create_product(client, csrf, slug="delete-me", name="Delete", price="2.00", category_id=category.id)
    keeper, doomed = app.state.catalog.list_products()
    client.post(
        f"/admin/products/{doomed.id}/images",
        content=PNG,
        headers={"Content-Type": "image/png", "X-File-Name": "gone.png", "X-CSRF-Token": csrf},
    )
    image_name = app.state.catalog.get_product(doomed.id).images[0].file_name

    response = client.post(f"/admin/products/{doomed.id}/delete", data={"csrf": csrf})
    assert response.status_code == 303
    remaining = app.state.catalog.list_products()
    assert [product.slug for product in remaining] == ["keep-me"]
    assert client.get("/product/delete-me").status_code == 404
    assert client.get(f"/media/{image_name}").status_code == 404

    registry_row = app.state.catalog._registry.get("product", "delete-me")  # released history
    assert registry_row is not None and registry_row["state"] == "released"
    assert app.state.catalog.get_product(keeper.id).slug == "keep-me"


def test_category_with_products_cannot_be_deleted_silently(client, admin_config, app):
    csrf = _login(client, admin_config)
    _create_category(client, csrf, name="Cameras", slug="cameras")
    _create_category(client, csrf, name="Tripods", slug="tripods")
    cameras, tripods = app.state.catalog.list_categories()
    _create_product(client, csrf, slug="cam-1", name="Cam 1", price="10.00", category_id=cameras.id)

    refused = client.post(
        f"/admin/categories/{cameras.id}/delete", data={"csrf": csrf, "reassign_to": ""}
    )
    assert refused.status_code == 409
    assert "CATEGORY_IN_USE" in refused.text
    assert len(app.state.catalog.list_products()) == 1
    assert app.state.catalog.get_category(cameras.id).slug == "cameras"

    moved = client.post(
        f"/admin/categories/{cameras.id}/delete",
        data={"csrf": csrf, "reassign_to": str(tripods.id)},
    )
    assert moved.status_code == 303
    product = app.state.catalog.list_products()[0]
    assert product.category_id == tripods.id
    assert product.slug == "cam-1"
    assert client.get("/product/cam-1").status_code == 200
    with pytest.raises(Exception):
        app.state.catalog.get_category(cameras.id)


# --- 9./10./11. uploads and paths ----------------------------------------


def test_upload_validation_rejects_wrong_type_and_size(client, admin_config, app, paths):
    csrf = _login(client, admin_config)
    _create_category(client, csrf)
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="upload-target", name="Target", price="1.00", category_id=category.id)
    product = app.state.catalog.list_products()[0]
    before = sorted(Path(paths["images_dir"]).iterdir())

    wrong_type = client.post(
        f"/admin/products/{product.id}/images",
        content=b"#!/bin/sh\necho not an image\n",
        headers={"Content-Type": "image/png", "X-File-Name": "script.png", "X-CSRF-Token": csrf},
    )
    assert wrong_type.status_code == 400
    assert app.state.catalog.get_product(product.id).images == ()

    oversized = client.post(
        f"/admin/products/{product.id}/images",
        content=PNG + b"x" * (3 * 1024 * 1024),
        headers={"Content-Type": "image/png", "X-File-Name": "huge.png", "X-CSRF-Token": csrf},
    )
    assert oversized.status_code == 400
    assert app.state.catalog.get_product(product.id).images == ()
    assert sorted(Path(paths["images_dir"]).iterdir()) == before, "no file may be left behind"

    generic = client.post(
        f"/admin/products/{product.id}/images",
        content=PNG,
        headers={"Content-Type": "image/png", "X-File-Name": "ok.png", "X-CSRF-Token": csrf},
    )
    assert generic.status_code == 303
    assert len(app.state.catalog.get_product(product.id).images) == 1


def test_safe_names_and_paths(tmp_path):
    store = ImageStore(tmp_path / "images")

    with pytest.raises(InvalidImageName):
        store.path_for("../secret.png")
    with pytest.raises(InvalidImageName):
        store.path_for("not-managed.png")
    with pytest.raises(UnsupportedImageType):
        store.save(b"<html>", original_name="page.png")

    stored = store.save(PNG, original_name="../../etc/passwd.png")
    assert stored.file_name != "../../etc/passwd.png"
    assert "/" not in stored.file_name and ".." not in stored.file_name
    assert stored.original_name == "passwd.png"  # only metadata, never a path
    assert re.match(r"^[0-9a-f]{32}\.png$", stored.file_name)
    assert store.path_for(stored.file_name).is_file()


def test_media_route_rejects_unknown_names(client):
    assert client.get("/media/not-a-managed-name.png").status_code == 404
    assert client.get("/media/" + "a" * 32 + ".png").status_code == 404


# --- 12./13./14./15./16. universality, money, languages, history ---------


def test_demo_seed_never_overwrites_the_user_catalog(client, admin_config, app, paths):
    csrf = _login(client, admin_config)
    _create_category(client, csrf, name="My category", slug="my-category")
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="my-product", name="My product", price="3.33", category_id=category.id)

    assert app.state.catalog.seed_demo_catalog() == 0, "an existing catalog is never overwritten"
    assert len(app.state.catalog.list_products()) == 1
    assert app.state.catalog.list_products()[0].price == Money(minor=333, currency="MDL")
    assert app.state.catalog.list_categories()[0].text("ru").name == "My category"

    fresh = TestClient(
        create_app(
            db_path=str(Path(paths["db_path"]).parent / "seeded.sqlite"),
            backup_dir=paths["backup_dir"],
            images_dir=str(Path(paths["images_dir"]).parent / "seeded-images"),
            admin_config=admin_config,
            seed_demo=True,
        ),
        follow_redirects=False,
    )
    assert fresh.get("/catalog").status_code == 200
    seeded_app_products = fresh.app.state.catalog.list_products()
    assert len(seeded_app_products) == 3
    assert fresh.app.state.catalog.seed_demo_catalog() == 0
    assert len(fresh.app.state.catalog.list_products()) == 3


def test_money_is_exact_and_rejects_float():
    assert Money.parse("19.99", "MDL") == Money(minor=1999, currency="MDL")
    assert Money.parse("0", "MDL").minor == 0
    assert Money.parse(2499.5 if False else "2499.50", "MDL").minor == 249950
    assert Money.parse("10,5", "MDL").minor == 1050
    assert Money(minor=129990, currency="MDL").format() == "1299.90 MDL"
    with pytest.raises(ValidationError):
        Money.parse(19.99, "MDL")  # float input is rejected on purpose
    with pytest.raises(ValidationError):
        Money.parse("abc", "MDL")
    with pytest.raises(ValidationError):
        Money(minor=1, currency="mdl")


def test_invalid_admin_input_is_refused_without_side_effects(client, admin_config, app):
    csrf = _login(client, admin_config)
    _create_category(client, csrf)

    bad_price = client.post(
        "/admin/products/new",
        data={"csrf": csrf, "slug": "bad", "name_ru": "Bad", "price": "abc", "currency": "MDL"},
    )
    assert bad_price.status_code == 400
    empty_name = client.post(
        "/admin/products/new",
        data={"csrf": csrf, "slug": "bad2", "name_ru": "", "price": "1.00", "currency": "MDL"},
    )
    assert empty_name.status_code == 400
    bad_currency = client.post(
        "/admin/products/new",
        data={"csrf": csrf, "slug": "bad3", "name_ru": "Bad 3", "price": "1.00", "currency": "US"},
    )
    assert bad_currency.status_code == 400
    assert app.state.catalog.list_products() == []


def test_multilingual_content_and_configurable_languages(client, admin_config, app):
    csrf = _login(client, admin_config)
    _create_category(client, csrf, name="Камеры", slug="kamery")
    category = app.state.catalog.list_categories()[0]
    response = client.post(
        "/admin/products/new",
        data={
            "csrf": csrf,
            "slug": "multi",
            "category_id": str(category.id),
            "price": "100.00",
            "currency": "MDL",
            "is_published": "1",
            "name_ru": "Камера",
            "description_ru": "Описание",
            "name_en": "Camera",
            "description_en": "Description",
        },
    )
    assert response.status_code == 303
    assert "Камера" in client.get("/product/multi?lang=ru").text
    assert "Camera" in client.get("/product/multi?lang=en").text
    # an unconfigured language falls back to the default one
    assert "Камера" in client.get("/product/multi?lang=de").text

    settings = client.post(
        "/admin/settings",
        data={
            "csrf": csrf,
            "shop_name": "Magazin",
            "shop_description": "",
            "shop_logo": "",
            "contact_email": "shop@example.com",
            "contact_phone": "",
            "contact_address": "",
            "language_code_0": "fr",
            "language_title_0": "Français",
            "language_code_1": "de",
            "language_title_1": "Deutsch",
            "default_language": "de",
        },
    )
    assert settings.status_code == 303
    assert app.state.catalog.get_settings().language_codes == ("fr", "de")
    assert app.state.catalog.get_settings().default_language == "de"
    assert app.state.catalog.get_settings().name == "Magazin"


def test_historical_slug_redirects_to_the_current_one(client, admin_config, app):
    csrf = _login(client, admin_config)
    _create_category(client, csrf)
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="old-slug", name="Renamed", price="9.99", category_id=category.id)
    product = app.state.catalog.list_products()[0]

    renamed = client.post(
        f"/admin/products/{product.id}",
        data={
            "csrf": csrf,
            "slug": "new-slug",
            "category_id": str(category.id),
            "price": "9.99",
            "currency": "MDL",
            "is_published": "1",
        },
    )
    assert renamed.status_code == 303
    assert app.state.catalog.get_product(product.id).slug == "new-slug"

    redirect = client.get("/product/old-slug")
    assert redirect.status_code == 301
    assert redirect.headers["location"] == "/product/new-slug"
    assert client.get("/product/new-slug").status_code == 200


def test_slug_suggestion_helper():
    assert slugify("Camera X100 Pro") == "camera-x100-pro"
    assert slugify("Камера X100") == "kamera-x100"
    assert slugify("  ...  ") == ""


# --- 17+ adapted from the Nursery image pipeline -------------------------


def test_image_presets_generate_variants(client, admin_config, app, paths):
    """Preset derivatives (Nursery ImageService.resize_image + image_presets)."""
    if not HAS_PILLOW:
        pytest.skip("Pillow is required for the preset derivative checks")
    csrf = _login(client, admin_config)
    _create_category(client, csrf)
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="big-photo", name="Big Photo", price="1.00", category_id=category.id)
    product = app.state.catalog.list_products()[0]

    upload = client.post(
        f"/admin/products/{product.id}/images",
        content=_image_bytes(1600, 1200),
        headers={"Content-Type": "image/png", "X-File-Name": "big.png", "X-CSRF-Token": csrf},
    )
    assert upload.status_code == 303, upload.text
    image = app.state.catalog.get_product(product.id).images[0]
    assert image.catalog_name.endswith("_catalog.png")
    assert image.detail_name.endswith("_detail.png")

    catalog_path = Path(paths["images_dir"]) / image.catalog_name
    detail_path = Path(paths["images_dir"]) / image.detail_name
    assert catalog_path.is_file() and detail_path.is_file()
    with PILImage.open(catalog_path) as opened:
        assert opened.size == (IMAGE_PRESETS["catalog"]["width"], IMAGE_PRESETS["catalog"]["height"])
    with PILImage.open(detail_path) as opened:
        assert opened.size == (IMAGE_PRESETS["detail"]["width"], IMAGE_PRESETS["detail"]["height"])

    assert f"/media/{image.catalog_name}" in client.get("/catalog").text
    assert f"/media/{image.detail_name}" in client.get("/product/big-photo").text
    assert client.get(f"/media/{image.catalog_name}").status_code == 200

    # a missing derivative falls back to the stored base file
    catalog_path.unlink()
    fallback = client.get(f"/media/{image.catalog_name}")
    assert fallback.status_code == 200
    assert fallback.content.startswith(b"\x89PNG")


def test_non_decodable_image_is_rejected(client, admin_config, app, paths):
    """Magic bytes alone are not enough: the file must decode (Nursery parity+)."""
    if not HAS_PILLOW:
        pytest.skip("Pillow is required for the decode check")
    csrf = _login(client, admin_config)
    _create_category(client, csrf)
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="fake-photo", name="Fake", price="1.00", category_id=category.id)
    product = app.state.catalog.list_products()[0]
    before = sorted(Path(paths["images_dir"]).iterdir())

    response = client.post(
        f"/admin/products/{product.id}/images",
        content=b"\x89PNG\r\n\x1a\n" + b"not really an image" * 4,
        headers={"Content-Type": "image/png", "X-File-Name": "fake.png", "X-CSRF-Token": csrf},
    )
    assert response.status_code == 400
    assert app.state.catalog.get_product(product.id).images == ()
    assert sorted(Path(paths["images_dir"]).iterdir()) == before


def test_oversized_dimensions_are_rejected(client, admin_config, app):
    if not HAS_PILLOW:
        pytest.skip("Pillow is required to build the wide image")
    csrf = _login(client, admin_config)
    _create_category(client, csrf)
    category = app.state.catalog.list_categories()[0]
    _create_product(client, csrf, slug="wide-photo", name="Wide", price="1.00", category_id=category.id)
    product = app.state.catalog.list_products()[0]

    response = client.post(
        f"/admin/products/{product.id}/images",
        content=_image_bytes(7000, 10),
        headers={"Content-Type": "image/png", "X-File-Name": "wide.png", "X-CSRF-Token": csrf},
    )
    assert response.status_code == 400
    assert app.state.catalog.get_product(product.id).images == ()


def test_default_currency_setting_is_used_by_the_admin_form(client, admin_config, app):
    csrf = _login(client, admin_config)

    saved = client.post(
        "/admin/settings",
        data={
            "csrf": csrf,
            "shop_name": "My Shop",
            "default_currency": "EUR",
            "language_code_0": "ru",
            "language_title_0": "Русский",
            "default_language": "ru",
        },
    )
    assert saved.status_code == 303
    assert app.state.catalog.get_settings().default_currency == "EUR"
    assert 'value="EUR"' in client.get("/admin/products/new").text

    invalid = client.post("/admin/settings", data={"csrf": csrf, "default_currency": "EU"})
    assert invalid.status_code == 400
    assert app.state.catalog.get_settings().default_currency == "EUR"


def test_public_ui_language_switches(client):
    """Adapted from Nursery translations/ui.py + get_ui(lang)."""
    assert "Все категории" in client.get("/catalog?lang=ru").text
    assert "Toate categoriile" in client.get("/catalog?lang=ro").text
    assert "All categories" in client.get("/catalog?lang=en").text
    # an unconfigured language falls back to the default (ru)
    assert "Все категории" in client.get("/catalog?lang=de").text
