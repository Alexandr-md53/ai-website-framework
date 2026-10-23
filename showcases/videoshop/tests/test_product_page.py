"""Block 3b-2: public product page (attributes, breadcrumbs, related)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app
from showcases.videoshop.web.i18n import UI

PASSWORD = "page-pass"


def _app(tmp_path):
    (tmp_path / "db").mkdir(exist_ok=True)
    (tmp_path / "backups").mkdir(exist_ok=True)
    return create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner", password_hash=hash_password(PASSWORD, iterations=1000), secret_key=b"page"
        ),
    )


def _client(tmp_path):
    return TestClient(_app(tmp_path), follow_redirects=False)


def _seed(client, attributes, *, category="cameras", slug="p1", name="Товар"):
    catalog = client.app.state.catalog
    cat = catalog.create_category(slug=category, texts={"ru": {"name": category}})
    product = catalog.create_product(
        slug=slug, category_id=cat.id, price="10.00", currency="MDL", is_published=True,
        texts={"ru": {"name": name}}, attributes=attributes,
    )
    return cat, product


def test_attributes_are_rendered_per_language(tmp_path):
    client = _client(tmp_path)
    _seed(client, [("ru", "Сенсор", "APS-C"), ("ro", "Senzor", "APS-C"), ("en", "Sensor", "APS-C")])
    ru = client.get("/product/p1?lang=ru").text
    ro = client.get("/product/p1?lang=ro").text
    en = client.get("/product/p1?lang=en").text
    assert "Сенсор" in ru and "Senzor" not in ru
    assert "Senzor" in ro and "Сенсор" not in ro
    assert "Sensor" in en
    assert 'class="specs"' in ru


def test_neutral_attribute_is_a_fallback(tmp_path):
    client = _client(tmp_path)
    _seed(client, [("", "Вес", "480 г")])
    for lang in ("ru", "ro", "en"):
        body = client.get(f"/product/p1?lang={lang}").text
        assert "Вес" in body and "480 г" in body


def test_no_attributes_means_no_specs_block(tmp_path):
    client = _client(tmp_path)
    _seed(client, [])
    body = client.get("/product/p1").text
    assert 'class="specs"' not in body


def test_breadcrumbs_order_links_and_current(tmp_path):
    client = _client(tmp_path)
    _seed(client, [])
    body = client.get("/product/p1?lang=ro").text
    assert 'class="crumbs"' in body
    assert 'aria-label="breadcrumb"' in body
    start = body.index('<nav class="crumbs"')
    nav = body[start:body.index("</nav>", start)]
    home = nav.index(UI["ro"]["breadcrumb_home"])
    catalog = nav.index(UI["ro"]["breadcrumb_catalog"])
    current = nav.index('aria-current="page"')
    assert home < catalog < current
    assert 'href="/?lang=ro"' in body
    assert 'href="/catalog?lang=ro"' in body
    assert 'href="/catalog?category=cameras&lang=ro"' in body


def test_related_shows_same_category_excluding_current(tmp_path):
    client = _client(tmp_path)
    catalog = client.app.state.catalog
    cat = catalog.create_category(slug="cameras", texts={"ru": {"name": "Камеры"}})
    other = catalog.create_category(slug="light", texts={"ru": {"name": "Свет"}})
    target = catalog.create_product(slug="p1", category_id=cat.id, price="1.00", currency="MDL", is_published=True,
                                    texts={"ru": {"name": "Целевой"}})
    catalog.create_product(slug="p2", category_id=cat.id, price="1.00", currency="MDL", is_published=True,
                           texts={"ru": {"name": "Сосед"}})
    catalog.create_product(slug="p3", category_id=other.id, price="1.00", currency="MDL", is_published=True,
                           texts={"ru": {"name": "Другая категория"}})
    body = client.get("/product/p1").text
    assert UI["ru"]["related_title"] in body
    assert "Сосед" in body and "Другая категория" not in body
    assert "Целевой" in body  # the title itself, but not as a related card link


def test_related_is_absent_when_alone(tmp_path):
    client = _client(tmp_path)
    _seed(client, [])
    body = client.get("/product/p1").text
    assert 'class="related"' not in body


def test_related_limit_is_four(tmp_path):
    client = _client(tmp_path)
    catalog = client.app.state.catalog
    cat = catalog.create_category(slug="cameras", texts={"ru": {"name": "Камеры"}})
    catalog.create_product(slug="p0", category_id=cat.id, price="1.00", currency="MDL", is_published=True,
                           texts={"ru": {"name": "Целевой"}})
    for index in range(6):
        catalog.create_product(slug=f"n{index}", category_id=cat.id, price="1.00", currency="MDL", is_published=True,
                               texts={"ru": {"name": f"Сосед{index}"}})
    body = client.get("/product/p0").text
    related_block = body[body.index('class="related"'):]
    assert related_block.count('class="card-p"') == 4


def test_i18n_keys_and_css_present(tmp_path):
    for lang in ("ru", "ro", "en"):
        for key in ("breadcrumb_home", "breadcrumb_catalog", "breadcrumb_category", "related_title"):
            assert UI[lang][key], (lang, key)
    assert len({UI[lang]["related_title"] for lang in ("ru", "ro", "en")}) == 3
    body = _client(tmp_path).get("/").text
    assert "@media(max-width:560px)" in body
    assert ".specs tr{display:block" in body
    assert ".thumbs{display:grid;grid-template-columns:1fr}" in body
