"""Phase 3: publishing an incomplete product warns instead of refusing."""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from showcases.videoshop.domain.catalog import CONTENT_LANGUAGES
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app

PASSWORD = "pub-pass"
TOKEN_RE = re.compile(r'name="csrf" value="([^"]+)"')

NAMES = {"en": "Camera", "ru": "Камера", "ro": "Cameră"}
DESCRIPTIONS = {"en": "Body only", "ru": "Только корпус", "ro": "Doar corpul"}
WARNING_TEXT = "Товар опубликован"


def _app(tmp_path):
    (tmp_path / "db").mkdir(exist_ok=True)
    (tmp_path / "backups").mkdir(exist_ok=True)
    return create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner",
            password_hash=hash_password(PASSWORD, iterations=1000),
            secret_key=b"pub",
        ),
    )


def _client(tmp_path):
    return TestClient(_app(tmp_path), follow_redirects=False)


def _login(client) -> str:
    assert client.post(
        "/admin/login", data={"username": "owner", "password": PASSWORD}
    ).status_code == 303
    return TOKEN_RE.search(client.get("/admin").text).group(1)


def _product(
    catalog,
    slug,
    *,
    text_languages=CONTENT_LANGUAGES,
    published=False,
):
    texts = {
        code: {"name": NAMES[code], "description": DESCRIPTIONS[code]}
        for code in text_languages
    }
    attributes = [(code, "Sensor", "APS-C") for code in text_languages]
    product = catalog.create_product(
        slug=slug,
        price="10.00",
        currency="MDL",
        texts=texts,
        attributes=attributes,
        is_published=published,
    )
    # create_product copies a name into the default language; re-save so the
    # requested language set is exact
    if set(product.texts) != set(text_languages):
        product = catalog.update_product(product.id, texts=texts)
    return product


def _publish(client, csrf, product_id, published):
    return client.post(
        f"/admin/products/{product_id}/publish",
        data={"csrf": csrf, "published": published},
    )


def test_complete_product_publishes_without_warning(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    catalog = client.app.state.catalog
    product = _product(catalog, "complete")

    response = _publish(client, csrf, product.id, "1")

    assert response.status_code == 303
    assert response.headers["location"] == f"/admin/products/{product.id}"
    assert catalog.get_product(product.id).is_published is True
    assert WARNING_TEXT not in client.get(f"/admin/products/{product.id}").text


def test_incomplete_product_publishes_with_a_warning(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    catalog = client.app.state.catalog
    product = _product(catalog, "no-ru", text_languages=("en", "ro"))

    response = _publish(client, csrf, product.id, "1")

    # published anyway: a warning, never a refusal
    assert response.status_code == 303
    assert response.headers["location"] == f"/admin/products/{product.id}?missing=ru"
    assert catalog.get_product(product.id).is_published is True

    page = client.get(response.headers["location"]).text
    assert WARNING_TEXT in page
    assert "RU" in page


def test_publishing_does_not_change_product_data(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    catalog = client.app.state.catalog
    product = _product(catalog, "no-ro", text_languages=("en", "ru"))

    before = catalog.get_product(product.id)
    texts_before = dict(before.texts)
    rows_before = before.attribute_rows

    assert _publish(client, csrf, product.id, "1").status_code == 303

    after = catalog.get_product(product.id)
    assert after.is_published is True
    assert dict(after.texts) == texts_before
    assert after.attribute_rows == rows_before


def test_unpublishing_never_warns(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    catalog = client.app.state.catalog
    product = _product(catalog, "hidden", text_languages=("en",), published=True)

    response = _publish(client, csrf, product.id, "0")

    assert response.status_code == 303
    assert response.headers["location"] == f"/admin/products/{product.id}"
    assert catalog.get_product(product.id).is_published is False


def test_already_published_incomplete_product_is_left_alone(tmp_path):
    """Legacy rows are never re-validated: only the switching moment is checked."""
    client = _client(tmp_path)
    csrf = _login(client)
    catalog = client.app.state.catalog
    legacy = _product(catalog, "legacy", text_languages=("en",), published=True)
    texts_before = dict(catalog.get_product(legacy.id).texts)

    # switching another product must not touch the legacy one
    other = _product(catalog, "other")
    assert _publish(client, csrf, other.id, "1").status_code == 303

    still = catalog.get_product(legacy.id)
    assert still.is_published is True
    assert dict(still.texts) == texts_before

    # and the list page keeps it published, with no warning banner of its own
    listing = client.get("/admin/products").text
    assert "legacy" in listing
