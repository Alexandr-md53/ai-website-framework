"""Block 3b-1: multilingual product attributes (data + admin)."""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.infrastructure.migrations.catalog import (
    CATALOG_MIGRATIONS,
    CATALOG_VERSION,
    migrate_catalog,
)
from showcases.videoshop.infrastructure.migrations.runner import migrate
from showcases.videoshop.infrastructure.retry import run_transaction_with_retry
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import ATTRIBUTE_SLOTS, create_app

PASSWORD = "attr-pass"
TOKEN_RE = re.compile(r'name="csrf" value="([^"]+)"')


def _app(tmp_path):
    (tmp_path / "db").mkdir(exist_ok=True)
    (tmp_path / "backups").mkdir(exist_ok=True)
    return create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner", password_hash=hash_password(PASSWORD, iterations=1000), secret_key=b"attr"
        ),
    )


def _client(tmp_path):
    return TestClient(_app(tmp_path), follow_redirects=False)


def _login(client) -> str:
    assert client.post("/admin/login", data={"username": "owner", "password": PASSWORD}).status_code == 303
    return TOKEN_RE.search(client.get("/admin").text).group(1)


def _category_and_product(client, csrf) -> int:
    client.post("/admin/categories/new", data={"csrf": csrf, "slug": "c1", "name_ru": "Категория", "is_published": "1"})
    client.post(
        "/admin/products/new",
        data={"csrf": csrf, "slug": "p1", "name_ru": "Товар", "price": "10.00", "currency": "MDL",
              "category_id": "1", "is_published": "1"},
    )
    return 1


def _form(csrf, groups):
    """Table payload: ``groups`` maps a group index to ``{lang: (name, value)}``."""
    data = {"csrf": csrf, "slug": "p1", "name_ru": "Товар", "price": "10.00", "currency": "MDL",
            "category_id": "1", "is_published": "1"}
    for group, cells in groups.items():
        for column, lang in enumerate(TABLE_LANGS):
            index = group * len(TABLE_LANGS) + column
            name, value = cells.get(lang, ("", ""))
            data[f"attribute_lang_{index}"] = lang
            data[f"attribute_name_{index}"] = name
            data[f"attribute_value_{index}"] = value
    return data


# --- migration -----------------------------------------------------------


def test_migration_6_to_7_keeps_data_and_is_idempotent(tmp_path):
    db = tmp_path / "db"
    db.mkdir()
    provider = VideoShopSQLiteProvider(db_path=str(db / "shop.sqlite"))
    steps_to_six = tuple(m for m in CATALOG_MIGRATIONS if m.version <= 6)
    assert migrate(provider, steps_to_six) == 6
    stamp = "2026-01-01T00:00:00+00:00"

    def seed(tx):
        tx.execute(
            "INSERT INTO products (price_minor, currency, is_published, position, created_at, updated_at) "
            "VALUES (1000, 'MDL', 1, 0, ?, ?)",
            (stamp, stamp),
        )
        tx.execute(
            "INSERT INTO product_attributes (product_id, position, name, value) VALUES (1, 0, 'Сенсор', 'APS-C')"
        )

    run_transaction_with_retry(provider, seed)
    assert migrate_catalog(provider) == CATALOG_VERSION
    with provider.read_transaction() as tx:
        assert tx.scalar("PRAGMA user_version") == CATALOG_VERSION
        assert tx.scalar("SELECT lang FROM product_attributes") == ""
        assert tx.scalar("SELECT COUNT(*) FROM product_attributes") == 1
    assert migrate_catalog(provider) == CATALOG_VERSION
    with provider.read_transaction() as tx:
        assert tx.scalar("SELECT COUNT(*) FROM product_attributes") == 1


# --- service level -------------------------------------------------------


def test_create_and_update_keep_languages(tmp_path):
    app = _app(tmp_path)
    catalog = app.state.catalog
    category = catalog.create_category(slug="c1", texts={"ru": {"name": "Категория"}})
    product = catalog.create_product(
        slug="p1", category_id=category.id, price="10.00", currency="MDL",
        texts={"ru": {"name": "Товар"}},
        attributes=[("ru", "Сенсор", "APS-C"), ("ro", "Senzor", "APS-C"), ("en", "Sensor", "APS-C")],
    )
    assert len(product.attribute_rows) == 3
    assert product.attributes_for("ru") == (("Сенсор", "APS-C"),)
    assert product.attributes_for("ro") == (("Senzor", "APS-C"),)
    assert product.attributes_for("en") == (("Sensor", "APS-C"),)

    updated = catalog.update_product(
        product.id, attributes=[("ru", "Сенсор", "Full Frame"), ("en", "Sensor", "Full Frame")]
    )
    assert len(updated.attribute_rows) == 2
    assert updated.attributes_for("ru") == (("Сенсор", "Full Frame"),)
    assert updated.attributes_for("en") == (("Sensor", "Full Frame"),)


def test_fallback_and_dedupe(tmp_path):
    app = _app(tmp_path)
    catalog = app.state.catalog
    category = catalog.create_category(slug="c1", texts={"ru": {"name": "Категория"}})
    product = catalog.create_product(
        slug="p1", category_id=category.id, price="10.00", currency="MDL",
        texts={"ru": {"name": "Товар"}},
        attributes=[("ru", "Сенсор", "APS-C"), ("", "Вес", "480 г")],
    )
    assert product.attributes_for("ru") == (("Сенсор", "APS-C"), ("Вес", "480 г"))
    assert product.attributes_for("ro") == (("Вес", "480 г"),)   # fallback to neutral only
    assert product.attributes_for("en") == (("Вес", "480 г"),)   # no default-language fallback

    deduped = catalog.update_product(
        product.id, attributes=[("ru", "Сенсор", "APS-C"), ("", "Сенсор", "старое")]
    )
    # block 3b-1-fix-TABLE: an update replaces only the localized rows, so the
    # neutral "Вес" row survives; the neutral "Сенсор" row is shadowed by name
    assert deduped.attributes_for("ru") == (("Сенсор", "APS-C"), ("Вес", "480 г"))
    assert ("", "Вес", "480 г") in deduped.attribute_rows
    assert ("", "Сенсор", "старое") in deduped.attribute_rows


