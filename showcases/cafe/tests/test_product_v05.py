"""
Café v0.5 Product Slice - Acceptance Tests (10 tests)
Must prove:
- / , /menu, /about exist and contain real cafe content
- SEO, bakery, 150 MDL
- language reuse, not competing i18n
- dist/cafe_site generation
"""
import pathlib, sys
import pytest

from showcases.cafe.product_app import render_page, HAS_LANGUAGE_SERVICE
from showcases.cafe.content.cafe_info import CAFE_IDENTITY, MENU

def test_product_app_uses_language_service_or_mirrors_contract():
    from showcases.cafe.product_app import resolve_language
    assert resolve_language(visitor_lang="en", admin_lang="ru") == "ru"
    assert resolve_language(visitor_lang="en", admin_lang=None) == "en"

def test_index_contains_real_content_ru():
    data = render_page("index", "ru")
    html = data["html"]
    assert CAFE_IDENTITY["name"] in html
    assert "150 MDL" in html
    assert "bakery" in html.lower() or "пекарня" in html.lower()

def test_index_contains_real_content_en():
    data = render_page("index", "en")
    html = data["html"]
    assert CAFE_IDENTITY["name"] in html
    assert "150 MDL" in html

def test_menu_contains_prices_and_bakery():
    data = render_page("menu", "ru")
    html = data["html"]
    assert "MDL" in html
    assert "25 MDL" in html or "28 MDL" in html

def test_about_contains_about_info():
    data_ru = render_page("about", "ru")
    data_en = render_page("about", "en")
    assert "пекарня" in data_ru["html"].lower() or "семейная" in data_ru["html"].lower()
    assert "bakery" in data_en["html"].lower() or "family" in data_en["html"].lower()

def test_seo_metadata_present():
    for page in ["index","menu","about"]:
        for lang in ["ru","en"]:
            data = render_page(page, lang)
            assert data["title"]
            assert data["description"]
            assert "description" in data["html"].lower()

def test_menu_prices_150_mdl_average_check():
    data = render_page("index", "ru")
    assert "150" in data["html"]
    assert any(it.price_mdl < 150 for it in MENU)

def test_generated_site_structure():
    from showcases.cafe.site_generator import generate, DIST
    dist = generate()
    assert dist.exists()
    assert (dist / "index.html").exists()
    assert (dist / "ru" / "index.html").exists()
    assert (dist / "en" / "index.html").exists()
    assert (dist / "ru" / "menu.html").exists()
    assert (dist / "ru" / "about.html").exists()
    content = (dist / "index.html").read_text(encoding="utf-8")
    assert CAFE_IDENTITY["name"] in content
    assert "150 MDL" in content

def test_product_app_routes():
    from showcases.cafe.product_app import create_product_app
    app = create_product_app()
    if app is None:
        pytest.skip("FastAPI not installed")
    from fastapi.testclient import TestClient
    client = TestClient(app)
    for path in ["/", "/menu", "/about"]:
        r = client.get(path)
        assert r.status_code == 200
        assert CAFE_IDENTITY["name"] in r.text
        assert "MDL" in r.text

def test_no_framework_changes():
    import pathlib
    fw = pathlib.Path("ai_framework")
    if not fw.exists():
        pytest.skip("ai_framework not present")
    for py in fw.rglob("*.py"):
        txt = py.read_text(encoding="utf-8", errors="ignore")
        assert "cafe_info" not in txt
        assert "150 MDL" not in txt
