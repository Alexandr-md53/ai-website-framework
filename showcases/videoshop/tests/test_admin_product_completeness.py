"""Phase 2: translation completeness indicator and the ``incomplete`` filter."""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from showcases.videoshop.domain.catalog import CONTENT_LANGUAGES
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app

PASSWORD = "tr-pass"
TOKEN_RE = re.compile(r'name="csrf" value="([^"]+)"')

NAMES = {"en": "Camera", "ru": "Камера", "ro": "Cameră"}
DESCRIPTIONS = {"en": "Body only", "ru": "Только корпус", "ro": "Doar corpul"}


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
            secret_key=b"tr",
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
    attribute_languages=CONTENT_LANGUAGES,
    with_description=True,
    name=None,
    category_id=None,
):
    texts = {
        code: {
            "name": name or NAMES[code],
            "description": DESCRIPTIONS[code] if with_description else "",
        }
        for code in text_languages
    }
    attributes = [(code, "Sensor", "APS-C") for code in attribute_languages]
    product = catalog.create_product(
        slug=slug,
        category_id=category_id,
        price="10.00",
        currency="MDL",
        texts=texts,
        attributes=attributes,
        is_published=True,
    )
    # create_product copies a name into the default language, so re-save to make
    # the requested language set exact (the admin form does the same on save)
    if set(product.texts) != set(text_languages):
        product = catalog.update_product(product.id, texts=texts)
    return product


def _badge(status: str, code: str) -> str:
    return 'class="tr-lang %s" data-lang="%s"' % (status, code)


# --- indicator -----------------------------------------------------------


def test_full_product_shows_three_present_badges_without_warnings(tmp_path):
    client = _client(tmp_path)
    _login(client)
    _product(client.app.state.catalog, "full")

    html = client.get("/admin/products").text
    for code in CONTENT_LANGUAGES:
        assert _badge("tr-ok", code) in html
    assert 'class="tr-warn" data-lang="' not in html


def test_missing_ru_is_red_and_the_filter_selects_it(tmp_path):
    client = _client(tmp_path)
    _login(client)
    _product(client.app.state.catalog, "no-ru", text_languages=("en", "ro"))

    html = client.get("/admin/products").text
    assert _badge("tr-ok", "en") in html
    assert _badge("tr-missing", "ru") in html
    assert _badge("tr-ok", "ro") in html

    filtered = client.get("/admin/products?incomplete=1").text
    assert "no-ru" in filtered


def test_missing_ro_is_red_and_the_filter_selects_it(tmp_path):
    client = _client(tmp_path)
    _login(client)
    _product(client.app.state.catalog, "no-ro", text_languages=("en", "ru"))

    html = client.get("/admin/products").text
    assert _badge("tr-missing", "ro") in html
    assert "no-ro" in client.get("/admin/products?incomplete=1").text


def test_missing_attributes_warn_but_do_not_make_the_product_incomplete(tmp_path):
    client = _client(tmp_path)
    _login(client)
    _product(
        client.app.state.catalog,
        "no-ro-attrs",
        attribute_languages=("en", "ru"),
    )

    html = client.get("/admin/products").text
    assert _badge("tr-ok", "ro") in html
    assert 'class="tr-warn" data-lang="ro"' in html
    # attributes are a warning only: the incomplete filter ignores them
    assert "no-ro-attrs" not in client.get("/admin/products?incomplete=1").text


def test_missing_description_warns_but_does_not_make_the_product_incomplete(tmp_path):
    client = _client(tmp_path)
    _login(client)
    _product(client.app.state.catalog, "no-desc", with_description=False)

    html = client.get("/admin/products").text
    assert 'class="tr-warn" data-lang="en"' in html
    assert "no-desc" not in client.get("/admin/products?incomplete=1").text


def test_indicator_shows_three_states_in_one_row(tmp_path):
    client = _client(tmp_path)
    _login(client)
    _product(
        client.app.state.catalog,
        "mixed",
        text_languages=("en", "ro"),
        attribute_languages=("en",),
    )

    html = client.get("/admin/products").text
    assert _badge("tr-ok", "en") in html
    assert _badge("tr-missing", "ru") in html
    assert _badge("tr-ok", "ro") in html
    assert 'class="tr-warn" data-lang="ro"' in html
    assert html.count('class="tr-warn" data-lang="') == 1


# --- source data ---------------------------------------------------------


def test_saving_an_empty_name_removes_the_language_row(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    catalog = client.app.state.catalog
    product = _product(catalog, "row-gone")

    response = client.post(
        f"/admin/products/{product.id}",
        data={
            "csrf": csrf,
            "slug": "row-gone",
            "name_en": NAMES["en"],
            "description_en": DESCRIPTIONS["en"],
            "name_ru": "",
            "description_ru": "",
            "name_ro": NAMES["ro"],
            "description_ro": DESCRIPTIONS["ro"],
            "price": "10.00",
            "currency": "MDL",
            "is_published": "1",
        },
    )
    assert response.status_code == 303
    assert "ru" not in catalog.get_product(product.id).texts
    assert _badge("tr-missing", "ru") in client.get("/admin/products").text


# --- filter --------------------------------------------------------------


def test_filter_combines_with_search_and_category(tmp_path):
    client = _client(tmp_path)
    _login(client)
    catalog = client.app.state.catalog
    first = catalog.create_category(slug="cat-a", texts={"ru": {"name": "A"}})
    second = catalog.create_category(slug="cat-b", texts={"ru": {"name": "B"}})

    _product(catalog, "complete-a", category_id=first.id)
    _product(catalog, "partial-a", text_languages=("en", "ro"),
             name="Partial", category_id=first.id)
    _product(catalog, "partial-b", text_languages=("en", "ro"),
             name="Partial", category_id=second.id)

    every = client.get("/admin/products").text
    assert "complete-a" in every

    incomplete = client.get("/admin/products?incomplete=1").text
    assert "partial-a" in incomplete
    assert "partial-b" in incomplete
    assert "complete-a" not in incomplete

    by_category = client.get(f"/admin/products?incomplete=1&category_id={second.id}").text
    assert "partial-b" in by_category
    assert "partial-a" not in by_category

    by_search = client.get("/admin/products?incomplete=1&q=Partial").text
    assert "partial-a" in by_search and "partial-b" in by_search

    missed = client.get("/admin/products?incomplete=1&q=Nothing").text
    assert "partial-a" not in missed

    # the checkbox keeps its state
    assert 'name="incomplete" value="1" checked' in incomplete


# --- fallback is not completeness ---------------------------------------


def test_fallback_is_not_completeness(tmp_path):
    client = _client(tmp_path)
    _login(client)
    _product(
        client.app.state.catalog,
        "only-en",
        text_languages=("en",),
        attribute_languages=("en",),
    )

    html = client.get("/admin/products").text
    assert _badge("tr-missing", "ru") in html
    assert _badge("tr-missing", "ro") in html

    # the storefront falls back to English, but the indicator stays red
    page = client.get("/product/only-en?lang=ru").text
    assert NAMES["en"] in page