def test_product_attributes_pairs_are_compatible(tmp_path):
    from showcases.videoshop.domain.catalog import DEFAULT_LANGUAGE

    app = _app(tmp_path)
    catalog = app.state.catalog
    category = catalog.create_category(slug="c1", texts={"ru": {"name": "Категория"}})
    product = catalog.create_product(
        slug="p1", category_id=category.id, price="10.00", currency="MDL",
        texts={"ru": {"name": "Товар"}},
        attributes=[("ru", "Сенсор", "APS-C"), ("", "Вес", "480 г")],
    )
    assert product.attributes == product.attributes_for(DEFAULT_LANGUAGE)


# --- admin form: 12 groups x (en, ru, ro) --------------------------------

TABLE_LANGS = ("en", "ru", "ro")
TABLE_ROWS = 12


def test_form_renders_table_of_12_groups_and_3_languages(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    product_id = _category_and_product(client, csrf)
    form = client.get(f"/admin/products/{product_id}").text
    assert ATTRIBUTE_SLOTS == 48
    assert form.count('name="attribute_lang_') == TABLE_ROWS * len(TABLE_LANGS) == 36
    assert form.count('name="attribute_name_') == 36
    assert form.count('name="attribute_value_') == 36
    # the language belongs to the column, not to a per-row select
    assert 'name="attribute_lang_0" value="en"' in form
    assert 'name="attribute_lang_1" value="ru"' in form
    assert 'name="attribute_lang_2" value="ro"' in form
    assert 'name="attribute_lang_35" value="ro"' in form
    assert 'select name="attribute_lang_' not in form
    assert "attrs-table" in form


def test_save_copies_master_into_empty_translations(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    product_id = _category_and_product(client, csrf)
    catalog = client.app.state.catalog

    assert client.post(
        f"/admin/products/{product_id}",
        data=_form(csrf, {0: {"en": ("Sensor", "APS-C")}}),
    ).status_code == 303
    rows = catalog.get_product(product_id).attribute_rows
    assert rows == (
        ("en", "Sensor", "APS-C"),
        ("ru", "Sensor", "APS-C"),
        ("ro", "Sensor", "APS-C"),
    )


def test_save_keeps_explicit_translations(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    product_id = _category_and_product(client, csrf)
    catalog = client.app.state.catalog

    client.post(
        f"/admin/products/{product_id}",
        data=_form(csrf, {0: {"en": ("Sensor", "APS-C"), "ru": ("Сенсор", "APS-C"),
                              "ro": ("Senzor", "APS-C")}}),
    )
    product = catalog.get_product(product_id)
    assert product.attributes_for("en") == (("Sensor", "APS-C"),)
    assert product.attributes_for("ru") == (("Сенсор", "APS-C"),)
    assert product.attributes_for("ro") == (("Senzor", "APS-C"),)


def test_empty_master_column_drops_the_group(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    product_id = _category_and_product(client, csrf)
    catalog = client.app.state.catalog

    client.post(
        f"/admin/products/{product_id}",
        data=_form(csrf, {0: {"ru": ("Сенсор", "APS-C")}}),
    )
    assert catalog.get_product(product_id).attribute_rows == ()


def test_save_does_not_delete_language_neutral_rows(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    product_id = _category_and_product(client, csrf)
    catalog = client.app.state.catalog
    catalog.update_product(product_id, attributes=[("", "Вес", "480 г")])

    client.post(
        f"/admin/products/{product_id}",
        data=_form(csrf, {0: {"en": ("Sensor", "APS-C")}}),
    )
    rows = catalog.get_product(product_id).attribute_rows
    assert ("", "Вес", "480 г") in rows
    assert ("en", "Sensor", "APS-C") in rows


def test_guard_refuses_more_than_12_rows_per_language(tmp_path):
    client = _client(tmp_path)
    csrf = _login(client)
    product_id = _category_and_product(client, csrf)
    catalog = client.app.state.catalog

    catalog.update_product(
        product_id, attributes=[("en", f"e{index}", "1") for index in range(13)]
    )
    assert len(catalog.get_product(product_id).attribute_rows) == 13

    response = client.post(
        f"/admin/products/{product_id}",
        data=_form(csrf, {0: {"en": ("Sensor", "APS-C")}}),
    )
    assert response.status_code == 400
    assert "Слишком много характеристик" in response.text
    # nothing was deleted
    assert len(catalog.get_product(product_id).attribute_rows) == 13


def test_attributes_for_falls_back_to_master_language(tmp_path):
    app = _app(tmp_path)
    catalog = app.state.catalog
    category = catalog.create_category(slug="c1", texts={"ru": {"name": "Категория"}})
    product = catalog.create_product(
        slug="p1", category_id=category.id, price="10.00", currency="MDL",
        texts={"ru": {"name": "Товар"}},
        attributes=[("en", "Sensor", "APS-C")],
    )
    assert product.attributes_for("ro") == (("Sensor", "APS-C"),)
    assert product.attributes_for("ru") == (("Sensor", "APS-C"),)
    assert product.attributes_for("en") == (("Sensor", "APS-C"),)
