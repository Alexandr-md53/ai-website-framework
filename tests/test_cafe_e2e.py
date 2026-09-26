"""
Cafe E2E v0.1 — Type C runnable, mirrors docs_site E2E pattern
- frozen route map smoke
- generation pipeline G1/G2: category → item → publish → SEO → generate → verify html
- stock invariants OUT_OF_STOCK / INSUFFICIENT_STOCK
- order lifecycle DRAFT → VALIDATED → CONFIRMED → CANCELLED (restore)
- second consumer uses same frozen framework primitives
"""

from fastapi.testclient import TestClient
from pathlib import Path
import tempfile

from showcases.cafe.app_factory import create_app, FROZEN_ROUTES
from showcases.cafe.services.cafe_menu_service import CafeMenuService
from ai_framework.rendering.jinja import JinjaTemplateRenderer
from ai_framework.rendering.seo import SeoInjector, SeoContext
from ai_framework.rendering.generated_page import GeneratedPage
from ai_framework.rendering.static_writer import StaticSiteWriter
from ai_framework.content.slug import Slug


def test_frozen_route_map_smoke():
    service = CafeMenuService()
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(service=service, out_dir=tmp)
        # collect actual routes
        actual = set()
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for m in route.methods:
                    if m in ("GET", "POST", "PATCH", "PUT", "DELETE"):
                        actual.add((m, route.path))
        frozen = set(FROZEN_ROUTES)
        missing = frozen - actual
        assert not missing, f"Missing frozen routes: {missing}"


def test_cafe_generation_pipeline_G1_G2():
    service = CafeMenuService()
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(service=service, out_dir=tmp)
        client = TestClient(app)

        # create category
        r = client.post("/menu/categories", json={"name": "Coffee", "slug": "coffee"})
        assert r.status_code == 200, r.text
        cat_id = r.json()["id"]

        # create item with stock=2, description >=10
        r = client.post(
            "/menu/items",
            json={
                "title": "Latte",
                "slug": "latte",
                "description": "Creamy latte with milk foam and espresso shot",
                "price": "4.50",
                "category_id": cat_id,
                "stock_quantity": 2,
                "dietary_tags": ["vegetarian"],
            },
        )
        assert r.status_code == 200, r.text
        item_id = r.json()["id"]
        assert r.json()["is_published"] is False

        # publish
        r = client.post(f"/menu/items/{item_id}/publish")
        assert r.status_code == 200, r.text
        assert r.json()["is_published"] is True

        # SEO
        r = client.patch(
            f"/menu/items/{item_id}/seo",
            json={
                "seo_title": "Cafe Latte SEO Title",
                "seo_description": "Best latte in town",
                "canonical_url": "/menu/coffee/latte/",
            },
        )
        assert r.status_code == 200
        assert r.json()["seo"]["seo_title"] == "Cafe Latte SEO Title"

        # public read
        r = client.get("/public/menu/latte")
        assert r.status_code == 200
        assert r.json()["slug"] == "latte"

        # generate site
        r = client.post("/site/generate")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["generated"] >= 4

        # verify FS contract
        out = Path(tmp)
        assert (out / "index.html").exists()
        assert (out / "menu" / "index.html").exists()
        assert (out / "menu" / "coffee" / "index.html").exists()
        assert (out / "menu" / "coffee" / "latte" / "index.html").exists()
        assert (out / "sitemap.xml").exists()

        # verify html contains title per minimal template
        html = (out / "menu" / "coffee" / "latte" / "index.html").read_text(
            encoding="utf-8"
        )
        assert "Latte" in html or "latte" in html
        assert "/menu/coffee/latte/" in html or "latte" in html.lower()

        # unpublish hides
        r = client.post(f"/menu/items/{item_id}/unpublish")
        assert r.status_code == 200
        r = client.get("/public/menu/latte")
        assert r.status_code == 404

        # re-publish for order tests
        client.post(f"/menu/items/{item_id}/publish")

        # Order lifecycle
        r = client.post(
            "/orders", json={"lines": [{"menu_item_id": item_id, "quantity": 1}]}
        )
        assert r.status_code == 200, r.text
        order_id = r.json()["id"]
        assert r.json()["total"] == "4.50"
        assert r.json()["status"] == "DRAFT"

        r = client.post(f"/orders/{order_id}/validate")
        assert r.status_code == 200
        assert r.json()["status"] == "VALIDATED"

        r = client.post(f"/orders/{order_id}/confirm")
        assert r.status_code == 200
        assert r.json()["status"] == "CONFIRMED"

        r = client.get(f"/menu/items/{item_id}")
        assert r.json()["stock_quantity"] == 1

        r = client.post(
            "/orders", json={"lines": [{"menu_item_id": item_id, "quantity": 2}]}
        )
        assert r.status_code == 400
        assert "INSUFFICIENT_STOCK" in r.text

        r = client.post(f"/orders/{order_id}/cancel")
        assert r.status_code == 200
        assert r.json()["status"] == "CANCELLED"
        r = client.get(f"/menu/items/{item_id}")
        assert r.json()["stock_quantity"] == 2

        r = client.post(
            "/menu/items",
            json={
                "title": "Espresso",
                "slug": "espresso",
                "description": "Strong espresso shot single origin",
                "price": "3.00",
                "category_id": cat_id,
                "stock_quantity": 0,
            },
        )
        espresso_id = r.json()["id"]
        client.post(f"/menu/items/{espresso_id}/publish")
        r = client.post(
            "/orders", json={"lines": [{"menu_item_id": espresso_id, "quantity": 1}]}
        )
        assert r.status_code == 400
        assert "OUT_OF_STOCK" in r.text


def test_second_consumer_uses_same_framework_primitives():
    s = Slug("latte")
    assert str(s) == "latte"
    try:
        Slug("bad/slug")
        assert False, "should have raised"
    except ValueError:
        pass

    tmpl_dir = Path("showcases/cafe/templates")
    renderer = JinjaTemplateRenderer(
        str(tmpl_dir)
        if tmpl_dir.exists()
        else str(Path(__file__).parent.parent / "showcases" / "cafe" / "templates")
    )
    injector = SeoInjector()
    seo_ctx = SeoContext(
        seo_title="Test",
        seo_description="desc",
        og_title="Test",
        og_description="desc",
        canonical_url="/test/",
        title="Test",
    )
    html = "<html><head></head><body>hi</body></html>"
    injected = injector.ensure_seo(html, seo_ctx)
    assert isinstance(injected, str)

    page = GeneratedPage(
        path="menu/coffee/latte/index.html", html="<html>latte</html>", kind="item"
    )
    assert page.path == "menu/coffee/latte/index.html"

    writer = StaticSiteWriter()
    assert hasattr(writer, "write")
    # also ensure it is callable
    assert callable(getattr(writer, "write"))
